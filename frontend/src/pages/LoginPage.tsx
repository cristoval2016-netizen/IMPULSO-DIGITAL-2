import { useState, type FormEvent } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function LoginPage() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/crm" replace />;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await login(email, password);
      nav("/crm");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login" onSubmit={onSubmit}>
        <div className="brand">Impulso<span>Digital</span></div>
        <h2>CRM · Acceso interno</h2>
        {error && <div className="alert">{error}</div>}
        <label>Correo
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>Contraseña
          <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </label>
        <button className="btn primary" disabled={busy}>{busy ? "Ingresando…" : "Ingresar"}</button>
      </form>
    </div>
  );
}
