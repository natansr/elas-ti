from dataclasses import dataclass, field


@dataclass
class StudentRecord:
    tipo_registro: str
    arquivo: str
    pagina: int
    numero_sequencial: int
    curso_original: str
    curso_normalizado: str
    ano: int
    semestre: int
    periodo: str
    nome_original: str
    nome_normalizado: str
    nome_chave: str
    turno: str | None = None
    tipo_ingresso: str | None = None
    motivo_entrada: str | None = None
    genderize_gender: str | None = None
    genderize_probability: float | None = None
    genderize_count: int | None = None
    p_female: float | None = None
    p_male: float | None = None
    confidence_class: str = "não identificado"


@dataclass
class DocumentResult:
    arquivo: str
    tipo_registro: str | None = None
    records: list[StudentRecord] = field(default_factory=list)
    registros_brutos: int = 0
    total_pdf: int | None = None
    needs_ocr: bool = False
    warnings: list[str] = field(default_factory=list)
    review: list[dict] = field(default_factory=list)

    @property
    def registros_unicos(self) -> int:
        return len(self.records)

    @property
    def duplicacoes_removidas(self) -> int:
        return self.registros_brutos - self.registros_unicos

    @property
    def status(self) -> str:
        return "WARNING" if self.warnings or self.needs_ocr else "OK"
