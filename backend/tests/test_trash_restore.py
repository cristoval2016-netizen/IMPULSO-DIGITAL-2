"""Pruebas del Módulo de Papelera, Soft Delete y Restauración Exclusiva por Administrador."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


def _login(client: TestClient, email: str, password: str = "Clave1234*") -> dict:
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_soft_delete_and_admin_only_restore_workflow(client, submission, admin_headers, make_user):
    # 1. Crear usuario comercial
    comercial = make_user("asesor.test@impulsodigital.co", role="comercial", password="Asesor123*")

    # 2. Registrar empresa con diagnóstico inicial en Puerto Boyacá
    r_diag = client.post("/api/public/diagnostics", json=submission(
        level_index=1,
        email="gerencia@plastboyaca.co",
        company={
            "name": "Plásticos Boyacá SAS",
            "nit": "900555444",
            "sector": "manufactura",
            "city": "Puerto Boyacá",
            "employees": 18,
        },
    ))
    assert r_diag.status_code == 201

    # Obtener ID de la empresa
    companies_list = client.get("/api/companies", headers=admin_headers).json()["items"]
    company = [c for c in companies_list if c["nit"] == "900555444"][0]
    comp_id = company["id"]

    # Agregar interacción manual previa
    client.post(
        f"/api/companies/{comp_id}/interactions",
        json={"type": "llamada", "summary": "Llamada inicial de sondeo comercial."},
        headers=admin_headers,
    )

    # 3. Soft-delete: Enviar a la papelera con motivo
    delete_reason = "El cliente cerró temporalmente operaciones por remodelación de planta."
    r_del = client.post(
        f"/api/companies/{comp_id}/soft-delete",
        json={"reason": delete_reason},
        headers=comercial["headers"],
    )
    assert r_del.status_code == 200, r_del.text
    assert "papelera" in r_del.json()["message"].lower()

    # 4. Verificar que ya NO aparece en el listado activo de empresas
    r_active = client.get("/api/companies", headers=admin_headers)
    assert not any(c["id"] == comp_id for c in r_active.json()["items"])

    # 5. Verificar que APARECE en la papelera con su historial intacto
    r_trash = client.get("/api/companies/trash", headers=admin_headers)
    assert r_trash.status_code == 200
    trashed = [c for c in r_trash.json() if c["id"] == comp_id]
    assert len(trashed) == 1
    t_item = trashed[0]
    assert t_item["name"] == "Plásticos Boyacá SAS"
    assert t_item["delete_reason"] == delete_reason
    assert t_item["diagnostics_count"] >= 1
    assert t_item["interactions_count"] >= 2  # Llamada previa + interacción de sistema por envío a papelera

    # 6. Intentar restaurar como COMERCIAL (Debe ser rechazado con 403 Forbidden)
    r_restore_forbidden = client.post(
        f"/api/companies/{comp_id}/restore",
        json={"reason": "Intento de recuperación por asesor"},
        headers=comercial["headers"],
    )
    assert r_restore_forbidden.status_code == 403
    assert "permisos" in r_restore_forbidden.json()["detail"].lower()

    # 7. Restaurar como ADMINISTRADOR solicitando motivo obligatorio
    restore_reason = "Cliente reabrió su sede y solicita continuar con el paquete de digitalización."
    r_restore_ok = client.post(
        f"/api/companies/{comp_id}/restore",
        json={"reason": restore_reason},
        headers=admin_headers,
    )
    assert r_restore_ok.status_code == 200, r_restore_ok.text
    restored_data = r_restore_ok.json()
    assert restored_data["id"] == comp_id
    assert restored_data["name"] == "Plásticos Boyacá SAS"

    # Verificar que el historial completo está recuperado
    assert len(restored_data["diagnostics"]) >= 1
    assert any("restaurada desde la papelera por Administrador" in i["summary"] for i in restored_data["interactions"])
    assert any(restore_reason in i["summary"] for i in restored_data["interactions"])

    # 8. Verificar que la empresa YA NO está en la papelera y REAPARECE en el CRM activo
    r_trash_after = client.get("/api/companies/trash", headers=admin_headers)
    assert not any(c["id"] == comp_id for c in r_trash_after.json())

    r_active_after = client.get("/api/companies", headers=admin_headers)
    assert any(c["id"] == comp_id for c in r_active_after.json()["items"])
