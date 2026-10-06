import React, { useEffect, useState, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../../api";

export interface Palm {
  id: number;
  code: str;
  lot: str;
  latitude: number;
  longitude: number;
  variety: str;
  planted_year: number;
  last_coconuts_count: number;
  annual_coconuts_count: number;
  active_bunches: number;
  health_status: "sana" | "enferma" | "muriendo";
  symptoms: str;
  diagnostic_details: str;
  treatment_plan: str | null;
  last_inspected_at: str;
  created_at: str;
}

type str = string;

interface FarmStats {
  total_hectares: number;
  total_palms: number;
  estimated_capacity: number;
  palms_density_per_ha: number;
  healthy_count: number;
  sick_count: number;
  dying_count: number;
  healthy_percentage: number;
  sick_percentage: number;
  dying_percentage: number;
  total_annual_coconuts: number;
  avg_coconuts_per_palm: number;
  lots_summary: Record<string, number>;
}

// Coordenadas de referencia de la finca de 4 Hectáreas (Puerto Boyacá)
const FARM_CENTER = { lat: 5.9750, lon: -74.5850 };
// 4 Hectáreas ~= 200m x 200m (aprox 0.0018 grados lat x 0.0018 grados lon)
const FARM_BOUNDS = {
  minLat: FARM_CENTER.lat - 0.0009,
  maxLat: FARM_CENTER.lat + 0.0009,
  minLon: FARM_CENTER.lon - 0.0009,
  maxLon: FARM_CENTER.lon + 0.0009,
};

const LOT_COLORS: Record<string, string> = {
  "Lote 1 (Norte)": "#065f46",
  "Lote 2 (Sur)": "#1e3a8a",
  "Lote 3 (Oriente)": "#701a75",
  "Lote 4 (Occidente)": "#854d0e",
};

export default function GuapiCocoPage() {
  const [palms, setPalms] = useState<Palm[]>([]);
  const [stats, setStats] = useState<FarmStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Filtros de visualización
  const [filterLot, setFilterLot] = useState<string>("todos");
  const [filterHealth, setFilterHealth] = useState<string>("todos");
  const [searchTerm, setSearchTerm] = useState("");

  // Palma seleccionada para inspección
  const [selectedPalm, setSelectedPalm] = useState<Palm | null>(null);
  const [selectedPalmPhoto, setSelectedPalmPhoto] = useState<string | null>(null);

  // Pestaña activa (mapa, censo, registrar, recomendaciones)
  const [activeTab, setActiveTab] = useState<"mapa" | "tabla" | "nueva" | "recomendaciones">("mapa");

  // Estado de geolocalización GPS del dispositivo
  const [gpsLoading, setGpsLoading] = useState(false);
  const [gpsError, setGpsError] = useState("");
  const [currentGps, setCurrentGps] = useState<{ lat: number; lon: number; accuracy: number } | null>(null);
  const [palmPhoto, setPalmPhoto] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState("");
  const photoInputRef = useRef<HTMLInputElement>(null);

  // Formulario para registrar nueva palma
  const [newPalm, setNewPalm] = useState({
    code: "",
    lot: "Lote 1 (Norte)",
    latitude: FARM_CENTER.lat,
    longitude: FARM_CENTER.lon,
    variety: "alto_pacifico",
    planted_year: 2020,
    last_coconuts_count: 14,
    annual_coconuts_count: 70,
    active_bunches: 5,
    symptoms: "Follaje verde vigoroso, sin anomalías",
  });

  // Modal para registrar cosecha rápida
  const [harvestModalPalm, setHarvestModalPalm] = useState<Palm | null>(null);
  const [harvestCount, setHarvestCount] = useState<number>(15);
  const [harvestGrade, setHarvestGrade] = useState("Primera");
  const [harvestNotes, setHarvestNotes] = useState("");

  // Cargar palmas y estadísticas
  const loadData = async () => {
    try {
      setLoading(true);
      const [palmsRes, statsRes] = await Promise.all([
        api<Palm[]>("/api/guapicoco/palms"),
        api<FarmStats>("/api/guapicoco/stats"),
      ]);
      setPalms(palmsRes);
      setStats(statsRes);
    } catch (err: any) {
      setError(err.message || "Error al cargar datos de Guapi Coco");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    let photoUrl: string | null = null;
    let cancelled = false;
    setSelectedPalmPhoto(null);
    if (selectedPalm) {
      fetch(`/api/guapicoco/palms/${selectedPalm.id}/photo`)
        .then((response) => response.ok ? response.blob() : null)
        .then((photo) => {
          if (photo && !cancelled) {
            photoUrl = URL.createObjectURL(photo);
            setSelectedPalmPhoto(photoUrl);
          }
        })
        .catch(() => {});
    }
    return () => {
      cancelled = true;
      if (photoUrl) URL.revokeObjectURL(photoUrl);
    };
  }, [selectedPalm?.id]);

  // Función para capturar coordenadas GPS del dispositivo del trabajador
  const captureGps = () => {
    if (!navigator.geolocation) {
      setGpsError("La geolocalización GPS no está soportada en este navegador/dispositivo.");
      return;
    }
    setGpsLoading(true);
    setGpsError("");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude, accuracy } = pos.coords;
        setCurrentGps({ lat: latitude, lon: longitude, accuracy: Math.round(accuracy) });
        setNewPalm((prev) => ({
          ...prev,
          latitude: Number(latitude.toFixed(6)),
          longitude: Number(longitude.toFixed(6)),
        }));
        setGpsLoading(false);
        setSuccessMsg(`📍 Coordenadas GPS fijadas con precisión de ±${Math.round(accuracy)}m.`);
        setTimeout(() => setSuccessMsg(""), 5000);
      },
      (err) => {
        setGpsLoading(false);
        setGpsError(`Error GPS: ${err.message}. Puedes usar las coordenadas calibradas en el mapa.`);
      },
      { enableHighAccuracy: true, timeout: 12000, maximumAge: 0 }
    );
  };

  const handlePalmPhoto = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    input.value = "";
    setPhotoError("");
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      setPhotoError("Selecciona un archivo de imagen válido.");
      return;
    }
    if (file.size > 15_000_000) {
      setPhotoError("La foto original no puede superar 15 MB.");
      return;
    }

    const sourceUrl = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = sourceUrl;
      await image.decode();
      const scale = Math.min(1, 1280 / Math.max(image.naturalWidth, image.naturalHeight));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(image.naturalWidth * scale);
      canvas.height = Math.round(image.naturalHeight * scale);
      const context = canvas.getContext("2d");
      if (!context) throw new Error("No se pudo procesar la fotografía.");
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const compressedPhoto = canvas.toDataURL("image/jpeg", 0.78);
      if (compressedPhoto.length > 2_000_000) {
        throw new Error("La foto comprimida supera el tamaño máximo permitido.");
      }
      setPalmPhoto(compressedPhoto);
    } catch (err) {
      setPhotoError((err as Error).message || "No se pudo procesar la fotografía.");
    } finally {
      URL.revokeObjectURL(sourceUrl);
    }
  };

  // Filtrado de palmas
  const filteredPalms = useMemo(() => {
    return palms.filter((p) => {
      const matchLot = filterLot === "todos" || p.lot === filterLot;
      const matchHealth = filterHealth === "todos" || p.health_status === filterHealth;
      const matchSearch =
        !searchTerm ||
        p.code.toLowerCase().includes(searchTerm.toLowerCase()) ||
        p.lot.toLowerCase().includes(searchTerm.toLowerCase());
      return matchLot && matchHealth && matchSearch;
    });
  }, [palms, filterLot, filterHealth, searchTerm]);

  // Guardar nueva palma
  const handleCreatePalm = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      const created = await api<Palm>("/api/guapicoco/palms", {
        method: "POST",
        body: JSON.stringify({ ...newPalm, photo_data_url: palmPhoto }),
      });
      setSuccessMsg(`¡Palma ${created.code} registrada y georreferenciada exitosamente!`);
      setTimeout(() => setSuccessMsg(""), 5000);
      setNewPalm({
        code: `GC-L${newPalm.lot.charAt(5)}-${Math.floor(100 + Math.random() * 900)}`,
        lot: newPalm.lot,
        latitude: FARM_CENTER.lat,
        longitude: FARM_CENTER.lon,
        variety: "alto_pacifico",
        planted_year: 2020,
        last_coconuts_count: 14,
        annual_coconuts_count: 70,
        active_bunches: 5,
        symptoms: "Follaje verde vigoroso, sin anomalías",
      });
      await loadData();
      setSelectedPalm(created);
      setPalmPhoto(null);
      setPhotoError("");
      setActiveTab("mapa");
    } catch (err: any) {
      setError(err.message || "Error al registrar la palma");
    }
  };

  // Registrar nueva cosecha
  const handleRecordHarvest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!harvestModalPalm) return;
    try {
      await api(`/api/guapicoco/palms/${harvestModalPalm.id}/harvest`, {
        method: "POST",
        body: JSON.stringify({
          coconuts_harvested: harvestCount,
          quality_grade: harvestGrade,
          notes: harvestNotes || "Cosecha regular",
        }),
      });
      setSuccessMsg(`Cosecha de ${harvestCount} cocos registrada para palma ${harvestModalPalm.code}.`);
      setTimeout(() => setSuccessMsg(""), 4000);
      setHarvestModalPalm(null);
      await loadData();
      if (selectedPalm?.id === harvestModalPalm.id) {
        const updated = await api<Palm>(`/api/guapicoco/palms/${harvestModalPalm.id}`);
        setSelectedPalm(updated);
      }
    } catch (err: any) {
      setError(err.message || "Error al registrar la cosecha");
    }
  };

  // Conversión de coordenadas GPS a porcentajes de posición (X, Y) en el mapa de 4 Ha
  const getMapCoordinates = (lat: number, lon: number) => {
    // Normalizar dentro de FARM_BOUNDS
    const percentX = ((lon - FARM_BOUNDS.minLon) / (FARM_BOUNDS.maxLon - FARM_BOUNDS.minLon)) * 100;
    const percentY = 100 - ((lat - FARM_BOUNDS.minLat) / (FARM_BOUNDS.maxLat - FARM_BOUNDS.minLat)) * 100;
    return {
      x: Math.max(4, Math.min(96, percentX)),
      y: Math.max(4, Math.min(96, percentY)),
    };
  };

  // Color e ícono por estado fitosanitario
  const getHealthMeta = (status: Palm["health_status"]) => {
    switch (status) {
      case "sana":
        return { label: "Sana / Óptima", color: "#10b981", bg: "#d1fae5", border: "#059669", icon: "🟢" };
      case "enferma":
        return { label: "Enferma / Alerta", color: "#f59e0b", bg: "#fef3c7", border: "#d97706", icon: "🟡" };
      case "muriendo":
        return { label: "Crítica / Muriendo", color: "#ef4444", bg: "#fee2e2", border: "#dc2626", icon: "🔴" };
      default:
        return { label: status, color: "#6b7280", bg: "#f3f4f6", border: "#9ca3af", icon: "⚪" };
    }
  };

  // Exportar censo a CSV
  const exportCsv = () => {
    if (!palms.length) return;
    const headers = [
      "Código",
      "Lote",
      "Latitud",
      "Longitud",
      "Variedad",
      "Año Siembra",
      "Cocos Última Cosecha",
      "Producción Anual",
      "Racimos Activos",
      "Estado Fitosanitario",
      "Síntomas",
      "Diagnóstico",
    ];
    const rows = palms.map((p) => [
      `"${p.code}"`,
      `"${p.lot}"`,
      p.latitude,
      p.longitude,
      `"${p.variety}"`,
      p.planted_year,
      p.last_coconuts_count,
      p.annual_coconuts_count,
      p.active_bunches,
      `"${p.health_status.toUpperCase()}"`,
      `"${p.symptoms.replace(/"/g, '""')}"`,
      `"${p.diagnostic_details.replace(/"/g, '""')}"`,
    ]);
    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `Censo_Palmas_GuapiCoco_4Ha_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div style={{ maxWidth: 1280, margin: "4rem auto", padding: "2rem", textAlign: "center", fontFamily: "system-ui, sans-serif" }}>
        <div style={{ fontSize: "3rem", marginBottom: "1rem" }}>🥥</div>
        <h2 style={{ color: "#065f46" }}>Cargando Sistema Georreferenciado Guapi Coco (4 Ha)...</h2>
        <p style={{ color: "#6b7280" }}>Sincronizando censo de palmas, cartografía de lotes y análisis fitosanitario...</p>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 1280, margin: "0 auto", padding: "1.5rem 1rem", fontFamily: "system-ui, sans-serif" }}>
      {/* Encabezado Principal */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: ".75rem" }}>
            <span style={{ fontSize: "2.4rem" }}>🥥</span>
            <div>
              <h1 style={{ margin: 0, fontSize: "1.85rem", color: "#065f46" }}>Guapi Coco · Finca Palma de Coco</h1>
              <p style={{ margin: "0.25rem 0 0", color: "#4b5563", fontSize: "0.95rem" }}>
                Sistema de Georreferenciación Satelital (4 Hectáreas), Censo de Producción y Control Fitosanitario
              </p>
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: ".5rem" }}>
          <Link to="/crm/empresas/1" className="btn ghost" style={{ textDecoration: "none" }}>
            ← Volver a CRM
          </Link>
          <Link to="/portal" className="btn ghost" style={{ textDecoration: "none" }}>
            Portal Cliente ↗
          </Link>
          <button onClick={exportCsv} className="btn primary" style={{ backgroundColor: "#065f46", borderColor: "#065f46" }}>
            📥 Exportar Censo CSV
          </button>
        </div>
      </div>

      {error && <div className="alert" style={{ marginBottom: "1rem", backgroundColor: "#fee2e2", color: "#991b1b", padding: ".75rem", borderRadius: 8 }}>{error}</div>}
      {successMsg && <div style={{ marginBottom: "1rem", backgroundColor: "#d1fae5", color: "#065f46", padding: ".75rem", borderRadius: 8, fontWeight: 600 }}>{successMsg}</div>}

      {/* KPI Cards de la Finca (4 Hectáreas) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1rem", marginBottom: "1.5rem" }}>
        <div className="card" style={{ padding: "1rem", borderLeft: "4px solid #065f46" }}>
          <small className="muted" style={{ textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 700 }}>Área Total de Finca</small>
          <div style={{ fontSize: "1.65rem", fontWeight: 800, color: "#065f46" }}>4.0 Hectáreas</div>
          <small style={{ color: "#6b7280" }}>4 Lotes delimitados (1 Ha c/u)</small>
        </div>

        <div className="card" style={{ padding: "1rem", borderLeft: "4px solid #0284c7" }}>
          <small className="muted" style={{ textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 700 }}>Censo de Palmas</small>
          <div style={{ fontSize: "1.65rem", fontWeight: 800, color: "#0284c7" }}>
            {stats?.total_palms ?? palms.length} <small style={{ fontSize: ".9rem", fontWeight: 500, color: "#6b7280" }}>/ ~560 cap.</small>
          </div>
          <small style={{ color: "#6b7280" }}>Densidad: {stats?.palms_density_per_ha ?? 0} palmas/Ha</small>
        </div>

        <div className="card" style={{ padding: "1rem", borderLeft: "4px solid #10b981" }}>
          <small className="muted" style={{ textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 700 }}>Palmas Sanas</small>
          <div style={{ fontSize: "1.65rem", fontWeight: 800, color: "#10b981" }}>
            {stats?.healthy_count ?? 0} <small style={{ fontSize: ".9rem", fontWeight: 500 }}>({stats?.healthy_percentage ?? 0}%)</small>
          </div>
          <small style={{ color: "#059669" }}>Vigorosas y productivas</small>
        </div>

        <div className="card" style={{ padding: "1rem", borderLeft: "4px solid #f59e0b" }}>
          <small className="muted" style={{ textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 700 }}>Palmas Enfermas</small>
          <div style={{ fontSize: "1.65rem", fontWeight: 800, color: "#f59e0b" }}>
            {stats?.sick_count ?? 0} <small style={{ fontSize: ".9rem", fontWeight: 500 }}>({stats?.sick_percentage ?? 0}%)</small>
          </div>
          <small style={{ color: "#d97706" }}>Baja carga o estrés</small>
        </div>

        <div className="card" style={{ padding: "1rem", borderLeft: "4px solid #ef4444" }}>
          <small className="muted" style={{ textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 700 }}>Críticas / Muriendo</small>
          <div style={{ fontSize: "1.65rem", fontWeight: 800, color: "#ef4444" }}>
            {stats?.dying_count ?? 0} <small style={{ fontSize: ".9rem", fontWeight: 500 }}>({stats?.dying_percentage ?? 0}%)</small>
          </div>
          <small style={{ color: "#dc2626" }}>Alerta fitosanitaria</small>
        </div>

        <div className="card" style={{ padding: "1rem", borderLeft: "4px solid #8b5cf6" }}>
          <small className="muted" style={{ textTransform: "uppercase", fontSize: "0.75rem", fontWeight: 700 }}>Producción Total</small>
          <div style={{ fontSize: "1.65rem", fontWeight: 800, color: "#8b5cf6" }}>
            {(stats?.total_annual_coconuts ?? 0).toLocaleString()} <small style={{ fontSize: ".85rem", fontWeight: 500 }}>cocos/año</small>
          </div>
          <small style={{ color: "#6b7280" }}>Promedio: {stats?.avg_coconuts_per_palm ?? 0} cocos/palma</small>
        </div>
      </div>

      {/* Pestañas de Navegación del Módulo */}
      <div style={{ display: "flex", gap: ".5rem", borderBottom: "2px solid #e5e7eb", marginBottom: "1.5rem" }}>
        <button
          className="btn ghost"
          onClick={() => setActiveTab("mapa")}
          style={{
            borderBottom: activeTab === "mapa" ? "3px solid #065f46" : "none",
            borderRadius: "4px 4px 0 0",
            fontWeight: activeTab === "mapa" ? 700 : 500,
            color: activeTab === "mapa" ? "#065f46" : "#4b5563",
          }}
        >
          🗺️ Mapa Satelital de las 4 Hectáreas
        </button>
        <button
          className="btn ghost"
          onClick={() => setActiveTab("tabla")}
          style={{
            borderBottom: activeTab === "tabla" ? "3px solid #065f46" : "none",
            borderRadius: "4px 4px 0 0",
            fontWeight: activeTab === "tabla" ? 700 : 500,
            color: activeTab === "tabla" ? "#065f46" : "#4b5563",
          }}
        >
          📋 Censo y Listado de Palmas ({filteredPalms.length})
        </button>
        <button
          className="btn ghost"
          onClick={() => setActiveTab("nueva")}
          style={{
            borderBottom: activeTab === "nueva" ? "3px solid #065f46" : "none",
            borderRadius: "4px 4px 0 0",
            fontWeight: activeTab === "nueva" ? 700 : 500,
            color: activeTab === "nueva" ? "#065f46" : "#4b5563",
          }}
        >
          📍 Registrar Palma con GPS
        </button>
        <button
          className="btn ghost"
          onClick={() => setActiveTab("recomendaciones")}
          style={{
            borderBottom: activeTab === "recomendaciones" ? "3px solid #065f46" : "none",
            borderRadius: "4px 4px 0 0",
            fontWeight: activeTab === "recomendaciones" ? 700 : 500,
            color: activeTab === "recomendaciones" ? "#065f46" : "#4b5563",
          }}
        >
          💡 Recomendaciones Agronómicas & Tecnológicas
        </button>
      </div>

      {/* ============================================================== */}
      {/* VISTA 1: MAPA SATELITAL INTERACTIVO (4 HECTÁREAS)              */}
      {/* ============================================================== */}
      {activeTab === "mapa" && (
        <div style={{ display: "grid", gridTemplateColumns: selectedPalm ? "1fr 380px" : "1fr", gap: "1.5rem" }}>
          <div className="card" style={{ padding: "1.25rem", position: "relative" }}>
            {/* Barra de Filtros del Mapa */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "1rem", marginBottom: "1rem" }}>
              <div style={{ display: "flex", gap: ".5rem", alignItems: "center" }}>
                <span style={{ fontWeight: 600, fontSize: "0.9rem" }}>Lote:</span>
                <select
                  value={filterLot}
                  onChange={(e) => setFilterLot(e.target.value)}
                  style={{ padding: ".35rem .6rem", borderRadius: 6, border: "1px solid #d1d5db" }}
                >
                  <option value="todos">Todos los 4 Lotes (4 Ha)</option>
                  <option value="Lote 1 (Norte)">Lote 1 (Norte) - 1 Ha</option>
                  <option value="Lote 2 (Sur)">Lote 2 (Sur) - 1 Ha</option>
                  <option value="Lote 3 (Oriente)">Lote 3 (Oriente) - 1 Ha</option>
                  <option value="Lote 4 (Occidente)">Lote 4 (Occidente) - 1 Ha</option>
                </select>

                <span style={{ fontWeight: 600, fontSize: "0.9rem", marginLeft: ".5rem" }}>Estado:</span>
                <select
                  value={filterHealth}
                  onChange={(e) => setFilterHealth(e.target.value)}
                  style={{ padding: ".35rem .6rem", borderRadius: 6, border: "1px solid #d1d5db" }}
                >
                  <option value="todos">Todos los estados</option>
                  <option value="sana">🟢 Solo Sanas</option>
                  <option value="enferma">🟡 Solo Enfermas</option>
                  <option value="muriendo">🔴 Solo Críticas / Muriendo</option>
                </select>
              </div>

              <div style={{ display: "flex", gap: ".75rem", fontSize: "0.85rem", alignItems: "center" }}>
                <span>🟢 Sana ({palms.filter((p) => p.health_status === "sana").length})</span>
                <span>🟡 Enferma ({palms.filter((p) => p.health_status === "enferma").length})</span>
                <span>🔴 Muriendo ({palms.filter((p) => p.health_status === "muriendo").length})</span>
              </div>
            </div>

            {/* Contenedor del Mapa Satelital de 4 Hectáreas */}
            <div
              style={{
                position: "relative",
                width: "100%",
                height: 540,
                backgroundColor: "#2d4a22",
                backgroundImage: `
                  radial-gradient(ellipse at center, rgba(34, 197, 94, 0.15) 0%, rgba(20, 83, 45, 0.95) 100%),
                  linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px)
                `,
                backgroundSize: "100% 100%, 40px 40px, 40px 40px",
                borderRadius: 12,
                overflow: "hidden",
                border: "3px solid #1e3a15",
                boxShadow: "inset 0 0 40px rgba(0,0,0,0.5)",
              }}
            >
              {/* División Visual de los 4 Lotes (4 Hectáreas: 2x2) */}
              <div
                style={{
                  position: "absolute",
                  left: "50%",
                  top: 0,
                  bottom: 0,
                  width: 2,
                  backgroundColor: "rgba(255, 255, 255, 0.25)",
                  borderRight: "1px dashed rgba(255, 255, 255, 0.4)",
                  zIndex: 1,
                }}
              />
              <div
                style={{
                  position: "absolute",
                  top: "50%",
                  left: 0,
                  right: 0,
                  height: 2,
                  backgroundColor: "rgba(255, 255, 255, 0.25)",
                  borderBottom: "1px dashed rgba(255, 255, 255, 0.4)",
                  zIndex: 1,
                }}
              />

              {/* Rótulos de los 4 Lotes de 1 Ha cada uno */}
              <div style={{ position: "absolute", top: 12, left: 16, color: "rgba(255,255,255,0.75)", fontSize: "0.8rem", fontWeight: 700, zIndex: 2 }}>
                LOTE 1 (NORTE) · 1 Ha
              </div>
              <div style={{ position: "absolute", top: 12, right: 16, color: "rgba(255,255,255,0.75)", fontSize: "0.8rem", fontWeight: 700, zIndex: 2 }}>
                LOTE 3 (ORIENTE) · 1 Ha
              </div>
              <div style={{ position: "absolute", bottom: 12, left: 16, color: "rgba(255,255,255,0.75)", fontSize: "0.8rem", fontWeight: 700, zIndex: 2 }}>
                LOTE 2 (SUR) · 1 Ha
              </div>
              <div style={{ position: "absolute", bottom: 12, right: 16, color: "rgba(255,255,255,0.75)", fontSize: "0.8rem", fontWeight: 700, zIndex: 2 }}>
                LOTE 4 (OCCIDENTE) · 1 Ha
              </div>

              {/* Indicador de Escala y Rosa de los Vientos */}
              <div
                style={{
                  position: "absolute",
                  bottom: 12,
                  left: "50%",
                  transform: "translateX(-50%)",
                  backgroundColor: "rgba(0, 0, 0, 0.65)",
                  color: "#fff",
                  padding: "4px 12px",
                  borderRadius: 20,
                  fontSize: "0.75rem",
                  zIndex: 3,
                  display: "flex",
                  alignItems: "center",
                  gap: ".5rem",
                }}
              >
                <span>📐 Finca 4 Hectáreas (200m × 200m)</span>
                <span>·</span>
                <span>🧭 N ↑</span>
              </div>

              {/* Render de las Palmas en el Mapa */}
              {filteredPalms.map((p) => {
                const coords = getMapCoordinates(p.latitude, p.longitude);
                const isSelected = selectedPalm?.id === p.id;
                const meta = getHealthMeta(p.health_status);

                return (
                  <div
                    key={p.id}
                    onClick={() => setSelectedPalm(p)}
                    title={`${p.code} · ${p.lot} · ${meta.label} (${p.last_coconuts_count} cocos)`}
                    className={`guapi-palm-marker${isSelected ? " selected" : ""}`}
                    style={{
                      position: "absolute",
                      left: `${coords.x}%`,
                      top: `${coords.y}%`,
                      transform: "translate(-50%, -50%)",
                      cursor: "pointer",
                      zIndex: isSelected ? 20 : 5,
                      transition: "transform 0.15s ease",
                    }}
                  >
                    <div
                      style={{
                        borderRadius: "50%",
                        backgroundColor: meta.color,
                        border: isSelected ? "3px solid #fff" : "2px solid rgba(0,0,0,0.4)",
                        boxShadow: isSelected
                          ? `0 0 15px ${meta.color}, 0 4px 8px rgba(0,0,0,0.5)`
                          : "0 2px 4px rgba(0,0,0,0.3)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        color: "#fff",
                        fontWeight: 700,
                      }}
                    >
                      🌴
                    </div>
                    {isSelected && (
                      <div
                        style={{
                          position: "absolute",
                          top: "100%",
                          left: "50%",
                          transform: "translateX(-50%)",
                          backgroundColor: "#1f2937",
                          color: "#fff",
                          padding: "2px 8px",
                          borderRadius: 4,
                          fontSize: "0.7rem",
                          whiteSpace: "nowrap",
                          marginTop: 4,
                          boxShadow: "0 2px 6px rgba(0,0,0,0.4)",
                        }}
                      >
                        {p.code}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Indicador de posición GPS actual del usuario si fue capturada */}
              {currentGps && (
                <div
                  style={{
                    position: "absolute",
                    left: `${getMapCoordinates(currentGps.lat, currentGps.lon).x}%`,
                    top: `${getMapCoordinates(currentGps.lat, currentGps.lon).y}%`,
                    transform: "translate(-50%, -50%)",
                    zIndex: 25,
                    pointerEvents: "none",
                  }}
                >
                  <div
                    style={{
                      width: 36,
                      height: 36,
                      borderRadius: "50%",
                      backgroundColor: "rgba(59, 130, 246, 0.25)",
                      border: "2px solid #3b82f6",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#3b82f6" }} />
                  </div>
                  <div style={{ position: "absolute", top: "100%", left: "50%", transform: "translateX(-50%)", backgroundColor: "#1e3a8a", color: "#fff", padding: "1px 6px", borderRadius: 4, fontSize: "0.65rem", whiteSpace: "nowrap" }}>
                    📍 Tu GPS (±{currentGps.accuracy}m)
                  </div>
                </div>
              )}
            </div>

            <p style={{ margin: "0.75rem 0 0", color: "#6b7280", fontSize: "0.85rem", textAlign: "center" }}>
              Haz clic en cualquier palma para ver su historial de cosechas, análisis fitosanitario y tratamiento recomendado.
            </p>
          </div>

          {/* Panel Lateral: Ficha Detallada de la Palma Seleccionada */}
          {selectedPalm && (
            <div className="card" style={{ padding: "1.25rem", height: "fit-content", borderTop: `4px solid ${getHealthMeta(selectedPalm.health_status).color}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.75rem" }}>
                <div>
                  <h3 style={{ margin: 0, fontSize: "1.25rem", display: "flex", alignItems: "center", gap: ".5rem" }}>
                    <span>🌴</span> {selectedPalm.code}
                  </h3>
                  <small style={{ color: "#6b7280" }}>{selectedPalm.lot} · Siembra: {selectedPalm.planted_year}</small>
                </div>
                <button
                  type="button"
                  className="btn ghost small"
                  onClick={() => setSelectedPalm(null)}
                  style={{ padding: "2px 6px" }}
                >
                  ✕
                </button>
              </div>

              {/* Badge de Estado Fitosanitario */}
              <div
                style={{
                  padding: ".5rem .75rem",
                  borderRadius: 6,
                  backgroundColor: getHealthMeta(selectedPalm.health_status).bg,
                  color: getHealthMeta(selectedPalm.health_status).border,
                  fontWeight: 700,
                  fontSize: "0.85rem",
                  marginBottom: "1rem",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <span>{getHealthMeta(selectedPalm.health_status).icon} Estado: {getHealthMeta(selectedPalm.health_status).label}</span>
                <span style={{ fontSize: "0.75rem", fontWeight: 500 }}>
                  Inspección: {new Date(selectedPalm.last_inspected_at).toLocaleDateString("es-CO")}
                </span>
              </div>

              {selectedPalmPhoto && (
                <img
                  className="palm-detail-photo"
                  src={selectedPalmPhoto}
                  alt={`Fotografía de la palma ${selectedPalm.code}`}
                />
              )}

              {/* Coordenadas GPS */}
              <div style={{ backgroundColor: "#f9fafb", padding: ".75rem", borderRadius: 8, marginBottom: "1rem", fontSize: "0.85rem" }}>
                <strong>📍 Georreferenciación GPS:</strong>
                <div style={{ marginTop: ".25rem", fontFamily: "monospace", color: "#374151" }}>
                  Lat: {selectedPalm.latitude.toFixed(6)} | Lon: {selectedPalm.longitude.toFixed(6)}
                </div>
                <div style={{ marginTop: ".25rem", color: "#6b7280" }}>
                  Variedad: <span style={{ textTransform: "capitalize" }}>{selectedPalm.variety.replace("_", " ")}</span>
                </div>
              </div>

              {/* Conteo de Producción */}
              <div style={{ marginBottom: "1rem" }}>
                <strong style={{ fontSize: "0.9rem" }}>🥥 Conteo de Producción:</strong>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: ".5rem", marginTop: ".35rem" }}>
                  <div style={{ backgroundColor: "#f3f4f6", padding: ".6rem", borderRadius: 6, textAlign: "center" }}>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#065f46" }}>
                      {selectedPalm.last_coconuts_count}
                    </div>
                    <small style={{ color: "#6b7280" }}>Última Cosecha</small>
                  </div>
                  <div style={{ backgroundColor: "#f3f4f6", padding: ".6rem", borderRadius: 6, textAlign: "center" }}>
                    <div style={{ fontSize: "1.3rem", fontWeight: 800, color: "#1e3a8a" }}>
                      {selectedPalm.annual_coconuts_count}
                    </div>
                    <small style={{ color: "#6b7280" }}>Total Acum. Año</small>
                  </div>
                </div>
                <small style={{ display: "block", marginTop: ".25rem", color: "#6b7280" }}>
                  Racimos activos: <strong>{selectedPalm.active_bunches} racimos</strong>
                </small>
              </div>

              {/* Análisis Fitosanitario y Síntomas */}
              <div style={{ marginBottom: "1rem", fontSize: "0.85rem" }}>
                <strong>🔍 Síntomas Reportados:</strong>
                <p style={{ margin: "0.25rem 0 .5rem", color: "#4b5563" }}>{selectedPalm.symptoms}</p>

                <strong>🩺 Diagnóstico Agronómico:</strong>
                <p style={{ margin: "0.25rem 0 .5rem", color: "#374151", fontWeight: 500 }}>
                  {selectedPalm.diagnostic_details}
                </p>

                {selectedPalm.treatment_plan && (
                  <div style={{ backgroundColor: "#fffbeb", borderLeft: "3px solid #f59e0b", padding: ".5rem", borderRadius: 4, marginTop: ".5rem" }}>
                    <strong style={{ color: "#92400e" }}>💊 Plan de Manejo Recomendado:</strong>
                    <p style={{ margin: "0.25rem 0 0", color: "#78350f", fontSize: "0.8rem", whiteSpace: "pre-line" }}>
                      {selectedPalm.treatment_plan}
                    </p>
                  </div>
                )}
              </div>

              {/* Botón para Registrar Cosecha en esta palma */}
              <div style={{ display: "flex", gap: ".5rem" }}>
                <button
                  type="button"
                  className="btn primary"
                  style={{ width: "100%", backgroundColor: "#065f46", borderColor: "#065f46" }}
                  onClick={() => {
                    setHarvestModalPalm(selectedPalm);
                    setHarvestCount(selectedPalm.last_coconuts_count || 15);
                  }}
                >
                  🧺 Registrar Cosecha
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* VISTA 2: LISTADO Y CENSO COMPLETO                             */}
      {/* ============================================================== */}
      {activeTab === "tabla" && (
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "1rem" }}>
            <div style={{ display: "flex", gap: ".5rem", flexWrap: "wrap" }}>
              <input
                placeholder="Buscar por código (ej. GC-L1)..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                style={{ padding: ".45rem .75rem", borderRadius: 6, border: "1px solid #d1d5db" }}
              />
              <select
                value={filterLot}
                onChange={(e) => setFilterLot(e.target.value)}
                style={{ padding: ".45rem .75rem", borderRadius: 6, border: "1px solid #d1d5db" }}
              >
                <option value="todos">Todos los lotes (4 Ha)</option>
                <option value="Lote 1 (Norte)">Lote 1 (Norte)</option>
                <option value="Lote 2 (Sur)">Lote 2 (Sur)</option>
                <option value="Lote 3 (Oriente)">Lote 3 (Oriente)</option>
                <option value="Lote 4 (Occidente)">Lote 4 (Occidente)</option>
              </select>
              <select
                value={filterHealth}
                onChange={(e) => setFilterHealth(e.target.value)}
                style={{ padding: ".45rem .75rem", borderRadius: 6, border: "1px solid #d1d5db" }}
              >
                <option value="todos">Todos los estados</option>
                <option value="sana">🟢 Sanas</option>
                <option value="enferma">🟡 Enfermas</option>
                <option value="muriendo">🔴 Críticas / Muriendo</option>
              </select>
            </div>
            <span style={{ fontSize: "0.85rem", color: "#6b7280" }}>
              Mostrando {filteredPalms.length} de {palms.length} palmas
            </span>
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.875rem" }}>
              <thead>
                <tr style={{ borderBottom: "2px solid #e5e7eb", textAlign: "left" }}>
                  <th style={{ padding: ".75rem .5rem" }}>Código</th>
                  <th>Lote</th>
                  <th>Coordenadas GPS</th>
                  <th>Variedad</th>
                  <th>Última Cosecha</th>
                  <th>Acum. Anual</th>
                  <th>Estado Fitosanitario</th>
                  <th>Diagnóstico</th>
                  <th>Acción</th>
                </tr>
              </thead>
              <tbody>
                {filteredPalms.map((p) => {
                  const meta = getHealthMeta(p.health_status);
                  return (
                    <tr key={p.id} style={{ borderBottom: "1px solid #f3f4f6" }}>
                      <td style={{ padding: ".75rem .5rem", fontWeight: 700 }}>
                        <span style={{ marginRight: ".35rem" }}>🌴</span>
                        {p.code}
                      </td>
                      <td>
                        <span style={{ color: LOT_COLORS[p.lot] || "#374151", fontWeight: 600 }}>{p.lot}</span>
                      </td>
                      <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#4b5563" }}>
                        {p.latitude.toFixed(5)}, {p.longitude.toFixed(5)}
                      </td>
                      <td style={{ textTransform: "capitalize" }}>{p.variety.replace("_", " ")}</td>
                      <td style={{ fontWeight: 700, color: "#065f46" }}>{p.last_coconuts_count} cocos</td>
                      <td style={{ fontWeight: 600 }}>{p.annual_coconuts_count} cocos</td>
                      <td>
                        <span
                          style={{
                            padding: "3px 8px",
                            borderRadius: 12,
                            fontSize: "0.75rem",
                            fontWeight: 700,
                            backgroundColor: meta.bg,
                            color: meta.border,
                            display: "inline-flex",
                            alignItems: "center",
                            gap: ".25rem",
                          }}
                        >
                          {meta.icon} {meta.label}
                        </span>
                      </td>
                      <td style={{ maxWidth: 220, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.diagnostic_details}>
                        {p.diagnostic_details}
                      </td>
                      <td>
                        <button
                          type="button"
                          className="btn ghost small"
                          onClick={() => {
                            setSelectedPalm(p);
                            setActiveTab("mapa");
                          }}
                        >
                          🔍 Ver en Mapa
                        </button>
                      </td>
                    </tr>
                  );
                })}
                {!filteredPalms.length && (
                  <tr>
                    <td colSpan={9} style={{ textAlign: "center", padding: "2rem", color: "#9ca3af" }}>
                      No se encontraron palmas con los filtros seleccionados.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* VISTA 3: REGISTRO DE NUEVA PALMA CON GEORREFERENCIACIÓN GPS   */}
      {/* ============================================================== */}
      {activeTab === "nueva" && (
        <div style={{ maxWidth: 720, margin: "0 auto" }}>
          <form className="card" onSubmit={handleCreatePalm} style={{ padding: "1.75rem" }}>
            <h2 style={{ margin: "0 0 1rem", fontSize: "1.4rem", color: "#065f46", display: "flex", alignItems: "center", gap: ".5rem" }}>
              <span>📍</span> Georreferenciar Nueva Palma de Coco (Finca 4 Ha)
            </h2>
            <p style={{ color: "#4b5563", fontSize: "0.9rem", margin: "0 0 1.5rem" }}>
              Usa el GPS de tu celular en el terreno o ingresa las coordenadas de la palma para incorporarla al censo y análisis fitosanitario.
            </p>

            {/* Capturador de GPS en Terreno */}
            <div style={{ backgroundColor: "#ecfdf5", border: "1px solid #a7f3d0", padding: "1rem", borderRadius: 8, marginBottom: "1.5rem" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: ".75rem" }}>
                <div>
                  <strong style={{ color: "#065f46" }}>📡 Georreferenciación Automática con GPS</strong>
                  <div style={{ fontSize: "0.85rem", color: "#047857" }}>
                    {currentGps
                      ? `Coordenadas capturadas: Lat ${currentGps.lat.toFixed(6)}, Lon ${currentGps.lon.toFixed(6)} (Precisión: ±${currentGps.accuracy}m)`
                      : "Párate junto a la palma y presiona el botón para tomar la ubicación exacta."}
                  </div>
                </div>
                <button
                  type="button"
                  className="btn primary"
                  disabled={gpsLoading}
                  onClick={captureGps}
                  style={{ backgroundColor: "#059669", borderColor: "#059669" }}
                >
                  {gpsLoading ? "Obteniendo GPS..." : "📍 Capturar mi posición GPS"}
                </button>
              </div>
              {gpsError && <div style={{ color: "#dc2626", fontSize: "0.8rem", marginTop: ".5rem" }}>{gpsError}</div>}
            </div>

            <div className="palm-photo-capture">
              <div className="palm-photo-heading">
                <div>
                  <strong>📷 Fotografía de la palma</strong>
                  <p>Toma una foto para adjuntarla al registro.</p>
                </div>
                <input
                  ref={photoInputRef}
                  className="palm-photo-input"
                  type="file"
                  accept="image/*"
                  capture="environment"
                  onChange={handlePalmPhoto}
                />
                <button
                  type="button"
                  className="btn primary palm-photo-button"
                  onClick={() => photoInputRef.current?.click()}
                >
                  {palmPhoto ? "Tomar otra foto" : "Tomar foto"}
                </button>
              </div>
              {photoError && <p className="palm-photo-error" role="alert">{photoError}</p>}
              {palmPhoto && (
                <div className="palm-photo-preview-wrap">
                  <img className="palm-photo-preview" src={palmPhoto} alt="Vista previa de la palma" />
                  <button type="button" className="btn ghost small" onClick={() => setPalmPhoto(null)}>
                    Quitar foto
                  </button>
                </div>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem" }}>
              <label>
                Código de Identificación de Palma *
                <input
                  required
                  placeholder="Ej. GC-L1-045"
                  value={newPalm.code}
                  onChange={(e) => setNewPalm({ ...newPalm, code: e.target.value })}
                />
              </label>

              <label>
                Lote de la Finca (1 Ha c/u) *
                <select
                  value={newPalm.lot}
                  onChange={(e) => setNewPalm({ ...newPalm, lot: e.target.value })}
                >
                  <option value="Lote 1 (Norte)">Lote 1 (Norte)</option>
                  <option value="Lote 2 (Sur)">Lote 2 (Sur)</option>
                  <option value="Lote 3 (Oriente)">Lote 3 (Oriente)</option>
                  <option value="Lote 4 (Occidente)">Lote 4 (Occidente)</option>
                </select>
              </label>

              <label>
                Latitud GPS *
                <input
                  type="number"
                  step="0.000001"
                  required
                  value={newPalm.latitude}
                  onChange={(e) => setNewPalm({ ...newPalm, latitude: Number(e.target.value) })}
                />
              </label>

              <label>
                Longitud GPS *
                <input
                  type="number"
                  step="0.000001"
                  required
                  value={newPalm.longitude}
                  onChange={(e) => setNewPalm({ ...newPalm, longitude: Number(e.target.value) })}
                />
              </label>

              <label>
                Variedad de Palma
                <select
                  value={newPalm.variety}
                  onChange={(e) => setNewPalm({ ...newPalm, variety: e.target.value })}
                >
                  <option value="alto_pacifico">Alto del Pacífico (Nativo resistente)</option>
                  <option value="hibrido_pb121">Híbrido PB-121 (Alta productividad)</option>
                  <option value="enano_amarillo">Enano Amarillo de Malasia</option>
                </select>
              </label>

              <label>
                Año de Siembra
                <input
                  type="number"
                  min={1990}
                  max={2026}
                  value={newPalm.planted_year}
                  onChange={(e) => setNewPalm({ ...newPalm, planted_year: Number(e.target.value) })}
                />
              </label>

              <label>
                Cocos en Última Cosecha / Conteo
                <input
                  type="number"
                  min={0}
                  required
                  value={newPalm.last_coconuts_count}
                  onChange={(e) => setNewPalm({ ...newPalm, last_coconuts_count: Number(e.target.value) })}
                />
              </label>

              <label>
                Producción Anual Estimada (cocos)
                <input
                  type="number"
                  min={0}
                  required
                  value={newPalm.annual_coconuts_count}
                  onChange={(e) => setNewPalm({ ...newPalm, annual_coconuts_count: Number(e.target.value) })}
                />
              </label>
            </div>

            <label style={{ marginTop: "1rem", display: "block" }}>
              Síntomas Observados y Estado del Follaje
              <textarea
                rows={3}
                value={newPalm.symptoms}
                onChange={(e) => setNewPalm({ ...newPalm, symptoms: e.target.value })}
                placeholder="Describe el estado de las hojas, presencia de orificios, amarillamiento o pudrición..."
                style={{ width: "100%", padding: ".5rem", borderRadius: 6, border: "1px solid #d1d5db" }}
              />
            </label>

            {/* Simulación en vivo del algoritmo */}
            <div style={{ backgroundColor: "#f9fafb", padding: ".75rem", borderRadius: 6, margin: "1rem 0", fontSize: "0.85rem" }}>
              <strong>💡 Diagnóstico preliminar según los datos ingresados:</strong>
              <div style={{ marginTop: ".25rem" }}>
                {newPalm.last_coconuts_count <= 2 || newPalm.symptoms.toLowerCase().includes("cogollo") || newPalm.symptoms.toLowerCase().includes("anillo rojo") ? (
                  <span style={{ color: "#dc2626", fontWeight: 700 }}>🔴 Alerta: Estado Crítico / Muriendo (Requiere intervención fitosanitaria inmediata)</span>
                ) : newPalm.last_coconuts_count < 10 || newPalm.symptoms.toLowerCase().includes("picudo") || newPalm.symptoms.toLowerCase().includes("clorosis") ? (
                  <span style={{ color: "#d97706", fontWeight: 700 }}>🟡 Alerta: Estado Enferma / En Observación (Déficit nutricional o plaga incipiente)</span>
                ) : (
                  <span style={{ color: "#059669", fontWeight: 700 }}>🟢 Óptimo: Palma Sana con buena carga productiva</span>
                )}
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: ".75rem", marginTop: "1.5rem" }}>
              <button type="button" className="btn ghost" onClick={() => setActiveTab("mapa")}>
                Cancelar
              </button>
              <button type="submit" className="btn primary" style={{ backgroundColor: "#065f46", borderColor: "#065f46" }}>
                💾 Guardar y Georreferenciar Palma
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ============================================================== */}
      {/* VISTA 4: RECOMENDACIONES TÉCNICAS & AGRONÓMICAS                */}
      {/* ============================================================== */}
      {activeTab === "recomendaciones" && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
          <div className="card" style={{ padding: "1.25rem", borderTop: "4px solid #059669" }}>
            <h3 style={{ margin: "0 0 .5rem", color: "#065f46" }}>📲 1. Operatividad en Terreno (Offline-First)</h3>
            <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
              En las zonas rurales y costeras productoras de coco (como Guapi o riberas del Magdalena Medio), la conectividad celular 3G/4G suele ser intermitente.
            </p>
            <ul style={{ fontSize: "0.85rem", color: "#374151", paddingLeft: "1.2rem", lineHeight: 1.5 }}>
              <li><strong>Almacenamiento Local (PWA & IndexedDB):</strong> Esta aplicación web puede instalarse como app nativa en teléfonos Android e iOS para guardar censos de palmas sin internet.</li>
              <li><strong>Sincronización en Lote:</strong> Al regresar a la casa de la finca o al pueblo con Wi-Fi, la app sincroniza automáticamente todas las palmas y cosechas registradas.</li>
              <li><strong>Antena GPS Externa Bluetooth:</strong> Para alcanzar precisiones centimétricas submétricas (útil para no confundir palmas adyacentes a 8 metros de distancia).</li>
            </ul>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderTop: "4px solid #0284c7" }}>
            <h3 style={{ margin: "0 0 .5rem", color: "#0369a1" }}>🏷️ 2. Placas QR / RFID en cada Palma</h3>
            <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
              Para agilizar las jornadas de cosecha de las 4 hectáreas (~560 palmas):
            </p>
            <ul style={{ fontSize: "0.85rem", color: "#374151", paddingLeft: "1.2rem", lineHeight: 1.5 }}>
              <li><strong>Placa de aluminio grabada con código QR:</strong> Clavada a 1.60 m de altura en el estípite con clavo de cobre inoxidable.</li>
              <li><strong>Escaneo Instantáneo con Cámara:</strong> El cosechador o agrónomo apunta con su celular, la web abre automáticamente la ficha de la palma y permite digitar el número de cocos en 3 segundos.</li>
              <li><strong>Evita errores humanos:</strong> Asegura que el conteo se atribuya a la coordenada GPS correcta sin equivocaciones de lote.</li>
            </ul>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderTop: "4px solid #f59e0b" }}>
            <h3 style={{ margin: "0 0 .5rem", color: "#d97706" }}>🪲 3. Manejo Fitosanitario del Picudo Negro</h3>
            <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
              El <strong>Picudo Negro (<em>Rhynchophorus palmarum</em>)</strong> es el principal vector del nematodo causante del <strong>Anillo Rojo</strong>, mortal para el cocotero.
            </p>
            <ul style={{ fontSize: "0.85rem", color: "#374151", paddingLeft: "1.2rem", lineHeight: 1.5 }}>
              <li><strong>Trampeo con Feromonas:</strong> Instalar trampas con feromona sintética (Rhyncolur) y trozos de caña de azúcar o piña fermentada en los bordes de la finca (1 trampa por hectárea = 4 trampas).</li>
              <li><strong>Protocolo de Erradicación:</strong> Cualquier palma con anillo rojo confirmado debe derribarse, picarse y tratarse con insecticida o cal viva para evitar focos de infestación a las palmas sanas.</li>
            </ul>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderTop: "4px solid #8b5cf6" }}>
            <h3 style={{ margin: "0 0 .5rem", color: "#6d28d9" }}>🧪 4. Nutrición y Fertilidad Específica</h3>
            <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
              El cocotero es una de las pocas plantas que demanda <strong>Cloro (Cl-)</strong> como micronutriente esencial para regular la apertura estomática y el llenado de agua de coco.
            </p>
            <ul style={{ fontSize: "0.85rem", color: "#374151", paddingLeft: "1.2rem", lineHeight: 1.5 }}>
              <li><strong>Cloruro de Potasio (KCl):</strong> 1.5 a 2.0 kg/palma/año repartido en dos aplicaciones en época de lluvia.</li>
              <li><strong>Sal Marina / Común (NaCl):</strong> 1.0 a 1.5 kg/palma/año en corona circular. Incrementa el peso del endospermo y la cantidad de frutos por racimo en un 25-30%.</li>
            </ul>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderTop: "4px solid #ef4444" }}>
            <h3 style={{ margin: "0 0 .5rem", color: "#b91c1c" }}>🚁 5. Drones con Cámara Multiespectral (NDVI)</h3>
            <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
              Para una finca de 4 hectáreas, un vuelo de dron de solo 15 minutos proporciona información crucial:
            </p>
            <ul style={{ fontSize: "0.85rem", color: "#374151", paddingLeft: "1.2rem", lineHeight: 1.5 }}>
              <li><strong>Índice de Vigor Vegetativo (NDVI):</strong> Detecta clorosis o marchitez en el cogollo hasta 3 semanas antes de que el ojo humano lo perciba en el suelo.</li>
              <li><strong>Cálculo Automático de Copas:</strong> Permite cotejar el censo digital con la ortofoto aérea exacta de las 4 hectáreas.</li>
            </ul>
          </div>

          <div className="card" style={{ padding: "1.25rem", borderTop: "4px solid #0891b2" }}>
            <h3 style={{ margin: "0 0 .5rem", color: "#0e7490" }}>🏷️ 6. Trazabilidad y Certificación de Origen</h3>
            <p style={{ fontSize: "0.9rem", color: "#4b5563" }}>
              Cada coco comercializado puede trazarse hasta la palma exacta y el lote de origen:
            </p>
            <ul style={{ fontSize: "0.85rem", color: "#374151", paddingLeft: "1.2rem", lineHeight: 1.5 }}>
              <li>Permite acceder a compradores premium de agua de coco embotellada y aceite virgen orgánico con sobreprecio de hasta el 40%.</li>
              <li>Cumple con la normativa ICA de registro de predio productor y Buenas Prácticas Agrícolas (BPA).</li>
            </ul>
          </div>
        </div>
      )}

      {/* Modal para Registrar Cosecha */}
      {harvestModalPalm && (
        <div className="modal-backdrop" style={{ position: "fixed", inset: 0, backgroundColor: "rgba(0,0,0,0.5)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
          <form className="card modal-box" onSubmit={handleRecordHarvest} style={{ maxWidth: 440, width: "90%", padding: "1.5rem" }}>
            <h3 style={{ margin: "0 0 .5rem", color: "#065f46" }}>🧺 Registrar Cosecha de Cocos</h3>
            <p style={{ color: "#6b7280", fontSize: "0.85rem", margin: "0 0 1rem" }}>
              Palma: <strong>{harvestModalPalm.code}</strong> ({harvestModalPalm.lot})
            </p>

            <label>
              Cocos cosechados en este pase *
              <input
                type="number"
                min={1}
                max={50}
                required
                value={harvestCount}
                onChange={(e) => setHarvestCount(Number(e.target.value))}
              />
            </label>

            <label>
              Calidad del fruto
              <select value={harvestGrade} onChange={(e) => setHarvestGrade(e.target.value)}>
                <option value="Primera">Primera Calidad (Grande / Agua abundante)</option>
                <option value="Segunda">Segunda Calidad (Mediano)</option>
                <option value="Industrial">Industrial (Extracción de aceite / copra)</option>
              </select>
            </label>

            <label>
              Observaciones / Novedad agronómica
              <input
                placeholder="Ej. Frutos bien formados, sin signos de ataque"
                value={harvestNotes}
                onChange={(e) => setHarvestNotes(e.target.value)}
              />
            </label>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: ".5rem", marginTop: "1.25rem" }}>
              <button type="button" className="btn ghost" onClick={() => setHarvestModalPalm(null)}>
                Cancelar
              </button>
              <button type="submit" className="btn primary" style={{ backgroundColor: "#065f46", borderColor: "#065f46" }}>
                Guardar Cosecha
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
