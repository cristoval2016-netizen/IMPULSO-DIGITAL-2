import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { useAuth } from "../../auth";
import { label, type TrashedCompany } from "../../types";

export default function TrashCompaniesPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [trashed, setTrashed] = useState<TrashedCompany[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Modal de Restauración (Pregunta motivo)
  const [restoringCompany, setRestoringCompany] = useState<TrashedCompany | null>(null);
  const [restoreReason, setRestoreReason] = useState("");
  const [submittingRestore, setSubmittingRestore] = useState(false);

  // Modal de Purga Definitiva
  const [purgingCompany, setPurgingCompany] = useState<TrashedCompany | null>(null);
  const [submittingPurge, setSubmittingPurge] = useState(false);

  const loadTrash = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api<TrashedCompany[]>("/api/companies/trash");
      setTrashed(data);
    } catch (err: any) {
      setError(err.message || "Error al cargar empresas en papelera");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadTrash();
  }, []);

  const handleOpenRestore = (company: TrashedCompany) => {
    setRestoringCompany(company);
    setRestoreReason("");
    setError(null);
  };

  const handleConfirmRestore = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!restoringCompany || !restoreReason.trim()) return;

    try {
      setSubmittingRestore(true);
      setError(null);
      await api(`/api/companies/${restoringCompany.id}/restore`, {
        method: "POST",
        body: JSON.stringify({ reason: restoreReason.trim() }),
      });
      setSuccessMsg(
        `¡Empresa '${restoringCompany.name}' restaurada exitosamente! Todo su historial de diagnósticos e interacciones ya se encuentra activo en el CRM.`
      );
      setRestoringCompany(null);
      await loadTrash();
    } catch (err: any) {
      setError(err.message || "Error al restaurar la empresa");
    } finally {
      setSubmittingRestore(false);
    }
  };

  const handleConfirmPurge = async () => {
    if (!purgingCompany) return;

    try {
      setSubmittingPurge(true);
      setError(null);
      await api(`/api/companies/${purgingCompany.id}/permanent`, {
        method: "DELETE",
      });
      setSuccessMsg(`Empresa '${purgingCompany.name}' eliminada definitivamente del sistema.`);
      setPurgingCompany(null);
      await loadTrash();
    } catch (err: any) {
      setError(err.message || "Error al purgar la empresa");
    } finally {
      setSubmittingPurge(false);
    }
  };

  const totalDiagnosticsPreserved = trashed.reduce((acc, c) => acc + c.diagnostics_count, 0);
  const totalInteractionsPreserved = trashed.reduce((acc, c) => acc + c.interactions_count, 0);
  const totalProjectsPreserved = trashed.reduce((acc, c) => acc + c.projects_count, 0);

  if (loading) {
    return <div className="p-8 text-center text-slate-500">Cargando papelera de empresas...</div>;
  }

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Encabezado */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-800">Papelera de Empresas & Recuperación</h1>
            <span className="bg-amber-100 text-amber-800 text-xs px-2.5 py-1 rounded-full font-semibold">
              Historial Protegido
            </span>
          </div>
          <p className="text-sm text-slate-600 mt-1">
            Empresas dadas de baja en el CRM. Ningún dato se destruye: sus diagnósticos, contactos, llamadas y proyectos permanecen intactos para su recuperación.
          </p>
        </div>
        <div className="flex items-center gap-2 self-start md:self-auto">
          <Link
            to="/crm/empresas"
            className="px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            ← Volver a Empresas Activas
          </Link>
          <button
            onClick={loadTrash}
            className="px-3.5 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-300 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            🔄 Actualizar
          </button>
        </div>
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

      {/* Tarjeta de Resumen del Historial Preservado */}
      <div className="bg-gradient-to-r from-amber-500/10 via-slate-50 to-white p-6 rounded-2xl border border-amber-200/80 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <span className="text-xs uppercase tracking-wider font-semibold text-amber-800">
              Garantía de Preservación de Datos
            </span>
            <h2 className="text-xl font-bold text-slate-900 mt-0.5">
              {trashed.length} {trashed.length === 1 ? "Empresa en la papelera" : "Empresas en la papelera"}
            </h2>
            <p className="text-xs text-slate-600 mt-1 max-w-2xl">
              Al enviar una empresa a la papelera, desaparece de la vista diaria comercial, pero <strong>todo su historial se preserva íntegramente</strong>. {isAdmin ? "Como Administrador, puedes restaurarla con su motivo en cualquier momento." : "La restauración de empresas está restringida a los Administradores del sistema."}
            </p>
          </div>

          <div className="flex items-center gap-4 self-start md:self-auto bg-white p-3 rounded-xl border border-slate-200 shadow-sm">
            <div className="text-center px-2">
              <div className="text-xl font-black text-indigo-700">{totalDiagnosticsPreserved}</div>
              <div className="text-[10px] text-slate-500">Diagnósticos</div>
            </div>
            <div className="w-px h-7 bg-slate-200" />
            <div className="text-center px-2">
              <div className="text-xl font-black text-slate-800">{totalInteractionsPreserved}</div>
              <div className="text-[10px] text-slate-500">Interacciones</div>
            </div>
            <div className="w-px h-7 bg-slate-200" />
            <div className="text-center px-2">
              <div className="text-xl font-black text-emerald-700">{totalProjectsPreserved}</div>
              <div className="text-[10px] text-slate-500">Proyectos Staging</div>
            </div>
          </div>
        </div>
      </div>

      {/* Tabla de Empresas en Papelera */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-600">
            <thead className="bg-slate-50 text-slate-700 text-xs uppercase font-semibold border-b border-slate-200">
              <tr>
                <th className="px-4 py-3">Empresa & Sector</th>
                <th className="px-4 py-3">Eliminada el</th>
                <th className="px-4 py-3">Eliminada por</th>
                <th className="px-4 py-3">Motivo de Baja</th>
                <th className="px-4 py-3">Historial Preservado</th>
                <th className="px-4 py-3 text-right">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {trashed.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-12 text-center text-slate-400">
                    <div className="text-3xl mb-2">🗑️</div>
                    <div className="font-semibold text-slate-600">La papelera está vacía</div>
                    <div className="text-xs text-slate-400 mt-1">No hay ninguna empresa dada de baja actualmente.</div>
                  </td>
                </tr>
              ) : (
                trashed.map((comp) => (
                  <tr key={comp.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-bold text-slate-800">{comp.name}</div>
                      <div className="text-xs text-slate-400">
                        NIT: {comp.nit || "S/N"} • {label(comp.sector)} • {comp.city || "Puerto Boyacá"}
                      </div>
                      <span className="inline-block mt-1 text-[11px] bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-medium">
                        Etapa previa: {label(comp.stage)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-700">
                      {comp.deleted_at
                        ? new Date(comp.deleted_at).toLocaleDateString("es-CO", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })
                        : "—"}
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <span className="font-medium text-slate-800">{comp.deleted_by_name || "Asesor / Sistema"}</span>
                    </td>
                    <td className="px-4 py-3 text-xs max-w-xs">
                      <div className="bg-amber-50 text-amber-900 border border-amber-200/80 p-2 rounded-lg italic">
                        "{comp.delete_reason || "Sin motivo especificado"}"
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs">
                      <div className="flex flex-wrap gap-1">
                        <span className="bg-indigo-50 text-indigo-700 px-2 py-0.5 rounded font-medium">
                          {comp.diagnostics_count} diag.
                        </span>
                        <span className="bg-slate-100 text-slate-700 px-2 py-0.5 rounded font-medium">
                          {comp.interactions_count} interac.
                        </span>
                        {comp.projects_count > 0 && (
                          <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded font-medium">
                            {comp.projects_count} proyecto(s)
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {isAdmin ? (
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleOpenRestore(comp)}
                            className="px-3 py-1.5 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg shadow-sm transition-colors flex items-center gap-1"
                          >
                            <span>♻️</span> Recuperar Empresa
                          </button>
                          <button
                            onClick={() => setPurgingCompany(comp)}
                            className="px-2.5 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
                            title="Eliminación definitiva (irreversible)"
                          >
                            Purgar
                          </button>
                        </div>
                      ) : (
                        <span
                          className="text-[11px] text-slate-400 bg-slate-100 px-2.5 py-1 rounded font-medium inline-block"
                          title="Solo el Administrador tiene autorización para restaurar empresas"
                        >
                          🔒 Requiere Administrador
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL 1: Restaurar Empresa (Pregunta el motivo de la restauración) */}
      {restoringCompany && (
        createPortal(
          <div className="trash-modal-overlay">
            <section
              className="trash-modal trash-modal-restore"
              role="dialog"
              aria-modal="true"
              aria-labelledby="restore-modal-title"
              aria-describedby="restore-modal-summary"
            >
              <div className="trash-modal-heading">
                <span className="trash-modal-icon trash-modal-icon-success" aria-hidden="true">↶</span>
                <div>
                  <h2 id="restore-modal-title">Recuperar empresa</h2>
                  <p className="trash-modal-company">{restoringCompany.name}</p>
                </div>
                <button
                  type="button"
                  className="trash-modal-close"
                  aria-label="Cerrar recuperación"
                  disabled={submittingRestore}
                  onClick={() => setRestoringCompany(null)}
                >
                  ×
                </button>
              </div>

              <div className="trash-modal-description trash-modal-description-success" id="restore-modal-summary">
                <strong>Se reactivará el historial:</strong> {restoringCompany.diagnostics_count} diagnósticos, {restoringCompany.interactions_count} notas o llamadas y {restoringCompany.contacts_count} contactos.
              </div>

              <form onSubmit={handleConfirmRestore} className="restore-modal-form">
                <label className="restore-modal-label" htmlFor="restore-reason">
                  Motivo de la recuperación <span aria-hidden="true">*</span>
                  <textarea
                    id="restore-reason"
                    required
                    rows={3}
                    value={restoreReason}
                    onChange={(e) => setRestoreReason(e.target.value)}
                    placeholder="Indica por qué se recupera esta empresa."
                    className="restore-modal-textarea"
                  />
                </label>
                <p className="restore-modal-hint">
                  El motivo quedará registrado en el historial de interacciones y en la auditoría.
                </p>

                <div className="trash-modal-actions">
                  <button
                    type="button"
                    className="trash-modal-button trash-modal-button-cancel"
                    autoFocus
                    disabled={submittingRestore}
                    onClick={() => setRestoringCompany(null)}
                  >
                    Cancelar
                  </button>
                  <button
                    type="submit"
                    className="trash-modal-button trash-modal-button-success"
                    disabled={submittingRestore || !restoreReason.trim()}
                  >
                    {submittingRestore ? "Recuperando..." : "Confirmar recuperación"}
                  </button>
                </div>
              </form>
            </section>
          </div>,
          document.body
        )
      )}

      {/* MODAL 2: Purga Definitiva (Advertencia de Seguridad) */}
      {purgingCompany && (
        createPortal(
          <div className="trash-modal-overlay">
            <section
              className="trash-modal trash-modal-purge"
              role="alertdialog"
              aria-modal="true"
              aria-labelledby="purge-modal-title"
              aria-describedby="purge-modal-description"
            >
              <div className="trash-modal-heading">
                <span className="trash-modal-icon trash-modal-icon-danger" aria-hidden="true">!</span>
                <div>
                  <h2 id="purge-modal-title">Confirmar purga</h2>
                  <p className="trash-modal-company">{purgingCompany.name}</p>
                </div>
                <button
                  type="button"
                  className="trash-modal-close"
                  aria-label="Cerrar confirmación"
                  disabled={submittingPurge}
                  onClick={() => setPurgingCompany(null)}
                >
                  ×
                </button>
              </div>

              <p className="trash-modal-description trash-modal-description-danger" id="purge-modal-description">
                Esta acción es permanente. Se eliminarán la empresa y sus diagnósticos, contactos, interacciones y proyectos.
              </p>

              <div className="trash-modal-actions">
                <button
                  type="button"
                  className="trash-modal-button trash-modal-button-cancel"
                  autoFocus
                  disabled={submittingPurge}
                  onClick={() => setPurgingCompany(null)}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="trash-modal-button trash-modal-button-danger"
                  disabled={submittingPurge}
                  onClick={handleConfirmPurge}
                >
                  {submittingPurge ? "Eliminando..." : "Eliminar definitivamente"}
                </button>
              </div>
            </section>
          </div>,
          document.body
        )
      )}
    </div>
  );
}
