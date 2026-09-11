from .parser_utils import parse_pages


def parse_ingressantes(pages: list[str], filename: str = "sintetico.pdf", aliases=None):
    return parse_pages(pages, filename, "ingressante", aliases)
