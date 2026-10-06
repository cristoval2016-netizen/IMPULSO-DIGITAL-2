"""Pruebas automáticas del Módulo 3: Automatización de Tareas, SLAs para Freelancers y Control de Calidad (QA)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.models import (
    MilestonePaymentStatus,
    MilestoneStage,
    Package,
    SLAStatus,
    TaskStatus,
)


def _login(client: TestClient, email: str, password: str = "Freelance123*") -> dict:
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def setup_freelancer_env(client, submission, admin_headers):
    # 1. Crear empresa con diagnóstico y proyecto
    r_diag = client.post("/api/public/diagnostics", json=submission(
        level_index=1,
        email="gerente@industria-boyaca.co",
        company={"name": "Industria Boyacá SAS", "nit": "901999888", "sector": "manufactura", "city": "Puerto Boyacá", "employees": 15},
    ))
    assert r_diag.status_code == 201
    comp_id = [c["id"] for c in client.get("/api/companies", headers=admin_headers).json()["items"] if c["nit"] == "901999888"][0]

    # Crear proyecto
    r_proj = client.post(
        f"/api/companies/{comp_id}/projects",
        json={"title": "Plataforma E-commerce y ERP", "package": "impulso_integral"},
        headers=admin_headers,
    )
    assert r_proj.status_code == 201
    project_id = r_proj.json()["id"]

    # 2. Registrar freelancer
    r_free = client.post(
        "/api/freelancers",
        json={
            "user_in": {
                "email": "dev.frontend@impulsodigital.co",
                "full_name": "Mateo Desarrollador",
                "password": "Freelance123*",
                "role": "freelancer",
            },
            "profile_in": {
                "speciality": "desarrollo_frontend",
                "skills": ["React", "TypeScript", "TailwindCSS"],
                "hourly_rate": 45000.0,
                "bank_info": "Bancolombia Ahorros 123456789",
            },
        },
        headers=admin_headers,
    )
    assert r_free.status_code == 201, r_free.text
    freelancer_user_id = r_free.json()["user_id"]
    freelancer_headers = _login(client, "dev.frontend@impulsodigital.co", "Freelance123*")

    return {
        "company_id": comp_id,
        "project_id": project_id,
        "freelancer_id": freelancer_user_id,
        "freelancer_headers": freelancer_headers,
    }


def test_freelancer_registration_and_profile(client, setup_freelancer_env, admin_headers):
    data = setup_freelancer_env
    # Listar freelancers como staff
    r_list = client.get("/api/freelancers", headers=admin_headers)
    assert r_list.status_code == 200
    assert any(f["user_email"] == "dev.frontend@impulsodigital.co" for f in r_list.json())

    # Obtener perfil propio como freelancer
    r_me = client.get("/api/freelancer/me", headers=data["freelancer_headers"])
    assert r_me.status_code == 200
    assert r_me.json()["speciality"] == "desarrollo_frontend"
    assert "React" in r_me.json()["skills"]


def test_task_assignment_and_freelancer_submission(client, setup_freelancer_env, admin_headers):
    data = setup_freelancer_env
    project_id = data["project_id"]
    freelancer_id = data["freelancer_id"]
    f_headers = data["freelancer_headers"]

    # 1. Staff asigna una tarea con SLA de 48 horas
    due_date = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    r_task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "project_id": project_id,
            "assigned_freelancer_id": freelancer_id,
            "title": "Maquetación Responsive del Catálogo Staging",
            "description": "Implementar la vista de catálogo con filtros y diseño responsive para móviles.",
            "priority": "alta",
            "sla_hours_allotted": 48,
            "due_date": due_date,
        },
        headers=admin_headers,
    )
    assert r_task.status_code == 201, r_task.text
    task_id = r_task.json()["id"]
    assert r_task.json()["status"] == TaskStatus.PENDIENTE.value

    # 2. Freelancer consulta sus tareas
    r_my_tasks = client.get("/api/freelancer/tasks", headers=f_headers)
    assert r_my_tasks.status_code == 200
    assert len(r_my_tasks.json()) >= 1
    assert r_my_tasks.json()[0]["id"] == task_id
    assert r_my_tasks.json()[0]["sla_status"] == SLAStatus.A_TIEMPO.value

    # 3. Freelancer entrega su trabajo para revisión de QA
    r_submit = client.post(
        f"/api/freelancer/tasks/{task_id}/submit",
        json={
            "deliverable_url": "https://staging.impulsodigital.co/preview/catalogo-v1",
            "notes": "Completada maquetación según especificación Figma.",
        },
        headers=f_headers,
    )
    assert r_submit.status_code == 200
    assert r_submit.json()["status"] == TaskStatus.EN_QA.value
    assert r_submit.json()["submitted_at"] is not None
    assert r_submit.json()["sla_status"] == SLAStatus.A_TIEMPO.value


def test_qa_review_process_and_scoring(client, setup_freelancer_env, admin_headers):
    data = setup_freelancer_env
    project_id = data["project_id"]
    freelancer_id = data["freelancer_id"]
    f_headers = data["freelancer_headers"]

    due_date = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r_task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "project_id": project_id,
            "assigned_freelancer_id": freelancer_id,
            "title": "Configuración de Carrito de Compras",
            "description": "Persistencia de items en LocalStorage y checkout simulado.",
            "sla_hours_allotted": 24,
            "due_date": due_date,
        },
        headers=admin_headers,
    )
    task_id = r_task.json()["id"]

    # Freelancer entrega
    client.post(
        f"/api/freelancer/tasks/{task_id}/submit",
        json={"deliverable_url": "https://github.com/impulso/staging-cart"},
        headers=f_headers,
    )

    # QA realiza revisión con checklist y puntaje
    checklist = {
        "responsive_design": True,
        "performance_lighthouse_above_90": True,
        "security_xss_checked": True,
        "cross_browser_verified": True,
    }
    r_qa = client.post(
        f"/api/qa/tasks/{task_id}/review",
        json={
            "score": 98,
            "approved": True,
            "feedback": "Excelente ejecución, rendimiento de 95 en Lighthouse y validaciones robustas.",
            "checklist": checklist,
        },
        headers=admin_headers,
    )
    assert r_qa.status_code == 200
    assert r_qa.json()["status"] == TaskStatus.COMPLETADA.value
    assert r_qa.json()["qa_score"] == 98
    assert r_qa.json()["qa_checklist"]["security_xss_checked"] is True


def test_milestone_payout_gatekeeper(client, setup_freelancer_env, admin_headers):
    """
    Verifica que la liberación de pagos esté estrictamente condicionada a:
    1. Aprobación técnica de QA
    2. Aprobación formal del cliente
    """
    data = setup_freelancer_env
    project_id = data["project_id"]
    freelancer_id = data["freelancer_id"]
    f_headers = data["freelancer_headers"]

    # 1. Crear hito contractual de $1'500.000 COP
    r_ms = client.post(
        f"/api/projects/{project_id}/milestones",
        json={
            "title": "Hito 2: Aprobación de Arquitectura y Diseño Staging",
            "stage": MilestoneStage.APROBACION_DISENO.value,
            "payout_amount": 1500000.0,
            "requires_client_approval": True,
            "notes": "Liberación sujeta a visto bueno del cliente y auditoría QA.",
        },
        headers=admin_headers,
    )
    assert r_ms.status_code == 201
    milestone_id = r_ms.json()["id"]
    assert r_ms.json()["payment_status"] == MilestonePaymentStatus.BLOQUEADO.value
    assert r_ms.json()["qa_approved"] is False
    assert r_ms.json()["client_approved"] is False

    # Asignar tarea vinculada a este hito
    due_date = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    r_task = client.post(
        f"/api/projects/{project_id}/tasks",
        json={
            "project_id": project_id,
            "milestone_id": milestone_id,
            "assigned_freelancer_id": freelancer_id,
            "title": "Prototipo Staging Aprobado",
            "description": "Despliegue de staging listo para validación.",
            "sla_hours_allotted": 72,
            "due_date": due_date,
        },
        headers=admin_headers,
    )
    task_id = r_task.json()["id"]

    # INTENTO 1 DE LIBERACIÓN: Fallará porque falta QA y Cliente
    r_fail_1 = client.post(
        f"/api/milestones/{milestone_id}/release-payout",
        json={"notes": "Intento de pago sin aprobaciones"},
        headers=admin_headers,
    )
    assert r_fail_1.status_code == 400
    assert "QA" in r_fail_1.json()["detail"]

    # Freelancer entrega y QA aprueba
    client.post(
        f"/api/freelancer/tasks/{task_id}/submit",
        json={"deliverable_url": "https://staging.test.co"},
        headers=f_headers,
    )
    client.post(
        f"/api/qa/tasks/{task_id}/review",
        json={"score": 100, "approved": True, "feedback": "QA aprobado 100%"},
        headers=admin_headers,
    )

    # INTENTO 2 DE LIBERACIÓN: Fallará porque aún falta visto bueno del cliente
    r_fail_2 = client.post(
        f"/api/milestones/{milestone_id}/release-payout",
        json={"notes": "Intento de pago sin aprobación de cliente"},
        headers=admin_headers,
    )
    assert r_fail_2.status_code == 400
    assert "cliente" in r_fail_2.json()["detail"].lower()

    # Cliente aprueba formalmente el hito
    r_client_ok = client.post(
        f"/api/milestones/{milestone_id}/approve-client",
        headers=admin_headers,
    )
    assert r_client_ok.status_code == 200
    assert r_client_ok.json()["client_approved"] is True

    # INTENTO 3 DE LIBERACIÓN: Debe tener éxito (ambas condiciones cumplidas)
    r_success = client.post(
        f"/api/milestones/{milestone_id}/release-payout",
        json={"notes": "Transferencia autorizada por tesorería."},
        headers=admin_headers,
    )
    assert r_success.status_code == 200
    assert r_success.json()["payment_status"] == MilestonePaymentStatus.LIBERADO.value
    assert r_success.json()["released_at"] is not None


def test_sla_dashboard_metrics_and_95_percent_target(client, setup_freelancer_env, admin_headers):
    """Verifica que el dashboard de QA y SLAs mida el cumplimiento del target del 95%."""
    r_dash = client.get("/api/qa/dashboard", headers=admin_headers)
    assert r_dash.status_code == 200
    metrics = r_dash.json()

    assert metrics["target_on_time_rate"] == 0.95
    assert "actual_on_time_rate" in metrics
    assert "meets_target" in metrics
    assert "total_tasks" in metrics
    assert "average_qa_score" in metrics
