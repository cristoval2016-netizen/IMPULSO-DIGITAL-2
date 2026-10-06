"""Dashboard comercial: métricas de conversión y exportación del dataset para ML."""
from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import get_settings
from app.database import get_db
from app.models import Company, Diagnostic, PipelineStage, User
from app.schemas import DashboardMetrics
from app.security import require_admin, require_staff
from app.services.questionnaire import DIMENSIONS, QUESTIONS

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])
settings = get_settings()


def _latest_diagnostics_subquery():
    return select(func.max(Diagnostic.id)).group_by(Diagnostic.company_id).scalar_subquery()


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(db: Session = Depends(get_db), _: User = Depends(require_staff)) -> DashboardMetrics:
    active_company = Company.is_deleted.is_(False)
    total_companies = db.scalar(select(func.count(Company.id)).where(active_company)) or 0
    total_diagnostics = db.scalar(
        select(func.count(Diagnostic.id)).join(Company, Company.id == Diagnostic.company_id).where(active_company)
    ) or 0
    diagnosed = db.scalar(
        select(func.count(func.distinct(Diagnostic.company_id))).join(Company, Company.id == Diagnostic.company_id).where(active_company)
    ) or 0
    converted = (
        db.scalar(select(func.count(Company.id)).where(Company.stage == PipelineStage.GANADO, active_company)) or 0
    )
    avg = db.scalar(
        select(func.avg(Diagnostic.total_score)).join(Company, Company.id == Diagnostic.company_id).where(active_company)
    ) or 0.0

    def group(column, *where) -> dict[str, int]:
        rows = db.execute(select(column, func.count()).where(*where).group_by(column)).all()
        return {(k.value if hasattr(k, "value") else str(k)): v for k, v in rows}

    latest = Diagnostic.id.in_(_latest_diagnostics_subquery())

    # Conversión por paquete recomendado (último diagnóstico de cada empresa activa)
    rows = db.execute(
        select(Diagnostic.recommended_package, Company.stage)
        .join(Company, Company.id == Diagnostic.company_id)
        .where(latest, active_company)
    ).all()
    pkg_totals: dict[str, list[int]] = {}
    for pkg, stage in rows:
        t = pkg_totals.setdefault(pkg.value, [0, 0])
        t[0] += 1
        t[1] += int(stage == PipelineStage.GANADO)

    return DashboardMetrics(
        total_companies=total_companies,
        total_diagnostics=total_diagnostics,
        converted=converted,
        conversion_rate=round(converted / diagnosed, 4) if diagnosed else 0.0,
        conversion_target=settings.conversion_target,
        average_score=round(float(avg), 1),
        by_sector=group(Company.sector, active_company),
        by_stage=group(Company.stage, active_company),
        by_level=group(Diagnostic.maturity_level, latest),
        by_package=group(Diagnostic.recommended_package, latest),
        conversion_by_package={k: round(w / n, 4) for k, (n, w) in pkg_totals.items()},
    )



@router.get("/export/ml-dataset.csv", dependencies=[Depends(require_admin)])
def export_ml_dataset(db: Session = Depends(get_db)) -> StreamingResponse:
    """Dataset anonimizado (sin datos personales) para entrenar el modelo de conversión."""
    diagnostics = db.scalars(
        select(Diagnostic)
        .options(selectinload(Diagnostic.company), selectinload(Diagnostic.answers))
        .order_by(Diagnostic.id)
    ).all()

    dims = list(DIMENSIONS)
    q_codes = [q.code for q in QUESTIONS]
    header = (
        ["diagnostic_id", "questionnaire_version", "sector", "employees", "total_score",
         "maturity_level", "recommended_package"]
        + [f"dim_{d}" for d in dims]
        + [f"q_{c}" for c in q_codes]
        + ["converted", "purchased_package"]
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(header)
    for d in diagnostics:
        points = {a.question_code: a.points for a in d.answers}
        writer.writerow(
            [d.id, d.questionnaire_version, d.company.sector.value, d.company.employees,
             d.total_score, d.maturity_level.value, d.recommended_package.value]
            + [d.dimension_scores.get(dim, "") for dim in dims]
            + [points.get(c, "") for c in q_codes]
            + [int(d.converted), d.purchased_package.value if d.purchased_package else ""]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=ml-dataset.csv"},
    )
