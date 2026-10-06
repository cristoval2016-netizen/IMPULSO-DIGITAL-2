import { useEffect, useState, type FormEvent } from "react";
import { api } from "../../api";
import { label, type SupportTicket, type TicketPriority } from "../../types";

export default function PortalTicketsPage() {
  const [tickets, setTickets] = useState<SupportTicket[]>([]);
  const [selectedTicket, setSelectedTicket] = useState<SupportTicket | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showNewModal, setShowNewModal] = useState(false);
  const [newTicket, setNewTicket] = useState<{
    subject: string;
    description: string;
    priority: TicketPriority;
  }>({
    subject: "",
    description: "",
    priority: "media",
  });
  const [replyText, setReplyText] = useState("");
  const [busy, setBusy] = useState(false);

  const loadTickets = () => {
    setLoading(true);
    api<SupportTicket[]>("/api/portal/tickets")
      .then((data) => {
        setTickets(data);
        if (data.length > 0 && !selectedTicket) {
          openTicket(data[0].id);
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  const openTicket = async (ticketId: number) => {
    try {
      const detail = await api<SupportTicket>(`/api/portal/tickets/${ticketId}`);
      setSelectedTicket(detail);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  useEffect(() => {
    loadTickets();
  }, []);

  const handleCreateTicket = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await api<SupportTicket>("/api/portal/tickets", {
        method: "POST",
        body: JSON.stringify(newTicket),
      });
      setShowNewModal(false);
      setNewTicket({ subject: "", description: "", priority: "media" });
      loadTickets();
      setSelectedTicket(created);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const handleSendReply = async (e: FormEvent) => {
    e.preventDefault();
    if (!selectedTicket || !replyText.trim()) return;
    setBusy(true);
    setError("");
    try {
      await api(`/api/portal/tickets/${selectedTicket.id}/messages`, {
        method: "POST",
        body: JSON.stringify({ message: replyText }),
      });
      setReplyText("");
      openTicket(selectedTicket.id);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Mesa de Ayuda & Soporte Posventa</h1>
          <p className="muted">
            Solicite asistencia técnica, consulte dudas sobre herramientas digitales o reporte incidencias.
          </p>
        </div>
        <button className="btn primary" onClick={() => setShowNewModal(true)}>
          + Crear Nuevo Ticket
        </button>
      </div>

      {error && <div className="alert">{error}</div>}

      <div className="grid-2">
        {/* Lista de Tickets */}
        <div className="card">
          <h3>Mis Tickets de Soporte</h3>
          {loading ? (
            <p className="muted">Cargando tickets...</p>
          ) : tickets.length === 0 ? (
            <p className="muted">No tiene tickets de soporte registrados.</p>
          ) : (
            <div className="ticket-list">
              {tickets.map((t) => (
                <div
                  key={t.id}
                  className={`ticket-item ${
                    selectedTicket?.id === t.id ? "active" : ""
                  }`}
                  onClick={() => openTicket(t.id)}
                >
                  <div className="ticket-top">
                    <span className="tag">#{t.id}</span>
                    <span className={`tag lvl-${t.status === "resuelto" ? "avanzado" : "en_desarrollo"}`}>
                      {label(t.status)}
                    </span>
                    <span className={`tag priority-${t.priority}`}>
                      {label(t.priority)}
                    </span>
                  </div>
                  <strong>{t.subject}</strong>
                  <div className="ticket-meta">
                    <small className="muted">
                      {new Date(t.created_at).toLocaleDateString("es-CO")} · {t.messages_count} mensajes
                    </small>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Detalle y Conversación del Ticket */}
        <div className="card">
          {selectedTicket ? (
            <div className="ticket-thread">
              <div className="ticket-thread-header">
                <h3>{selectedTicket.subject}</h3>
                <span className={`tag lvl-${selectedTicket.status === "resuelto" ? "avanzado" : "en_desarrollo"}`}>
                  {label(selectedTicket.status)}
                </span>
              </div>

              <div className="messages-stream">
                {(selectedTicket.messages ?? []).map((m) => (
                  <div
                    key={m.id}
                    className={`message-bubble ${
                      m.sender_role === "cliente" ? "client-bubble" : "staff-bubble"
                    }`}
                  >
                    <div className="bubble-head">
                      <strong>{m.sender_name ?? "Usuario"}</strong>
                      <small>
                        {new Date(m.created_at).toLocaleTimeString("es-CO", {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </small>
                    </div>
                    <p>{m.message}</p>
                  </div>
                ))}
              </div>

              <form onSubmit={handleSendReply} className="reply-form">
                <input
                  required
                  placeholder="Escriba su respuesta o consulta..."
                  value={replyText}
                  onChange={(e) => setReplyText(e.target.value)}
                  disabled={busy}
                />
                <button className="btn primary" disabled={busy || !replyText.trim()}>
                  {busy ? "Enviando..." : "Responder"}
                </button>
              </form>
            </div>
          ) : (
            <p className="muted center-text">Seleccione un ticket para ver la conversación.</p>
          )}
        </div>
      </div>

      {/* Modal Nuevo Ticket */}
      {showNewModal && (
        <div className="modal-backdrop">
          <form className="card modal-box" onSubmit={handleCreateTicket}>
            <h3>Abrir Ticket de Soporte</h3>
            <label>
              Asunto / Resumen del problema *
              <input
                required
                minLength={3}
                placeholder="Ej. Problema al conectar WhatsApp Business..."
                value={newTicket.subject}
                onChange={(e) =>
                  setNewTicket({ ...newTicket, subject: e.target.value })
                }
              />
            </label>
            <label>
              Prioridad *
              <select
                value={newTicket.priority}
                onChange={(e) =>
                  setNewTicket({
                    ...newTicket,
                    priority: e.target.value as TicketPriority,
                  })
                }
              >
                <option value="baja">Baja</option>
                <option value="media">Media</option>
                <option value="alta">Alta</option>
                <option value="urgente">Urgente</option>
              </select>
            </label>
            <label>
              Descripción detallada *
              <textarea
                required
                rows={4}
                placeholder="Describa el inconveniente o consulta con el mayor detalle posible..."
                value={newTicket.description}
                onChange={(e) =>
                  setNewTicket({ ...newTicket, description: e.target.value })
                }
              />
            </label>
            <div className="actions">
              <button
                type="button"
                className="btn ghost"
                onClick={() => setShowNewModal(false)}
              >
                Cancelar
              </button>
              <button type="submit" className="btn primary" disabled={busy}>
                {busy ? "Creando..." : "Enviar Ticket"}
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
