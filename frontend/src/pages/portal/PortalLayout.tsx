import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Outlet } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import type { ClientProfile } from "../../types";

export default function PortalLayout() {
  const { user, loading, logout } = useAuth();
  const [profile, setProfile] = useState<ClientProfile | null>(null);

  useEffect(() => {
    if (user && user.role === "cliente") {
      api<ClientProfile>("/api/portal/profile")
        .then(setProfile)
        .catch(() => {});
    }
  }, [user]);

  if (loading) return <div className="center">Cargando Portal...</div>;
  if (!user) return <Navigate to="/portal/login" replace />;

  return (
    <div className="portal-shell">
      <header className="portal-header">
        <div className="portal-brand">
          <Link to="/portal" className="brand light">
            Impulso<span>Digital</span>
          </Link>
          <span className="portal-badge">Portal del Cliente</span>
        </div>

        <nav className="portal-nav">
          <NavLink to="/portal" end>
            🚀 Mi Proyecto (Staging)
          </NavLink>
          <NavLink to="/portal/soporte">
            🎫 Mesa de Ayuda
          </NavLink>
          <NavLink to="/portal/capacitacion">
            🎓 Capacitación & Videos
          </NavLink>
        </nav>

        <div className="portal-user-info">
          {profile && (
            <div className="portal-company-tag">
              <strong>{profile.company_name}</strong>
              <small>📍 {profile.city ?? "Puerto Boyacá"} · NDA Activo</small>
            </div>
          )}
          <button className="btn ghost light-btn" onClick={logout}>
            Cerrar Sesión
          </button>
        </div>
      </header>

      <main className="portal-content">
        <Outlet context={{ profile }} />
      </main>

      <footer className="portal-footer">
        <p>
          🔒 Acceso Seguro SGA · Protección de Datos Personales (Ley 1581 de 2012) · Acuerdos de Confidencialidad NDA · Impulso Digital
        </p>
      </footer>
    </div>
  );
}
