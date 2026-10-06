import pytest

from app.models import MaturityLevel, Package, Sector
from app.services import maturity
from app.services.questionnaire import QUESTIONS
from tests.conftest import answers_with


def test_sector_weights_sum_to_one():
    for sector, weights in maturity.SECTOR_WEIGHTS.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-9, sector
        assert set(weights) == set(maturity.DIMENSIONS)


def test_all_questions_have_valid_points():
    for q in QUESTIONS:
        assert q.dimension in maturity.DIMENSIONS
        assert all(0 <= o.points <= 4 for o in q.options)
        assert max(o.points for o in q.options) == 4


def test_lowest_answers_give_zero_and_basic_package():
    r = maturity.evaluate(answers_with(0), Sector.COMERCIO, employees=10)
    assert r.total_score == 0
    assert r.maturity_level == MaturityLevel.INICIAL
    assert r.recommended_package == Package.BASICO
    assert len(r.recommendations) == maturity.MAX_RECOMMENDATIONS


def test_highest_answers_give_100_and_premium():
    r = maturity.evaluate(answers_with(3), Sector.SERVICIOS, employees=20)
    assert r.total_score == 100
    assert r.maturity_level == MaturityLevel.AVANZADO
    assert r.recommended_package == Package.PREMIUM
    assert "sólida" in r.recommendations[0]


@pytest.mark.parametrize(
    "score,level",
    [(0, MaturityLevel.INICIAL), (29.9, MaturityLevel.INICIAL),
     (30, MaturityLevel.EN_DESARROLLO), (54.9, MaturityLevel.EN_DESARROLLO),
     (55, MaturityLevel.INTERMEDIO), (74.9, MaturityLevel.INTERMEDIO),
     (75, MaturityLevel.AVANZADO), (100, MaturityLevel.AVANZADO)],
)
def test_level_thresholds(score, level):
    assert maturity.classify_level(score) == level


def test_medium_company_never_gets_basic():
    assert maturity.recommend_package(MaturityLevel.INICIAL, 50) == Package.INTEGRAL
    assert maturity.recommend_package(MaturityLevel.INICIAL, 49) == Package.BASICO


def test_micro_company_premium_is_adjusted_to_integral():
    assert maturity.recommend_package(MaturityLevel.AVANZADO, 5) == Package.INTEGRAL
    assert maturity.recommend_package(MaturityLevel.AVANZADO, 6) == Package.PREMIUM


def test_sector_weighting_changes_score():
    # Solo fuerte en gestión/operaciones: pesa más en manufactura que en comercio
    answers = answers_with(0)
    for q in QUESTIONS:
        if q.dimension == "gestion_operaciones":
            answers[q.code] = q.options[3].value
    manu = maturity.evaluate(answers, Sector.MANUFACTURA, 10).total_score
    com = maturity.evaluate(answers, Sector.COMERCIO, 10).total_score
    assert manu == 30.0 and com == 10.0


def test_recommendations_prioritize_sector_relevant_gaps():
    r = maturity.evaluate(answers_with(0), Sector.COMERCIO, 10)
    # En comercio, comercio electrónico (peso 0.25) es la brecha más importante
    assert r.recommendations[0] == maturity.DIMENSION_RECOMMENDATIONS["comercio_electronico"]


def test_missing_answers_raise():
    answers = answers_with(1)
    answers.pop(QUESTIONS[0].code)
    with pytest.raises(maturity.InvalidAnswersError, match="Faltan"):
        maturity.evaluate(answers, Sector.COMERCIO, 10)


def test_invalid_option_raises():
    answers = answers_with(1)
    answers[QUESTIONS[0].code] = "inventada"
    with pytest.raises(maturity.InvalidAnswersError, match="no válida"):
        maturity.evaluate(answers, Sector.COMERCIO, 10)


def test_unknown_question_raises():
    answers = answers_with(1) | {"pregunta_x": "a"}
    with pytest.raises(maturity.InvalidAnswersError, match="desconocidas"):
        maturity.evaluate(answers, Sector.COMERCIO, 10)
