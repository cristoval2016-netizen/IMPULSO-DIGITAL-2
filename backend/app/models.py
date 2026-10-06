"""Modelo relacional (PostgreSQL) de la Plataforma de Diagnóstico y CRM.

Entidades:
- User:            personal interno (admin / comercial) que opera el CRM.
- Company:         Pyme registrada (lead / cliente), con sector y etapa del pipeline.
- Contact:         persona de contacto + registro de consentimiento (Ley 1581 de 2012).
- Diagnostic:      resultado de una auditoría de madurez digital.
- DiagnosticAnswer:respuestas individuales (dataset base para futuros modelos de ML).
- Interaction:     historial de interacciones comerciales con la empresa.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _enum(e: type[enum.Enum]) -> Enum:
    # Guardamos el valor (string) y no usamos ENUM nativo para facilitar migraciones.
    return Enum(e, native_enum=False, length=30, values_callable=lambda x: [m.value for m in x])


# ---------------------------------------------------------------------------
# Enumeraciones de negocio
# ---------------------------------------------------------------------------
class UserRole(str, enum.Enum):
    ADMIN = "admin"
    COMERCIAL = "comercial"
    CLIENTE = "cliente"
    FREELANCER = "freelancer"


# --- Módulo 3: Automatización, SLAs y Control de Calidad (QA) ---
class MilestoneStage(str, enum.Enum):
    INICIO = "inicio"
    DISENO = "diseno"
    APROBACION_DISENO = "aprobacion_diseno"
    ENTREGA_FINAL = "entrega_final"


class MilestonePaymentStatus(str, enum.Enum):
    BLOQUEADO = "bloqueado"
    PENDIENTE_APROBACION = "pendiente_aprobacion"
    APROBADO_QA = "aprobado_qa"
    LIBERADO = "liberado"
    PAGADO = "pagado"


class FreelancerSpeciality(str, enum.Enum):
    DESARROLLO_WEB = "desarrollo_web"
    DESARROLLO_FRONTEND = "desarrollo_frontend"
    DESARROLLO_BACKEND = "desarrollo_backend"
    DEV_FULLSTACK = "dev_fullstack"
    DISENO_UI = "diseno_ui"
    MARKETING_PAUTA = "marketing_pauta"
    COPYWRITING = "copywriting"


class TaskStatus(str, enum.Enum):
    PENDIENTE = "pendiente"
    EN_PROCESO = "en_proceso"
    EN_QA = "en_qa"
    RECHAZADO_QA = "rechazado_qa"
    COMPLETADA = "completada"


class SLAStatus(str, enum.Enum):
    A_TIEMPO = "a_tiempo"
    EN_RIESGO = "en_riesgo"
    VENCIDO = "vencido"
    CUMPLIDO = "cumplido"
    INCUMPLIDO = "incumplido"


class ProjectStatus(str, enum.Enum):
    KICKOFF = "kickoff"
    DISENO = "diseno"
    STAGING = "staging"
    CAPACITACION = "capacitacion"
    FINALIZADO = "finalizado"


class DeliverableStatus(str, enum.Enum):
    PENDIENTE = "pendiente"
    EN_REVISION = "en_revision"
    APROBADO = "aprobado"
    AJUSTES_SOLICITADOS = "ajustes_solicitados"


class TicketPriority(str, enum.Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"
    URGENTE = "urgente"


class TicketStatus(str, enum.Enum):
    ABIERTO = "abierto"
    EN_PROCESO = "en_proceso"
    RESUELTO = "resuelto"
    CERRADO = "cerrado"


class Sector(str, enum.Enum):
    COMERCIO = "comercio"
    SERVICIOS = "servicios"
    MANUFACTURA = "manufactura"


class PipelineStage(str, enum.Enum):
    NUEVO = "nuevo"                # Completó el diagnóstico
    CONTACTADO = "contactado"
    PROPUESTA = "propuesta"
    NEGOCIACION = "negociacion"
    GANADO = "ganado"              # Cliente pago
    PERDIDO = "perdido"


class MaturityLevel(str, enum.Enum):
    INICIAL = "inicial"
    EN_DESARROLLO = "en_desarrollo"
    INTERMEDIO = "intermedio"
    AVANZADO = "avanzado"


class Package(str, enum.Enum):
    BASICO = "impulso_basico"
    INTEGRAL = "impulso_integral"
    PREMIUM = "impulso_premium"


class InteractionType(str, enum.Enum):
    LLAMADA = "llamada"
    EMAIL = "email"
    REUNION = "reunion"
    WHATSAPP = "whatsapp"
    NOTA = "nota"
    SISTEMA = "sistema"            # Eventos automáticos (diagnóstico, cambio de etapa...)


# ---------------------------------------------------------------------------
# Tablas
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), default=UserRole.COMERCIAL)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    # Si role == CLIENTE, está vinculado a su empresa (aislamiento multitenant)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE", use_alter=True), nullable=True, index=True
    )

    assigned_companies: Mapped[list[Company]] = relationship(
        "Company", back_populates="assigned_to", foreign_keys="Company.assigned_to_id"
    )
    company: Mapped[Company | None] = relationship(
        "Company", foreign_keys=[company_id], back_populates="client_users"
    )
    freelancer_profile: Mapped[FreelancerProfile | None] = relationship(
        "FreelancerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    assigned_tasks: Mapped[list[FreelancerTask]] = relationship(
        "FreelancerTask", back_populates="assigned_freelancer", foreign_keys="FreelancerTask.assigned_freelancer_id"
    )


class Company(Base):
    __tablename__ = "companies"
    __table_args__ = (UniqueConstraint("nit", name="uq_company_nit"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    nit: Mapped[str | None] = mapped_column(String(30), nullable=True)
    sector: Mapped[Sector] = mapped_column(_enum(Sector), index=True)
    city: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employees: Mapped[int] = mapped_column(Integer, default=1)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)

    stage: Mapped[PipelineStage] = mapped_column(
        _enum(PipelineStage), default=PipelineStage.NUEVO, index=True
    )
    assigned_to_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    # Soft delete / Papelera de reciclaje y recuperación
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    delete_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    assigned_to: Mapped[User | None] = relationship(
        "User", back_populates="assigned_companies", foreign_keys=[assigned_to_id]
    )
    deleted_by: Mapped[User | None] = relationship(
        "User", foreign_keys=[deleted_by_id]
    )

    client_users: Mapped[list[User]] = relationship(
        "User", back_populates="company", foreign_keys="User.company_id", cascade="all, delete-orphan"
    )
    contacts: Mapped[list[Contact]] = relationship(
        back_populates="company", cascade="all, delete-orphan"
    )
    diagnostics: Mapped[list[Diagnostic]] = relationship(
        back_populates="company", cascade="all, delete-orphan", order_by="Diagnostic.created_at"
    )
    interactions: Mapped[list[Interaction]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="Interaction.occurred_at.desc()",
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="Project.created_at.desc()",
    )
    tickets: Mapped[list[SupportTicket]] = relationship(
        back_populates="company",
        cascade="all, delete-orphan",
        order_by="SupportTicket.created_at.desc()",
    )


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"))
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # --- Ley 1581 de 2012: autorización previa, expresa e informada ---
    data_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    consent_policy_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    consent_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    marketing_consent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped[Company] = relationship(back_populates="contacts")


class Diagnostic(Base):
    __tablename__ = "diagnostics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("contacts.id"), nullable=True)

    questionnaire_version: Mapped[str] = mapped_column(String(20))
    total_score: Mapped[float] = mapped_column(Float)                  # 0 - 100
    maturity_level: Mapped[MaturityLevel] = mapped_column(_enum(MaturityLevel), index=True)
    recommended_package: Mapped[Package] = mapped_column(_enum(Package), index=True)
    dimension_scores: Mapped[dict] = mapped_column(JSON, default=dict)  # {dimension: 0-100}
    recommendations: Mapped[list] = mapped_column(JSON, default=list)   # textos priorizados

    # Etiqueta para el futuro modelo de ML de predicción de conversión
    converted: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    purchased_package: Mapped[Package | None] = mapped_column(_enum(Package), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped[Company] = relationship(back_populates="diagnostics")
    answers: Mapped[list[DiagnosticAnswer]] = relationship(
        back_populates="diagnostic", cascade="all, delete-orphan"
    )


class DiagnosticAnswer(Base):
    __tablename__ = "diagnostic_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    diagnostic_id: Mapped[int] = mapped_column(
        ForeignKey("diagnostics.id", ondelete="CASCADE"), index=True
    )
    question_code: Mapped[str] = mapped_column(String(50))
    dimension: Mapped[str] = mapped_column(String(50))
    option_value: Mapped[str] = mapped_column(String(50))
    points: Mapped[int] = mapped_column(Integer)

    diagnostic: Mapped[Diagnostic] = relationship(back_populates="answers")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    type: Mapped[InteractionType] = mapped_column(_enum(InteractionType))
    summary: Mapped[str] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    company: Mapped[Company] = relationship(back_populates="interactions")
    user: Mapped[User | None] = relationship()


# ---------------------------------------------------------------------------
# Módulo 2: Portal del Cliente (SGA - Sistema de Gestión y Accesos)
# ---------------------------------------------------------------------------
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    package: Mapped[Package] = mapped_column(_enum(Package))
    status: Mapped[ProjectStatus] = mapped_column(
        _enum(ProjectStatus), default=ProjectStatus.KICKOFF, index=True
    )
    progress_percent: Mapped[int] = mapped_column(Integer, default=0)
    staging_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    production_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    target_delivery_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    company: Mapped[Company] = relationship(back_populates="projects")
    deliverables: Mapped[list[Deliverable]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Deliverable.id"
    )
    milestones: Mapped[list[Milestone]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="Milestone.id"
    )
    tasks: Mapped[list[FreelancerTask]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="FreelancerTask.due_date"
    )


class Deliverable(Base):
    __tablename__ = "deliverables"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    preview_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[DeliverableStatus] = mapped_column(
        _enum(DeliverableStatus), default=DeliverableStatus.PENDIENTE, index=True
    )
    client_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="deliverables")
    reviewed_by: Mapped[User | None] = relationship()


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), index=True
    )
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    subject: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    priority: Mapped[TicketPriority] = mapped_column(
        _enum(TicketPriority), default=TicketPriority.MEDIA
    )
    status: Mapped[TicketStatus] = mapped_column(
        _enum(TicketStatus), default=TicketStatus.ABIERTO, index=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    company: Mapped[Company] = relationship(back_populates="tickets")
    created_by: Mapped[User] = relationship(foreign_keys=[created_by_id])
    messages: Mapped[list[TicketMessage]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="TicketMessage.created_at"
    )


class TicketMessage(Base):
    __tablename__ = "ticket_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ticket_id: Mapped[int] = mapped_column(
        ForeignKey("support_tickets.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    ticket: Mapped[SupportTicket] = relationship(back_populates="messages")
    user: Mapped[User] = relationship()


class TrainingMaterial(Base):
    __tablename__ = "training_materials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), index=True)
    # Si package_required es None, está disponible para todos los clientes
    package_required: Mapped[Package | None] = mapped_column(_enum(Package), nullable=True)
    video_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    manual_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    """Trazabilidad y registro de no repudio (ISO/IEC 27001, NDA, Ley 1581)."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    details: Mapped[str] = mapped_column(Text)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    company: Mapped[Company | None] = relationship()
    user: Mapped[User | None] = relationship()


# ---------------------------------------------------------------------------
# Módulo 3: Automatización de Tareas, SLAs y Control de Calidad (QA)
# ---------------------------------------------------------------------------
class FreelancerProfile(Base):
    __tablename__ = "freelancer_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    speciality: Mapped[FreelancerSpeciality] = mapped_column(_enum(FreelancerSpeciality))
    skills: Mapped[list] = mapped_column(JSON, default=list)
    hourly_rate: Mapped[float] = mapped_column(Float, default=0.0)
    bank_info: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rating: Mapped[float] = mapped_column(Float, default=5.0)
    completed_tasks_count: Mapped[int] = mapped_column(Integer, default=0)
    on_time_delivery_rate: Mapped[float] = mapped_column(Float, default=1.0)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User] = relationship(back_populates="freelancer_profile")


class Milestone(Base):
    """Hito contractual del proyecto para liberación de pagos según cumplimiento."""
    __tablename__ = "milestones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    stage: Mapped[MilestoneStage] = mapped_column(_enum(MilestoneStage))
    payout_amount: Mapped[float] = mapped_column(Float, default=0.0)
    payment_status: Mapped[MilestonePaymentStatus] = mapped_column(
        _enum(MilestonePaymentStatus), default=MilestonePaymentStatus.BLOQUEADO, index=True
    )
    requires_client_approval: Mapped[bool] = mapped_column(Boolean, default=True)
    client_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    qa_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped[Project] = relationship(back_populates="milestones")
    released_by: Mapped[User | None] = relationship()
    tasks: Mapped[list[FreelancerTask]] = relationship(
        back_populates="milestone", cascade="all, delete-orphan", order_by="FreelancerTask.id"
    )


class FreelancerTask(Base):
    """Tarea técnica con SLA estricto (meta operativa: >=95% entregas a tiempo)."""
    __tablename__ = "freelancer_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    milestone_id: Mapped[int | None] = mapped_column(
        ForeignKey("milestones.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assigned_freelancer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    deliverable_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[TaskStatus] = mapped_column(
        _enum(TaskStatus), default=TaskStatus.PENDIENTE, index=True
    )
    priority: Mapped[TicketPriority] = mapped_column(
        _enum(TicketPriority), default=TicketPriority.MEDIA
    )
    sla_hours_allotted: Mapped[int] = mapped_column(Integer, default=48)
    due_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sla_status: Mapped[SLAStatus] = mapped_column(
        _enum(SLAStatus), default=SLAStatus.A_TIEMPO, index=True
    )

    # Control de Calidad (QA)
    qa_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    qa_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    qa_checklist: Mapped[dict] = mapped_column(JSON, default=dict)
    qa_reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    project: Mapped[Project] = relationship(back_populates="tasks")
    milestone: Mapped[Milestone | None] = relationship(back_populates="tasks")
    assigned_freelancer: Mapped[User] = relationship(
        back_populates="assigned_tasks", foreign_keys=[assigned_freelancer_id]
    )
    qa_reviewed_by: Mapped[User | None] = relationship(foreign_keys=[qa_reviewed_by_id])

