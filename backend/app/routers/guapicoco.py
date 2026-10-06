"""Módulo Guapi Coco: Georreferenciación, Censo y Fitosanidad de Palma de Coco (Finca 4 Ha).

Funcionalidades:
- Censo georreferenciado de palmas de coco por hectárea/lote (Finca 4 Ha).
- Captura de coordenadas GPS en tiempo real.
- Registro y conteo de producción por palma (cocos/racimo, producción anual).
- Diagnóstico fitosanitario automático basado en umbrales de producción y sintomatología.
"""
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
    select,
)
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.database import Base, get_db

router = APIRouter(prefix="/api/guapicoco", tags=["Guapi Coco - Palma de Coco"])


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Modelos de Base de Datos
# ---------------------------------------------------------------------------
class PalmHealthStatus(str, enum.Enum):
    SANA = "sana"
    ENFERMA = "enferma"
    MURIENDO = "muriendo"


class PalmVariety(str, enum.Enum):
    ALTO_PACIFICO = "alto_pacifico"
    ENANO_AMARILLO = "enano_amarillo"
    HIBRIDO_PB121 = "hibrido_pb121"


class CoconutPalm(Base):
    __tablename__ = "guapicoco_palms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    lot: Mapped[str] = mapped_column(String(30), default="Lote 1 (Norte)")  # Lote 1 a 4
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    variety: Mapped[str] = mapped_column(String(50), default="alto_pacifico")
    planted_year: Mapped[int] = mapped_column(Integer, default=2019)

    # Conteo de producción
    last_coconuts_count: Mapped[int] = mapped_column(Integer, default=15)  # Cocos en última cosecha
    annual_coconuts_count: Mapped[int] = mapped_column(Integer, default=75)  # Acumulado anual
    active_bunches: Mapped[int] = mapped_column(Integer, default=6)  # Racimos activos

    # Diagnóstico y Fitosanidad
    health_status: Mapped[PalmHealthStatus] = mapped_column(
        SqlEnum(PalmHealthStatus, native_enum=False), default=PalmHealthStatus.SANA
    )
    symptoms: Mapped[str] = mapped_column(Text, default="Follaje verde vigoroso, sin anomalías")
    diagnostic_details: Mapped[str] = mapped_column(
        Text, default="Palma en óptima producción y sanidad foliar."
    )
    treatment_plan: Mapped[str | None] = mapped_column(Text, nullable=True)

    last_inspected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    harvest_logs: Mapped[list["PalmHarvestLog"]] = relationship(
        "PalmHarvestLog", back_populates="palm", cascade="all, delete-orphan", order_by="desc(PalmHarvestLog.harvest_date)"
    )


class PalmHarvestLog(Base):
    __tablename__ = "guapicoco_harvest_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    palm_id: Mapped[int] = mapped_column(Integer, ForeignKey("guapicoco_palms.id"), nullable=False)
    harvest_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    coconuts_harvested: Mapped[int] = mapped_column(Integer, nullable=False)
    quality_grade: Mapped[str] = mapped_column(String(20), default="Primera")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    palm: Mapped[CoconutPalm] = relationship("CoconutPalm", back_populates="harvest_logs")


# ---------------------------------------------------------------------------
# Algoritmo de Diagnóstico Fitosanitario
# ---------------------------------------------------------------------------
def analyze_palm_health(
    coconuts_last_harvest: int,
    annual_estimate: int,
    symptoms_text: str,
) -> tuple[PalmHealthStatus, str, str]:
    """Evalúa la sanidad de la palma según producción esperada y signos patológicos.

    Estándares agronómicos para Palma de Coco en el Pacífico / Trópico húmedo:
    - Óptimo: > 60 cocos/año o >= 12 cocos por cosecha.
    - Alerta (Enferma): 20 a 50 cocos/año o 4 a 11 cocos por cosecha o síntomas de clorosis/picudo.
    - Crítico (Muriendo): < 15 cocos/año o <= 3 cocos o signos de pudrición de cogollo o anillo rojo.
    """
    symptoms_lower = symptoms_text.lower()

    # Signos críticos letales
    is_lethal = any(
        kw in symptoms_lower
        for kw in [
            "anillo rojo",
            "pudricion de cogollo",
            "pudrición de cogollo",
            "flecha colapsada",
            "cogollo podrido",
            "muerte descendente",
            "necrosis apical",
        ]
    )
    # Signos de enfermedad intermedia
    is_sick = any(
        kw in symptoms_lower
        for kw in [
            "picudo",
            "rhynchophorus",
            "clorosis",
            "amarillamiento",
            "hojas caidas",
            "aserrin",
            "aserrín",
            "caida prematura",
            "caída prematura",
            "manchas foliares",
            "deficit potasio",
            "déficit",
        ]
    )

    if is_lethal or coconuts_last_harvest <= 2 or annual_estimate < 15:
        status = PalmHealthStatus.MURIENDO
        diagnostic = (
            "ESTADO CRÍTICO: Colapso productivo severo o sintomatología letal (posible Pudrición "
            "de Cogollo o Marchitez por Anillo Rojo transmitido por picudo negro)."
        )
        treatment = (
            "1. Aislar inmediatamente la palma del resto del lote. "
            "2. Tomar muestra fitopatológica. "
            "3. En caso de Anillo Rojo confirmado, erradicación sanitaria y quema/entierro con cal "
            "para evitar contagio a palmas colindantes en un radio de 50 metros. "
            "4. Colocar trampas con feromonas Rhyncolur en el perímetro."
        )
    elif is_sick or coconuts_last_harvest < 10 or annual_estimate < 50:
        status = PalmHealthStatus.ENFERMA
        diagnostic = (
            "ESTADO DE ALERTA: Rendimiento inferior al potencial agronómico con signos de estrés "
            "fitosanitario o nutricional."
        )
        treatment = (
            "1. Monitoreo intensivo de estípite buscando orificios de entrada de Rhynchophorus palmarum. "
            "2. Plan de fertilización foliar y edáfica: aplicar Cloruro de Potasio (KCl) 2 kg/palma "
            "y Sal Común (NaCl) 1.5 kg/palma (esencial para palmas de coco). "
            "3. Poda sanitaria de hojas bajeras cloróticas."
        )
    else:
        status = PalmHealthStatus.SANA
        diagnostic = "ESTADO ÓPTIMO: Excelente nivel de floración, carga productiva y vigor foliar."
        treatment = (
            "Mantener plan de nutrición semestral y desmalezado circular (plateo) en radio de 1.5 metros."
        )

    return status, diagnostic, treatment


# ---------------------------------------------------------------------------
# Esquemas Pydantic
# ---------------------------------------------------------------------------
class PalmIn(BaseModel):
    code: str = Field(..., example="PC-L1-001")
    lot: str = Field("Lote 1 (Norte)", example="Lote 1 (Norte)")
    latitude: float = Field(..., example=5.975412)
    longitude: float = Field(..., example=-74.585123)
    variety: str = "alto_pacifico"
    planted_year: int = 2019
    last_coconuts_count: int = Field(15, ge=0)
    annual_coconuts_count: int = Field(75, ge=0)
    active_bunches: int = Field(6, ge=0)
    symptoms: str = "Follaje verde vigoroso, sin anomalías"


class PalmUpdateIn(BaseModel):
    lot: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    variety: str | None = None
    planted_year: int | None = None
    last_coconuts_count: int | None = None
    annual_coconuts_count: int | None = None
    active_bunches: int | None = None
    symptoms: str | None = None


class HarvestLogCreateIn(BaseModel):
    coconuts_harvested: int = Field(..., ge=1)
    quality_grade: str = "Primera"
    notes: str | None = None


class HarvestLogOut(BaseModel):
    id: int
    palm_id: int
    harvest_date: datetime
    coconuts_harvested: int
    quality_grade: str
    notes: str | None

    class Config:
        from_attributes = True


class PalmOut(BaseModel):
    id: int
    code: str
    lot: str
    latitude: float
    longitude: float
    variety: str
    planted_year: int
    last_coconuts_count: int
    annual_coconuts_count: int
    active_bunches: int
    health_status: PalmHealthStatus
    symptoms: str
    diagnostic_details: str
    treatment_plan: str | None
    last_inspected_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class FarmStatsOut(BaseModel):
    total_hectares: float = 4.0
    total_palms: int
    estimated_capacity: int = 560
    palms_density_per_ha: float
    healthy_count: int
    sick_count: int
    dying_count: int
    healthy_percentage: float
    sick_percentage: float
    dying_percentage: float
    total_annual_coconuts: int
    avg_coconuts_per_palm: float
    lots_summary: dict[str, int]


# ---------------------------------------------------------------------------
# Endpoints API
# ---------------------------------------------------------------------------
@router.get("/palms", response_model=list[PalmOut])
def list_palms(
    lot: str | None = None,
    health: PalmHealthStatus | None = None,
    db: Session = Depends(get_db),
) -> list[CoconutPalm]:
    """Lista las palmas de coco georreferenciadas con opción de filtrado."""
    stmt = select(CoconutPalm).order_by(CoconutPalm.id.asc())
    if lot:
        stmt = stmt.where(CoconutPalm.lot == lot)
    if health:
        stmt = stmt.where(CoconutPalm.health_status == health)
    return list(db.scalars(stmt).all())


@router.get("/palms/{palm_id}", response_model=PalmOut)
def get_palm(palm_id: int, db: Session = Depends(get_db)) -> CoconutPalm:
    palm = db.get(CoconutPalm, palm_id)
    if not palm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Palma no encontrada")
    return palm


@router.post("/palms", response_model=PalmOut, status_code=status.HTTP_201_CREATED)
def create_palm(data: PalmIn, db: Session = Depends(get_db)) -> CoconutPalm:
    """Registra una nueva palma de coco con coordenadas GPS y análisis inicial de salud."""
    existing = db.scalar(select(CoconutPalm).where(CoconutPalm.code == data.code))
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Ya existe una palma registrada con el código {data.code}"
        )

    health_status, diag, treat = analyze_palm_health(
        data.last_coconuts_count, data.annual_coconuts_count, data.symptoms
    )

    palm = CoconutPalm(
        code=data.code,
        lot=data.lot,
        latitude=data.latitude,
        longitude=data.longitude,
        variety=data.variety,
        planted_year=data.planted_year,
        last_coconuts_count=data.last_coconuts_count,
        annual_coconuts_count=data.annual_coconuts_count,
        active_bunches=data.active_bunches,
        health_status=health_status,
        symptoms=data.symptoms,
        diagnostic_details=diag,
        treatment_plan=treat,
        last_inspected_at=utcnow(),
    )
    db.add(palm)
    db.commit()
    db.refresh(palm)
    return palm


@router.patch("/palms/{palm_id}", response_model=PalmOut)
def update_palm(palm_id: int, data: PalmUpdateIn, db: Session = Depends(get_db)) -> CoconutPalm:
    """Actualiza datos de la palma, conteo de cosecha y re-calcula diagnóstico fitosanitario."""
    palm = db.get(CoconutPalm, palm_id)
    if not palm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Palma no encontrada")

    updates = data.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(palm, k, v)

    # Re-evaluar estado fitosanitario con los datos actualizados
    health_status, diag, treat = analyze_palm_health(
        palm.last_coconuts_count, palm.annual_coconuts_count, palm.symptoms
    )
    palm.health_status = health_status
    palm.diagnostic_details = diag
    palm.treatment_plan = treat
    palm.last_inspected_at = utcnow()

    db.commit()
    db.refresh(palm)
    return palm


@router.delete("/palms/{palm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_palm(palm_id: int, db: Session = Depends(get_db)):
    palm = db.get(CoconutPalm, palm_id)
    if not palm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Palma no encontrada")
    db.delete(palm)
    db.commit()


@router.post("/palms/{palm_id}/harvest", response_model=HarvestLogOut)
def record_harvest(
    palm_id: int, data: HarvestLogCreateIn, db: Session = Depends(get_db)
) -> PalmHarvestLog:
    """Registra una cosecha para una palma y actualiza sus contadores de producción."""
    palm = db.get(CoconutPalm, palm_id)
    if not palm:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Palma no encontrada")

    log = PalmHarvestLog(
        palm_id=palm.id,
        coconuts_harvested=data.coconuts_harvested,
        quality_grade=data.quality_grade,
        notes=data.notes,
    )
    db.add(log)

    # Actualizar conteo de la palma
    palm.last_coconuts_count = data.coconuts_harvested
    palm.annual_coconuts_count += data.coconuts_harvested
    health_status, diag, treat = analyze_palm_health(
        palm.last_coconuts_count, palm.annual_coconuts_count, palm.symptoms
    )
    palm.health_status = health_status
    palm.diagnostic_details = diag
    palm.treatment_plan = treat
    palm.last_inspected_at = utcnow()

    db.commit()
    db.refresh(log)
    return log


@router.get("/stats", response_model=FarmStatsOut)
def get_farm_stats(db: Session = Depends(get_db)) -> FarmStatsOut:
    """Calcula las métricas consolidadas de la finca de 4 hectáreas."""
    palms = list(db.scalars(select(CoconutPalm)).all())
    total = len(palms)

    healthy = sum(1 for p in palms if p.health_status == PalmHealthStatus.SANA)
    sick = sum(1 for p in palms if p.health_status == PalmHealthStatus.ENFERMA)
    dying = sum(1 for p in palms if p.health_status == PalmHealthStatus.MURIENDO)

    total_annual = sum(p.annual_coconuts_count for p in palms)
    avg_per_palm = round(total_annual / total, 1) if total > 0 else 0.0

    lots_summary: dict[str, int] = {}
    for p in palms:
        lots_summary[p.lot] = lots_summary.get(p.lot, 0) + 1

    return FarmStatsOut(
        total_hectares=4.0,
        total_palms=total,
        estimated_capacity=560,
        palms_density_per_ha=round(total / 4.0, 1),
        healthy_count=healthy,
        sick_count=sick,
        dying_count=dying,
        healthy_percentage=round((healthy / total * 100), 1) if total > 0 else 0.0,
        sick_percentage=round((sick / total * 100), 1) if total > 0 else 0.0,
        dying_percentage=round((dying / total * 100), 1) if total > 0 else 0.0,
        total_annual_coconuts=total_annual,
        avg_coconuts_per_palm=avg_per_palm,
        lots_summary=lots_summary,
    )


@router.post("/seed-demo")
def seed_demo_farm(db: Session = Depends(get_db)):
    """Inicializa la finca de 4 hectáreas con un conjunto representativo de 40 palmas georreferenciadas."""
    if db.scalar(select(CoconutPalm).limit(1)):
        return {"message": "La finca ya contiene palmas censadas", "total": db.scalar(select(func.count(CoconutPalm.id)))}

    # Centro de la finca en Puerto Boyacá (Finca Guapi Coco - 4 Hectáreas: ~200m x 200m)
    # 1 grado de latitud ~= 111,111 m -> 100m ~= 0.0009 grados
    center_lat = 5.9750
    center_lon = -74.5850

    lots = [
        ("Lote 1 (Norte)", 0.0004, -0.0004),
        ("Lote 2 (Sur)", -0.0004, -0.0004),
        ("Lote 3 (Oriente)", 0.0004, 0.0004),
        ("Lote 4 (Occidente)", -0.0004, 0.0004),
    ]

    palms_to_create: list[CoconutPalm] = []
    palm_id = 1

    for lot_name, d_lat, d_lon in lots:
        for r in range(3):
            for c in range(3):
                code = f"GC-{lot_name[:2].upper()}{r+1}{c+1}-{palm_id:03d}"
                lat = center_lat + d_lat + (r - 1) * 0.00025
                lon = center_lon + d_lon + (c - 1) * 0.00025

                # Distribuir algunos casos de salud para demostración realista
                if palm_id in (5, 14, 22):
                    last_coconuts = 6
                    annual = 35
                    symptoms = "Clorosis foliar moderada en hojas bajeras y presencia de perforación de picudo negro"
                elif palm_id in (8, 29):
                    last_coconuts = 1
                    annual = 8
                    symptoms = "Necrosis apical severa, flecha colapsada y pudrición de cogollo evidente"
                else:
                    last_coconuts = 14 + (palm_id % 7)
                    annual = 70 + (palm_id % 25)
                    symptoms = "Follaje verde vigoroso, racimos cargados y excelente desarrollo foliar"

                health_status, diag, treat = analyze_palm_health(last_coconuts, annual, symptoms)

                palms_to_create.append(
                    CoconutPalm(
                        code=code,
                        lot=lot_name,
                        latitude=round(lat, 6),
                        longitude=round(lon, 6),
                        variety="alto_pacifico" if palm_id % 2 == 0 else "hibrido_pb121",
                        planted_year=2018 + (palm_id % 4),
                        last_coconuts_count=last_coconuts,
                        annual_coconuts_count=annual,
                        active_bunches=max(2, last_coconuts // 2),
                        health_status=health_status,
                        symptoms=symptoms,
                        diagnostic_details=diag,
                        treatment_plan=treat,
                        last_inspected_at=utcnow(),
                    )
                )
                palm_id += 1

    db.add_all(palms_to_create)
    db.commit()
    return {"message": "Finca Guapi Coco de 4 Hectáreas poblada exitosamente", "palms_created": len(palms_to_create)}
