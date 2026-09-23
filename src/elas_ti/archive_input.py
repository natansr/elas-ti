"""PDFs avulsos e 7z locais, com extração temporária e sem alterar originais."""

import hashlib
from contextlib import contextmanager
from pathlib import Path, PurePosixPath, PureWindowsPath
from tempfile import TemporaryDirectory

import py7zr

from .pdf_reader import discover_pdfs

MAX_UNCOMPRESSED = 1024 * 1024 * 1024  # 1 GiB por arquivo 7z


class ArchiveInputError(ValueError):
    """Mensagem operacional sem nomes de arquivos ou conteúdo dos documentos."""


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").digest()


def validate_members(members):
    seen = set()
    total = 0
    for member in members:
        name = member.filename
        path = PurePosixPath(name)
        if (
            not name
            or path.is_absolute()
            or PureWindowsPath(name).drive
            or "\\" in name
            or ".." in path.parts
            or ":" in name
            or any(ord(c) < 32 for c in name)
            or not (member.is_file or member.is_directory)
            or member.is_symlink
        ):
            raise ArchiveInputError(
                "Arquivo 7z com caminhos ou tipos de entrada não permitidos."
            )
        key = str(path).casefold()
        if key in seen:
            raise ArchiveInputError("Arquivo 7z com caminhos internos repetidos.")
        seen.add(key)
        total += member.uncompressed or 0
    if total > MAX_UNCOMPRESSED:
        raise ArchiveInputError("Arquivo 7z excede o limite de 1 GiB descompactado.")


@contextmanager
def prepared_pdfs(root: Path, workdir: Path):
    """Mantém os PDFs extraídos apenas durante a leitura, dentro da saída privada."""
    paths = discover_pdfs(root)
    archives = sorted(
        p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".7z"
    )
    if not archives:
        yield paths
        return
    fingerprints = {digest(path) for path in paths}
    duplicates = 0
    with TemporaryDirectory(prefix="extracao_7z_", dir=workdir) as temporary:
        for index, path in enumerate(archives, 1):
            destination = Path(temporary) / str(index)
            destination.mkdir(mode=0o700)
            try:
                with py7zr.SevenZipFile(
                    path, "r", max_extract_size=MAX_UNCOMPRESSED
                ) as archive:
                    if archive.needs_password():
                        raise ArchiveInputError(
                            "Arquivo 7z protegido por senha; descompacte-o localmente antes da análise."
                        )
                    members = archive.list()
                    validate_members(members)
                    targets = [
                        m.filename
                        for m in members
                        if m.is_file and Path(m.filename).suffix.lower() == ".pdf"
                    ]
                    if not targets:
                        raise ArchiveInputError(
                            "Arquivo 7z sem PDFs; confira o conteúdo antes da análise."
                        )
                    for target in targets:
                        (destination / target).parent.mkdir(parents=True, exist_ok=True)
                    archive.extract(path=destination, targets=targets, recursive=False)
                for target in targets:
                    extracted = destination / target
                    if extracted.is_symlink() or not extracted.resolve().is_relative_to(
                        destination.resolve()
                    ):
                        raise ArchiveInputError("Extração 7z com destino inválido.")
                    extracted.chmod(0o600)
                    fingerprint = digest(extracted)
                    if fingerprint in fingerprints:
                        duplicates += 1
                    else:
                        fingerprints.add(fingerprint)
                        paths.append(extracted)
            except ArchiveInputError as error:
                raise ArchiveInputError(f"Compactado {index}: {error}") from None
            except Exception:
                # Erros da biblioteca podem conter nomes ou caminhos sensíveis.
                raise ArchiveInputError(
                    f"Compactado {index}: não foi possível extrair os PDFs; arquivo corrompido, incompleto ou incompatível."
                ) from None
        print(
            f"Arquivos 7z processados: {len(archives)}; cópias idênticas de PDFs ignoradas: {duplicates}."
        )
        yield paths
