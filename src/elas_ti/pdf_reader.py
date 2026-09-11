from pathlib import Path

import pymupdf

from .models import DocumentResult
from .parser_utils import parse_pages
from .name_normalizer import name_key


def read_pdf(path: Path, aliases=None) -> DocumentResult:
    try:
        with pymupdf.open(path) as pdf:
            pages = [page.get_text(sort=True) for page in pdf]
    except Exception:
        return DocumentResult(str(path), warnings=["Não foi possível abrir o PDF (corrompido, protegido ou inacessível)."])
    text = name_key(" ".join(pages))
    entrant = "RELACAO DE ALUNOS INGRESSANTES" in text
    graduate = "RELACAO DE ALUNOS PARA COLACAO DE GRAU" in text
    if entrant == graduate:
        return DocumentResult(str(path), needs_ocr=not text,
                              warnings=["Tipo de documento ausente ou ambíguo."])
    return parse_pages(pages, str(path), "ingressante" if entrant else "concluinte", aliases)


def discover_pdfs(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")
