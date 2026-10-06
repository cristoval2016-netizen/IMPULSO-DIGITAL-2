import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";
import { label, type CompanySummary } from "../../types";

const PAGE_SIZE = 20;

export default function CompaniesPage() {
  const [items, setItems] = useState<CompanySummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({ search: "", sector: "", stage: "", package: "", level: "" });
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE) });
    Object.entries(filters).forEach(([k, v]) => v && params.set(k, v));
    const t = setTimeout(() => {
      api<{ total: number; items: CompanySummary[] }>(`/api/companies?${params}`)
        .then((r) => { setItems(r.items); setTotal(r.total); })
        .catch((e) => setError(e.message));
    }, 250);
    return () => clearTimeout(t);
  }, [filters, page]);

  const setF = (k: keyof typeof filters) => (e: { target: { value: string } }) => {
    setPage(1);
    setFilters({ ...filters, [k]: e.target.value });
  };

  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div>
      <div className="page-head"><h1>Empresas <small className="muted">({total})</small></h1></div>
      {error && <div className="alert">{error}</div>}

      <div className="filters card">
        <input placeholder="Buscar por nombre, NIT o ciudad" value={filters.search} onChange={setF("search")} />
        <select value={filters.sector} onChange={setF("sector")}>
          <option value="">Todos los sectores</option>
          {["comercio", "servicios", "manufactura"].map((s) => <option key={s} value={s}>{label(s)}</option>)}
        </select>
        <select value={filters.stage} onChange={setF("stage")}>
          <option value="">Todas las etapas</option>
          {["nuevo", "contactado", "propuesta", "negociacion", "ganado", "perdido"].map((s) =>
            <option key={s} value={s}>{label(s)}</option>)}
        </select>
        <select value={filters.level} onChange={setF("level")}>
          <option value="">Todos los niveles</option>
          {["inicial", "en_desarrollo", "intermedio", "avanzado"].map((s) =>
            <option key={s} value={s}>{label(s)}</option>)}
        </select>
        <select value={filters.package} onChange={setF("package")}>
          <option value="">Todos los paquetes</option>
          {["impulso_basico", "impulso_integral", "impulso_premium"].map((s) =>
            <option key={s} value={s}>{label(s)}</option>)}
        </select>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr><th>Empresa</th><th>Sector</th><th>Ciudad</th><th>Puntaje</th><th>Nivel</th>
              <th>Paquete</th><th>Etapa</th><th>Registro</th></tr>
          </thead>
          <tbody>
            {items.map((c) => (
              <tr key={c.id}>
                <td><Link to={`/crm/empresas/${c.id}`}>{c.name}</Link><br /><small className="muted">{c.nit}</small></td>
                <td>{label(c.sector)}</td>
                <td>{c.city ?? "—"}</td>
                <td>{c.latest_score ?? "—"}</td>
                <td><span className={`tag lvl-${c.latest_level}`}>{label(c.latest_level)}</span></td>
                <td>{label(c.latest_package)}</td>
                <td><span className={`tag stage-${c.stage}`}>{label(c.stage)}</span></td>
                <td>{new Date(c.created_at).toLocaleDateString("es-CO")}</td>
              </tr>
            ))}
            {!items.length && <tr><td colSpan={8} className="muted">No hay empresas con esos filtros.</td></tr>}
          </tbody>
        </table>
        <div className="pager">
          <button className="btn ghost" disabled={page <= 1} onClick={() => setPage(page - 1)}>←</button>
          <span>Página {page} de {pages}</span>
          <button className="btn ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>→</button>
        </div>
      </div>
    </div>
  );
}
