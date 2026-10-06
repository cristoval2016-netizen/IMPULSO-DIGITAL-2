"""Módulo 3: Automatización de Tareas, SLAs para Freelancers y Control de Calidad (QA).

Funcionalidades:
- Asignación de tareas a freelancers con tiempos de entrega (SLA) parametrizados.
- Monitoreo de cumplimiento del SLA con meta operativa del 95% de entregas a tiempo.
- Portal de tareas del freelancer (entrega de enlaces de trabajo y seguimiento).
- Motor de revisión de Control de Calidad (QA) con checklist estructurado y scoring.
- Gestión de hitos (Milestones) y liberación condicionada de pagos (Gatekeeper: QA + Cliente).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import (
    AuditLog,
    Company,
    FreelancerProfile,
    FreelancerSpeciality,
    FreelancerTask,
    Milestone,
    MilestonePaymentStatus,
    MilestoneStage,
    Project,
    SLAStatus,
    TaskStatus,
    TicketPriority,
    User,
    UserRole,
    utcnow,
)
from app.schemas import (
    FreelancerProfileCreate,
    FreelancerProfileOut,
    FreelancerProfileUpdate,
    FreelancerTaskCreate,
    FreelancerTaskOut,
    FreelancerTaskUpdate,
    MilestoneCreate,
    MilestoneOut,
    MilestoneReleaseIn,
    QAReviewIn,
    SLADashboardMetrics,
    TaskSubmitIn,
    UserCreate,
)
from app.security import (
    get_current_user,
    hash_password,
    log_audit,
    require_admin,
    require_freelancer,
    require_freelancer_or_staff,
    require_staff,
)

router = APIRouter(tags=["Módulo 3: Freelancers, SLAs y QA"])


# ---------------------------------------------------------------------------
# Helpers internos para SLA y métricas
# ---------------------------------------------------------------------------
def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _compute_task_sla(task: FreelancerTask) -> SLAStatus:
    """Calcula dinámicamente el estado del SLA para una tarea."""
    now = datetime.now(timezone.utc)
    due = _as_utc(task.due_date)
    if due is None:
        return SLAStatus.A_TIEMPO

    # Si ya fue entregada o completada
    reference_time = _as_utc(task.submitted_at or task.completed_at)
    if reference_time is not None:
        if reference_time <= due:
            return SLAStatus.A_TIEMPO
        return SLAStatus.VENCIDO

    # Si aún está en progreso o pendiente
    if now > due:
        return SLAStatus.VENCIDO
    # Si faltan menos de 12 horas para vencerse
    if now + timedelta(hours=12) >= due:
        return SLAStatus.EN_RIESGO
    return SLAStatus.A_TIEMPO



def _update_freelancer_stats(db: Session, freelancer_user_id: int):
    """Actualiza el % de entregas a tiempo y tareas completadas del perfil freelancer."""
    profile = db.execute(
        select(FreelancerProfile).where(FreelancerProfile.user_id == freelancer_user_id)
    ).scalar_one_or_none()

    if not profile:
        return

    tasks = db.execute(
        select(FreelancerTask).where(FreelancerTask.assigned_freelancer_id == freelancer_user_id)
    ).scalars().all()

    completed_or_submitted = [
        t for t in tasks if t.status in (TaskStatus.COMPLETADA, TaskStatus.EN_QA)
    ]

    total = len(completed_or_submitted)
    if total == 0:
        profile.completed_tasks_count = 0
        profile.on_time_delivery_rate = 1.0
    else:
        on_time = sum(1 for t in completed_or_submitted if t.sla_status == SLAStatus.A_TIEMPO)
        profile.completed_tasks_count = sum(1 for t in completed_or_submitted if t.status == TaskStatus.COMPLETADA)
        profile.on_time_delivery_rate = round(on_time / total, 4)

    db.flush()


def _format_task_out(t: FreelancerTask) -> FreelancerTaskOut:
    return FreelancerTaskOut(
        id=t.id,
        project_id=t.project_id,
        project_title=t.project.title if t.project else None,
        milestone_id=t.milestone_id,
        milestone_title=t.milestone.title if t.milestone else None,
        assigned_freelancer_id=t.assigned_freelancer_id,
        freelancer_name=t.assigned_freelancer.full_name if t.assigned_freelancer else None,
        title=t.title,
        description=t.description,
        deliverable_url=t.deliverable_url,
        status=t.status,
        priority=t.priority,
        sla_hours_allotted=t.sla_hours_allotted,
        due_date=t.due_date,
        submitted_at=t.submitted_at,
        completed_at=t.completed_at,
        sla_status=t.sla_status,
        qa_score=t.qa_score,
        qa_feedback=t.qa_feedback,
        qa_checklist=t.qa_checklist or {},
        qa_reviewed_by_id=t.qa_reviewed_by_id,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# ---------------------------------------------------------------------------
# Perfiles y Red de Freelancers
# ---------------------------------------------------------------------------
@router.get("/freelancers", response_model=list[FreelancerProfileOut])
def list_freelancers(
    speciality: FreelancerSpeciality | None = None,
    available_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Lista todos los perfiles de la red de freelancers (solo staff)."""
    stmt = select(FreelancerProfile).options(selectinload(FreelancerProfile.user))
    if speciality:
        stmt = stmt.where(FreelancerProfile.speciality == speciality)
    if available_only:
        stmt = stmt.where(FreelancerProfile.is_available.is_(True))

    profiles = db.execute(stmt).scalars().all()
    results = []
    for p in profiles:
        results.append(
            FreelancerProfileOut(
                id=p.id,
                user_id=p.user_id,
                user_name=p.user.full_name if p.user else None,
                user_email=p.user.email if p.user else None,
                speciality=p.speciality,
                skills=p.skills or [],
                hourly_rate=p.hourly_rate,
                rating=p.rating,
                completed_tasks_count=p.completed_tasks_count,
                on_time_delivery_rate=p.on_time_delivery_rate,
                is_available=p.is_available,
                created_at=p.created_at,
            )
        )
    return results


@router.post("/freelancers", response_model=FreelancerProfileOut, status_code=status.HTTP_201_CREATED)
def register_freelancer(
    user_in: UserCreate,
    profile_in: FreelancerProfileCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Crea una cuenta y perfil para un nuevo freelancer colaborador."""
    existing = db.execute(select(User).where(User.email == user_in.email)).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El email ya está registrado")

    user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role=UserRole.FREELANCER,
        is_active=True,
    )
    db.add(user)
    db.flush()

    profile = FreelancerProfile(
        user_id=user.id,
        speciality=profile_in.speciality,
        skills=profile_in.skills,
        hourly_rate=profile_in.hourly_rate,
        bank_info=profile_in.bank_info,
        is_available=True,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return FreelancerProfileOut(
        id=profile.id,
        user_id=user.id,
        user_name=user.full_name,
        user_email=user.email,
        speciality=profile.speciality,
        skills=profile.skills or [],
        hourly_rate=profile.hourly_rate,
        rating=profile.rating,
        completed_tasks_count=profile.completed_tasks_count,
        on_time_delivery_rate=profile.on_time_delivery_rate,
        is_available=profile.is_available,
        created_at=profile.created_at,
    )


@router.get("/freelancer/me", response_model=FreelancerProfileOut)
def get_my_freelancer_profile(
    user: User = Depends(require_freelancer),
    db: Session = Depends(get_db),
):
    """Obtiene el perfil del freelancer autenticado."""
    profile = db.execute(
        select(FreelancerProfile).where(FreelancerProfile.user_id == user.id)
    ).scalar_one_or_none()
    if not profile:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Perfil freelancer no encontrado")

    return FreelancerProfileOut(
        id=profile.id,
        user_id=user.id,
        user_name=user.full_name,
        user_email=user.email,
        speciality=profile.speciality,
        skills=profile.skills or [],
        hourly_rate=profile.hourly_rate,
        rating=profile.rating,
        completed_tasks_count=profile.completed_tasks_count,
        on_time_delivery_rate=profile.on_time_delivery_rate,
        is_available=profile.is_available,
        created_at=profile.created_at,
    )


# ---------------------------------------------------------------------------
# Gestión de Tareas y Monitoreo de SLAs
# ---------------------------------------------------------------------------
@router.post("/projects/{project_id}/tasks", response_model=FreelancerTaskOut, status_code=status.HTTP_201_CREATED)
def create_task_for_project(
    project_id: int,
    task_in: FreelancerTaskCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Asigna una nueva tarea técnica a un freelancer con SLA comprometido."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")

    freelancer = db.get(User, task_in.assigned_freelancer_id)
    if not freelancer or freelancer.role != UserRole.FREELANCER:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El usuario asignado no es un freelancer válido")

    if task_in.milestone_id:
        milestone = db.get(Milestone, task_in.milestone_id)
        if not milestone or milestone.project_id != project_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "El hito no pertenece a este proyecto")

    task = FreelancerTask(
        project_id=project_id,
        milestone_id=task_in.milestone_id,
        assigned_freelancer_id=task_in.assigned_freelancer_id,
        title=task_in.title,
        description=task_in.description,
        priority=task_in.priority,
        sla_hours_allotted=task_in.sla_hours_allotted,
        due_date=task_in.due_date,
        status=TaskStatus.PENDIENTE,
        sla_status=SLAStatus.A_TIEMPO,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    # Recargar con relaciones
    task = db.execute(
        select(FreelancerTask)
        .options(
            selectinload(FreelancerTask.project),
            selectinload(FreelancerTask.milestone),
            selectinload(FreelancerTask.assigned_freelancer),
        )
        .where(FreelancerTask.id == task.id)
    ).scalar_one()

    return _format_task_out(task)


@router.get("/freelancer/tasks", response_model=list[FreelancerTaskOut])
def list_tasks(
    project_id: int | None = None,
    milestone_id: int | None = None,
    task_status: TaskStatus | None = None,
    sla_status: SLAStatus | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_freelancer_or_staff),
):
    """Lista tareas. Si es freelancer solo ve las suyas; si es staff puede ver todas o filtrar."""
    stmt = (
        select(FreelancerTask)
        .options(
            selectinload(FreelancerTask.project),
            selectinload(FreelancerTask.milestone),
            selectinload(FreelancerTask.assigned_freelancer),
        )
        .order_by(FreelancerTask.due_date.asc())
    )

    if current_user.role == UserRole.FREELANCER:
        stmt = stmt.where(FreelancerTask.assigned_freelancer_id == current_user.id)
    elif project_id:
        stmt = stmt.where(FreelancerTask.project_id == project_id)

    if milestone_id:
        stmt = stmt.where(FreelancerTask.milestone_id == milestone_id)
    if task_status:
        stmt = stmt.where(FreelancerTask.status == task_status)

    tasks = db.execute(stmt).scalars().all()

    # Recalcular SLAs dinámicamente para las tareas en curso
    updated = False
    for t in tasks:
        new_sla = _compute_task_sla(t)
        if t.sla_status != new_sla:
            t.sla_status = new_sla
            updated = True

    if updated:
        db.commit()

    if sla_status:
        tasks = [t for t in tasks if t.sla_status == sla_status]

    return [_format_task_out(t) for t in tasks]


@router.post("/freelancer/tasks/{task_id}/submit", response_model=FreelancerTaskOut)
def submit_task_for_qa(
    task_id: int,
    submit_in: TaskSubmitIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_freelancer_or_staff),
):
    """El freelancer entrega el entregable técnico para someterlo a Control de Calidad (QA)."""
    task = db.execute(
        select(FreelancerTask)
        .options(
            selectinload(FreelancerTask.project),
            selectinload(FreelancerTask.milestone),
            selectinload(FreelancerTask.assigned_freelancer),
        )
        .where(FreelancerTask.id == task_id)
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")

    if current_user.role == UserRole.FREELANCER and task.assigned_freelancer_id != current_user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permisos sobre esta tarea")

    task.deliverable_url = submit_in.deliverable_url
    task.submitted_at = utcnow()
    task.status = TaskStatus.EN_QA
    task.sla_status = _compute_task_sla(task)

    db.commit()
    db.refresh(task)

    _update_freelancer_stats(db, task.assigned_freelancer_id)

    return _format_task_out(task)


# ---------------------------------------------------------------------------
# Control de Calidad (QA) y Verificación Técnica
# ---------------------------------------------------------------------------
@router.post("/qa/tasks/{task_id}/review", response_model=FreelancerTaskOut)
def review_task_qa(
    task_id: int,
    review_in: QAReviewIn,
    db: Session = Depends(get_db),
    qa_user: User = Depends(require_staff),
):
    """Revisión de Control de Calidad (QA) con checklist y puntaje (0-100)."""
    task = db.execute(
        select(FreelancerTask)
        .options(
            selectinload(FreelancerTask.project),
            selectinload(FreelancerTask.milestone),
            selectinload(FreelancerTask.assigned_freelancer),
        )
        .where(FreelancerTask.id == task_id)
    ).scalar_one_or_none()

    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tarea no encontrada")

    task.qa_score = review_in.score
    task.qa_feedback = review_in.feedback
    task.qa_checklist = review_in.checklist
    task.qa_reviewed_by_id = qa_user.id

    if review_in.approved:
        task.status = TaskStatus.COMPLETADA
        task.completed_at = utcnow()
        task.sla_status = _compute_task_sla(task)
    else:
        task.status = TaskStatus.RECHAZADO_QA

    db.commit()
    db.refresh(task)

    # Actualizar estadísticas del freelancer
    _update_freelancer_stats(db, task.assigned_freelancer_id)

    # Verificar si el hito (milestone) asociado ya tiene todas sus tareas aprobadas
    if task.milestone_id and review_in.approved:
        all_milestone_tasks = db.execute(
            select(FreelancerTask).where(FreelancerTask.milestone_id == task.milestone_id)
        ).scalars().all()

        all_approved = all(
            t.status == TaskStatus.COMPLETADA
            for t in all_milestone_tasks
        )
        if all_approved and all_milestone_tasks:
            milestone = db.get(Milestone, task.milestone_id)
            if milestone:
                milestone.qa_approved = True
                if milestone.payment_status == MilestonePaymentStatus.BLOQUEADO:
                    milestone.payment_status = MilestonePaymentStatus.PENDIENTE_APROBACION
                db.commit()

    return _format_task_out(task)


@router.get("/qa/dashboard", response_model=SLADashboardMetrics)
def get_qa_sla_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Métricas operativas del SLA (objetivo >=95% de entregas a tiempo) y QA."""
    tasks = db.execute(select(FreelancerTask)).scalars().all()

    total_tasks = len(tasks)
    completed_or_submitted = [
        t for t in tasks if t.status in (TaskStatus.COMPLETADA, TaskStatus.EN_QA)
    ]
    completed_tasks = sum(1 for t in tasks if t.status == TaskStatus.COMPLETADA)
    on_time_tasks = sum(1 for t in completed_or_submitted if t.sla_status == SLAStatus.A_TIEMPO)
    delayed_tasks = sum(1 for t in completed_or_submitted if t.sla_status == SLAStatus.VENCIDO)

    active_tasks = sum(
        1 for t in tasks if t.status in (TaskStatus.PENDIENTE, TaskStatus.EN_PROCESO, TaskStatus.EN_QA)
    )
    tasks_at_risk = sum(1 for t in tasks if _compute_task_sla(t) == SLAStatus.EN_RIESGO)

    # Ratio actual de entregas a tiempo
    if len(completed_or_submitted) > 0:
        actual_rate = round(on_time_tasks / len(completed_or_submitted), 4)
    else:
        actual_rate = 1.0  # Sin tareas evaluadas aún

    meets_target = actual_rate >= 0.95

    # Puntaje promedio de QA
    qa_scores = [t.qa_score for t in tasks if t.qa_score is not None]
    avg_qa_score = round(sum(qa_scores) / len(qa_scores), 1) if qa_scores else 100.0

    # Hitos y pagos
    milestones = db.execute(select(Milestone)).scalars().all()
    released = sum(m.payout_amount for m in milestones if m.payment_status == MilestonePaymentStatus.LIBERADO)
    pending = sum(m.payout_amount for m in milestones if m.payment_status != MilestonePaymentStatus.LIBERADO)

    return SLADashboardMetrics(
        target_on_time_rate=0.95,
        actual_on_time_rate=actual_rate,
        meets_target=meets_target,
        total_tasks=total_tasks,
        completed_tasks=completed_tasks,
        on_time_tasks=on_time_tasks,
        delayed_tasks=delayed_tasks,
        active_tasks=active_tasks,
        tasks_at_risk=tasks_at_risk,
        average_qa_score=avg_qa_score,
        milestone_payouts_released=released,
        milestone_payouts_pending=pending,
    )


# ---------------------------------------------------------------------------
# Hitos Contractuales y Liberación de Pagos (Gatekeeper)
# ---------------------------------------------------------------------------
@router.post("/projects/{project_id}/milestones", response_model=MilestoneOut, status_code=status.HTTP_201_CREATED)
def create_project_milestone(
    project_id: int,
    milestone_in: MilestoneCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Crea un nuevo hito contractual asociado al proyecto (inicio, diseño, entrega final)."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")

    milestone = Milestone(
        project_id=project_id,
        title=milestone_in.title,
        stage=milestone_in.stage,
        payout_amount=milestone_in.payout_amount,
        requires_client_approval=milestone_in.requires_client_approval,
        notes=milestone_in.notes,
        payment_status=MilestonePaymentStatus.BLOQUEADO,
        client_approved=False,
        qa_approved=False,
    )
    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    return MilestoneOut(
        id=milestone.id,
        project_id=milestone.project_id,
        project_title=project.title,
        title=milestone.title,
        stage=milestone.stage,
        payout_amount=milestone.payout_amount,
        payment_status=milestone.payment_status,
        requires_client_approval=milestone.requires_client_approval,
        client_approved=milestone.client_approved,
        qa_approved=milestone.qa_approved,
        released_at=milestone.released_at,
        released_by_id=milestone.released_by_id,
        notes=milestone.notes,
        tasks_count=0,
        created_at=milestone.created_at,
    )


@router.get("/projects/{project_id}/milestones", response_model=list[MilestoneOut])
def list_project_milestones(
    project_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_freelancer_or_staff),
):
    """Lista todos los hitos y estado de liberación de pagos de un proyecto."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proyecto no encontrado")

    milestones = db.execute(
        select(Milestone)
        .options(selectinload(Milestone.tasks))
        .where(Milestone.project_id == project_id)
        .order_by(Milestone.id.asc())
    ).scalars().all()

    results = []
    for m in milestones:
        results.append(
            MilestoneOut(
                id=m.id,
                project_id=m.project_id,
                project_title=project.title,
                title=m.title,
                stage=m.stage,
                payout_amount=m.payout_amount,
                payment_status=m.payment_status,
                requires_client_approval=m.requires_client_approval,
                client_approved=m.client_approved,
                qa_approved=m.qa_approved,
                released_at=m.released_at,
                released_by_id=m.released_by_id,
                notes=m.notes,
                tasks_count=len(m.tasks),
                created_at=m.created_at,
            )
        )
    return results


@router.post("/milestones/{milestone_id}/approve-client", response_model=MilestoneOut)
def approve_milestone_client(
    milestone_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Registra la conformidad del cliente con el entregable del hito."""
    milestone = db.execute(
        select(Milestone).options(selectinload(Milestone.project), selectinload(Milestone.tasks)).where(Milestone.id == milestone_id)
    ).scalar_one_or_none()

    if not milestone:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hito no encontrado")

    milestone.client_approved = True
    if milestone.payment_status == MilestonePaymentStatus.BLOQUEADO:
        milestone.payment_status = MilestonePaymentStatus.PENDIENTE_APROBACION

    db.commit()
    db.refresh(milestone)

    return MilestoneOut(
        id=milestone.id,
        project_id=milestone.project_id,
        project_title=milestone.project.title if milestone.project else None,
        title=milestone.title,
        stage=milestone.stage,
        payout_amount=milestone.payout_amount,
        payment_status=milestone.payment_status,
        requires_client_approval=milestone.requires_client_approval,
        client_approved=milestone.client_approved,
        qa_approved=milestone.qa_approved,
        released_at=milestone.released_at,
        released_by_id=milestone.released_by_id,
        notes=milestone.notes,
        tasks_count=len(milestone.tasks),
        created_at=milestone.created_at,
    )


@router.post("/milestones/{milestone_id}/release-payout", response_model=MilestoneOut)
def release_milestone_payout(
    milestone_id: int,
    release_in: MilestoneReleaseIn,
    request: Request,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Gatekeeper estricto: Libera el pago del hito al freelancer.
    Condición obligatoria:
    1. QA técnico debe estar aprobado (qa_approved == True).
    2. Aprobación formal del cliente (client_approved == True) si requires_client_approval es True.
    """
    milestone = db.execute(
        select(Milestone).options(selectinload(Milestone.project), selectinload(Milestone.tasks)).where(Milestone.id == milestone_id)
    ).scalar_one_or_none()

    if not milestone:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Hito no encontrado")

    if milestone.payment_status == MilestonePaymentStatus.LIBERADO:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Este pago ya fue liberado previamente")

    # Validación 1: Control de Calidad
    if not milestone.qa_approved:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No se puede liberar el pago: El control de calidad (QA) técnico no ha sido aprobado.",
        )

    # Validación 2: Aprobación del Cliente
    if milestone.requires_client_approval and not milestone.client_approved:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No se puede liberar el pago: El cliente aún no ha dado la aprobación formal del entregable.",
        )

    # Liberación de fondos
    milestone.payment_status = MilestonePaymentStatus.LIBERADO
    milestone.released_at = utcnow()
    milestone.released_by_id = admin_user.id
    if release_in.notes:
        milestone.notes = f"{milestone.notes or ''}\n[LIBERACIÓN]: {release_in.notes}".strip()

    # Registro de auditoría (no repudio)
    log_audit(
        db=db,
        action="PAGO_HITO_LIBERADO",
        details=f"Liberado pago de ${milestone.payout_amount:,.2f} COP para el hito '{milestone.title}' (Proyecto ID {milestone.project_id}). QA: Aprobado, Cliente: Aprobado.",
        user=admin_user,
        company_id=milestone.project.company_id if milestone.project else None,
        ip_address=request.client.host if request.client else None,
    )

    db.commit()
    db.refresh(milestone)

    return MilestoneOut(
        id=milestone.id,
        project_id=milestone.project_id,
        project_title=milestone.project.title if milestone.project else None,
        title=milestone.title,
        stage=milestone.stage,
        payout_amount=milestone.payout_amount,
        payment_status=milestone.payment_status,
        requires_client_approval=milestone.requires_client_approval,
        client_approved=milestone.client_approved,
        qa_approved=milestone.qa_approved,
        released_at=milestone.released_at,
        released_by_id=milestone.released_by_id,
        notes=milestone.notes,
        tasks_count=len(milestone.tasks),
        created_at=milestone.created_at,
    )
