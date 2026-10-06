"""CRM: gestión de empresas (leads/clientes), pipeline e historial de interacciones."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    AuditLog,
    Company,
    Diagnostic,
    Interaction,
    InteractionType,
    MaturityLevel,
    Package,
    PipelineStage,
    Project,
    Sector,
    SupportTicket,
    User,
    UserRole,
    utcnow,
)
from app.schemas import (
    CompanyDeleteIn,
    CompanyDetail,
    CompanyRestoreIn,
    CompanySummary,
    CompanyUpdate,
    InteractionCreate,
    InteractionOut,
    PaginatedCompanies,
    TrashedCompanyOut,
)
from app.security import log_audit, require_admin, require_staff

router = APIRouter(prefix="/api/companies", tags=["CRM"])


def _summary_fields(company: Company) -> dict:
    latest: Diagnostic | None = company.diagnostics[-1] if company.diagnostics else None
    return {
        "latest_score": latest.total_score if latest else None,
        "latest_level": latest.maturity_level if latest else None,
        "latest_package": latest.recommended_package if latest else None,
    }


def _to_summary(company: Company) -> CompanySummary:
    return CompanySummary.model_validate(company).model_copy(update=_summary_fields(company))


def _to_detail(company: Company) -> CompanyDetail:
    return CompanyDetail.model_validate(company).model_copy(update=_summary_fields(company))


def _get_company_or_404(db: Session, company_id: int, include_deleted: bool = False) -> Company:
    stmt = (
        select(Company)
        .where(Company.id == company_id)
        .options(
            selectinload(Company.contacts),
            selectinload(Company.diagnostics),
            selectinload(Company.interactions),
            selectinload(Company.projects),
            selectinload(Company.tickets),
            selectinload(Company.deleted_by),
        )
    )
    if not include_deleted:
        stmt = stmt.where(Company.is_deleted.is_(False))
    company = db.scalar(stmt)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa no encontrada")
    return company



@router.get("", response_model=PaginatedCompanies)
def list_companies(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
    search: str | None = Query(default=None, description="Nombre, NIT o ciudad"),
    sector: Sector | None = None,
    stage: PipelineStage | None = None,
    level: MaturityLevel | None = None,
    package: Package | None = None,
    assigned_to_id: int | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedCompanies:
    stmt = select(Company).where(Company.is_deleted.is_(False))
    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Company.name).like(like),
                func.lower(Company.nit).like(like),
                func.lower(Company.city).like(like),
            )
        )
    if sector:
        stmt = stmt.where(Company.sector == sector)
    if stage:
        stmt = stmt.where(Company.stage == stage)
    if assigned_to_id:
        stmt = stmt.where(Company.assigned_to_id == assigned_to_id)
    if level or package:
        # Filtrar por el ÚLTIMO diagnóstico de cada empresa
        latest_id = (
            select(func.max(Diagnostic.id)).group_by(Diagnostic.company_id).scalar_subquery()
        )
        stmt = stmt.join(Diagnostic, Diagnostic.company_id == Company.id).where(
            Diagnostic.id.in_(latest_id)
        )
        if level:
            stmt = stmt.where(Diagnostic.maturity_level == level)
        if package:
            stmt = stmt.where(Diagnostic.recommended_package == package)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    companies = db.scalars(
        stmt.options(selectinload(Company.diagnostics))
        .order_by(Company.created_at.desc(), Company.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return PaginatedCompanies(total=total, items=[_to_summary(c) for c in companies])


@router.get("/trash", response_model=list[TrashedCompanyOut])
def list_trash_companies(
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
) -> list[TrashedCompanyOut]:
    """Lista las empresas enviadas a la papelera (soft delete) con su historial preservado."""
    companies = db.scalars(
        select(Company)
        .where(Company.is_deleted.is_(True))
        .options(
            selectinload(Company.deleted_by),
            selectinload(Company.diagnostics),
            selectinload(Company.contacts),
            selectinload(Company.interactions),
            selectinload(Company.projects),
            selectinload(Company.tickets),
        )
        .order_by(Company.deleted_at.desc(), Company.id.desc())
    ).all()

    results = []
    for c in companies:
        results.append(
            TrashedCompanyOut(
                id=c.id,
                name=c.name,
                nit=c.nit,
                sector=c.sector,
                city=c.city,
                stage=c.stage,
                deleted_at=c.deleted_at,
                deleted_by_id=c.deleted_by_id,
                deleted_by_name=c.deleted_by.full_name if c.deleted_by else None,
                delete_reason=c.delete_reason,
                diagnostics_count=len(c.diagnostics),
                contacts_count=len(c.contacts),
                interactions_count=len(c.interactions),
                projects_count=len(c.projects),
                tickets_count=len(c.tickets),
                created_at=c.created_at,
            )
        )
    return results


@router.get("/{company_id}", response_model=CompanyDetail)
def get_company(
    company_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)
) -> CompanyDetail:
    return _to_detail(_get_company_or_404(db, company_id))



@router.patch("/{company_id}", response_model=CompanyDetail)
def update_company(
    company_id: int,
    data: CompanyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> CompanyDetail:
    company = _get_company_or_404(db, company_id)
    is_admin = user.role == UserRole.ADMIN
    changes = data.model_dump(exclude_unset=True)

    # --- Reglas de autorización ---
    if "assigned_to_id" in changes and not is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo un administrador puede reasignar")
    if not is_admin and company.assigned_to_id not in (None, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Esta empresa está asignada a otro asesor")

    events: list[str] = []

    if "assigned_to_id" in changes:
        new_owner_id = changes["assigned_to_id"]
        if new_owner_id is not None:
            owner = db.get(User, new_owner_id)
            if owner is None or not owner.is_active:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Usuario asignado no válido")
            events.append(f"Asignada a {owner.full_name}.")
        else:
            events.append("Asignación removida.")
        company.assigned_to_id = new_owner_id

    if data.stage is not None and data.stage != company.stage:
        old = company.stage
        company.stage = data.stage
        events.append(f"Etapa cambiada de '{old.value}' a '{data.stage.value}'.")
        # Un asesor que mueve un lead libre se convierte en su responsable
        if not is_admin and company.assigned_to_id is None:
            company.assigned_to_id = user.id
            events.append(f"Asignada automáticamente a {user.full_name}.")

        latest = company.diagnostics[-1] if company.diagnostics else None
        if latest is not None:
            # Etiqueta de conversión (target para el futuro modelo de ML)
            if data.stage == PipelineStage.GANADO:
                latest.converted = True
                latest.converted_at = utcnow()
                latest.purchased_package = data.purchased_package or latest.recommended_package
            elif old == PipelineStage.GANADO:
                latest.converted = False
                latest.converted_at = None
                latest.purchased_package = None

    if events:
        db.add(
            Interaction(
                company_id=company.id,
                user_id=user.id,
                type=InteractionType.SISTEMA,
                summary=" ".join(events),
            )
        )
    db.commit()
    db.expire_all()
    return _to_detail(_get_company_or_404(db, company_id))


@router.get("/{company_id}/interactions", response_model=list[InteractionOut])
def list_interactions(
    company_id: int, db: Session = Depends(get_db), _: User = Depends(require_staff)
) -> list[Interaction]:
    return _get_company_or_404(db, company_id).interactions


@router.post(
    "/{company_id}/interactions",
    response_model=InteractionOut,
    status_code=status.HTTP_201_CREATED,
)
def add_interaction(
    company_id: int,
    data: InteractionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
) -> Interaction:
    _get_company_or_404(db, company_id)
    interaction = Interaction(
        company_id=company_id,
        user_id=user.id,
        type=data.type,
        summary=data.summary,
        occurred_at=data.occurred_at or utcnow(),
    )
    db.add(interaction)
    db.commit()
    return interaction


# ---------------------------------------------------------------------------
# Módulo de Papelera y Recuperación de Empresas (Soft Delete con Historial)
# ---------------------------------------------------------------------------
@router.post("/{company_id}/soft-delete")
def soft_delete_company(
    company_id: int,
    data: CompanyDeleteIn,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Envía la empresa a la papelera (soft delete) preservando todo su historial intacto."""
    company = _get_company_or_404(db, company_id)
    is_admin = user.role == UserRole.ADMIN

    if not is_admin and company.assigned_to_id not in (None, user.id):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "No puede eliminar una empresa asignada a otro asesor",
        )

    company.is_deleted = True
    company.deleted_at = utcnow()
    company.deleted_by_id = user.id
    company.delete_reason = data.reason

    # Registro en el historial de interacciones
    db.add(
        Interaction(
            company_id=company.id,
            user_id=user.id,
            type=InteractionType.SISTEMA,
            summary=f"Empresa enviada a la papelera por {user.full_name}. Motivo: {data.reason}",
        )
    )

    # Registro de auditoría (ISO 27001 / Ley 1581)
    log_audit(
        db=db,
        action="EMPRESA_ENVIADA_A_PAPELERA",
        details=f"Empresa '{company.name}' (NIT: {company.nit or 'S/N'}) enviada a la papelera por {user.full_name}. Motivo: {data.reason}",
        user=user,
        company_id=company.id,
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    return {
        "status": "ok",
        "message": f"Empresa '{company.name}' enviada a la papelera exitosamente. Su historial se encuentra intacto.",
    }


@router.post("/{company_id}/restore", response_model=CompanyDetail)
def restore_company(
    company_id: int,
    data: CompanyRestoreIn,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Restaura una empresa desde la papelera con TODO su historial de interacciones,
    diagnósticos, contactos y proyectos. ACCIÓN EXCLUSIVA PARA EL ADMINISTRADOR.
    """
    company = _get_company_or_404(db, company_id, include_deleted=True)

    if not company.is_deleted:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La empresa no se encuentra en la papelera",
        )

    prev_reason = company.delete_reason
    company.is_deleted = False
    company.deleted_at = None
    company.deleted_by_id = None
    company.delete_reason = None

    # Registro formal de la restauración en las interacciones
    db.add(
        Interaction(
            company_id=company.id,
            user_id=admin_user.id,
            type=InteractionType.SISTEMA,
            summary=f"Empresa restaurada desde la papelera por Administrador {admin_user.full_name}. Motivo de restauración: {data.reason} (Motivo de baja original: {prev_reason or 'No indicado'}).",
        )
    )

    # Registro de auditoría
    log_audit(
        db=db,
        action="EMPRESA_RESTAURADA",
        details=f"Empresa '{company.name}' restaurada al CRM activo por Administrador {admin_user.full_name}. Motivo: {data.reason}",
        user=admin_user,
        company_id=company.id,
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    db.expire_all()
    return _to_detail(_get_company_or_404(db, company_id))


@router.delete("/{company_id}/permanent")
def permanent_delete_company(
    company_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Eliminación física definitiva de la empresa y todos sus datos dependientes.
    ACCIÓN IRREVERSIBLE. SOLO ADMINISTRADOR (Ley 1581 de 2012 - Derecho al olvido).
    """
    company = _get_company_or_404(db, company_id, include_deleted=True)
    comp_name = company.name
    comp_nit = company.nit

    log_audit(
        db=db,
        action="EMPRESA_PURGADA_DEFINITIVAMENTE",
        details=f"Empresa '{comp_name}' (NIT: {comp_nit or 'S/N'}) y todo su historial fueron eliminados definitivamente por el Administrador {admin_user.full_name}.",
        user=admin_user,
        company_id=None,
        ip_address=request.client.host if request.client else None,
    )

    db.delete(company)
    db.commit()
    return {
        "status": "ok",
        "message": f"Empresa '{comp_name}' eliminada definitivamente de la base de datos.",
    }

