"""Motor de evaluación de madurez digital y recomendación de paquete.

Algoritmo (configurable):
1. Puntaje por dimensión (0-100) = puntos obtenidos / puntos máximos.
2. Puntaje total (0-100) = promedio ponderado por dimensión según el SECTOR
   (p.ej. el comercio electrónico pesa más en "comercio"; la gestión en "manufactura").
3. Nivel de madurez por umbrales del puntaje total.
4. Paquete recomendado según nivel, ajustado por tamaño de la empresa.
5. Recomendaciones priorizadas sobre las dimensiones más débiles.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models import MaturityLevel, Package, Sector
from app.services.questionnaire import (
    DIMENSIONS,
    MAX_POINTS_PER_QUESTION,
    QUESTIONS,
    QUESTIONS_BY_CODE,
)

# Pesos por sector (cada fila suma 1.0)
SECTOR_WEIGHTS: dict[Sector, dict[str, float]] = {
    Sector.COMERCIO: {
        "presencia_web": 0.15,
        "redes_sociales": 0.20,
        "comercio_electronico": 0.25,
        "marketing_digital": 0.20,
        "gestion_operaciones": 0.10,
        "datos_analitica": 0.10,
    },
    Sector.SERVICIOS: {
        "presencia_web": 0.20,
        "redes_sociales": 0.20,
        "comercio_electronico": 0.10,
        "marketing_digital": 0.20,
        "gestion_operaciones": 0.15,
        "datos_analitica": 0.15,
    },
    Sector.MANUFACTURA: {
        "presencia_web": 0.20,
        "redes_sociales": 0.10,
        "comercio_electronico": 0.10,
        "marketing_digital": 0.15,
        "gestion_operaciones": 0.30,
        "datos_analitica": 0.15,
    },
}

# Umbrales de nivel (límite superior exclusivo)
LEVEL_THRESHOLDS: list[tuple[float, MaturityLevel]] = [
    (30.0, MaturityLevel.INICIAL),
    (55.0, MaturityLevel.EN_DESARROLLO),
    (75.0, MaturityLevel.INTERMEDIO),
    (float("inf"), MaturityLevel.AVANZADO),
]

LEVEL_TO_PACKAGE: dict[MaturityLevel, Package] = {
    MaturityLevel.INICIAL: Package.BASICO,
    MaturityLevel.EN_DESARROLLO: Package.INTEGRAL,
    MaturityLevel.INTERMEDIO: Package.PREMIUM,
    MaturityLevel.AVANZADO: Package.PREMIUM,
}

MEDIUM_COMPANY_EMPLOYEES = 50   # Empresas medianas necesitan al menos el Integral
MICRO_COMPANY_EMPLOYEES = 5     # Microempresas: Premium se ajusta a Integral (presupuesto)
WEAK_DIMENSION_THRESHOLD = 75.0
MAX_RECOMMENDATIONS = 3

PACKAGE_INFO: dict[Package, dict[str, str]] = {
    Package.BASICO: {
        "name": "Impulso Básico",
        "description": "Presencia digital esencial: sitio web adaptable, Perfil de Empresa "
        "en Google, configuración de redes sociales y WhatsApp Business.",
    },
    Package.INTEGRAL: {
        "name": "Impulso Integral",
        "description": "Todo lo del Básico más tienda en línea / pasarela de pagos, "
        "estrategia de contenidos y campañas de publicidad digital.",
    },
    Package.PREMIUM: {
        "name": "Impulso Premium",
        "description": "Transformación avanzada: automatización de marketing, integración "
        "CRM/ERP, tableros de analítica y acompañamiento estratégico continuo.",
    },
}

LEVEL_LABELS: dict[MaturityLevel, str] = {
    MaturityLevel.INICIAL: "Inicial",
    MaturityLevel.EN_DESARROLLO: "En desarrollo",
    MaturityLevel.INTERMEDIO: "Intermedio",
    MaturityLevel.AVANZADO: "Avanzado",
}

DIMENSION_RECOMMENDATIONS: dict[str, str] = {
    "presencia_web": "Cree o renueve su sitio web adaptable a móviles y complete su Perfil "
    "de Empresa en Google para que nuevos clientes lo encuentren.",
    "redes_sociales": "Defina un calendario de contenidos y migre la atención a WhatsApp "
    "Business con catálogo y respuestas rápidas.",
    "comercio_electronico": "Habilite la venta en línea con una tienda propia y una pasarela "
    "de pagos (PSE / tarjetas) para vender 24/7.",
    "marketing_digital": "Inicie campañas de publicidad segmentada con presupuesto definido "
    "y mida su retorno; active campañas de recompra a clientes actuales.",
    "gestion_operaciones": "Adopte facturación electrónica y un CRM para centralizar la "
    "información de clientes, inventario y ventas.",
    "datos_analitica": "Instale herramientas de analítica y construya un tablero de "
    "indicadores clave para tomar decisiones basadas en datos.",
}


class InvalidAnswersError(ValueError):
    """Respuestas incompletas o con opciones inexistentes."""


@dataclass
class ScoredAnswer:
    question_code: str
    dimension: str
    option_value: str
    points: int


@dataclass
class EvaluationResult:
    total_score: float
    maturity_level: MaturityLevel
    recommended_package: Package
    dimension_scores: dict[str, float]
    recommendations: list[str]
    answers: list[ScoredAnswer] = field(default_factory=list)


def score_answers(answers: dict[str, str]) -> list[ScoredAnswer]:
    """Valida y puntúa las respuestas {question_code: option_value}."""
    missing = [q.code for q in QUESTIONS if q.code not in answers]
    if missing:
        raise InvalidAnswersError(f"Faltan respuestas para: {', '.join(missing)}")

    unknown = [code for code in answers if code not in QUESTIONS_BY_CODE]
    if unknown:
        raise InvalidAnswersError(f"Preguntas desconocidas: {', '.join(unknown)}")

    scored: list[ScoredAnswer] = []
    for q in QUESTIONS:
        value = answers[q.code]
        option = next((o for o in q.options if o.value == value), None)
        if option is None:
            raise InvalidAnswersError(f"Opción '{value}' no válida para la pregunta '{q.code}'")
        scored.append(ScoredAnswer(q.code, q.dimension, option.value, option.points))
    return scored


def compute_dimension_scores(scored: list[ScoredAnswer]) -> dict[str, float]:
    totals = {d: 0 for d in DIMENSIONS}
    counts = {d: 0 for d in DIMENSIONS}
    for a in scored:
        totals[a.dimension] += a.points
        counts[a.dimension] += 1
    return {
        d: round(100.0 * totals[d] / (counts[d] * MAX_POINTS_PER_QUESTION), 1) if counts[d] else 0.0
        for d in DIMENSIONS
    }


def compute_total_score(dimension_scores: dict[str, float], sector: Sector) -> float:
    weights = SECTOR_WEIGHTS[sector]
    return round(sum(dimension_scores[d] * w for d, w in weights.items()), 1)


def classify_level(total_score: float) -> MaturityLevel:
    for upper, level in LEVEL_THRESHOLDS:
        if total_score < upper:
            return level
    return MaturityLevel.AVANZADO  # pragma: no cover


def recommend_package(level: MaturityLevel, employees: int) -> Package:
    package = LEVEL_TO_PACKAGE[level]
    if employees >= MEDIUM_COMPANY_EMPLOYEES and package == Package.BASICO:
        package = Package.INTEGRAL
    if employees <= MICRO_COMPANY_EMPLOYEES and package == Package.PREMIUM:
        package = Package.INTEGRAL
    return package


def build_recommendations(dimension_scores: dict[str, float], sector: Sector) -> list[str]:
    """Prioriza dimensiones débiles por brecha ponderada con la importancia del sector."""
    weights = SECTOR_WEIGHTS[sector]
    weak = [d for d, s in dimension_scores.items() if s < WEAK_DIMENSION_THRESHOLD]
    weak.sort(key=lambda d: (100 - dimension_scores[d]) * weights[d], reverse=True)
    recs = [DIMENSION_RECOMMENDATIONS[d] for d in weak[:MAX_RECOMMENDATIONS]]
    if not recs:
        recs = [
            "Su madurez digital es sólida. Le recomendamos automatizar procesos y "
            "explorar analítica predictiva para seguir creciendo."
        ]
    return recs


def evaluate(answers: dict[str, str], sector: Sector, employees: int) -> EvaluationResult:
    scored = score_answers(answers)
    dimension_scores = compute_dimension_scores(scored)
    total = compute_total_score(dimension_scores, sector)
    level = classify_level(total)
    return EvaluationResult(
        total_score=total,
        maturity_level=level,
        recommended_package=recommend_package(level, employees),
        dimension_scores=dimension_scores,
        recommendations=build_recommendations(dimension_scores, sector),
        answers=scored,
    )
