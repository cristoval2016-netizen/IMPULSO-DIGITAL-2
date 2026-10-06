import { useEffect, useState } from "react";
import { api } from "../../api";
import { label, type FreelancerProfile, type FreelancerTask, type Milestone, type SLADashboardMetrics } from "../../types";

export default function QASlaDashboardPage() {
  const [metrics, setMetrics] = useState<SLADashboardMetrics | null>(null);
  const [tasks, setTasks] = useState<FreelancerTask[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [freelancers, setFreelancers] = useState<FreelancerProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<"qa" | "milestones" | "freelancers">("qa");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal de revisión QA
  const [reviewingTask, setReviewingTask] = useState<FreelancerTask | null>(null);
  const [qaScore, setQaScore] = useState<number>(95);
  const [qaFeedback, setQaFeedback] = useState<string>("");
  const [qaChecklist, setQaChecklist] = useState<Record<string, boolean>>({
    responsive_design: true,
    performance_lighthouse: true,
    security_xss_checked: true,
    staging_functional: true,
    pyme_spec_met: true,
  });
  const [submittingQA, setSubmittingQA] = useState(false);

  // Modal de liberación de pago
  const [releasingMilestone, setReleasingMilestone] = useState<Milestone | null>(null);
  const [releaseNotes, setReleaseNotes] = useState<string>("");
  const [submittingRelease, setSubmittingRelease] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [mRes, tRes, fRes] = await Promise.all([
        api<SLADashboardMetrics>("/api/qa/dashboard"),
        api<FreelancerTask[]>("/api/freelancer/tasks"),
        api<FreelancerProfile[]>("/api/freelancers"),
      ]);
      setMetrics(mRes);
      setTasks(tRes);
      setFreelancers(fRes);

      // Cargar hitos del primer proyecto si existen tareas
      if (tRes.length > 0 && tRes[0].project_id) {
        const msRes = await api<Milestone[]>(`/api/projects/${tRes[0].project_id}/milestones`);
        setMilestones(msRes);
      }
    } catch (err: any) {
      setError(err.message || "Error al cargar datos del módulo QA");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenQAReview = (task: FreelancerTask) => {
    setReviewingTask(task);
    setQaScore(task.qa_score ?? 95);
    setQaFeedback(task.qa_feedback ?? "");
    setQaChecklist(
      Object.keys(task.qa_checklist || {}).length > 0
        ? task.qa_checklist
        : {
            responsive_design: true,
            performance_lighthouse: true,
            security_xss_checked: true,
            staging_functional: true,
            pyme_spec_met: true,
          }
    );
  };

  const submitQAReview = async (approved: boolean) => {
    if (!reviewingTask) return;
    try {
      setSubmittingQA(true);
      setError(null);
      await api(`/api/qa/tasks/${reviewingTask.id}/review`, {
        method: "POST",
        body: JSON.stringify({
          score: Number(qaScore),
          approved,
          feedback: qaFeedback || (approved ? "Aprobado por control de calidad." : "Ajustes requeridos."),
          checklist: qaChecklist,
        }),
      });
      setSuccessMsg(`Control de Calidad ${approved ? "Aprobado" : "Rechazado con Observaciones"} exitosamente.`);
      setReviewingTask(null);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Error al registrar la revisión QA");
    } finally {
      setSubmittingQA(false);
    }
  };

  const handleOpenReleaseModal = (m: Milestone) => {
    setReleasingMilestone(m);
    setReleaseNotes("");
  };

  const submitMilestoneRelease = async () => {
    if (!releasingMilestone) return;
    try {
      setSubmittingRelease(true);
      setError(null);
      await api(`/api/milestones/${releasingMilestone.id}/release-payout`, {
        method: "POST",
        body: JSON.stringify({
          notes: releaseNotes || "Transferencia autorizada tras validación de QA y cliente.",
        }),
      });
      setSuccessMsg(`Pago de $${releasingMilestone.payout_amount.toLocaleString("es-CO")} COP liberado exitosamente.`);
      setReleasingMilestone(null);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Error al liberar el pago del hito");
    } finally {
      setSubmittingRelease(false);
    }
  };

  const handleSimulateClientApproval = async (m: Milestone) => {
    try {
      setError(null);
      await api(`/api/milestones/${m.id}/approve-client`, { method: "POST" });
      setSuccessMsg(`Aprobación formal del cliente registrada para el hito '${m.title}'.`);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Error al registrar aprobación");
    }
  };

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Cargando métricas de QA y SLAs...</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-800">Control de Calidad (QA) & SLAs Operativos</h1>
            <span className="bg-indigo-100 text-indigo-700 text-xs px-2.5 py-1 rounded-full font-semibold">
              Módulo 3
            </span>
          </div>
          <p className="text-sm text-slate-600 mt-1">
            Monitoreo estricto del cumplimiento de tiempos de entrega (SLA ≥95%) y liberación condicionada de pagos por hitos.
          </p>
        </div>
        <button
          onClick={loadData}
          className="self-start md:self-auto px-3.5 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm"
        >
          🔄 Actualizar Datos
        </button>
      </div>

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

      {/* Tarjeta de Cumplimiento de SLA Operativo (Meta: ≥95%) */}
      {metrics && (
        <div className={`p-6 rounded-2xl border ${metrics.meets_target ? "bg-gradient-to-r from-emerald-500/10 via-teal-500/5 to-white border-emerald-200" : "bg-gradient-to-r from-amber-500/10 via-red-500/5 to-white border-amber-200"} shadow-sm`}>
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs uppercase tracking-wider font-semibold text-slate-600">
                  Compromiso del Plan Operativo
                </span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${metrics.meets_target ? "bg-emerald-600 text-white" : "bg-amber-600 text-white"}`}>
                  {metrics.meets_target ? "✓ Meta Cumplida" : "⚠ Alerta de Desviación"}
                </span>
              </div>
              <h2 className="text-xl font-bold text-slate-900 mt-1">
                {metrics.meets_target
                  ? "Cumpliendo con el 95% de los tiempos de entrega comprometidos"
                  : "Por debajo del 95% en tiempos de entrega comprometidos"}
              </h2>
              <p className="text-sm text-slate-600 mt-1">
                Tasa real actual: <strong className="text-slate-900">{(metrics.actual_on_time_rate * 100).toFixed(1)}%</strong> entregas a tiempo (Meta mínima: 95.0%).
              </p>
            </div>

            <div className="flex items-center gap-6 self-start md:self-auto bg-white/80 backdrop-blur p-4 rounded-xl border border-slate-200">
              <div className="text-center px-2">
                <div className="text-2xl font-black text-slate-800">{(metrics.actual_on_time_rate * 100).toFixed(0)}%</div>
                <div className="text-[11px] text-slate-500 font-medium">Cumplimiento Real</div>
              </div>
              <div className="w-px h-8 bg-slate-200" />
              <div className="text-center px-2">
                <div className="text-2xl font-black text-emerald-600">95%</div>
                <div className="text-[11px] text-slate-500 font-medium">Meta Operativa</div>
              </div>
              <div className="w-px h-8 bg-slate-200" />
              <div className="text-center px-2">
                <div className="text-2xl font-black text-indigo-600">{metrics.average_qa_score}/100</div>
                <div className="text-[11px] text-slate-500 font-medium">Calidad Promedio</div>
              </div>
            </div>
          </div>

          {/* Grilla de Métricas Secundarias */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mt-6 pt-6 border-t border-slate-200/80">
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs text-slate-500">Total Tareas</div>
              <div className="text-lg font-bold text-slate-800">{metrics.total_tasks}</div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs text-slate-500">Completadas</div>
              <div className="text-lg font-bold text-emerald-700">{metrics.completed_tasks}</div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs text-slate-500">A Tiempo (SLA)</div>
              <div className="text-lg font-bold text-blue-700">{metrics.on_time_tasks}</div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs text-slate-500">En Riesgo (&lt;12h)</div>
              <div className="text-lg font-bold text-amber-600">{metrics.tasks_at_risk}</div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs text-slate-500">Pagos Liberados</div>
              <div className="text-base font-bold text-emerald-700">
                ${(metrics.milestone_payouts_released / 1000).toFixed(0)}k COP
              </div>
            </div>
            <div className="bg-white p-3 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-xs text-slate-500">Pagos Bloqueados</div>
              <div className="text-base font-bold text-slate-700">
                ${(metrics.milestone_payouts_pending / 1000).toFixed(0)}k COP
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Pestañas de Navegación del Módulo 3 */}
      <div className="flex border-b border-slate-200 gap-4">
        <button
          onClick={() => setActiveTab("qa")}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${activeTab === "qa" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}
        >
          📋 Control de Calidad (QA) ({tasks.length})
        </button>
        <button
          onClick={() => setActiveTab("milestones")}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${activeTab === "milestones" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}
        >
          🔐 Pagos por Hitos & Gatekeeper ({milestones.length})
        </button>
        <button
          onClick={() => setActiveTab("freelancers")}
          className={`pb-3 text-sm font-semibold border-b-2 transition-colors ${activeTab === "freelancers" ? "border-indigo-600 text-indigo-600" : "border-transparent text-slate-500 hover:text-slate-700"}`}
        >
          👥 Red de Freelancers ({freelancers.length})
        </button>
      </div>

      {/* PESTAÑA 1: Tareas y Control de Calidad (QA) */}
      {activeTab === "qa" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-slate-800">
              Tareas Asignadas y Revisiones Técnicas
            </h3>
            <span className="text-xs text-slate-500">
              Las tareas deben ser aprobadas por QA antes de que el hito sea elegible para pago.
            </span>
          </div>

          <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-600">
                <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Tarea & Proyecto</th>
                    <th className="px-4 py-3">Freelancer</th>
                    <th className="px-4 py-3">Plazo SLA</th>
                    <th className="px-4 py-3">Estado SLA</th>
                    <th className="px-4 py-3">Estado Tarea</th>
                    <th className="px-4 py-3">Puntaje QA</th>
                    <th className="px-4 py-3 text-right">Acción</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tasks.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                        No hay tareas registradas en el sistema.
                      </td>
                    </tr>
                  ) : (
                    tasks.map((task) => {
                      const isAtRisk = task.sla_status === "en_riesgo";
                      const isOverdue = task.sla_status === "vencido";
                      return (
                        <tr key={task.id} className="hover:bg-slate-50/70 transition-colors">
                          <td className="px-4 py-3">
                            <div className="font-semibold text-slate-800">{task.title}</div>
                            <div className="text-xs text-slate-400">{task.project_title || `Proyecto #${task.project_id}`}</div>
                            {task.deliverable_url && (
                              <a
                                href={task.deliverable_url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-1 text-xs text-indigo-600 hover:underline mt-1 font-medium"
                              >
                                🔗 Ver entregable técnico ↗
                              </a>
                            )}
                          </td>
                          <td className="px-4 py-3">
                            <div className="font-medium text-slate-700">{task.freelancer_name || `Freelancer #${task.assigned_freelancer_id}`}</div>
                            <div className="text-xs text-slate-400">Prioridad: {label(task.priority)}</div>
                          </td>
                          <td className="px-4 py-3 text-xs">
                            <div>{new Date(task.due_date).toLocaleDateString("es-CO", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</div>
                            <div className="text-slate-400">SLA: {task.sla_hours_allotted}h</div>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`text-xs px-2.5 py-1 rounded-full font-semibold ${isOverdue ? "bg-red-100 text-red-700" : isAtRisk ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800"}`}
                            >
                              {label(task.sla_status)}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={`text-xs px-2 py-0.5 rounded font-medium ${task.status === "completada" ? "bg-emerald-50 text-emerald-700 border border-emerald-200" : task.status === "en_qa" ? "bg-blue-50 text-blue-700 border border-blue-200 font-semibold" : task.status === "rechazado_qa" ? "bg-red-50 text-red-700 border border-red-200" : "bg-slate-100 text-slate-700"}`}
                            >
                              {label(task.status)}
                            </span>
                          </td>
                          <td className="px-4 py-3 font-semibold text-slate-800">
                            {task.qa_score !== null ? `${task.qa_score}/100` : <span className="text-slate-400 font-normal">Sin evaluar</span>}
                          </td>
                          <td className="px-4 py-3 text-right">
                            <button
                              onClick={() => handleOpenQAReview(task)}
                              className="px-3 py-1.5 text-xs font-semibold bg-indigo-50 text-indigo-700 hover:bg-indigo-100 rounded-lg transition-colors border border-indigo-200"
                            >
                              {task.qa_score !== null ? "Editar QA" : "Revisar QA"}
                            </button>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* PESTAÑA 2: Hitos y Gatekeeper de Pagos */}
      {activeTab === "milestones" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-semibold text-slate-800">
                Hitos Contractuales y Liberación de Pagos (Gatekeeper)
              </h3>
              <p className="text-xs text-slate-500">
                Regla de seguridad: Ningún pago puede liberarse sin aprobación técnica de QA Y visto bueno formal del cliente.
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {milestones.length === 0 ? (
              <div className="col-span-3 p-8 text-center text-slate-400 bg-white rounded-xl border border-slate-200">
                No hay hitos contractuales cargados para este proyecto.
              </div>
            ) : (
              milestones.map((m) => {
                const isPaid = m.payment_status === "liberado" || m.payment_status === "pagado";
                const isPending = m.payment_status === "pendiente_aprobacion";
                const canRelease = m.qa_approved && (!m.requires_client_approval || m.client_approved);

                return (
                  <div
                    key={m.id}
                    className={`bg-white rounded-xl border p-5 flex flex-col justify-between shadow-sm transition-all ${isPaid ? "border-emerald-300 ring-2 ring-emerald-500/10" : isPending ? "border-amber-300" : "border-slate-200"}`}
                  >
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                          {label(m.stage)}
                        </span>
                        <span
                          className={`text-xs px-2.5 py-0.5 rounded-full font-bold ${isPaid ? "bg-emerald-100 text-emerald-800" : isPending ? "bg-amber-100 text-amber-800" : "bg-slate-100 text-slate-600"}`}
                        >
                          {label(m.payment_status)}
                        </span>
                      </div>

                      <h4 className="text-base font-bold text-slate-900 leading-snug">{m.title}</h4>
                      <div className="text-xl font-black text-indigo-700">
                        ${m.payout_amount.toLocaleString("es-CO")} <span className="text-xs text-slate-500 font-normal">COP</span>
                      </div>

                      {m.notes && (
                        <p className="text-xs text-slate-500 bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                          {m.notes}
                        </p>
                      )}

                      {/* Checklist del Gatekeeper */}
                      <div className="space-y-2 pt-2 border-t border-slate-100 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-slate-600 flex items-center gap-1.5">
                            {m.qa_approved ? "✅" : "⏳"} Control de Calidad (QA):
                          </span>
                          <span className={`font-semibold ${m.qa_approved ? "text-emerald-700" : "text-amber-700"}`}>
                            {m.qa_approved ? "Aprobado" : "Pendiente"}
                          </span>
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-slate-600 flex items-center gap-1.5">
                            {m.client_approved ? "✅" : "⏳"} Aprobación Cliente:
                          </span>
                          <div className="flex items-center gap-1">
                            <span className={`font-semibold ${m.client_approved ? "text-emerald-700" : "text-amber-700"}`}>
                              {m.client_approved ? "Conforme" : "Pendiente"}
                            </span>
                            {!m.client_approved && !isPaid && (
                              <button
                                onClick={() => handleSimulateClientApproval(m)}
                                title="Registrar aprobación formal del cliente"
                                className="text-[10px] text-indigo-600 hover:underline ml-1"
                              >
                                (Aprobar)
                              </button>
                            )}
                          </div>
                        </div>

                        {m.released_at && (
                          <div className="flex items-center justify-between text-slate-400 pt-1 text-[11px]">
                            <span>Liberado:</span>
                            <span>{new Date(m.released_at).toLocaleDateString("es-CO")}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-5 pt-3 border-t border-slate-100">
                      {isPaid ? (
                        <div className="text-center py-2 text-xs font-bold text-emerald-700 bg-emerald-50 rounded-lg">
                          ✓ Pago Transferido al Freelancer
                        </div>
                      ) : (
                        <button
                          disabled={!canRelease}
                          onClick={() => handleOpenReleaseModal(m)}
                          className={`w-full py-2 px-3 text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-1.5 ${canRelease ? "bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm" : "bg-slate-100 text-slate-400 cursor-not-allowed"}`}
                        >
                          {canRelease ? "🔓 Liberar Pago de Hito" : "🔒 Pago Bloqueado (Faltan Aprobaciones)"}
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* PESTAÑA 3: Red de Freelancers */}
      {activeTab === "freelancers" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-slate-800">
              Red de Desarrolladores y Diseñadores Freelance
            </h3>
            <span className="text-xs text-slate-500">
              Evaluación continua de desempeño y cumplimiento de tiempos de entrega.
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {freelancers.map((f) => (
              <div key={f.id} className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm space-y-4">
                <div className="flex items-start justify-between">
                  <div>
                    <h4 className="font-bold text-slate-900">{f.user_name}</h4>
                    <p className="text-xs text-slate-500">{f.user_email}</p>
                    <span className="inline-block mt-1 bg-indigo-50 text-indigo-700 text-xs px-2 py-0.5 rounded font-medium border border-indigo-100">
                      {label(f.speciality)}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-bold text-amber-600 flex items-center gap-0.5">
                      ★ {f.rating.toFixed(1)}
                    </div>
                    <div className="text-[11px] text-slate-400">Calificación</div>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-2 text-center text-xs bg-slate-50 p-2.5 rounded-lg border border-slate-100">
                  <div>
                    <div className="font-bold text-slate-800">{(f.on_time_delivery_rate * 100).toFixed(0)}%</div>
                    <div className="text-slate-400 text-[10px]">Entregas a Tiempo</div>
                  </div>
                  <div>
                    <div className="font-bold text-slate-800">{f.completed_tasks_count}</div>
                    <div className="text-slate-400 text-[10px]">Tareas Realizadas</div>
                  </div>
                </div>

                <div>
                  <div className="text-xs font-semibold text-slate-600 mb-1.5">Habilidades Técnicas:</div>
                  <div className="flex flex-wrap gap-1">
                    {f.skills.map((s, idx) => (
                      <span key={idx} className="bg-slate-100 text-slate-700 text-[11px] px-2 py-0.5 rounded">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs pt-3 border-t border-slate-100 text-slate-500">
                  <span>Tarifa: ${f.hourly_rate.toLocaleString("es-CO")} COP/h</span>
                  <span className={f.is_available ? "text-emerald-600 font-semibold" : "text-slate-400"}>
                    {f.is_available ? "● Disponible" : "○ Ocupado"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODAL: Revisión de Control de Calidad (QA) */}
      {reviewingTask && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Auditoría de Control de Calidad (QA)</h3>
                <p className="text-xs text-slate-500">Tarea: {reviewingTask.title}</p>
              </div>
              <button onClick={() => setReviewingTask(null)} className="text-slate-400 hover:text-slate-600 text-lg">
                ✕
              </button>
            </div>

            {reviewingTask.deliverable_url && (
              <div className="p-3 bg-indigo-50/60 rounded-xl border border-indigo-100 flex items-center justify-between">
                <div>
                  <div className="text-xs text-indigo-700 font-medium">Entregable para Inspección:</div>
                  <a
                    href={reviewingTask.deliverable_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-xs font-semibold text-indigo-900 hover:underline break-all"
                  >
                    {reviewingTask.deliverable_url}
                  </a>
                </div>
                <a
                  href={reviewingTask.deliverable_url}
                  target="_blank"
                  rel="noreferrer"
                  className="px-2.5 py-1 text-xs bg-indigo-600 text-white rounded font-medium hover:bg-indigo-700"
                >
                  Abrir ↗
                </a>
              </div>
            )}

            {/* Checklist de Verificación de Calidad */}
            <div className="space-y-2">
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Checklist de Validación Técnica:
              </label>
              <div className="space-y-2 bg-slate-50 p-3.5 rounded-xl border border-slate-200">
                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!qaChecklist.responsive_design}
                    onChange={(e) => setQaChecklist({ ...qaChecklist, responsive_design: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Diseño 100% Adaptable y Móvil (Mobile-First)</span>
                </label>
                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!qaChecklist.performance_lighthouse}
                    onChange={(e) => setQaChecklist({ ...qaChecklist, performance_lighthouse: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Rendimiento y Velocidad de Carga (Lighthouse &gt;85)</span>
                </label>
                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!qaChecklist.security_xss_checked}
                    onChange={(e) => setQaChecklist({ ...qaChecklist, security_xss_checked: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Seguridad contra vulnerabilidades (CORS, Headers, XSS)</span>
                </label>
                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!qaChecklist.staging_functional}
                    onChange={(e) => setQaChecklist({ ...qaChecklist, staging_functional: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Despliegue operativo y navegación en ambiente Staging</span>
                </label>
                <label className="flex items-center gap-2.5 text-xs text-slate-700 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={!!qaChecklist.pyme_spec_met}
                    onChange={(e) => setQaChecklist({ ...qaChecklist, pyme_spec_met: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span>Cumplimiento fiel de los requerimientos de la Pyme</span>
                </label>
              </div>
            </div>

            {/* Puntaje de Calidad */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                  Puntaje de Calidad (QA Score):
                </label>
                <span className="text-sm font-black text-indigo-600">{qaScore} / 100</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={1}
                value={qaScore}
                onChange={(e) => setQaScore(Number(e.target.value))}
                className="w-full accent-indigo-600"
              />
            </div>

            {/* Retroalimentación Técnica */}
            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Feedback Técnico para el Freelancer:
              </label>
              <textarea
                value={qaFeedback}
                onChange={(e) => setQaFeedback(e.target.value)}
                placeholder="Indique hallazgos, fortalezas de la entrega o ajustes obligatorios..."
                rows={3}
                className="w-full text-xs p-3 border border-slate-300 rounded-xl focus:ring-2 focus:ring-indigo-500 focus:outline-none"
              />
            </div>

            {/* Botones de Acción */}
            <div className="flex items-center justify-end gap-3 pt-3 border-t">
              <button
                type="button"
                onClick={() => setReviewingTask(null)}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={submittingQA}
                onClick={() => submitQAReview(false)}
                className="px-4 py-2 text-xs font-bold bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 rounded-lg"
              >
                Rechazar (Solicitar Correcciones)
              </button>
              <button
                type="button"
                disabled={submittingQA}
                onClick={() => submitQAReview(true)}
                className="px-4 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm"
              >
                {submittingQA ? "Guardando..." : "✓ Aprobar Control de Calidad"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL: Liberación de Pago por Hito */}
      {releasingMilestone && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b pb-3">
              <div>
                <h3 className="text-lg font-bold text-slate-900">Liberación de Pago por Hito</h3>
                <p className="text-xs text-slate-500">{releasingMilestone.title}</p>
              </div>
              <button onClick={() => setReleasingMilestone(null)} className="text-slate-400 hover:text-slate-600 text-lg">
                ✕
              </button>
            </div>

            <div className="p-4 bg-emerald-50 rounded-xl border border-emerald-200 text-center">
              <div className="text-xs text-emerald-800 font-medium">Monto a Desembolsar:</div>
              <div className="text-2xl font-black text-emerald-700">
                ${releasingMilestone.payout_amount.toLocaleString("es-CO")} COP
              </div>
              <div className="text-[11px] text-emerald-600 mt-1">
                ✓ Auditoría QA y aprobación de cliente verificadas.
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 uppercase tracking-wider block mb-1">
                Notas de Transferencia / Comprobante:
              </label>
              <input
                type="text"
                value={releaseNotes}
                onChange={(e) => setReleaseNotes(e.target.value)}
                placeholder="Ej. Transferencia Bancolombia Ref #992812"
                className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t">
              <button
                type="button"
                onClick={() => setReleasingMilestone(null)}
                className="px-4 py-2 text-xs font-medium text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={submittingRelease}
                onClick={submitMilestoneRelease}
                className="px-4 py-2 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm"
              >
                {submittingRelease ? "Liberando..." : "Confirmar Liberación de Fondos"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
