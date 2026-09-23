import logging
import os
import platform
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

from dotenv import load_dotenv

from .cache import GenderCache
from .genderize_client import GenderizeClient, apply_prediction
from .models import DocumentResult, StudentRecord
from .name_normalizer import name_key
from .pdf_reader import discover_pdfs, read_pdf
from .privacy import load_snapshot, pseudonymize_payload, write_snapshot
from .reports import audit_documents, generate_reports


def protect_output(output: Path):
    project = Path(__file__).resolve().parents[2]
    resolved = output.resolve()
    if resolved == project or any(
        resolved.is_relative_to(project / p)
        for p in ("src", "tests", ".git", ".github", "site")
    ):
        raise ValueError("Diretório de saída reservado ao código")
    output.mkdir(parents=True, exist_ok=True)
    marker = output / ".gitignore"
    if marker.exists() and "*" not in marker.read_text(encoding="utf-8").splitlines():
        raise ValueError("Diretório de saída não está integralmente ignorado pelo Git")
    if not marker.exists():
        marker.write_text("*\n", encoding="utf-8")


def detect_document_overlap(documents):
    seen = {}
    for d in documents:
        for r in d.records:
            identity = (
                r.tipo_registro,
                r.curso_normalizado,
                r.periodo,
                r.numero_sequencial,
                r.nome_chave,
            )
            if identity in seen:
                other = seen[identity]
                warning = "Possível relatório repetido entre arquivos; resolver sobreposição antes da análise."
                for doc in (d, other):
                    if warning not in doc.warnings:
                        doc.warnings.append(warning)
            else:
                seen[identity] = d


def save_snapshot(records, documents, output, settings):
    payload = {
        "schema_version": 1,
        "python_version": platform.python_version(),
        "dependencies": {
            p: version(p)
            for p in ("PyMuPDF", "requests", "python-dotenv", "numpy", "matplotlib")
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "settings": {k: getattr(settings, k) for k in dir(settings) if k.isupper()},
        "records": [asdict(r) for r in records],
        "documents": [asdict(d) for d in documents],
    }
    write_snapshot(pseudonymize_payload(payload), output / "registros_snapshot.json")


def rebuild(output: Path, settings):
    from types import SimpleNamespace

    path = output / "registros_snapshot.json"
    if not path.exists():
        raise ValueError(
            "Snapshot local ausente; execute primeiro a análise normal ou --no-api."
        )
    try:
        payload = load_snapshot(output)
        records = [StudentRecord(**r) for r in payload["records"]]
        documents = []
        for item in payload["documents"]:
            item["records"] = [StudentRecord(**r) for r in item["records"]]
            documents.append(DocumentResult(**item))
        snapshot_settings = SimpleNamespace(**payload["settings"])
        snapshot_settings.MIN_GROUP_SIZE = max(
            getattr(snapshot_settings, "MIN_GROUP_SIZE", 5),
            getattr(settings, "MIN_GROUP_SIZE", 5),
        )
    except (ValueError, TypeError, KeyError):
        raise ValueError(
            "Snapshot inválido ou incompatível; gere novamente a análise."
        ) from None
    audit_documents(documents, output)
    generate_reports(records, documents, output, snapshot_settings)
    print(
        f"Relatórios reconstruídos do snapshot local: {len(records)} registros; nenhuma chamada à API."
    )
    return 0


def run(args, settings):
    protect_output(args.output_dir)
    if args.rebuild_reports:
        return rebuild(args.output_dir, settings)
    documents = [
        read_pdf(p, settings.COURSE_ALIASES) for p in discover_pdfs(args.pdf_root)
    ]
    logging.getLogger(__name__).debug("Documentos localizados: %d", len(documents))
    detect_document_overlap(documents)
    print(audit_documents(documents, args.output_dir))
    if not documents:
        print("Nenhum PDF disponível; não há resultados científicos a estimar.")
    warnings = any(d.status != "OK" for d in documents)
    if args.dry_run or args.validate:
        return 1 if warnings else 0
    if any(d.blocking for d in documents):
        print(
            "Análise interrompida: revise validacao_pdfs.txt antes de consultar a API ou agregar os registros."
        )
        return 1
    records = [r for d in documents for r in d.records]
    if settings.COURSES_OF_INTEREST:
        courses = {name_key(c) for c in settings.COURSES_OF_INTEREST}
        records = [r for r in records if name_key(r.curso_normalizado) in courses]
    if records:
        load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        # O log de urllib3 em DEBUG inclui a query string com chave e nomes.
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        with GenderCache(Path("cache/genderize.sqlite")) as cache:
            client = GenderizeClient(
                cache,
                os.getenv("GENDERIZE_API_KEY"),
                settings.COUNTRY_ID,
                settings.GENDERIZE_NAME_MODE,
                settings.GENDERIZE_BATCH_SIZE,
            )
            predictions = client.lookup(
                [r.nome_normalizado for r in records],
                no_api=args.no_api or args.match_cohorts,
            )
            for r in records:
                apply_prediction(
                    r,
                    predictions[r.nome_normalizado],
                    settings.HIGH_CONFIDENCE,
                    settings.MEDIUM_CONFIDENCE,
                )
    save_snapshot(records, documents, args.output_dir, settings)
    generate_reports(records, documents, args.output_dir, settings)
    print(
        f"Saídas locais geradas: {len(records)} registros; relatórios agregados sem nomes."
    )
    return 0
