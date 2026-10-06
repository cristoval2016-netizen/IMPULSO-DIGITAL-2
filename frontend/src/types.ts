export type Sector = "comercio" | "servicios" | "manufactura";
export type Stage = "nuevo" | "contactado" | "propuesta" | "negociacion" | "ganado" | "perdido";
export type Level = "inicial" | "en_desarrollo" | "intermedio" | "avanzado";
export type PackageCode = "impulso_basico" | "impulso_integral" | "impulso_premium";
export type InteractionType = "llamada" | "email" | "reunion" | "whatsapp" | "nota" | "sistema";

export interface Questionnaire {
  version: string;
  dimensions: { code: string; label: string }[];
  questions: {
    code: string;
    dimension: string;
    text: string;
    options: { value: string; label: string }[];
  }[];
}

export interface DiagnosticResult {
  diagnostic_id: number;
  company_name: string;
  sector: Sector;
  total_score: number;
  maturity_level: Level;
  maturity_label: string;
  dimension_scores: Record<string, number>;
  recommendations: string[];
  recommended_package: { code: PackageCode; name: string; description: string };
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: "admin" | "comercial" | "cliente" | "freelancer";
  company_id?: number | null;
  is_active: boolean;
}


export interface CompanySummary {
  id: number;
  name: string;
  nit: string | null;
  sector: Sector;
  city: string | null;
  employees: number;
  stage: Stage;
  assigned_to_id: number | null;
  created_at: string;
  latest_score: number | null;
  latest_level: Level | null;
  latest_package: PackageCode | null;
}

export interface Interaction {
  id: number;
  type: InteractionType;
  summary: string;
  occurred_at: string;
  user_id: number | null;
}

export interface CompanyDetail extends CompanySummary {
  website: string | null;
  updated_at: string;
  contacts: {
    id: number;
    full_name: string;
    email: string;
    phone: string | null;
    position: string | null;
    data_consent: boolean;
    consent_at: string | null;
    marketing_consent: boolean;
  }[];
  diagnostics: {
    id: number;
    total_score: number;
    maturity_level: Level;
    recommended_package: PackageCode;
    dimension_scores: Record<string, number>;
    recommendations: string[];
    converted: boolean;
    purchased_package: PackageCode | null;
    created_at: string;
  }[];
  interactions: Interaction[];
}

export interface Metrics {
  total_companies: number;
  total_diagnostics: number;
  converted: number;
  conversion_rate: number;
  conversion_target: number;
  average_score: number;
  by_sector: Record<string, number>;
  by_level: Record<string, number>;
  by_package: Record<string, number>;
  by_stage: Record<string, number>;
  conversion_by_package: Record<string, number>;
}

export const LABELS: Record<string, string> = {
  comercio: "Comercio",
  servicios: "Servicios",
  manufactura: "Manufactura",
  nuevo: "Nuevo",
  contactado: "Contactado",
  propuesta: "Propuesta",
  negociacion: "Negociación",
  ganado: "Ganado",
  perdido: "Perdido",
  inicial: "Inicial",
  en_desarrollo: "En desarrollo",
  intermedio: "Intermedio",
  avanzado: "Avanzado",
  impulso_basico: "Impulso Básico",
  impulso_integral: "Impulso Integral",
  impulso_premium: "Impulso Premium",
  llamada: "Llamada",
  email: "Email",
  reunion: "Reunión",
  whatsapp: "WhatsApp",
  nota: "Nota",
  sistema: "Sistema",
  presencia_web: "Presencia web",
  redes_sociales: "Redes sociales",
  comercio_electronico: "Comercio electrónico",
  marketing_digital: "Marketing digital",
  gestion_operaciones: "Herramientas de gestión",
  datos_analitica: "Datos y analítica",
  // Portal
  kickoff: "Kickoff / Inicio",
  diseno: "Diseño & Prototipado",
  staging: "Staging (Pruebas)",
  capacitacion: "Capacitación",
  finalizado: "Lanzado / Finalizado",
  pendiente: "Pendiente",
  en_revision: "En Revisión",
  aprobado: "Aprobado",
  ajustes_solicitados: "Ajustes Solicitados",
  baja: "Baja",
  media: "Media",
  alta: "Alta",
  urgente: "Urgente",
  abierto: "Abierto",
  en_proceso: "En Proceso",
  resuelto: "Resuelto",
  cerrado: "Cerrado",
  // Módulo 3: SLAs, QA y Freelancers
  desarrollo_web: "Desarrollo Web",
  desarrollo_frontend: "Desarrollo Frontend",
  desarrollo_backend: "Desarrollo Backend",
  dev_fullstack: "Desarrollo Full Stack",
  diseno_ui: "Diseño UI/UX",
  marketing_pauta: "Marketing & Pauta",
  copywriting: "Copywriting",
  en_qa: "En Revisión QA",
  rechazado_qa: "Ajustes Requeridos por QA",
  completada: "Completada / Aprobada",
  a_tiempo: "A Tiempo (SLA OK)",
  en_riesgo: "En Riesgo (<12h SLA)",
  vencido: "Vencido (Incumplió SLA)",
  cumplido: "Cumplido",
  bloqueado: "Pago Bloqueado",
  pendiente_aprobacion: "Pendiente Aprobación",
  aprobado_qa: "Aprobado por QA",
  liberado: "Pago Liberado",
  pagado: "Pagado",
  inicio: "Hito Inicial",
  entrega_final: "Entrega Final",
};

export const label = (k: string | null | undefined) => (k ? LABELS[k] ?? k : "—");

// Módulo 2: Portal del Cliente
export type ProjectStatus = "kickoff" | "diseno" | "staging" | "capacitacion" | "finalizado";
export type DeliverableStatus = "pendiente" | "en_revision" | "aprobado" | "ajustes_solicitados";
export type TicketPriority = "baja" | "media" | "alta" | "urgente";
export type TicketStatus = "abierto" | "en_proceso" | "resuelto" | "cerrado";

export interface ClientProfile {
  user_id: number;
  full_name: string;
  email: string;
  role: "cliente";
  company_id: number;
  company_name: string;
  nit: string | null;
  sector: Sector;
  city: string | null;
  assigned_advisor: string | null;
  nda_signed: boolean;
  law_1581_accepted: boolean;
}

export interface Deliverable {
  id: number;
  project_id: number;
  title: string;
  description: string;
  preview_url: string | null;
  status: DeliverableStatus;
  client_feedback: string | null;
  reviewed_at: string | null;
  reviewed_by_id: number | null;
  created_at: string;
}

export interface Project {
  id: number;
  company_id: number;
  title: string;
  package: PackageCode;
  status: ProjectStatus;
  progress_percent: number;
  staging_url: string | null;
  production_url: string | null;
  target_delivery_date: string | null;
  created_at: string;
  updated_at: string;
  deliverables?: Deliverable[];
}

export interface TicketMessage {
  id: number;
  ticket_id: number;
  user_id: number;
  message: string;
  created_at: string;
  sender_name: string | null;
  sender_role: string | null;
}

export interface SupportTicket {
  id: number;
  company_id: number;
  created_by_id: number;
  subject: string;
  description: string;
  priority: TicketPriority;
  status: TicketStatus;
  created_at: string;
  updated_at: string;
  messages_count: number;
  messages?: TicketMessage[];
}

export interface TrainingMaterial {
  id: number;
  title: string;
  description: string;
  category: string;
  package_required: PackageCode | null;
  video_url: string | null;
  manual_url: string | null;
  duration_minutes: number | null;
  order_index: number;
  is_active: boolean;
  created_at: string;
}

// Módulo 3: Automatización de Tareas, SLAs y Control de Calidad (QA)
export type FreelancerSpeciality =
  | "desarrollo_web"
  | "desarrollo_frontend"
  | "desarrollo_backend"
  | "dev_fullstack"
  | "diseno_ui"
  | "marketing_pauta"
  | "copywriting";

export type TaskStatus = "pendiente" | "en_proceso" | "en_qa" | "rechazado_qa" | "completada";
export type SLAStatus = "a_tiempo" | "en_riesgo" | "vencido" | "cumplido";
export type MilestoneStage = "inicio" | "diseno" | "aprobacion_diseno" | "entrega_final";
export type MilestonePaymentStatus =
  | "bloqueado"
  | "pendiente_aprobacion"
  | "aprobado_qa"
  | "liberado"
  | "pagado";

export interface FreelancerProfile {
  id: number;
  user_id: number;
  user_name?: string | null;
  user_email?: string | null;
  speciality: FreelancerSpeciality;
  skills: string[];
  hourly_rate: number;
  rating: number;
  completed_tasks_count: number;
  on_time_delivery_rate: number;
  is_available: boolean;
  created_at: string;
}

export interface Milestone {
  id: number;
  project_id: number;
  project_title?: string | null;
  title: string;
  stage: MilestoneStage;
  payout_amount: number;
  payment_status: MilestonePaymentStatus;
  requires_client_approval: boolean;
  client_approved: boolean;
  qa_approved: boolean;
  released_at: string | null;
  released_by_id?: number | null;
  notes?: string | null;
  tasks_count: number;
  created_at: string;
}

export interface FreelancerTask {
  id: number;
  project_id: number;
  project_title?: string | null;
  milestone_id: number | null;
  milestone_title?: string | null;
  assigned_freelancer_id: number;
  freelancer_name?: string | null;
  title: string;
  description: string;
  deliverable_url: string | null;
  status: TaskStatus;
  priority: TicketPriority;
  sla_hours_allotted: number;
  due_date: string;
  submitted_at: string | null;
  completed_at: string | null;
  sla_status: SLAStatus;
  qa_score: number | null;
  qa_feedback: string | null;
  qa_checklist: Record<string, boolean>;
  qa_reviewed_by_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface SLADashboardMetrics {
  target_on_time_rate: number;
  actual_on_time_rate: number;
  meets_target: boolean;
  total_tasks: number;
  completed_tasks: number;
  on_time_tasks: number;
  delayed_tasks: number;
  active_tasks: number;
  tasks_at_risk: number;
  average_qa_score: number;
  milestone_payouts_released: number;
  milestone_payouts_pending: number;
}

// Módulo de Papelera y Recuperación de Empresas
export interface TrashedCompany {
  id: number;
  name: string;
  nit: string | null;
  sector: Sector;
  city: string | null;
  stage: Stage;
  deleted_at: string | null;
  deleted_by_id: number | null;
  deleted_by_name: string | null;
  delete_reason: string | null;
  diagnostics_count: number;
  contacts_count: number;
  interactions_count: number;
  projects_count: number;
  tickets_count: number;
  created_at: string;
}



