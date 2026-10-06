"""Pruebas automáticas del Módulo 2: Portal del Cliente (SGA)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.models import (
    DeliverableStatus,
    Package,
    PipelineStage,
    ProjectStatus,
    TicketPriority,
    TicketStatus,
)


def _client_login(client: TestClient, email: str, password: str = "Cliente123*") -> dict:
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def setup_portal_data(client, submission, admin_headers):
    """Crea dos empresas distintas (Empresa A y Empresa B) para validar multitenancy."""
    # Empresa A
    r_a = client.post("/api/public/diagnostics", json=submission(
        level_index=1, email="gerencia@empresa-a.co",
        company={"name": "Empresa A SAS", "nit": "901001001", "sector": "comercio", "city": "Puerto Boyacá", "employees": 10},
    ))
    assert r_a.status_code == 201
    comp_a_id = [c["id"] for c in client.get("/api/companies", headers=admin_headers).json()["items"] if c["nit"] == "901001001"][0]

    # Crear usuario cliente para Empresa A
    r_user_a = client.post(
        f"/api/companies/{comp_a_id}/client-users",
        json={"email": "cliente.a@empresa-a.co", "full_name": "Carlos Gerente A", "password": "Cliente123*"},
        headers=admin_headers,
    )
    assert r_user_a.status_code == 201

    # Empresa B
    r_b = client.post("/api/public/diagnostics", json=submission(
        level_index=3, email="contacto@empresa-b.co",
        company={"name": "Empresa B SAS", "nit": "902002002", "sector": "servicios", "city": "Puerto Boyacá", "employees": 25},
    ))
    assert r_b.status_code == 201
    comp_b_id = [c["id"] for c in client.get("/api/companies", headers=admin_headers).json()["items"] if c["nit"] == "902002002"][0]

    # Crear usuario cliente para Empresa B
    r_user_b = client.post(
        f"/api/companies/{comp_b_id}/client-users",
        json={"email": "cliente.b@empresa-b.co", "full_name": "Beatriz Directora B", "password": "Cliente123*"},
        headers=admin_headers,
    )
    assert r_user_b.status_code == 201

    headers_a = _client_login(client, "cliente.a@empresa-a.co")
    headers_b = _client_login(client, "cliente.b@empresa-b.co")

    return {
        "company_a_id": comp_a_id,
        "company_b_id": comp_b_id,
        "headers_a": headers_a,
        "headers_b": headers_b,
    }


def test_client_profile_and_access(client, setup_portal_data):
    data = setup_portal_data
    r = client.get("/api/portal/profile", headers=data["headers_a"])
    assert r.status_code == 200
    profile = r.json()
    assert profile["company_id"] == data["company_a_id"]
    assert profile["company_name"] == "Empresa A SAS"
    assert profile["nda_signed"] is True
    assert profile["law_1581_accepted"] is True


def test_multitenant_isolation(client, setup_portal_data, admin_headers):
    data = setup_portal_data

    # Staff crea un proyecto para Empresa B
    r_proj = client.post(
        f"/api/companies/{data['company_b_id']}/projects",
        json={
            "title": "Sitio Web y Pasarela Empresa B",
            "package": "impulso_integral",
            "status": "staging",
            "staging_url": "https://staging.empresa-b.com",
            "progress_percent": 60,
        },
        headers=admin_headers,
    )
    assert r_proj.status_code == 201
    proj_b_id = r_proj.json()["id"]

    # Cliente B PUEDE ver su proyecto
    r_b_view = client.get(f"/api/portal/projects/{proj_b_id}", headers=data["headers_b"])
    assert r_b_view.status_code == 200
    assert r_b_view.json()["title"] == "Sitio Web y Pasarela Empresa B"

    # Cliente A INTENTA ver el proyecto de Empresa B -> DEBE RECIBIR 403 (Prohibido)
    r_a_view = client.get(f"/api/portal/projects/{proj_b_id}", headers=data["headers_a"])
    assert r_a_view.status_code == 403
    assert "Violación de acceso" in r_a_view.text


def test_deliverable_review_and_audit_trail(client, setup_portal_data, admin_headers):
    data = setup_portal_data

    # 1. Staff crea proyecto y entregable para Empresa A
    r_proj = client.post(
        f"/api/companies/{data['company_a_id']}/projects",
        json={"title": "Transformación Digital A", "package": "impulso_basico", "status": "diseno"},
        headers=admin_headers,
    )
    proj_id = r_proj.json()["id"]

    r_deliv = client.post(
        f"/api/projects/{proj_id}/deliverables",
        json={
            "title": "Wireframes y Prototipo UI",
            "description": "Propuesta gráfica y estructura de secciones",
            "preview_url": "https://figma.com/preview/empresa-a",
        },
        headers=admin_headers,
    )
    assert r_deliv.status_code == 201
    deliv_id = r_deliv.json()["id"]

    # 2. Cliente A solicita ajustes
    r_rev1 = client.post(
        f"/api/portal/deliverables/{deliv_id}/review",
        json={"status": "ajustes_solicitados", "feedback": "Favor cambiar color primario al azul corporativo."},
        headers=data["headers_a"],
    )
    assert r_rev1.status_code == 200
    assert r_rev1.json()["status"] == "ajustes_solicitados"
    assert "azul corporativo" in r_rev1.json()["client_feedback"]

    # 3. Cliente A aprueba tras correcciones
    r_rev2 = client.post(
        f"/api/portal/deliverables/{deliv_id}/review",
        json={"status": "aprobado", "feedback": "¡Aprobado! Cumple con la identidad de marca."},
        headers=data["headers_a"],
    )
    assert r_rev2.status_code == 200
    assert r_rev2.json()["status"] == "aprobado"

    # 4. Auditoría (ISO 27001 / Trazabilidad de no repudio)
    r_logs = client.get(f"/api/companies/{data['company_a_id']}/audit-logs", headers=admin_headers)
    assert r_logs.status_code == 200
    actions = [log["action"] for log in r_logs.json()]
    assert "AJUSTE_SOLICITADO_ENTREGABLE" in actions
    assert "APROBACION_ENTREGABLE" in actions


def test_support_tickets_workflow(client, setup_portal_data, admin_headers):
    data = setup_portal_data

    # 1. Cliente A abre ticket de soporte
    r_ticket = client.post(
        "/api/portal/tickets",
        json={
            "subject": "Duda sobre integración de WhatsApp Business",
            "description": "¿Cómo configuro el catálogo de productos?",
            "priority": "alta",
        },
        headers=data["headers_a"],
    )
    assert r_ticket.status_code == 201
    ticket_id = r_ticket.json()["id"]
    assert r_ticket.json()["status"] == "abierto"
    assert r_ticket.json()["messages_count"] == 1

    # 2. Cliente B intenta ver el ticket de Cliente A -> 403
    assert client.get(f"/api/portal/tickets/{ticket_id}", headers=data["headers_b"]).status_code == 403

    # 3. Staff responde al ticket
    r_reply_staff = client.post(
        f"/api/portal/tickets/{ticket_id}/messages",
        json={"message": "Hola Carlos, adjuntamos la guía paso a paso para WhatsApp Business."},
        headers=admin_headers,
    )
    assert r_reply_staff.status_code == 200
    assert r_reply_staff.json()["sender_role"] == "admin"

    # 4. Cliente A responde y consulta el ticket completo
    r_reply_client = client.post(
        f"/api/portal/tickets/{ticket_id}/messages",
        json={"message": "¡Muchas gracias! Ya quedó configurado."},
        headers=data["headers_a"],
    )
    assert r_reply_client.status_code == 200

    r_detail = client.get(f"/api/portal/tickets/{ticket_id}", headers=data["headers_a"])
    assert r_detail.status_code == 200
    messages = r_detail.json()["messages"]
    assert len(messages) == 3


def test_training_materials_access(client, setup_portal_data, admin_headers):
    data = setup_portal_data

    # Admin sube materiales educativos
    client.post(
        "/api/portal/training",
        json={
            "title": "Tutorial WhatsApp Business",
            "description": "Aprenda a crear su catálogo y respuestas rápidas",
            "category": "WhatsApp Business",
            "package_required": "impulso_basico",
            "video_url": "https://youtube.com/watch?v=demo1",
            "duration_minutes": 15,
        },
        headers=admin_headers,
    )
    client.post(
        "/api/portal/training",
        json={
            "title": "Gestión de Pasarela de Pagos Avanzada",
            "description": "Automatización de cobros y conciliación bancaria",
            "category": "E-commerce",
            "package_required": "impulso_premium",
            "video_url": "https://youtube.com/watch?v=demo2",
            "duration_minutes": 30,
        },
        headers=admin_headers,
    )

    # Cliente A (Impulso Básico / Integral) consulta catálogo de capacitación
    r_train_a = client.get("/api/portal/training", headers=data["headers_a"])
    assert r_train_a.status_code == 200
    titles = [m["title"] for m in r_train_a.json()]
    assert "Tutorial WhatsApp Business" in titles
