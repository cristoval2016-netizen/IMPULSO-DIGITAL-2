import { useEffect, useState } from "react";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { label, type FreelancerProfile, type FreelancerTask } from "../../types";

export default function FreelancerPortalPage() {
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState<FreelancerProfile | null>(null);
  const [tasks, setTasks] = useState<FreelancerTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal para entregar tarea
  const [submittingTask, setSubmittingTask] = useState<FreelancerTask | null>(null);
  const [deliverableUrl, setDeliverableUrl] = useState("");
  const [deliveryNotes, setDeliveryNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [pRes, tRes] = await Promise.all([
        api<FreelancerProfile>("/api/freelancer/me"),
        api<FreelancerTask[]>("/api/freelancer/tasks"),
      ]);
      setProfile(pRes);
      setTasks(tRes);
    } catch (err: any) {
      setError(err.message || "Error al cargar la información del colaborador");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenSubmitModal = (t: FreelancerTask) => {
    setSubmittingTask(t);
    setDeliverableUrl(t.deliverable_url || "");
    setDeliveryNotes("");
  };

  const handleSubmitDeliverable = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!submittingTask || !deliverableUrl) return;

    try {
      setIsSubmitting(true);
      setError(null);
      await api(`/api/freelancer/tasks/${submittingTask.id}/submit`, {
        method: "POST",
        body: JSON.stringify({
          deliverable_url: deliverableUrl,
          notes: deliveryNotes,
        }),
      });
      setSuccessMsg("¡Entregable enviado con éxito! Ha ingresado a la cola de Control de Calidad (QA).");
      setSubmittingTask(null);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Error al enviar el entregable");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Cargando portal del colaborador...</div>;
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
      {/* Barra Superior */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between sticky top-0 z-20">
        <div className="flex items-center gap-3">
          <div className="text-xl font-bold text-slate-900 tracking-tight">
            Impulso<span className="text-indigo-600">Digital</span>
          </div>
          <span className="bg-indigo-50 text-indigo-700 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-indigo-100">
            Red Freelance & QA
          </span>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <div className="text-sm font-bold text-slate-800">{user?.full_name}</div>
            <div className="text-xs text-slate-500">{user?.email}</div>
          </div>
          <button
            onClick={logout}
            className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200"
          >
            Cerrar Sesión
          </button>
        </div>
      </header>

      {/* Contenido Principal */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 space-y-6">
        {error && (
          <div className="p-4 bg-red-50 border-l-4 border-red-500 text-red-700 text-sm rounded">
            {error}
          </div>
        )}

        {successMsg && (
          <div className="p-4 bg-emerald-50 border-l-4 border-emerald-500 text-emerald-800 text-sm rounded flex justify-between items-center">
            <span>{successMsg}</span>
            <button onClick={() => setSuccessMsg(null)} className="text-emerald-700 font-bold hover:underline">
              ✕
            </button>
          </div>
        )}

        {/* Tarjeta de Perfil & KPIs del Freelancer */}
        {profile && (
          <div className="bg-white rounded-2xl border border-slate-200 p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <span className="text-xs font-semibold uppercase tracking-wider text-indigo-600">
                  {label(profile.speciality)}
                </span>
                <h2 className="text-2xl font-bold text-slate-900 mt-1">
                  Bienvenido, {profile.user_name || user?.full_name}
                </h2>
                <div className="flex flex-wrap items-center gap-2 mt-2">
                  {profile.skills.map((s, idx) => (
                    <span key={idx} className="bg-slate-100 text-slate-700 text-xs px-2.5 py-0.5 rounded-full font-medium">
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {/* Indicadores de Rendimiento */}
              <div className="flex items-center gap-6 self-start md:self-auto bg-slate-50 p-4 rounded-xl border border-slate-200/80">
                <div className="text-center px-2">
                  <div className="text-2xl font-black text-emerald-600">
                    {(profile.on_time_delivery_rate * 100).toFixed(0)}%
                  </div>
                  <div className="text-[11px] text-slate-500 font-medium">Entregas a Tiempo</div>
                  <div className="text-[9px] text-emerald-700 font-bold">Meta: ≥95%</div>
                </div>
                <div className="w-px h-8 bg-slate-200" />
                <div className="text-center px-2">
                  <div className="text-2xl font-black text-amber-500">★ {profile.rating.toFixed(1)}</div>
                  <div className="text-[11px] text-slate-500 font-medium">Calificación QA</div>
                </div>
                <div className="w-px h-8 bg-slate-200" />
                <div className="text-center px-2">
                  <div className="text-2xl font-black text-indigo-600">{profile.completed_tasks_count}</div>
                  <div className="text-[11px] text-slate-500 font-medium">Completadas</div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Sección de Tareas Asignadas */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-bold text-slate-900">
              Mis Tareas Asignadas y Acuerdos de Nivel de Servicio (SLA)
            </h3>
            <span className="text-xs text-slate-500 font-medium">
              SLA Operativo: Entregas antes de la fecha límite garantizan la liberación de pagos.
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {tasks.length === 0 ? (
              <div className="p-8 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
                No tienes tareas asignadas actualmente.
              </div>
            ) : (
              tasks.map((task) => {
                const isOverdue = task.sla_status === "vencido";
                const isAtRisk = task.sla_status === "en_riesgo";
                const isApproved = task.status === "completada";
                const isInQA = task.status === "en_qa";

                return (
                  <div
                    key={task.id}
                    className={`bg-white rounded-xl border p-5 shadow-sm space-y-4 transition-all ${isApproved ? "border-emerald-200 bg-emerald-50/20" : isOverdue ? "border-red-200" : isAtRisk ? "border-amber-200" : "border-slate-200"}`}
                  >
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b pb-3">
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-base font-bold text-slate-900">{task.title}</h4>
                          <span
                            className={`text-xs px-2.5 py-0.5 rounded-full font-semibold ${isOverdue ? "bg-red-100 text-red-700" : isAtRisk ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}
                          >
                            {label(task.sla_status)}
                          </span>
                        </div>
                        <p className="text-xs text-slate-500 mt-0.5">
                          {task.project_title || `Proyecto #${task.project_id}`} {task.milestone_title ? `• Hito: ${task.milestone_title}` : ""}
                        </p>
                      </div>

                      <div className="flex items-center gap-3 text-xs">
                        <span className="text-slate-500">
                          Plazo: <strong>{new Date(task.due_date).toLocaleDateString("es-CO", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</strong>
                        </span>
                        <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">
                          SLA: {task.sla_hours_allotted}h
                        </span>
                        <span
                          className={`px-2.5 py-0.5 rounded font-bold ${isApproved ? "bg-emerald-100 text-emerald-800" : isInQA ? "bg-blue-100 text-blue-800" : "bg-slate-100 text-slate-700"}`}
                        >
                          {label(task.status)}
                        </span>
                      </div>
                    </div>

                    <p className="text-sm text-slate-600">{task.description}</p>

                    {/* Feedback de Control de Calidad si ya fue evaluado */}
                    {task.qa_score !== null && (
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
                        <div className="flex items-center justify-between font-semibold">
                          <span className="text-slate-700">Resultado de Control de Calidad (QA):</span>
                          <span className={task.qa_score >= 80 ? "text-emerald-700" : "text-amber-700"}>
                            Puntaje: {task.qa_score}/100
                          </span>
                        </div>
                        {task.qa_feedback && <p className="text-slate-600 italic">"{task.qa_feedback}"</p>}
                      </div>
                    )}

                    {/* Enlace y Botón de Entrega */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2">
                      <div>
                        {task.deliverable_url ? (
                          <div className="text-xs text-slate-600 flex items-center gap-1.5">
                            <span>Entregable actual:</span>
                            <a
                              href={task.deliverable_url}
                              target="_blank"
                              rel="noreferrer"
                              className="text-indigo-600 font-semibold hover:underline"
                            >
                              {task.deliverable_url} ↗
                            </a>
                          </div>
                        ) : (
                          <span className="text-xs text-slate-400 italic">Sin entregable registrado aún</span>
                        )}
                      </div>

                      <div>
                        {isApproved ? (
                          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-lg border border-emerald-200 inline-block">
                            ✓ Tarea Aprobada por QA
                          </span>
                        ) : (
                          <button
                            onClick={() => handleOpenSubmitModal(task)}
                            className="w-full sm:w-auto px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors"
                          >
                            {task.deliverable_url ? "Actualizar Entregable QA" : "📤 Entregar Trabajo para QA"}
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </main>

      {/* Modal para Entregar Trabajo */}
      {submittingTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Entregar Trabajo para Control de Calidad</h3>
                <p className="text-xs text-slate-500">{submittingTask.title}</p>
              </div>
              <button onClick={() => setSubmittingTask(null)} className="text-slate-400 hover:text-slate-600 text-lg">
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmitDeliverable} className="space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                  Enlace del Entregable Técnico (URL Staging, Repositorio o Figma): *
                </label>
                <input
                  type="url"
                  required
                  value={deliverableUrl}
                  onChange={(e) => setDeliverableUrl(e.target.value)}
                  placeholder="https://staging.impulsodigital.co/... o https://github.com/..."
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                  Notas de Entrega o Instrucciones de Verificación:
                </label>
                <textarea
                  rows={3}
                  value={deliveryNotes}
                  onChange={(e) => setDeliveryNotes(e.target.value)}
                  placeholder="Describa brevemente qué se implementó y cómo probarlo..."
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t">
                <button
                  type="button"
                  onClick={() => setSubmittingTask(null)}
                  className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-4 py-2 text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg shadow-sm"
                >
                  {isSubmitting ? "Enviando..." : "Confirmar Entrega para QA"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
