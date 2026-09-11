import re
import unicodedata


def normalize_name(name: str) -> str:
    return " ".join(unicodedata.normalize("NFC", name).split())


def name_key(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).upper()
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w\s]|_", " ", text).split())
