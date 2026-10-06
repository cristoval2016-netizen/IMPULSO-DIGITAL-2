"""Esquemas Pydantic (contratos de entrada/salida de la API)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import (
    DeliverableStatus,
    FreelancerSpeciality,
    InteractionType,
    MaturityLevel,
    MilestonePaymentStatus,
    MilestoneStage,
    Package,
    PipelineStage,
    ProjectStatus,
    Sector,
    SLAStatus,
    TaskStatus,
    TicketPriority,
    TicketStatus,
    UserRole,
)


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------- Auth / Users
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole | None = None
    full_name: str | None = None
    company_id: int | None = None


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.COMERCIAL
    company_id: int | None = None


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str
    role: UserRole
    company_id: int | None = None
    is_active: bool


# ---------------------------------------------------------- Diagnóstico público
class CompanyIn(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    nit: str | None = Field(default=None, max_length=30)
    sector: Sector
    city: str | None = Field(default=None, max_length=100)
    employees: int = Field(ge=1, le=100_000)
    website: str | None = Field(default=None, max_length=255)

    @field_validator("nit")
    @classmethod
    def normalize_nit(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip().replace(".", "").replace(" ", "")
        return v or None


class ContactIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    position: str | None = Field(default=None, max_length=100)


class DiagnosticSubmission(BaseModel):
    company: CompanyIn
    contact: ContactIn
    answers: dict[str, str]
    data_consent: bool = Field(
        description="Autorización de tratamiento de datos personales (Ley 1581 de 2012)"
    )
    marketing_consent: bool = False

    @field_validator("data_consent")
    @classmethod
    def consent_required(cls, v: bool) -> bool:
        if not v:
            raise ValueError(
                "Debe autorizar el tratamiento de datos personales (Ley 1581 de 2012)"
            )
        return v


class PackageOut(BaseModel):
    code: Package
    name: str
    description: str


class DiagnosticResult(BaseModel):
    diagnostic_id: int
    company_name: str
    sector: Sector
    total_score: float
    maturity_level: MaturityLevel
    maturity_label: str
    dimension_scores: dict[str, float]
    recommendations: list[str]
    recommended_package: PackageOut


# ------------------------------------------------------------------------- CRM
class ContactOut(ORMModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    position: str | None
    data_consent: bool
    consent_at: datetime | None
    marketing_consent: bool


class DiagnosticOut(ORMModel):
    id: int
    questionnaire_version: str
    total_score: float
    maturity_level: MaturityLevel
    recommended_package: Package
    dimension_scores: dict[str, float]
    recommendations: list[str]
    converted: bool
    converted_at: datetime | None
    purchased_package: Package | None
    created_at: datetime


class InteractionCreate(BaseModel):
    type: InteractionType
    summary: str = Field(min_length=2, max_length=5000)
    occurred_at: datetime | None = None

    @field_validator("type")
    @classmethod
    def no_system_type(cls, v: InteractionType) -> InteractionType:
        if v == InteractionType.SISTEMA:
            raise ValueError("El tipo 'sistema' está reservado para eventos automáticos")
        return v


class InteractionOut(ORMModel):
    id: int
    type: InteractionType
    summary: str
    occurred_at: datetime
    user_id: int | None


class CompanySummary(ORMModel):
    id: int
    name: str
    nit: str | None
    sector: Sector
    city: str | None
    employees: int
    stage: PipelineStage
    assigned_to_id: int | None
    created_at: datetime
    latest_score: float | None = None
    latest_level: MaturityLevel | None = None
    latest_package: Package | None = None


class CompanyDetail(CompanySummary):
    website: str | None
    updated_at: datetime
    contacts: list[ContactOut]
    diagnostics: list[DiagnosticOut]
    interactions: list[InteractionOut]


class CompanyUpdate(BaseModel):
    stage: PipelineStage | None = None
    assigned_to_id: int | None = None
    purchased_package: Package | None = Field(
        default=None, description="Paquete contratado (al pasar a 'ganado')"
    )


class CompanyDeleteIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500, description="Motivo de la eliminación / traslado a papelera")


class CompanyRestoreIn(BaseModel):
    reason: str = Field(min_length=3, max_length=500, description="Motivo de la restauración")


class TrashedCompanyOut(ORMModel):
    id: int
    name: str
    nit: str | None
    sector: Sector
    city: str | None
    stage: PipelineStage
    deleted_at: datetime | None
    deleted_by_id: int | None
    deleted_by_name: str | None = None
    delete_reason: str | None
    diagnostics_count: int = 0
    contacts_count: int = 0
    interactions_count: int = 0
    projects_count: int = 0
    tickets_count: int = 0
    created_at: datetime


class PaginatedCompanies(BaseModel):
    total: int
    items: list[CompanySummary]



# ------------------------------------------------------------------- Dashboard
class DashboardMetrics(BaseModel):
    total_companies: int
    total_diagnostics: int
    converted: int
    conversion_rate: float
    conversion_target: float
    average_score: float
    by_sector: dict[str, int]
    by_level: dict[str, int]
    by_package: dict[str, int]
    by_stage: dict[str, int]
    conversion_by_package: dict[str, float]


# ------------------------------------------------------------------- Módulo 2: Portal del Cliente
class ClientAccessCreate(BaseModel):
    contact_id: int | None = None
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=128)


class ClientProfileOut(BaseModel):
    user_id: int
    full_name: str
    email: EmailStr
    role: UserRole
    company_id: int
    company_name: str
    nit: str | None
    sector: Sector
    city: str | None
    assigned_advisor: str | None = None
    nda_signed: bool = True
    law_1581_accepted: bool = True


class DeliverableCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=2)
    preview_url: str | None = None


class DeliverableOut(ORMModel):
    id: int
    project_id: int
    title: str
    description: str
    preview_url: str | None
    status: DeliverableStatus
    client_feedback: str | None
    reviewed_at: datetime | None
    reviewed_by_id: int | None
    created_at: datetime


class DeliverableReview(BaseModel):
    status: DeliverableStatus = Field(description="APROBADO o AJUSTES_SOLICITADOS")
    feedback: str | None = Field(default=None, description="Observaciones o solicitud de cambios")

    @field_validator("status")
    @classmethod
    def validate_review_status(cls, v: DeliverableStatus) -> DeliverableStatus:
        if v not in (DeliverableStatus.APROBADO, DeliverableStatus.AJUSTES_SOLICITADOS):
            raise ValueError("El estado de revisión debe ser 'aprobado' o 'ajustes_solicitados'")
        return v


class ProjectCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    package: Package
    status: ProjectStatus = ProjectStatus.KICKOFF
    progress_percent: int = Field(ge=0, le=100, default=0)
    staging_url: str | None = None
    production_url: str | None = None
    target_delivery_date: datetime | None = None


class ProjectUpdate(BaseModel):
    title: str | None = None
    status: ProjectStatus | None = None
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    staging_url: str | None = None
    production_url: str | None = None
    target_delivery_date: datetime | None = None


class ProjectOut(ORMModel):
    id: int
    company_id: int
    title: str
    package: Package
    status: ProjectStatus
    progress_percent: int
    staging_url: str | None
    production_url: str | None
    target_delivery_date: datetime | None
    created_at: datetime
    updated_at: datetime


class ProjectDetailOut(ProjectOut):
    deliverables: list[DeliverableOut] = []


class TicketMessageCreate(BaseModel):
    message: str = Field(min_length=2, max_length=5000)


class TicketMessageOut(ORMModel):
    id: int
    ticket_id: int
    user_id: int
    message: str
    created_at: datetime
    sender_name: str | None = None
    sender_role: UserRole | None = None


class SupportTicketCreate(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    priority: TicketPriority = TicketPriority.MEDIA


class SupportTicketUpdate(BaseModel):
    status: TicketStatus | None = None
    priority: TicketPriority | None = None


class SupportTicketOut(ORMModel):
    id: int
    company_id: int
    created_by_id: int
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    created_at: datetime
    updated_at: datetime
    messages_count: int = 0


class SupportTicketDetailOut(SupportTicketOut):
    messages: list[TicketMessageOut] = []


class TrainingMaterialCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str
    category: str
    package_required: Package | None = None
    video_url: str | None = None
    manual_url: str | None = None
    duration_minutes: int | None = None
    order_index: int = 0
    is_active: bool = True


class TrainingMaterialOut(ORMModel):
    id: int
    title: str
    description: str
    category: str
    package_required: Package | None
    video_url: str | None
    manual_url: str | None
    duration_minutes: int | None
    order_index: int
    is_active: bool
    created_at: datetime


class AuditLogOut(ORMModel):
    id: int
    company_id: int | None
    user_id: int | None
    action: str
    details: str
    ip_address: str | None
    created_at: datetime


# ------------------------------------------------------------------- Módulo 3: Freelancers, SLAs y QA
class FreelancerProfileCreate(BaseModel):
    speciality: FreelancerSpeciality = FreelancerSpeciality.DESARROLLO_WEB
    skills: list[str] = Field(default_factory=list)
    hourly_rate: float = Field(ge=0.0, default=0.0)
    bank_info: str | None = None


class FreelancerProfileUpdate(BaseModel):
    speciality: FreelancerSpeciality | None = None
    skills: list[str] | None = None
    hourly_rate: float | None = Field(default=None, ge=0.0)
    bank_info: str | None = None
    is_available: bool | None = None


class FreelancerProfileOut(ORMModel):
    id: int
    user_id: int
    user_name: str | None = None
    user_email: str | None = None
    speciality: FreelancerSpeciality
    skills: list[str] = []
    hourly_rate: float
    rating: float
    completed_tasks_count: int
    on_time_delivery_rate: float
    is_available: bool
    created_at: datetime


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    stage: MilestoneStage
    payout_amount: float = Field(ge=0.0)
    requires_client_approval: bool = True
    notes: str | None = None


class MilestoneReleaseIn(BaseModel):
    notes: str | None = None


class MilestoneOut(ORMModel):
    id: int
    project_id: int
    project_title: str | None = None
    title: str
    stage: MilestoneStage
    payout_amount: float
    payment_status: MilestonePaymentStatus
    requires_client_approval: bool
    client_approved: bool
    qa_approved: bool
    released_at: datetime | None
    released_by_id: int | None
    notes: str | None
    tasks_count: int = 0
    created_at: datetime


class FreelancerTaskCreate(BaseModel):
    project_id: int
    milestone_id: int | None = None
    assigned_freelancer_id: int
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=5)
    priority: TicketPriority = TicketPriority.MEDIA
    sla_hours_allotted: int = Field(ge=1, le=720, default=48)
    due_date: datetime


class FreelancerTaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    priority: TicketPriority | None = None
    deliverable_url: str | None = None
    due_date: datetime | None = None


class TaskSubmitIn(BaseModel):
    deliverable_url: str = Field(min_length=3)
    notes: str | None = None


class QAReviewIn(BaseModel):
    score: int = Field(ge=0, le=100, description="Puntaje de calidad de 0 a 100")
    approved: bool = Field(description="Aprobar para entrega al cliente o rechazar para correcciones")
    feedback: str = Field(min_length=3, description="Retroalimentación técnica detallada")
    checklist: dict = Field(default_factory=dict, description="Puntos verificados de calidad y seguridad")


class FreelancerTaskOut(ORMModel):
    id: int
    project_id: int
    project_title: str | None = None
    milestone_id: int | None
    milestone_title: str | None = None
    assigned_freelancer_id: int
    freelancer_name: str | None = None
    title: str
    description: str
    deliverable_url: str | None
    status: TaskStatus
    priority: TicketPriority
    sla_hours_allotted: int
    due_date: datetime
    submitted_at: datetime | None
    completed_at: datetime | None
    sla_status: SLAStatus
    qa_score: int | None
    qa_feedback: str | None
    qa_checklist: dict = {}
    qa_reviewed_by_id: int | None
    created_at: datetime
    updated_at: datetime


class SLADashboardMetrics(BaseModel):
    target_on_time_rate: float = 0.95
    actual_on_time_rate: float
    meets_target: bool
    total_tasks: int
    completed_tasks: int
    on_time_tasks: int
    delayed_tasks: int
    active_tasks: int
    tasks_at_risk: int
    average_qa_score: float
    milestone_payouts_released: float
    milestone_payouts_pending: float


