import { useCallback, useEffect, useState, type FormEvent } from "react";
import { createPortal } from "react-dom";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../../api";
import { useAuth } from "../../auth";
import { label, type CompanyDetail, type InteractionType, type PackageCode, type Project, type Stage, type User } from "../../types";

const STAGES: Stage[] = ["nuevo", "contactado", "propuesta", "negociacion", "ganado", "perdido"];
const TYPES: InteractionType[] = ["llamada", "email", "reunion", "whatsapp", "nota"];

export default function CompanyDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [c, setC] = useState<CompanyDetail | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [note, setNote] = useState({ type: "llamada" as InteractionType, summary: "" });
  const [wonPackage, setWonPackage] = useState<PackageCode | "">("");

  // Modales
  const [showClientModal, setShowClientModal] = useState<{ email: string; full_name: string; password: string } | null>(null);
  const [clientExistsNotice, setClientExistsNotice] = useState<string | null>(null);
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [newProject, setNewProject] = useState({ title: "", package: "impulso_integral" as PackageCode, staging_url: "", progress_percent: 50 });
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteReason, setDeleteReason] = useState("");
  const [deleting, setDeleting] = useState(false);
  const [busy, setBusy] = useState(false);


  const load = useCallback(() => {
    api<CompanyDetail>(`/api/companies/${id}`).then(setC).catch((e) => setError(e.message));
  }, [id]);

  const loadProjects = useCallback(() => {
    api<Project[]>(`/api/portal/projects?company_id=${id}`)
      .then(setProjects)
      .catch(() => {});
  }, [id]);

  useEffect(() => {
    load();
    loadProjects();
    if (user?.role === "admin") api<User[]>("/api/users").then(setUsers).catch(() => {});
  }, [load, loadProjects, user]);

  const handleCreateClientUser = async (e: FormEvent) => {
    e.preventDefault();
    if (!showClientModal) return;
    setBusy(true);
    setError("");
    setSuccessMsg("");
    try {
      await api(`/api/companies/${id}/client-users`, {
        method: "POST",
        body: JSON.stringify(showClientModal),
      });
      setSuccessMsg(`¡Acceso generado! Credenciales creadas para ${showClientModal.email}.`);
      setShowClientModal(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setShowClientModal(null);
        setClientExistsNotice(showClientModal.email);
      } else {
        setError((err as Error).message);
      }
    } finally {
      setBusy(false);
    }
  };

  const handleCreateProject = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api(`/api/companies/${id}/projects`, {
        method: "POST",
        body: JSON.stringify(newProject),
      });
      setShowProjectModal(false);
      setNewProject({ title: "", package: "impulso_integral" as PackageCode, staging_url: "", progress_percent: 50 });
      loadProjects();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const patch = async (body: Record<string, unknown>) => {
    setError("");
    try {
      setC(await api<CompanyDetail>(`/api/companies/${id}`, { method: "PATCH", body: JSON.stringify(body) }));
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const changeStage = (stage: Stage) => {
    if (stage === "ganado") patch({ stage, purchased_package: wonPackage || undefined });
    else patch({ stage });
  };

  const addNote = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      await api(`/api/companies/${id}/interactions`, { method: "POST", body: JSON.stringify(note) });
      setNote({ ...note, summary: "" });
      load();
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const handleDeleteCompany = async (e: FormEvent) => {
    e.preventDefault();
    if (!deleteReason.trim()) return;
    setDeleting(true);
    setError("");
    try {
      await api(`/api/companies/${id}/soft-delete`, {
        method: "POST",
        body: JSON.stringify({ reason: deleteReason.trim() }),
      });
      navigate("/crm/empresas");
    } catch (err: any) {
      setError(err.message || "Error al enviar la empresa a la papelera");
    } finally {
      setDeleting(false);
      setShowDeleteModal(false);
    }
  };

  if (!c) return error ? <div className="alert">{error}</div> : <p>Cargando…</p>;
  const latest = c.diagnostics[c.diagnostics.length - 1];
  const userName = (uid: number | null) => users.find((u) => u.id === uid)?.full_name ?? (uid ? `Usuario #${uid}` : "Sistema");
  const authorizedAdvisors = users.filter((u) => {
    const n = u.full_name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
    return (
      n.includes("jose cristobal") ||
      n.includes("edinson reynel") ||
      u.email === "asesor@impulsodigital.co" ||
      u.email === "edinson.castillo@impulsodigital.co"
    );
  });

  return (
    <div>
      <Link to="/crm/empresas" className="muted">← Empresas</Link>
      <div className="page-head" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: ".75rem" }}>
          <h1>{c.name}</h1>
          <span className={`tag stage-${c.stage}`}>{label(c.stage)}</span>
        </div>
        <div>
          <button
            type="button"
            className="btn ghost small"
            style={{ color: "#dc2626", borderColor: "#fca5a5" }}
            onClick={() => {
              setDeleteReason("");
              setShowDeleteModal(true);
            }}
          >
            🗑️ Mover a Papelera
          </button>
        </div>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="grid-2">
        <div className="card">
          <h3>Información</h3>
          <dl>
            <dt>NIT</dt><dd>{c.nit ?? "—"}</dd>
            <dt>Sector</dt><dd>{label(c.sector)}</dd>
            <dt>Ciudad</dt><dd>{c.city ?? "—"}</dd>
            <dt>Empleados</dt><dd>{c.employees}</dd>
            <dt>Sitio web</dt><dd>{c.website ?? "—"}</dd>
          </dl>
          <h3>Contactos</h3>
          {c.contacts.map((p) => (
            <div key={p.id} className="contact">
              <strong>{p.full_name}</strong> {p.position && <small className="muted">· {p.position}</small>}<br />
              <a href={`mailto:${p.email}`}>{p.email}</a> {p.phone && <>· {p.phone}</>}<br />
              <small className={p.data_consent ? "ok-text" : "warn-text"}>
                {p.data_consent
                  ? `✔ Autorización Ley 1581 (${new Date(p.consent_at!).toLocaleString("es-CO")})`
                  : "✖ Sin autorización de datos"}
                {p.marketing_consent && " · Acepta marketing"}
              </small>
              <div style={{ marginTop: ".35rem" }}>
                <button
                  type="button"
                  className="btn ghost small"
                  onClick={() => setShowClientModal({ email: p.email, full_name: p.full_name, password: "Cliente123*" })}
                >
                  🔑 Crear Acceso al Portal
                </button>
              </div>
            </div>
          ))}
        </div>

        <div className="card">
          <h3>Gestión comercial</h3>
          <label>Etapa del pipeline
            <select value={c.stage} onChange={(e) => changeStage(e.target.value as Stage)}>
              {STAGES.map((s) => <option key={s} value={s}>{label(s)}</option>)}
            </select>
          </label>
          {c.stage !== "ganado" && (
            <label>Paquete contratado (si se marca como Ganado)
              <select value={wonPackage} onChange={(e) => setWonPackage(e.target.value as PackageCode)}>
                <option value="">El recomendado</option>
                {["impulso_basico", "impulso_integral", "impulso_premium"].map((p) =>
                  <option key={p} value={p}>{label(p)}</option>)}
              </select>
            </label>
          )}
          {user?.role === "admin" ? (
            <label>Asesor asignado
              <select value={c.assigned_to_id ?? ""}
                onChange={(e) => patch({ assigned_to_id: e.target.value ? Number(e.target.value) : null })}>
                <option value="">Sin asignar</option>
                {authorizedAdvisors.map((u) => <option key={u.id} value={u.id}>{u.full_name}</option>)}
              </select>
            </label>
          ) : (
            <p className="muted">
              Asesor: {c.assigned_to_id ? userName(c.assigned_to_id) : "Sin asignar"}
            </p>
          )}

          {latest && (
            <>
              <h3>Último diagnóstico</h3>
              <p>
                <b>{latest.total_score}</b>/100 · {label(latest.maturity_level)} · Recomendado:{" "}
                <b>{label(latest.recommended_package)}</b>
                {latest.converted && <> · <span className="ok-text">Convertido ({label(latest.purchased_package)})</span></>}
              </p>
              <div className="bars">
                {Object.entries(latest.dimension_scores).map(([d, s]) => (
                  <div className="bar" key={d}>
                    <span>{label(d)}</span>
                    <div className="track"><div style={{ width: `${s}%` }} /></div>
                    <b>{Math.round(s)}</b>
                  </div>
                ))}
              </div>
              <small className="muted">Total de diagnósticos: {c.diagnostics.length}</small>
            </>
          )}
        </div>
      </div>

      {successMsg && <div className="alert" style={{ background: "#ecfdf5", color: "#065f46", borderColor: "#a7f3d0" }}>{successMsg}</div>}

      {/* Proyectos en Staging para el Portal del Cliente */}
      <div className="card">
        <div className="page-head" style={{ margin: "0 0 1rem" }}>
          <div>
            <h3>Proyectos & Fase Staging (Portal del Cliente)</h3>
            <p className="muted" style={{ margin: 0 }}>
              Proyectos visibles en el Portal del Cliente para seguimiento y aprobación de entregables.
            </p>
          </div>
          <button
            type="button"
            className="btn primary small"
            onClick={() => setShowProjectModal(true)}
          >
            + Crear Proyecto Staging
          </button>
        </div>

        {projects.length === 0 ? (
          <p className="muted">No hay proyectos de desarrollo creados para esta empresa aún.</p>
        ) : (
          <div style={{ display: "grid", gap: "1rem" }}>
            {projects.map((p) => (
              <div key={p.id} className="card" style={{ background: "#f8fafc", margin: 0 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: ".5rem" }}>
                  <div>
                    <strong>{p.title}</strong> · <span className="tag">{label(p.package)}</span>
                  </div>
                  <span className={`tag lvl-${p.status === "finalizado" ? "avanzado" : "en_desarrollo"}`}>
                    {label(p.status)} ({p.progress_percent}%)
                  </span>
                </div>
                {p.staging_url && (
                  <p style={{ margin: "0 0 .5rem", fontSize: ".88rem" }}>
                    URL Staging: <a href={p.staging_url} target="_blank" rel="noreferrer">{p.staging_url} ↗</a>
                  </p>
                )}
                <div className="progress" style={{ margin: 0 }}>
                  <div style={{ width: `${p.progress_percent}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card">
        <h3>Historial de interacciones</h3>
        <form className="note-form" onSubmit={addNote}>
          <select value={note.type} onChange={(e) => setNote({ ...note, type: e.target.value as InteractionType })}>
            {TYPES.map((t) => <option key={t} value={t}>{label(t)}</option>)}
          </select>
          <input required minLength={2} placeholder="Resumen de la interacción…" value={note.summary}
            onChange={(e) => setNote({ ...note, summary: e.target.value })} />
          <button className="btn primary">Registrar</button>
        </form>
        <ul className="timeline">
          {c.interactions.map((i) => (
            <li key={i.id} className={`t-${i.type}`}>
              <div>
                <span className="tag">{label(i.type)}</span>{" "}
                <small className="muted">
                  {new Date(i.occurred_at).toLocaleString("es-CO")} · {userName(i.user_id)}
                </small>
              </div>
              <p>{i.summary}</p>
            </li>
          ))}
        </ul>
      </div>

      {/* Modal Crear Acceso Cliente al Portal */}
      {showClientModal && (
        <div className="modal-backdrop">
          <form className="card modal-box" onSubmit={handleCreateClientUser}>
            <h3>Crear Acceso al Portal del Cliente (SGA)</h3>
            <p className="muted" style={{ margin: "0 0 1rem" }}>
              Genera credenciales de acceso para que el cliente ingrese a su portal privado en <code>/portal/login</code>.
            </p>
            <label>
              Nombre Completo *
              <input
                required
                value={showClientModal.full_name}
                onChange={(e) => setShowClientModal({ ...showClientModal, full_name: e.target.value })}
              />
            </label>
            <label>
              Correo Electrónico *
              <input
                type="email"
                required
                value={showClientModal.email}
                onChange={(e) => setShowClientModal({ ...showClientModal, email: e.target.value })}
              />
            </label>
            <label>
              Contraseña Temporal *
              <input
                type="password"
                required
                minLength={8}
                value={showClientModal.password}
                onChange={(e) => setShowClientModal({ ...showClientModal, password: e.target.value })}
              />
            </label>
            <div className="actions">
              <button type="button" className="btn ghost" onClick={() => setShowClientModal(null)}>
                Cancelar
              </button>
              <button type="submit" className="btn primary" disabled={busy}>
                {busy ? "Creando..." : "Crear Credenciales"}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Modal Crear Proyecto Staging */}
      {showProjectModal && (
        <div className="modal-backdrop">
          <form className="card modal-box" onSubmit={handleCreateProject}>
            <h3>Crear Proyecto en Desarrollo (Staging)</h3>
            <label>
              Nombre del Proyecto *
              <input
                required
                placeholder="Ej. Implementación Web & Tienda Virtual..."
                value={newProject.title}
                onChange={(e) => setNewProject({ ...newProject, title: e.target.value })}
              />
            </label>
            <label>
              Paquete Contratado *
              <select
                value={newProject.package}
                onChange={(e) => setNewProject({ ...newProject, package: e.target.value as PackageCode })}
              >
                <option value="impulso_basico">Impulso Básico</option>
                <option value="impulso_integral">Impulso Integral</option>
                <option value="impulso_premium">Impulso Premium</option>
              </select>
            </label>
            <label>
              URL Ambiente Staging (Pruebas)
              <input
                placeholder="https://cliente.staging.impulsodigital.co"
                value={newProject.staging_url}
                onChange={(e) => setNewProject({ ...newProject, staging_url: e.target.value })}
              />
            </label>
            <label>
              Porcentaje Inicial de Avance (0 - 100%)
              <input
                type="number"
                min={0}
                max={100}
                value={newProject.progress_percent}
                onChange={(e) => setNewProject({ ...newProject, progress_percent: Number(e.target.value) })}
              />
            </label>
            <div className="actions">
              <button type="button" className="btn ghost" onClick={() => setShowProjectModal(false)}>
                Cancelar
              </button>
              <button type="submit" className="btn primary" disabled={busy}>
                {busy ? "Creando..." : "Crear Proyecto"}
              </button>
            </div>
          </form>
        </div>
      )}

      {showDeleteModal && (
        <div className="modal-backdrop">
          <form className="modal-card" onSubmit={handleDeleteCompany}>
            <h3>Mover Empresa a la Papelera</h3>
            <p className="muted" style={{ fontSize: ".85rem" }}>
              La empresa <strong>{c.name}</strong> desaparecerá de la vista comercial activa, pero <strong>todo su historial se preservará intacto</strong> en la papelera para su posterior recuperación por el Administrador.
            </p>
            <label>
              Motivo de la baja o traslado a papelera: *
              <textarea
                required
                rows={3}
                placeholder="Indique el motivo (ej. Cierre de negocio, lead duplicado, solicitud expresa de la Pyme...)"
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
              />
            </label>
            <div className="actions">
              <button type="button" className="btn ghost" onClick={() => setShowDeleteModal(false)}>
                Cancelar
              </button>
              <button type="submit" className="btn danger" disabled={deleting || !deleteReason.trim()}>
                {deleting ? "Enviando a papelera..." : "Confirmar y Mover a Papelera"}
              </button>
            </div>
          </form>
        </div>
      )}

      {clientExistsNotice &&
        createPortal(
          <div className="modal-backdrop">
            <section
              className="card client-exists-modal"
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="client-exists-title"
              aria-describedby="client-exists-message"
            >
              <button
                type="button"
                className="client-exists-close"
                aria-label="Cerrar aviso"
                onClick={() => setClientExistsNotice(null)}
              >
                ×
              </button>
              <div className="client-exists-content">
                <span className="client-exists-icon" aria-hidden="true">i</span>
                <div>
                  <h2 id="client-exists-title">Acceso ya creado</h2>
                  <p id="client-exists-message">
                    El usuario <strong>{clientExistsNotice}</strong> ya se encuentra creado en nuestra base de datos.
                  </p>
                </div>
              </div>
              <div className="client-exists-actions">
                <button
                  type="button"
                  className="btn primary"
                  autoFocus
                  onClick={() => setClientExistsNotice(null)}
                >
                  Entendido
                </button>
              </div>
            </section>
          </div>,
          document.body
        )}
    </div>
  );
}

