"""Extração conservadora: linhas sem fronteira segura não viram registros."""

import re
import unicodedata
from collections import defaultdict

from .models import HOMONYM_WARNING, DocumentResult, StudentRecord
from .name_normalizer import name_key, normalize_name

PERIOD = re.compile(r"ANO/SEMESTRE\s*:\s*(\d{4})\s*/\s*([12])(?!\d)", re.I)
GRAD_PERIOD = re.compile(
    r"CONCLUINTES\s+NO\s+ANO/SEMESTRE\s*:\s*(\d{4})\s*/\s*([12])(?!\d)", re.I
)
SHIFT = r"(?:NOTURNO|MATUTINO|VESPERTINO|INTEGRAL|DIURNO)"
ENTRY = r"(?:Vestibular|SISU|ENEM|SAS|Graduado|Transferência(?:\s+(?:Interna|Externa))?|Portador de Diploma|Reingresso|Reingresso Especial|Processo Seletivo)"


def valid_name(value):
    return (
        bool(value)
        and value == value.upper()
        and all(
            c.isalpha() or unicodedata.category(c) == "Mn" or c in " .'-’"
            for c in value
        )
    )


def wrapped_graduate_name(lines, index, sequence):
    """Nome em duas linhas, acima/abaixo da sequência e do turno centralizados."""
    if index < 2 or index + 2 >= len(lines):
        return ""
    before = re.match(r"^(\d+)\s+", lines[index - 2])
    after = re.match(r"^(\d+)\s+", lines[index + 2])
    fragments = [lines[index - 1], lines[index + 1]]
    if (
        before
        and after
        and int(before[1]) == sequence - 1
        and int(after[1]) == sequence + 1
        and all(valid_name(part) for part in fragments)
        and not any(re.search(r"\b" + SHIFT + r"\b", part, re.I) for part in fragments)
    ):
        return " ".join(fragments)
    return ""


def parse_pages(
    pages: list[str], filename: str, kind: str, aliases: dict | None = None
) -> DocumentResult:
    result = DocumentResult(filename, kind)
    course = None
    period = None
    totals, subtotals = set(), set()
    aliases = {name_key(k): name_key(v) for k, v in (aliases or {}).items()}
    for page_number, text in enumerate(pages, 1):
        if not text.strip():
            result.needs_ocr = True
            result.warnings.append(
                f"Página {page_number} sem texto pesquisável; requer inspeção/OCR."
            )
            continue
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for i, line in enumerate(lines):
            found = (GRAD_PERIOD if kind == "concluinte" else PERIOD).search(line)
            if "ANO/SEMESTRE" in line.upper() and not found:
                course = period = None
                result.warnings.append(
                    f"Página {page_number}: período inválido; contexto descartado."
                )
            if found:
                period = (int(found[1]), int(found[2]))
                candidate = lines[i - 1] if i else ""
                # O curso está imediatamente antes do período nos relatórios suportados.
                if candidate and not re.search(
                    r"RELAÇÃO|UNIVERSIDADE|UNIDADE|^\d|ANO/SEMESTRE|Página",
                    candidate,
                    re.I,
                ):
                    course = re.sub(r"^CURSO\s*:\s*", "", candidate, flags=re.I)
                else:
                    course = None
                    result.warnings.append(
                        f"Página {page_number}: curso não identificado no cabeçalho."
                    )
            total = re.search(r"^Total\s*:\s*(\d+)\s*$", line, re.I)
            subtotal = re.search(
                r"^Subtotal de matriculados\s*:\s*(\d+)\s*$", line, re.I
            )
            if total:
                totals.add(int(total[1]))
            if subtotal:
                subtotals.add(int(subtotal[1]))
            row = re.match(r"^(\d+)\s+(.+)$", line)
            if not row:
                if re.fullmatch(r"\d+", line):
                    result.warnings.append(
                        f"Página {page_number}: sequência isolada; layout exige revisão."
                    )
                continue
            if not course or not period:
                result.warnings.append(
                    f"Página {page_number}, linha {i + 1}: registro sem cabeçalho seguro."
                )
                continue
            payload = row[2]
            entry = (
                re.search(r"\b" + ENTRY + r"\b", payload, re.I)
                if kind == "ingressante"
                else None
            )
            shift = re.search(r"\b(" + SHIFT + r")\b", payload, re.I)
            boundary = entry if kind == "ingressante" else shift
            if boundary is None:
                result.warnings.append(
                    f"Página {page_number}, sequência {row[1]}: colunas não reconhecidas."
                )
                continue
            original = payload[: boundary.start()].rstrip()
            if not original and kind == "concluinte":
                original = wrapped_graduate_name(lines, i, int(row[1]))
            if not valid_name(original):
                result.warnings.append(
                    f"Página {page_number}, sequência {row[1]}: nome não delimitado com segurança."
                )
                continue
            year, semester = period
            result.records.append(
                StudentRecord(
                    tipo_registro=kind,
                    arquivo=filename,
                    pagina=page_number,
                    numero_sequencial=int(row[1]),
                    curso_original=course,
                    curso_normalizado=aliases.get(name_key(course), name_key(course)),
                    ano=year,
                    semestre=semester,
                    periodo=f"{year}/{semester}",
                    nome_original=original,
                    nome_normalizado=normalize_name(original),
                    nome_chave=name_key(original),
                    turno=shift[0].upper() if shift else None,
                    tipo_ingresso=entry[0] if entry else None,
                )
            )
    result.registros_brutos = len(result.records)
    unique = {}
    for r in result.records:
        identity = (
            r.tipo_registro,
            r.arquivo,
            r.curso_normalizado,
            r.periodo,
            r.numero_sequencial,
            r.nome_chave,
        )
        if identity in unique and (
            unique[identity].turno,
            unique[identity].tipo_ingresso,
        ) != (r.turno, r.tipo_ingresso):
            result.warnings.append(
                "Repetição com atributos divergentes; revisar documento."
            )
        unique.setdefault(identity, r)
    result.records = list(unique.values())
    sequences = defaultdict(set)
    for r in result.records:
        sequences[(r.curso_normalizado, r.periodo, r.numero_sequencial)].add(
            r.nome_chave
        )
    if any(len(names) > 1 for names in sequences.values()):
        result.warnings.append(
            "Mesma sequência com nomes divergentes; revisar documento."
        )
    names = defaultdict(list)
    for r in result.records:
        names[(r.curso_normalizado, r.periodo, r.nome_chave)].append(r)
    for group in names.values():
        if len(group) > 1:
            result.warnings.append(HOMONYM_WARNING)
            for r in group:
                result.review.append(
                    {
                        "arquivo": filename,
                        "pagina": r.pagina,
                        "numero_sequencial": r.numero_sequencial,
                        "motivo": "homônimo",
                        "nome_chave": r.nome_chave,
                    }
                )
    candidates = totals or subtotals
    if len(candidates) == 1:
        result.total_pdf = next(iter(candidates))
        if result.total_pdf != result.registros_unicos:
            result.warnings.append(
                f"Total divergente: extraídos={result.registros_unicos}, total_pdf={result.total_pdf}."
            )
    elif candidates:
        result.warnings.append(
            "Múltiplos totais distintos; validação global não é segura."
        )
    if not result.records:
        result.warnings.append("Nenhum registro extraído.")
    return result
