import { useEffect, useState } from "react";
import { api } from "../../api";
import { label, type TrainingMaterial } from "../../types";

export default function PortalTrainingPage() {
  const [materials, setMaterials] = useState<TrainingMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");

  useEffect(() => {
    setLoading(true);
    api<TrainingMaterial[]>("/api/portal/training")
      .then(setMaterials)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const categories = Array.from(new Set(materials.map((m) => m.category)));
  const filtered = categoryFilter
    ? materials.filter((m) => m.category === categoryFilter)
    : materials;

  return (
    <div>
      <div className="page-head">
        <div>
          <h1>Centro de Capacitación & Autonomía Digital</h1>
          <p className="muted">
            Manuales prácticos y tutoriales en video paso a paso para que su equipo domine las herramientas digitales entregadas.
          </p>
        </div>
      </div>

      {error && <div className="alert">{error}</div>}

      {/* Filtro por Categoría */}
      <div className="card filters-simple">
        <button
          className={`btn ${categoryFilter === "" ? "primary" : "ghost"}`}
          onClick={() => setCategoryFilter("")}
        >
          Todos los módulos ({materials.length})
        </button>
        {categories.map((c) => (
          <button
            key={c}
            className={`btn ${categoryFilter === c ? "primary" : "ghost"}`}
            onClick={() => setCategoryFilter(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="card">Cargando material educativo...</div>
      ) : filtered.length === 0 ? (
        <div className="card">
          <p className="muted">No hay capacitaciones disponibles en esta categoría.</p>
        </div>
      ) : (
        <div className="training-grid">
          {filtered.map((item) => (
            <div key={item.id} className="card training-card">
              <div className="training-header">
                <span className="tag">{item.category}</span>
                {item.package_required && (
                  <span className="tag lvl-intermedio">
                    {label(item.package_required)}
                  </span>
                )}
                {item.duration_minutes && (
                  <small className="muted">⏱ {item.duration_minutes} min</small>
                )}
              </div>

              <h3>{item.title}</h3>
              <p>{item.description}</p>

              <div className="training-actions">
                {item.video_url && (
                  <a
                    href={item.video_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn primary small"
                  >
                    ▶ Ver Video Tutorial
                  </a>
                )}
                {item.manual_url && (
                  <a
                    href={item.manual_url}
                    target="_blank"
                    rel="noreferrer"
                    className="btn ghost small"
                  >
                    📄 Descargar Manual PDF
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
