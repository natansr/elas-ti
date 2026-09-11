"""Entrada CLI; execute a partir da raiz do projeto."""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import config
from elas_ti.pdf_reader import discover_pdfs, read_pdf
from elas_ti.reports import audit_documents


def main(argv=None):
    parser = argparse.ArgumentParser(description="ELAS-TI")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--pdf-root", type=Path, default=Path("pdfs"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    documents = [read_pdf(p, config.COURSE_ALIASES) for p in discover_pdfs(args.pdf_root)]
    print(audit_documents(documents, args.output_dir))
    if not documents:
        print("Nenhum PDF disponível; não há resultados científicos a estimar.")
    return 1 if any(d.status != "OK" for d in documents) else 0


if __name__ == "__main__":
    raise SystemExit(main())
