"""Entrada CLI; execute a partir da raiz do projeto."""

import argparse
import logging
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
import config
from elas_ti.genderize_client import GenderizeError
from elas_ti.pipeline import run


def main(argv=None):
    parser = argparse.ArgumentParser(description="ELAS-TI")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument(
        "--graphs", action="store_true", help="Menu local de gráficos Matplotlib"
    )
    modes.add_argument(
        "--dry-run", action="store_true", help="Extrair e auditar sem API"
    )
    modes.add_argument(
        "--export-site",
        action="store_true",
        help="Exportar snapshot local como JSON/CSV agregados para o site, sem API",
    )
    modes.add_argument("--validate", action="store_true", help="Validar PDFs sem API")
    modes.add_argument(
        "--rebuild-reports",
        action="store_true",
        help="Reconstruir do snapshot local sem PDFs/API",
    )
    modes.add_argument(
        "--match-cohorts",
        action="store_true",
        help="Analisar coortes usando apenas cache",
    )
    parser.add_argument(
        "--no-api", action="store_true", help="Usar apenas predições em cache"
    )
    parser.add_argument(
        "--verbose", action="store_true", help="Log operacional, sem nomes/chaves"
    )
    parser.add_argument("--pdf-root", type=Path, default=Path("pdfs"))
    parser.add_argument("--output-dir", type=Path, default=Path("output"))
    parser.add_argument("--site-data-dir", type=Path, default=Path("site/data"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("elas_ti").setLevel(
        logging.DEBUG if args.verbose else logging.INFO
    )
    try:
        if args.export_site:
            from elas_ti.public_export import export_site

            return export_site(args.output_dir, args.site_data_dir)
        if args.graphs:
            from elas_ti.plot_menu import run_menu

            return run_menu(args.output_dir)
        return run(args, config)
    except GenderizeError as error:
        print(str(error), file=sys.stderr)
        return 2
    except ValueError:
        print(
            "Dados ou configuração inválidos; verifique o snapshot, cache e config.py.",
            file=sys.stderr,
        )
        return 2
    except (OSError, sqlite3.Error):
        print(
            "Falha de leitura/gravação local; verifique caminhos e permissões.",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
