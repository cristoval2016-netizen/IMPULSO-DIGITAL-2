import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth";

export default function PortalLoginPage() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) {
    if (user.role === "cliente") return <Navigate to="/portal" replace />;
    return <Navigate to="/crm" replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      nav("/portal");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap portal-login-bg">
      <form className="card login portal-login-card" onSubmit={onSubmit}>
        <div className="brand">
          Impulso<span>Digital</span>
        </div>
        <h2>Portal del Cliente</h2>
        <p className="muted">
          Consulte la fase de desarrollo de su proyecto, apruebe diseños y acceda a soporte y capacitaciones.
        </p>

        {error && <div className="alert">{error}</div>}

        <label>
          Correo Electrónico Autorizado
          <input
            type="email"
            required
            placeholder="ejemplo@empresa.co"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Contraseña
          <input
            type="password"
            required
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>

        <button className="btn primary" disabled={busy}>
          {busy ? "Validando credenciales..." : "Ingresar a Mi Portal"}
        </button>

        <div className="login-footer-hint">
          <small>
            🔒 Cumplimiento estricto de la <strong>Ley 1581 de 2012</strong> y acuerdos de confidencialidad NDA.
          </small>
          <div className="login-links">
            <Link to="/">¿No tiene diagnóstico? Inícielo aquí</Link>
            <span>·</span>
            <Link to="/crm/login">Acceso Personal Interno</Link>
          </div>
        </div>
      </form>
    </div>
  );
}
