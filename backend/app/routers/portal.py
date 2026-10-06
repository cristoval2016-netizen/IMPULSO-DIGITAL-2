"""Módulo 2: Portal del Cliente (SGA - Sistema de Gestión y Accesos).

Funcionalidades:
- Aislamiento multitenant estricto (Ley 1581 de 2012 y NDA): cada cliente solo ve su empresa.
- Gestión de proyectos en fase de desarrollo (Staging) y cronograma.
- Aprobación formal de entregables y registro de feedback con no repudio (AuditLog).
- Mesa de ayuda (Tickets de soporte posventa).
- Catálogo de capacitaciones y manuales en video para autonomía digital.
- Creación y gestión de accesos para clientes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    AuditLog,
    Company,
    Deliverable,
    DeliverableStatus,
    Interaction,
    InteractionType,
    Package,
    Project,
    ProjectStatus,
    SupportTicket,
    TicketMessage,
    TicketPriority,
    TicketStatus,
    TrainingMaterial,
    User,
    UserRole,
    utcnow,
)
from app.schemas import (
    AuditLogOut,
    ClientAccessCreate,
    ClientProfileOut,
    DeliverableCreate,
    DeliverableOut,
    DeliverableReview,
    ProjectCreate,
    ProjectDetailOut,
    ProjectOut,
    ProjectUpdate,
    SupportTicketCreate,
    SupportTicketDetailOut,
    SupportTicketOut,
    TicketMessageCreate,
    TicketMessageOut,
    TrainingMaterialCreate,
    TrainingMaterialOut,
    UserOut,
)
from app.security import (
    get_current_user,
    hash_password,
    log_audit,
    require_admin,
    require_client,
    require_client_or_staff,
    require_staff,
)

router = APIRouter(tags=["Portal del Cliente (SGA)"])


# ---------------------------------------------------------------------------
# Helpers de autorización multi-inquilino (Multitenancy & SGA)
# ---------------------------------------------------------------------------
def _get_client_company_id(user: User) -> int:
    if user.role == UserRole.CLIENTE:
        if not user.company_id:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Usuario cliente sin empresa asignada. Contacte a soporte.",
            )
        return user.company_id
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Acceso restringido a clientes")


def _verify_company_access(user: User, company_id: int):
    """Verifica que un cliente solo pueda interactuar con su propia empresa."""
    if user.role == UserRole.CLIENTE and user.company_id != company_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Violación de acceso: no está autorizado para ver o modificar información de otra empresa.",
        )


# ===========================================================================
# 1. PERFIL Y SEGURIDAD DEL CLIENTE
# ===========================================================================
@router.get("/api/portal/profile", response_model=ClientProfileOut)
def get_client_profile(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> ClientProfileOut:
    company_id = _get_client_company_id(user)
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa no encontrada")

    advisor_name = company.assigned_to.full_name if company.assigned_to else None
    return ClientProfileOut(
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        company_id=company.id,
        company_name=company.name,
        nit=company.nit,
        sector=company.sector,
        city=company.city,
        assigned_advisor=advisor_name,
        nda_signed=True,
        law_1581_accepted=True,
    )


# ===========================================================================
# 2. PROYECTOS Y FASE DE DESARROLLO (STAGING)
# ===========================================================================
@router.get("/api/portal/projects", response_model=list[ProjectOut])
def list_client_projects(
    user: User = Depends(require_client_or_staff),
    company_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[Project]:
    if user.role == UserRole.CLIENTE:
        cid = _get_client_company_id(user)
    else:
        cid = company_id or user.company_id
        if not cid:
            return list(db.scalars(select(Project).order_by(Project.created_at.desc())).all())

    return list(
        db.scalars(
            select(Project)
            .where(Project.company_id == cid)
            .order_by(Project.created_at.desc())
        ).all()
    )


@router.get("/api/portal/projects/{project_id}", response_model=ProjectDetailOut)
def get_project_detail(
    project_id: int,
    user: User = Depends(require_client_or_staff),
    db: Session = Depends(get_db),
) -> Project:
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.deliverables))
    )
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")

    _verify_company_access(user, project.company_id)
    return project


@router.post(
    "/api/portal/deliverables/{deliverable_id}/review",
    response_model=DeliverableOut,
)
def review_deliverable(
    deliverable_id: int,
    review: DeliverableReview,
    request: Request,
    user: User = Depends(require_client_or_staff),
    db: Session = Depends(get_db),
) -> Deliverable:
    """Aprobación o solicitud de ajustes por parte del cliente con trazabilidad auditada."""
    deliverable = db.scalar(
        select(Deliverable)
        .where(Deliverable.id == deliverable_id)
        .options(selectinload(Deliverable.project))
    )
    if not deliverable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entregable no encontrado")

    _verify_company_access(user, deliverable.project.company_id)

    deliverable.status = review.status
    deliverable.client_feedback = review.feedback
    deliverable.reviewed_at = utcnow()
    deliverable.reviewed_by_id = user.id

    ip = request.client.host if request.client else None
    action_name = (
        "APROBACION_ENTREGABLE"
        if review.status == DeliverableStatus.APROBADO
        else "AJUSTE_SOLICITADO_ENTREGABLE"
    )
    action_desc = (
        f"El usuario {user.full_name} ({user.email}) marcó como '{review.status.value}' "
        f"el entregable '{deliverable.title}' (ID {deliverable.id}). "
        f"Comentarios: {review.feedback or 'Sin comentarios adicionales'}"
    )

    # 1. Auditoría formal (ISO 27001 / No repudio)
    log_audit(
        db,
        action=action_name,
        details=action_desc,
        user=user,
        company_id=deliverable.project.company_id,
        ip_address=ip,
    )

    # 2. Historial en CRM
    db.add(
        Interaction(
            company_id=deliverable.project.company_id,
            user_id=user.id,
            type=InteractionType.SISTEMA,
            summary=f"Portal Cliente: {action_desc}",
        )
    )

    db.commit()
    db.refresh(deliverable)
    return deliverable


# ===========================================================================
# 3. MESA DE AYUDA Y SOPORTE POSVENTA (TICKETS)
# ===========================================================================
@router.get("/api/portal/tickets", response_model=list[SupportTicketOut])
def list_tickets(
    user: User = Depends(require_client_or_staff),
    company_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[SupportTicketOut]:
    stmt = select(SupportTicket).options(selectinload(SupportTicket.messages))
    if user.role == UserRole.CLIENTE:
        cid = _get_client_company_id(user)
        stmt = stmt.where(SupportTicket.company_id == cid)
    elif company_id:
        stmt = stmt.where(SupportTicket.company_id == company_id)

    tickets = db.scalars(stmt.order_by(SupportTicket.created_at.desc())).all()
    results = []
    for t in tickets:
        item = SupportTicketOut.model_validate(t)
        item.messages_count = len(t.messages)
        results.append(item)
    return results


@router.post(
    "/api/portal/tickets",
    response_model=SupportTicketDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def create_ticket(
    data: SupportTicketCreate,
    request: Request,
    user: User = Depends(require_client_or_staff),
    company_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SupportTicketDetailOut:
    if user.role == UserRole.CLIENTE:
        cid = _get_client_company_id(user)
    else:
        cid = company_id or user.company_id
        if not cid:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Debe especificar company_id para el ticket"
            )

    company = db.get(Company, cid)
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa no encontrada")

    ticket = SupportTicket(
        company_id=cid,
        created_by_id=user.id,
        subject=data.subject,
        description=data.description,
        priority=data.priority,
        status=TicketStatus.ABIERTO,
    )
    db.add(ticket)
    db.flush()

    # Añadir mensaje inicial
    msg = TicketMessage(
        ticket_id=ticket.id,
        user_id=user.id,
        message=data.description,
    )
    db.add(msg)

    # Auditoría
    ip = request.client.host if request.client else None
    log_audit(
        db,
        action="CREACION_TICKET_SOPORTE",
        details=f"Ticket #{ticket.id} creado por {user.full_name}: '{ticket.subject}' (Prioridad: {ticket.priority.value})",
        user=user,
        company_id=cid,
        ip_address=ip,
    )

    db.add(
        Interaction(
            company_id=cid,
            user_id=user.id,
            type=InteractionType.SISTEMA,
            summary=f"Soporte Posventa: Ticket #{ticket.id} creado - '{ticket.subject}'",
        )
    )

    db.commit()
    db.refresh(ticket)

    return SupportTicketDetailOut(
        id=ticket.id,
        company_id=ticket.company_id,
        created_by_id=ticket.created_by_id,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages_count=1,
        messages=[
            TicketMessageOut(
                id=msg.id,
                ticket_id=msg.ticket_id,
                user_id=msg.user_id,
                message=msg.message,
                created_at=msg.created_at,
                sender_name=user.full_name,
                sender_role=user.role,
            )
        ],
    )


@router.get("/api/portal/tickets/{ticket_id}", response_model=SupportTicketDetailOut)
def get_ticket_detail(
    ticket_id: int,
    user: User = Depends(require_client_or_staff),
    db: Session = Depends(get_db),
) -> SupportTicketDetailOut:
    ticket = db.scalar(
        select(SupportTicket)
        .where(SupportTicket.id == ticket_id)
        .options(
            selectinload(SupportTicket.messages).selectinload(TicketMessage.user)
        )
    )
    if not ticket:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket no encontrado")

    _verify_company_access(user, ticket.company_id)

    messages = [
        TicketMessageOut(
            id=m.id,
            ticket_id=m.ticket_id,
            user_id=m.user_id,
            message=m.message,
            created_at=m.created_at,
            sender_name=m.user.full_name if m.user else "Usuario",
            sender_role=m.user.role if m.user else None,
        )
        for m in ticket.messages
    ]

    return SupportTicketDetailOut(
        id=ticket.id,
        company_id=ticket.company_id,
        created_by_id=ticket.created_by_id,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        status=ticket.status,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        messages_count=len(messages),
        messages=messages,
    )


@router.post(
    "/api/portal/tickets/{ticket_id}/messages",
    response_model=TicketMessageOut,
)
def reply_ticket(
    ticket_id: int,
    data: TicketMessageCreate,
    user: User = Depends(require_client_or_staff),
    db: Session = Depends(get_db),
) -> TicketMessageOut:
    ticket = db.get(SupportTicket, ticket_id)
    if not ticket:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ticket no encontrado")

    _verify_company_access(user, ticket.company_id)

    msg = TicketMessage(
        ticket_id=ticket.id,
        user_id=user.id,
        message=data.message,
    )
    db.add(msg)

    # Actualizar estado según quién responde
    if user.role == UserRole.CLIENTE:
        if ticket.status in (TicketStatus.RESUELTO, TicketStatus.CERRADO):
            ticket.status = TicketStatus.EN_PROCESO
    else:
        # El staff respondió
        if ticket.status == TicketStatus.ABIERTO:
            ticket.status = TicketStatus.EN_PROCESO

    ticket.updated_at = utcnow()
    db.commit()
    db.refresh(msg)

    return TicketMessageOut(
        id=msg.id,
        ticket_id=msg.ticket_id,
        user_id=msg.user_id,
        message=msg.message,
        created_at=msg.created_at,
        sender_name=user.full_name,
        sender_role=user.role,
    )


# ===========================================================================
# 4. CAPACITACIÓN Y AUTONOMÍA DIGITAL
# ===========================================================================
@router.get("/api/portal/training", response_model=list[TrainingMaterialOut])
def list_training_materials(
    user: User = Depends(require_client_or_staff),
    db: Session = Depends(get_db),
) -> list[TrainingMaterial]:
    """Materiales educativos en video y manuales. Filtra según el paquete del cliente."""
    stmt = select(TrainingMaterial).where(TrainingMaterial.is_active == True)  # noqa: E712

    if user.role == UserRole.CLIENTE and user.company_id:
        company = db.get(Company, user.company_id)
        latest_pkg = None
        if company and company.diagnostics:
            latest_pkg = company.diagnostics[-1].purchased_package or company.diagnostics[-1].recommended_package

        # Regla de acceso por paquete:
        # Material universal (None) disponible para todos.
        # Paquete Basico: solo Basico.
        # Paquete Integral: Basico e Integral.
        # Paquete Premium: todos.
        if latest_pkg == Package.BASICO:
            stmt = stmt.where(
                (TrainingMaterial.package_required == None)  # noqa: E711
                | (TrainingMaterial.package_required == Package.BASICO)
            )
        elif latest_pkg == Package.INTEGRAL:
            stmt = stmt.where(
                (TrainingMaterial.package_required == None)  # noqa: E711
                | (TrainingMaterial.package_required == Package.BASICO)
                | (TrainingMaterial.package_required == Package.INTEGRAL)
            )

    return list(
        db.scalars(stmt.order_by(TrainingMaterial.order_index, TrainingMaterial.title)).all()
    )


@router.post(
    "/api/portal/training",
    response_model=TrainingMaterialOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_training_material(
    data: TrainingMaterialCreate, db: Session = Depends(get_db)
) -> TrainingMaterial:
    material = TrainingMaterial(**data.model_dump())
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


# ===========================================================================
# 5. GESTIÓN ADMINISTRATIVA: CREACIÓN DE ACCESOS Y PROYECTOS PARA CLIENTES
# ===========================================================================
@router.post(
    "/api/companies/{company_id}/client-users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
def create_client_user(
    company_id: int,
    data: ClientAccessCreate,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> User:
    """Crea una cuenta de acceso al portal para un representante de la empresa."""
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa no encontrada")

    if db.scalar(select(User).where(func.lower(User.email) == data.email.lower())):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya existe un usuario con este correo electrónico"
        )

    client_user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        role=UserRole.CLIENTE,
        company_id=company.id,
        hashed_password=hash_password(data.password),
    )
    db.add(client_user)

    log_audit(
        db,
        action="CREACION_ACCESO_CLIENTE",
        details=f"Acceso al Portal creado para '{client_user.full_name}' ({client_user.email}) en {company.name}",
        user=user,
        company_id=company.id,
    )
    db.commit()
    db.refresh(client_user)
    return client_user


@router.post(
    "/api/companies/{company_id}/projects",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
def create_company_project(
    company_id: int,
    data: ProjectCreate,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Project:
    company = db.get(Company, company_id)
    if not company:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Empresa no encontrada")

    project = Project(
        company_id=company.id,
        title=data.title,
        package=data.package,
        status=data.status,
        progress_percent=data.progress_percent,
        staging_url=data.staging_url,
        production_url=data.production_url,
        target_delivery_date=data.target_delivery_date,
    )
    db.add(project)
    db.flush()

    log_audit(
        db,
        action="CREACION_PROYECTO",
        details=f"Proyecto '{project.title}' creado por {user.full_name} para {company.name}",
        user=user,
        company_id=company.id,
    )

    db.commit()
    db.refresh(project)
    return project


@router.post(
    "/api/projects/{project_id}/deliverables",
    response_model=DeliverableOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_staff)],
)
def add_deliverable_to_project(
    project_id: int,
    data: DeliverableCreate,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Deliverable:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")

    deliverable = Deliverable(
        project_id=project.id,
        title=data.title,
        description=data.description,
        preview_url=data.preview_url,
        status=DeliverableStatus.EN_REVISION,
    )
    db.add(deliverable)
    db.flush()

    log_audit(
        db,
        action="CREACION_ENTREGABLE",
        details=f"Entregable '{deliverable.title}' añadido al proyecto #{project.id} por {user.full_name}",
        user=user,
        company_id=project.company_id,
    )

    db.commit()
    db.refresh(deliverable)
    return deliverable


@router.patch(
    "/api/projects/{project_id}",
    response_model=ProjectOut,
    dependencies=[Depends(require_staff)],
)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    user: User = Depends(require_staff),
    db: Session = Depends(get_db),
) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(project, k, v)

    project.updated_at = utcnow()
    log_audit(
        db,
        action="ACTUALIZACION_PROYECTO",
        details=f"Proyecto #{project.id} actualizado por {user.full_name}",
        user=user,
        company_id=project.company_id,
    )
    db.commit()
    db.refresh(project)
    return project


@router.get(
    "/api/companies/{company_id}/audit-logs",
    response_model=list[AuditLogOut],
    dependencies=[Depends(require_staff)],
)
def get_company_audit_logs(
    company_id: int, db: Session = Depends(get_db)
) -> list[AuditLog]:
    """Registro de trazabilidad y auditoría (cumplimiento ISO/IEC 27001, NDA y Ley 1581)."""
    return list(
        db.scalars(
            select(AuditLog)
            .where(AuditLog.company_id == company_id)
            .order_by(AuditLog.created_at.desc())
        ).all()
    )
