"""Banco de preguntas del diagnóstico de madurez digital.

Cada pregunta pertenece a una dimensión y cada opción otorga entre 0 y 4 puntos.
Para cambiar el cuestionario, incrementa QUESTIONNAIRE_VERSION: los diagnósticos
históricos conservan la versión con la que fueron respondidos (útil para ML).
"""
from __future__ import annotations

from dataclasses import dataclass

QUESTIONNAIRE_VERSION = "1.0"

MAX_POINTS_PER_QUESTION = 4


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    points: int


@dataclass(frozen=True)
class Question:
    code: str
    dimension: str
    text: str
    options: tuple[Option, ...]


DIMENSIONS: dict[str, str] = {
    "presencia_web": "Presencia web",
    "redes_sociales": "Redes sociales",
    "comercio_electronico": "Comercio electrónico",
    "marketing_digital": "Marketing digital",
    "gestion_operaciones": "Herramientas de gestión",
    "datos_analitica": "Datos y analítica",
}


def _opts(*items: tuple[str, str, int]) -> tuple[Option, ...]:
    return tuple(Option(v, l, p) for v, l, p in items)


QUESTIONS: tuple[Question, ...] = (
    # --- Presencia web ---
    Question(
        "web_sitio",
        "presencia_web",
        "¿Su empresa cuenta con sitio web?",
        _opts(
            ("no", "No tenemos sitio web", 0),
            ("basico", "Sí, una página básica informativa", 1),
            ("actualizado", "Sí, actualizado y adaptado a móviles", 3),
            ("optimizado", "Sí, optimizado (SEO, velocidad, formularios de contacto)", 4),
        ),
    ),
    Question(
        "web_google",
        "presencia_web",
        "¿Su negocio aparece en Google Maps / Perfil de Empresa de Google?",
        _opts(
            ("no", "No", 0),
            ("no_se", "No lo sé", 0),
            ("si_incompleto", "Sí, pero con información incompleta", 2),
            ("si_gestionado", "Sí, completo y respondemos reseñas", 4),
        ),
    ),
    # --- Redes sociales ---
    Question(
        "rs_presencia",
        "redes_sociales",
        "¿Cómo usa las redes sociales (Instagram, Facebook, TikTok, LinkedIn)?",
        _opts(
            ("no", "No tenemos redes sociales", 0),
            ("esporadico", "Tenemos perfiles pero publicamos esporádicamente", 1),
            ("regular", "Publicamos con regularidad", 3),
            ("estrategia", "Tenemos un calendario y estrategia de contenidos", 4),
        ),
    ),
    Question(
        "rs_atencion",
        "redes_sociales",
        "¿Atiende clientes por WhatsApp Business o mensajería de redes?",
        _opts(
            ("no", "No", 0),
            ("personal", "Sí, desde un WhatsApp personal", 1),
            ("business", "Sí, con WhatsApp Business (catálogo, respuestas rápidas)", 3),
            ("automatizado", "Sí, con automatizaciones o chatbot", 4),
        ),
    ),
    # --- Comercio electrónico ---
    Question(
        "ec_venta_online",
        "comercio_electronico",
        "¿Vende sus productos o servicios en línea?",
        _opts(
            ("no", "No vendemos en línea", 0),
            ("redes", "Solo por redes sociales / WhatsApp", 1),
            ("marketplace", "En marketplaces (Mercado Libre, Rappi, etc.)", 2),
            ("tienda_propia", "Tenemos tienda en línea propia", 4),
        ),
    ),
    Question(
        "ec_pagos",
        "comercio_electronico",
        "¿Qué medios de pago digitales acepta?",
        _opts(
            ("efectivo", "Solo efectivo", 0),
            ("transferencia", "Transferencias / Nequi / Daviplata", 1),
            ("datafono", "Datáfono y transferencias", 2),
            ("pasarela", "Pasarela de pagos en línea (PSE, tarjetas)", 4),
        ),
    ),
    # --- Marketing digital ---
    Question(
        "mk_publicidad",
        "marketing_digital",
        "¿Invierte en publicidad digital (Meta Ads, Google Ads)?",
        _opts(
            ("no", "No", 0),
            ("ocasional", "Ocasionalmente, sin medir resultados", 1),
            ("regular", "Regularmente con un presupuesto definido", 3),
            ("medido", "Sí, y medimos el retorno (ROI) de cada campaña", 4),
        ),
    ),
    Question(
        "mk_base_clientes",
        "marketing_digital",
        "¿Cómo se comunica con sus clientes actuales para que vuelvan a comprar?",
        _opts(
            ("no", "No hacemos seguimiento", 0),
            ("manual", "Mensajes manuales ocasionales", 1),
            ("listas", "Listas de difusión / email periódico", 3),
            ("automatizado", "Email marketing o campañas automatizadas", 4),
        ),
    ),
    # --- Herramientas de gestión ---
    Question(
        "go_facturacion",
        "gestion_operaciones",
        "¿Cómo gestiona su facturación e inventario?",
        _opts(
            ("papel", "En papel o cuaderno", 0),
            ("excel", "En hojas de cálculo (Excel)", 1),
            ("software", "Software de facturación electrónica", 3),
            ("erp", "ERP o sistema integrado (facturación + inventario + contabilidad)", 4),
        ),
    ),
    Question(
        "go_clientes",
        "gestion_operaciones",
        "¿Dónde registra la información de sus clientes?",
        _opts(
            ("no", "No la registramos", 0),
            ("libreta", "Libreta o contactos del celular", 1),
            ("excel", "Hojas de cálculo", 2),
            ("crm", "En un CRM", 4),
        ),
    ),
    # --- Datos y analítica ---
    Question(
        "da_metricas",
        "datos_analitica",
        "¿Mide indicadores de su negocio digital (visitas, ventas, conversiones)?",
        _opts(
            ("no", "No medimos", 0),
            ("basico", "Revisamos estadísticas básicas de redes", 1),
            ("analytics", "Usamos Google Analytics u otra herramienta", 3),
            ("tablero", "Tenemos tableros de indicadores para decidir", 4),
        ),
    ),
    Question(
        "da_decisiones",
        "datos_analitica",
        "¿Cómo toma decisiones comerciales (precios, productos, campañas)?",
        _opts(
            ("intuicion", "Por intuición o experiencia", 0),
            ("ventas", "Revisando las ventas del mes", 1),
            ("datos", "Analizando datos históricos de ventas y clientes", 3),
            ("predictivo", "Con análisis de datos y proyecciones", 4),
        ),
    ),
)

QUESTIONS_BY_CODE: dict[str, Question] = {q.code: q for q in QUESTIONS}


def questionnaire_as_dict() -> dict:
    """Representación serializable del cuestionario para el frontend."""
    return {
        "version": QUESTIONNAIRE_VERSION,
        "dimensions": [{"code": c, "label": l} for c, l in DIMENSIONS.items()],
        "questions": [
            {
                "code": q.code,
                "dimension": q.dimension,
                "text": q.text,
                "options": [{"value": o.value, "label": o.label} for o in q.options],
            }
            for q in QUESTIONS
        ],
    }
