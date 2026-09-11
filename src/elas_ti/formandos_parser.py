from .parser_utils import parse_pages


def parse_formandos(pages: list[str], filename: str = "sintetico.pdf", aliases=None):
    return parse_pages(pages, filename, "concluinte", aliases)
