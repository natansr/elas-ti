import re


def period_index(period: str) -> int:
    match = re.fullmatch(r"(\d{4})/([12])", period)
    if not match:
        raise ValueError(f"Período inválido: {period}")
    return int(match[1]) * 2 + int(match[2]) - 1


def semester_difference(start: str, end: str) -> int:
    return period_index(end) - period_index(start)
