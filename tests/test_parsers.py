import pytest

from elas_ti.formandos_parser import parse_formandos
from elas_ti.ingressantes_parser import parse_ingressantes
from elas_ti.name_normalizer import name_key, normalize_name
from elas_ti.utils import period_index, semester_difference

ENTRANTS = """RELAÇÃO DE ALUNOS INGRESSANTES
ENGENHARIA DE SOFTWARE
ANO/SEMESTRE : 2019 / 1
Aluno Tipo de Ingresso Motivo de Entrada Cota Turno
1 ANA TESTE SILVA Vestibular VESTIBULAR NOTURNO
2 JOAO EXEMPLO SOUZA Vestibular VESTIBULAR NOTURNO
Subtotal de matriculados: 2
Total: 2
"""
GRADS = """RELAÇÃO DE ALUNOS PARA COLAÇÃO DE GRAU
ENGENHARIA DE SOFTWARE
CONCLUINTES NO ANO/SEMESTRE: 2025/2
Seq. Nome do Discente Turno Assinatura
1 ANA TESTE SILVA NOTURNO
"""


def test_ingressantes_and_repetitions():
    result = parse_ingressantes([ENTRANTS, ENTRANTS], "arbitrario.pdf")
    assert result.registros_brutos == 4
    assert result.registros_unicos == 2
    assert result.duplicacoes_removidas == 2
    assert result.status == "OK"
    r = result.records[0]
    assert (r.periodo, r.curso_original, r.turno) == (
        "2019/1",
        "ENGENHARIA DE SOFTWARE",
        "NOTURNO",
    )
    assert r.nome_original == "ANA TESTE SILVA"
    assert r.tipo_ingresso == "Vestibular"
    assert r.motivo_entrada is None


def test_graduates():
    r = parse_formandos([GRADS]).records[0]
    assert (r.periodo, r.tipo_registro, r.numero_sequencial) == (
        "2025/2",
        "concluinte",
        1,
    )


def test_homonyms_kept():
    result = parse_ingressantes(
        [ENTRANTS.replace("JOAO EXEMPLO SOUZA", "ANA TESTE SILVA")]
    )
    assert result.registros_unicos == 2
    assert len(result.review) == 2
    assert result.status == "WARNING"


def test_total_mismatch():
    assert (
        parse_ingressantes([ENTRANTS.replace("Total: 2", "Total: 3")]).status
        == "WARNING"
    )


def test_empty_page_needs_ocr():
    assert parse_ingressantes([""]).needs_ocr


def test_unknown_column_is_not_invented():
    result = parse_ingressantes([ENTRANTS.replace("Vestibular", "Desconhecido")])
    assert not result.records
    assert result.status == "WARNING"


def test_normalization():
    assert name_key("JÚLIO CÉSAR TESTE") == name_key("JULIO CESAR TESTE")
    assert normalize_name("  ANA   TE\u0301STE ") == "ANA TÉSTE"
    assert name_key("ANA-TESTE, SILVA") == "ANA TESTE SILVA"


@pytest.mark.parametrize("end,expected", [("2019/2", 1), ("2020/1", 2), ("2020/2", 3)])
def test_semesters(end, expected):
    assert semester_difference("2019/1", end) == expected


def test_period_order_and_invalid():
    assert sorted(["2020/1", "2019/2", "2019/1"], key=period_index) == [
        "2019/1",
        "2019/2",
        "2020/1",
    ]
    with pytest.raises(ValueError):
        period_index("2020/3")


def test_alias_and_continuation_page():
    result = parse_ingressantes(
        [ENTRANTS, "3 MARIA DEMONSTRACAO LIMA Vestibular VESTIBULAR NOTURNO"],
        aliases={"Engenharia de Software": "Computação"},
    )
    assert result.records[-1].curso_normalizado == "COMPUTACAO"
    assert result.records[-1].pagina == 2
    assert result.status == "WARNING"  # O total 2 não valida os 3 registros.


def test_invalid_period_and_split_sequence_are_flagged():
    assert not parse_ingressantes([ENTRANTS.replace("2019 / 1", "2019 / 12")]).records
    assert (
        parse_ingressantes([ENTRANTS + "3\nMARIA DEMONSTRACAO LIMA"]).status
        == "WARNING"
    )
