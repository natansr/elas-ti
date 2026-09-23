"""Confere os arquivos que compõem o site antes da publicação."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from elas_ti.public_schema import validate_directory

if __name__ == "__main__":
    try:
        count = validate_directory(
            Path(sys.argv[1]) if len(sys.argv) > 1 else Path("site")
        )
    except (ValueError, TypeError, KeyError, OSError):
        print("Site inválido: confira o esquema público e os arquivos em site/.")
        raise SystemExit(1) from None
    print(f"Site validado: {count} agregados; JSON e CSV consistentes.")
