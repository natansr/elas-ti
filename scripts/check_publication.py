"""Verificação preventiva de dados/credenciais versionados (não substitui revisão)."""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from elas_ti.public_schema import validate_csv, validate_data

PATTERNS = [
    rb"gh[pousr]_[A-Za-z0-9]{20,}",
    rb"github_pat_[A-Za-z0-9_]{30,}",
    rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    rb"(?im)^GENDERIZE_API_KEY\s*=\s*[\"']?[A-Za-z0-9_-]{16,}",
]


def blocked_path(path):
    p = PurePosixPath(path)
    if path == "site/data/resumo.csv":
        return False
    if "pdfs" in p.parts and p.name != ".gitkeep":
        return True
    return (
        p.name.startswith(".env")
        and p.name != ".env.example"
        or p.suffix.lower() in {".pdf", ".csv", ".sqlite", ".db", ".key"}
        or any(part in {"cache", "output", ".venv"} for part in p.parts)
        or p.name == "registros_snapshot.json"
    )


def git(*args):
    return subprocess.check_output(["git", *args])


def check(history=False):
    entries = []
    if history:
        for commit in git("rev-list", "--all").decode().splitlines():
            for line in git("ls-tree", "-r", "-z", commit).split(b"\0"):
                if line:
                    info, path = line.split(b"\t", 1)
                    entries.append((path.decode(), info.split()[2].decode()))
    else:
        for line in git("ls-files", "--stage", "-z").split(b"\0"):
            if line:
                info, path = line.split(b"\t", 1)
                entries.append((path.decode(), info.split()[1].decode()))
    failures, inspected = set(), set()
    for path, blob in entries:
        if blocked_path(path):
            failures.add(f"Arquivo privado versionado: {path}")
        if path in {"site/data/resumo.json", "site/data/resumo.csv"}:
            try:
                public = git("cat-file", "blob", blob).decode("utf-8-sig")
                if path.endswith(".json"):
                    validate_data(json.loads(public))
                else:
                    validate_csv(public)
            except (ValueError, TypeError, KeyError):
                failures.add(f"Exportação pública inválida: {path} ({blob[:12]})")
        if blob not in inspected:
            content = git("cat-file", "blob", blob)
            if any(re.search(pattern, content) for pattern in PATTERNS):
                failures.add(
                    f"Possível credencial em objeto Git {blob[:12]} (conteúdo omitido)"
                )
            inspected.add(blob)
    for failure in sorted(failures):
        print(failure)
    print(
        f"Objetos examinados: {len(inspected)}; problemas detectados: {len(failures)}."
    )
    return bool(failures)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--history", action="store_true", help="Verificar todo o histórico local"
    )
    raise SystemExit(check(parser.parse_args().history))
