"""Endpoints públicos: cuestionario y envío del diagnóstico gratuito."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import (
    Company,
    Contact,
    Diagnostic,
    DiagnosticAnswer,
    Interaction,
    InteractionType,
    PipelineStage,
    utcnow,
)
from app.schemas import DiagnosticResult, DiagnosticSubmission, PackageOut
from app.services import maturity
from app.services.questionnaire import QUESTIONNAIRE_VERSION, questionnaire_as_dict

router = APIRouter(prefix="/api/public", tags=["Diagnóstico público"])
settings = get_settings()


@router.get("/questionnaire")
def get_questionnaire() -> dict:
    return questionnaire_as_dict()


@router.get("/packages", response_model=list[PackageOut])
def get_packages() -> list[PackageOut]:
    return [PackageOut(code=p, **info) for p, info in maturity.PACKAGE_INFO.items()]


def _upsert_company(db: Session, data) -> Company:
    company = None
    if data.nit:
        company = db.scalar(select(Company).where(Company.nit == data.nit))
    if company is None:
        company = Company(**data.model_dump())
        db.add(company)
    else:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(company, field, value)
        if company.stage == PipelineStage.PERDIDO:
            company.stage = PipelineStage.NUEVO  # Re-activación del lead
    db.flush()
    return company


def _upsert_contact(db: Session, company: Company, data, submission, ip: str | None) -> Contact:
    contact = db.scalar(
        select(Contact).where(Contact.company_id == company.id, Contact.email == data.email)
    )
    if contact is None:
        contact = Contact(company_id=company.id, **data.model_dump())
        db.add(contact)
    else:
        for field, value in data.model_dump().items():
            setattr(contact, field, value)
    # Registro de la autorización (prueba del consentimiento - Ley 1581 de 2012)
    contact.data_consent = True
    contact.consent_at = utcnow()
    contact.consent_policy_version = settings.privacy_policy_version
    contact.consent_ip = ip
    contact.marketing_consent = submission.marketing_consent
    db.flush()
    return contact


@router.post("/diagnostics", response_model=DiagnosticResult, status_code=status.HTTP_201_CREATED)
def submit_diagnostic(
    submission: DiagnosticSubmission, request: Request, db: Session = Depends(get_db)
) -> DiagnosticResult:
    try:
        result = maturity.evaluate(
            submission.answers, submission.company.sector, submission.company.employees
        )
    except maturity.InvalidAnswersError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    ip = request.client.host if request.client else None
    company = _upsert_company(db, submission.company)
    contact = _upsert_contact(db, company, submission.contact, submission, ip)

    diagnostic = Diagnostic(
        company_id=company.id,
        contact_id=contact.id,
        questionnaire_version=QUESTIONNAIRE_VERSION,
        total_score=result.total_score,
        maturity_level=result.maturity_level,
        recommended_package=result.recommended_package,
        dimension_scores=result.dimension_scores,
        recommendations=result.recommendations,
        answers=[
            DiagnosticAnswer(
                question_code=a.question_code,
                dimension=a.dimension,
                option_value=a.option_value,
                points=a.points,
            )
            for a in result.answers
        ],
    )
    db.add(diagnostic)

    package_info = maturity.PACKAGE_INFO[result.recommended_package]
    db.add(
        Interaction(
            company_id=company.id,
            type=InteractionType.SISTEMA,
            summary=(
                f"Diagnóstico completado por {contact.full_name}: puntaje {result.total_score}, "
                f"nivel {maturity.LEVEL_LABELS[result.maturity_level]}, "
                f"recomendado {package_info['name']}."
            ),
        )
    )
    db.commit()

    return DiagnosticResult(
        diagnostic_id=diagnostic.id,
        company_name=company.name,
        sector=company.sector,
        total_score=result.total_score,
        maturity_level=result.maturity_level,
        maturity_label=maturity.LEVEL_LABELS[result.maturity_level],
        dimension_scores=result.dimension_scores,
        recommendations=result.recommendations,
        recommended_package=PackageOut(code=result.recommended_package, **package_info),
    )
