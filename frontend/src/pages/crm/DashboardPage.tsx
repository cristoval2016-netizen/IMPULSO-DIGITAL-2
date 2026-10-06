import { useEffect, useState } from "react";
import { api, downloadFile } from "../../api";
import { useAuth } from "../../auth";
import { label, type Metrics } from "../../types";

const pct = (n: number) => `${(n * 100).toFixed(1)}%`;

function Breakdown({ title, data }: { title: string; data: Record<string, number> }) {
  const total = Object.values(data).reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="card">
      <h3>{title}</h3>
      <div className="bars">
        {Object.entries(data).map(([k, v]) => (
          <div className="bar" key={k}>
            <span>{label(k)}</span>
            <div className="track"><div style={{ width: `${(v / total) * 100}%` }} /></div>
            <b>{v}</b>
          </div>
        ))}
        {!Object.keys(data).length && <p className="muted">Sin datos aún</p>}
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const [m, setM] = useState<Metrics | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api<Metrics>("/api/dashboard/metrics").then(setM).catch((e) => setError(e.message));
  }, []);

  if (error) return <div className="alert">{error}</div>;
  if (!m) return <p>Cargando…</p>;

  const onTarget = m.conversion_rate >= m.conversion_target;

  return (
    <div>
      <div className="page-head">
        <h1>Dashboard comercial</h1>
        {user?.role === "admin" && (
          <button className="btn ghost"
            onClick={() => downloadFile("/api/dashboard/export/ml-dataset.csv", "ml-dataset.csv")}>
            ⬇ Exportar dataset ML (anonimizado)
          </button>
        )}
      </div>

      <div className="kpis">
        <div className="card kpi"><small>Empresas</small><b>{m.total_companies}</b></div>
        <div className="card kpi"><small>Diagnósticos</small><b>{m.total_diagnostics}</b></div>
        <div className="card kpi"><small>Clientes pagos</small><b>{m.converted}</b></div>
        <div className={`card kpi ${onTarget ? "ok" : "warn"}`}>
          <small>Conversión (meta {pct(m.conversion_target)})</small>
          <b>{pct(m.conversion_rate)}</b>
        </div>
        <div className="card kpi"><small>Puntaje promedio</small><b>{m.average_score}</b></div>
      </div>

      <div className="grid-2">
        <Breakdown title="Pipeline" data={m.by_stage} />
        <Breakdown title="Paquete recomendado" data={m.by_package} />
        <Breakdown title="Nivel de madurez" data={m.by_level} />
        <Breakdown title="Sector económico" data={m.by_sector} />
      </div>

      <div className="card">
        <h3>Conversión por paquete recomendado</h3>
        <table>
          <thead><tr><th>Paquete</th><th>Tasa de conversión</th></tr></thead>
          <tbody>
            {Object.entries(m.conversion_by_package).map(([k, v]) => (
              <tr key={k}><td>{label(k)}</td><td>{pct(v)}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
