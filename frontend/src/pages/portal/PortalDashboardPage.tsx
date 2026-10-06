import { useEffect, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { api } from "../../api";
import { label, type ClientProfile, type Deliverable, type Project } from "../../types";

export default function PortalDashboardPage() {
  const { profile } = useOutletContext<{ profile: ClientProfile | null }>();
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reviewModal, setReviewModal] = useState<{
    deliverable: Deliverable;
    status: "aprobado" | "ajustes_solicitados";
    feedback: string;
  } | null>(null);
  const [sendingReview, setSendingReview] = useState(false);

  const selectProjectById = async (pid: number) => {
    try {
      const detail = await api<Project>(`/api/portal/projects/${pid}`);
      setSelectedProject(detail);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const loadProjects = () => {
    setLoading(true);
    api<Project[]>("/api/portal/projects")
      .then(async (list) => {
        setProjects(list);
        if (list.length > 0) {
          const detail = await api<Project>(`/api/portal/projects/${list[0].id}`);
          setSelectedProject(detail);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleReviewSubmit = async () => {
    if (!reviewModal) return;
    setSendingReview(true);
    setError("");
    try {
      await api(`/api/portal/deliverables/${reviewModal.deliverable.id}/review`, {
        method: "POST",
        body: JSON.stringify({
          status: reviewModal.status,
          feedback: reviewModal.feedback || undefined,
        }),
      });
      setReviewModal(null);
      // Recargar detalles del proyecto
      if (selectedProject) {
        const detail = await api<Project>(`/api/portal/projects/${selectedProject.id}`);
        setSelectedProject(detail);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSendingReview(false);
    }
  };

  if (loading) return <div className="card">Cargando estado del proyecto...</div>;

  return (
    <div>
      {error && <div className="alert">{error}</div>}

      <div className="portal-welcome card">
        <div className="portal-welcome-text">
          <h1>¡Bienvenido, {profile?.full_name ?? "Cliente"}!</h1>
          <p>
            Aquí puede revisar el avance de su transformación digital en tiempo real, probar las funciones en <strong>Staging</strong> y aprobar cada entregable de forma transparente.
          </p>
        </div>
        {profile?.assigned_advisor && (
          <div className="advisor-badge">
            <small>Su Asesor Asignado:</small>
            <strong>👤 {profile.assigned_advisor}</strong>
            <small className="ok-text">Acompañamiento Posventa Activo</small>
          </div>
        )}
      </div>

      {projects.length > 1 && (
        <div className="card">
          <label>
            Seleccionar Proyecto:
            <select
              value={selectedProject?.id ?? ""}
              onChange={(e) => selectProjectById(Number(e.target.value))}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title} ({label(p.status)})
                </option>
              ))}
            </select>
          </label>
        </div>
      )}

      {!selectedProject ? (
        <div className="card">
          <p className="muted">No hay proyectos activos registrados para su empresa aún.</p>
        </div>
      ) : (
        <>
          {/* Tarjeta de Proyecto y Estado Staging */}
          <div className="card project-hero-card">
            <div className="project-head">
              <div>
                <span className="tag">{label(selectedProject.package)}</span>
                <h2>{selectedProject.title}</h2>
              </div>
              <span className={`tag lvl-${selectedProject.status === "finalizado" ? "avanzado" : "en_desarrollo"}`}>
                Fase actual: {label(selectedProject.status)}
              </span>
            </div>

            {/* Barra de progreso */}
            <div className="progress-section">
              <div className="progress-label">
                <span>Avance Global de Entrega</span>
                <b>{selectedProject.progress_percent}%</b>
              </div>
              <div className="progress large">
                <div style={{ width: `${selectedProject.progress_percent}%` }} />
              </div>
            </div>

            {/* Acceso a Ambientes */}
            <div className="environments-grid">
              {selectedProject.staging_url ? (
                <div className="env-box staging">
                  <div>
                    <strong>🌐 Ambiente de Pruebas (Staging)</strong>
                    <p>Pruebe los avances, catálogo y botones antes del lanzamiento oficial.</p>
                  </div>
                  <a
                    href={selectedProject.staging_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn primary"
                  >
                    Abrir Staging ↗
                  </a>
                </div>
              ) : (
                <div className="env-box">
                  <span>Ambiente de Staging en preparación técnica</span>
                </div>
              )}

              {selectedProject.production_url && (
                <div className="env-box prod">
                  <div>
                    <strong>🚀 Sitio Web de Producción</strong>
                    <p>Dominio definitivo visible para sus clientes.</p>
                  </div>
                  <a
                    href={selectedProject.production_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn ghost"
                  >
                    Ver Sitio Web ↗
                  </a>
                </div>
              )}
            </div>
          </div>

          {/* Lista de Entregables para Aprobación */}
          <div className="card">
            <div className="section-head">
              <div>
                <h3>Aprobación de Entregables & Diseños</h3>
                <p className="muted">
                  Revise los diseños y componentes desarrollados. Su aprobación formal queda registrada bajo acuerdos NDA.
                </p>
              </div>
            </div>

            <div className="deliverables-list">
              {(selectedProject.deliverables ?? []).map((d) => (
                <div key={d.id} className={`deliverable-item status-${d.status}`}>
                  <div className="deliv-main">
                    <div className="deliv-title">
                      <h4>{d.title}</h4>
                      <span className={`tag status-tag-${d.status}`}>{label(d.status)}</span>
                    </div>
                    <p>{d.description}</p>
                    {d.client_feedback && (
                      <div className="deliv-feedback">
                        <small><strong>Comentario de revisión:</strong> {d.client_feedback}</small>
                      </div>
                    )}
                  </div>

                  <div className="deliv-actions">
                    {d.preview_url && (
                      <a
                        href={d.preview_url}
                        target="_blank"
                        rel="noreferrer"
                        className="btn ghost small"
                      >
                        Ver Prototipo ↗
                      </a>
                    )}

                    {d.status !== "aprobado" && (
                      <>
                        <button
                          className="btn ok-btn small"
                          onClick={() =>
                            setReviewModal({
                              deliverable: d,
                              status: "aprobado",
                              feedback: "",
                            })
                          }
                        >
                          ✔ Aprobar
                        </button>
                        <button
                          className="btn warn-btn small"
                          onClick={() =>
                            setReviewModal({
                              deliverable: d,
                              status: "ajustes_solicitados",
                              feedback: "",
                            })
                          }
                        >
                          ✏ Solicitar Ajustes
                        </button>
                      </>
                    )}
                  </div>
                </div>
              ))}

              {(!selectedProject.deliverables || selectedProject.deliverables.length === 0) && (
                <p className="muted">No hay entregables asignados por ahora.</p>
              )}
            </div>
          </div>
        </>
      )}

      {/* Modal de Aprobación / Ajustes */}
      {reviewModal && (
        <div className="modal-backdrop">
          <div className="card modal-box">
            <h3>
              {reviewModal.status === "aprobado"
                ? "Aprobar Entregable"
                : "Solicitar Ajustes al Entregable"}
            </h3>
            <p>
              <strong>Entregable:</strong> {reviewModal.deliverable.title}
            </p>
            <label>
              Observaciones o comentarios de su equipo:
              <textarea
                rows={4}
                placeholder={
                  reviewModal.status === "aprobado"
                    ? "Opcional: Indique qué le pareció el resultado..."
                    : "Describa detalladamente los cambios requeridos..."
                }
                value={reviewModal.feedback}
                onChange={(e) =>
                  setReviewModal({ ...reviewModal, feedback: e.target.value })
                }
              />
            </label>

            <div className="actions">
              <button
                className="btn ghost"
                disabled={sendingReview}
                onClick={() => setReviewModal(null)}
              >
                Cancelar
              </button>
              <button
                className={`btn ${
                  reviewModal.status === "aprobado" ? "primary" : "warn-btn"
                }`}
                disabled={
                  sendingReview ||
                  (reviewModal.status === "ajustes_solicitados" &&
                    !reviewModal.feedback.trim())
                }
                onClick={handleReviewSubmit}
              >
                {sendingReview
                  ? "Registrando..."
                  : reviewModal.status === "aprobado"
                  ? "Confirmar Aprobación"
                  : "Enviar Solicitud de Ajustes"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
