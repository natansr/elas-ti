"""Configurações científicas e operacionais do ELAS-TI."""

PROJECT_NAME = "ELAS-TI"
COUNTRY_ID = "BR"
GENDERIZE_NAME_MODE = "full"
GENDERIZE_BATCH_SIZE = 100
HIGH_CONFIDENCE = 0.90
MEDIUM_CONFIDENCE = 0.75
MONTE_CARLO_ITERATIONS = 100000
RANDOM_SEED = 42
MIN_FOLLOWUP_SEMESTERS = None
COURSES_OF_INTEREST = []
COURSE_ALIASES = {}

# Reduz exposição em gráficos e resumos; não garante anonimato por si só.
MIN_GROUP_SIZE = 5
