import { Navigate, NavLink, Outlet, Route, Routes } from "react-router-dom";
import { useAuth } from "./auth";
import DiagnosticPage from "./pages/DiagnosticPage";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/crm/DashboardPage";
import CompaniesPage from "./pages/crm/CompaniesPage";
import CompanyDetailPage from "./pages/crm/CompanyDetailPage";

// Módulo 2: Portal del Cliente
import PortalLayout from "./pages/portal/PortalLayout";
import PortalLoginPage from "./pages/portal/PortalLoginPage";
import PortalDashboardPage from "./pages/portal/PortalDashboardPage";
import PortalTicketsPage from "./pages/portal/PortalTicketsPage";
import PortalTrainingPage from "./pages/portal/PortalTrainingPage";

// Módulo 3: QA, SLAs y Freelancers
import QASlaDashboardPage from "./pages/crm/QASlaDashboardPage";
import FreelancerPortalPage from "./pages/freelancer/FreelancerPortalPage";

// Módulo: Papelera y Recuperación de Empresas
import TrashCompaniesPage from "./pages/crm/TrashCompaniesPage";

// Módulo Agroindustrial: Guapi Coco (Georreferenciación & Salud de Palma 4 Ha)
import GuapiCocoPage from "./pages/guapicoco/GuapiCocoPage";

function CrmLayout() {
  const { user, loading, logout } = useAuth();
  if (loading) return <div className="center">Cargando…</div>;
  if (!user) return <Navigate to="/crm/login" replace />;
  if (user.role === "cliente") return <Navigate to="/portal" replace />;
  if (user.role === "freelancer") return <Navigate to="/freelancer" replace />;
  return (
    <div className="crm">
      <aside className="sidebar">
        <div className="brand">Impulso<span>Digital</span></div>
        <nav>
          <NavLink to="/crm" end>Dashboard</NavLink>
          <NavLink to="/crm/empresas">Empresas</NavLink>
          <NavLink to="/crm/qa-slas">Control QA & SLAs</NavLink>
          <NavLink to="/crm/papelera">Papelera</NavLink>
          <a href="/portal/login" target="_blank" rel="noreferrer">Portal Cliente ↗</a>
          <a href="/freelancer" target="_blank" rel="noreferrer">Portal Freelancer ↗</a>
          <a href="/" target="_blank" rel="noreferrer">Formulario público ↗</a>
        </nav>
        <div className="user-box">
          <strong>{user.full_name}</strong>
          <small>{user.role === "admin" ? "Administrador" : "Comercial"}</small>
          <button className="btn ghost" onClick={logout}>Cerrar sesión</button>
        </div>
      </aside>
      <main className="crm-main"><Outlet /></main>
    </div>
  );
}


function FreelancerGuard() {
  const { user, loading } = useAuth();
  if (loading) return <div className="center">Cargando…</div>;
  if (!user) return <Navigate to="/crm/login" replace />;
  if (user.role !== "freelancer" && user.role !== "admin") return <Navigate to="/crm" replace />;
  return <FreelancerPortalPage />;
}

export default function App() {
  return (
    <Routes>
      {/* Módulo 1: Diagnóstico Público y CRM */}
      <Route path="/" element={<DiagnosticPage />} />
      <Route path="/crm/login" element={<LoginPage />} />
      <Route path="/crm" element={<CrmLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="empresas" element={<CompaniesPage />} />
        <Route path="empresas/:id" element={<CompanyDetailPage />} />
        <Route path="qa-slas" element={<QASlaDashboardPage />} />
        <Route path="papelera" element={<TrashCompaniesPage />} />
      </Route>


      {/* Módulo 2: Portal del Cliente (SGA) */}
      <Route path="/portal/login" element={<PortalLoginPage />} />
      <Route path="/portal" element={<PortalLayout />}>
        <Route index element={<PortalDashboardPage />} />
        <Route path="soporte" element={<PortalTicketsPage />} />
        <Route path="capacitacion" element={<PortalTrainingPage />} />
      </Route>

      {/* Módulo 3: Portal del Freelancer */}
      <Route path="/freelancer" element={<FreelancerGuard />} />

      {/* Módulo Finca Guapi Coco (Georreferenciación 4 Ha & Salud de Palma) */}
      <Route path="/guapicoco" element={<GuapiCocoPage />} />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

