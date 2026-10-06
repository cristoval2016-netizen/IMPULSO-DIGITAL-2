def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_questionnaire_does_not_leak_points(client):
    data = client.get("/api/public/questionnaire").json()
    assert data["version"] and len(data["questions"]) == 12
    for q in data["questions"]:
        for o in q["options"]:
            assert "points" not in o


def test_submit_diagnostic_creates_lead(client, submission, admin_headers):
    r = client.post("/api/public/diagnostics", json=submission(level_index=0))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_score"] == 0
    assert body["maturity_level"] == "inicial"
    assert body["recommended_package"]["code"] == "impulso_basico"
    assert body["recommended_package"]["name"] == "Impulso Básico"

    companies = client.get("/api/companies", headers=admin_headers).json()
    assert companies["total"] == 1
    c = companies["items"][0]
    assert c["stage"] == "nuevo" and c["latest_package"] == "impulso_basico"

    detail = client.get(f"/api/companies/{c['id']}", headers=admin_headers).json()
    contact = detail["contacts"][0]
    assert contact["data_consent"] is True and contact["consent_at"]
    assert detail["interactions"][0]["type"] == "sistema"


def test_consent_is_mandatory(client, submission):
    r = client.post("/api/public/diagnostics", json=submission(data_consent=False))
    assert r.status_code == 422
    assert "1581" in r.text


def test_incomplete_answers_rejected(client, submission):
    payload = submission()
    payload["answers"].popitem()
    r = client.post("/api/public/diagnostics", json=payload)
    assert r.status_code == 422


def test_same_nit_reuses_company(client, submission, admin_headers):
    client.post("/api/public/diagnostics", json=submission(level_index=0))
    client.post("/api/public/diagnostics", json=submission(level_index=3, employees=30))
    companies = client.get("/api/companies", headers=admin_headers).json()
    assert companies["total"] == 1
    item = companies["items"][0]
    assert item["latest_score"] == 100 and item["latest_package"] == "impulso_premium"
    detail = client.get(f"/api/companies/{item['id']}", headers=admin_headers).json()
    assert len(detail["diagnostics"]) == 2 and len(detail["contacts"]) == 1


def test_crm_requires_authentication(client):
    assert client.get("/api/companies").status_code == 401
    assert client.get("/api/dashboard/metrics").status_code == 401
    bad = {"Authorization": "Bearer token-falso"}
    assert client.get("/api/companies", headers=bad).status_code == 401


def test_wrong_password(client):
    r = client.post("/api/auth/login", data={"username": "admin@test.co", "password": "x"})
    assert r.status_code == 401


def test_only_admin_manages_users_and_exports(client, make_user):
    comercial = make_user("vendedor@test.co")
    h = comercial["headers"]
    assert client.get("/api/users", headers=h).status_code == 403
    assert client.post("/api/users", headers=h, json={
        "email": "x@test.co", "full_name": "X", "password": "Clave1234*"}).status_code == 403
    assert client.get("/api/dashboard/export/ml-dataset.csv", headers=h).status_code == 403


def test_pipeline_won_marks_conversion(client, submission, admin_headers):
    client.post("/api/public/diagnostics", json=submission(level_index=1))
    cid = client.get("/api/companies", headers=admin_headers).json()["items"][0]["id"]

    r = client.patch(f"/api/companies/{cid}", headers=admin_headers,
                     json={"stage": "ganado", "purchased_package": "impulso_integral"})
    assert r.status_code == 200
    diag = r.json()["diagnostics"][-1]
    assert diag["converted"] is True and diag["purchased_package"] == "impulso_integral"

    m = client.get("/api/dashboard/metrics", headers=admin_headers).json()
    assert m["converted"] == 1 and m["conversion_rate"] == 1.0
    assert m["conversion_target"] == 0.24

    # Revertir la etapa limpia la etiqueta de conversión
    r = client.patch(f"/api/companies/{cid}", headers=admin_headers, json={"stage": "negociacion"})
    assert r.json()["diagnostics"][-1]["converted"] is False


def test_comercial_ownership_rules(client, submission, make_user):
    a = make_user("asesor1@test.co")
    b = make_user("asesor2@test.co")
    client.post("/api/public/diagnostics", json=submission())
    cid = client.get("/api/companies", headers=a["headers"]).json()["items"][0]["id"]

    # Un comercial no puede reasignar
    r = client.patch(f"/api/companies/{cid}", headers=a["headers"], json={"assigned_to_id": b["id"]})
    assert r.status_code == 403

    # Al mover un lead libre, queda asignado a quien lo movió
    r = client.patch(f"/api/companies/{cid}", headers=a["headers"], json={"stage": "contactado"})
    assert r.status_code == 200 and r.json()["assigned_to_id"] == a["id"]

    # Otro comercial ya no puede modificarlo
    r = client.patch(f"/api/companies/{cid}", headers=b["headers"], json={"stage": "propuesta"})
    assert r.status_code == 403


def test_interactions(client, submission, admin_headers):
    client.post("/api/public/diagnostics", json=submission())
    cid = client.get("/api/companies", headers=admin_headers).json()["items"][0]["id"]
    r = client.post(f"/api/companies/{cid}/interactions", headers=admin_headers,
                    json={"type": "llamada", "summary": "Llamada de seguimiento"})
    assert r.status_code == 201
    r = client.post(f"/api/companies/{cid}/interactions", headers=admin_headers,
                    json={"type": "sistema", "summary": "intento"})
    assert r.status_code == 422
    items = client.get(f"/api/companies/{cid}/interactions", headers=admin_headers).json()
    assert {i["type"] for i in items} == {"llamada", "sistema"}


def test_filters(client, submission, admin_headers):
    client.post("/api/public/diagnostics", json=submission(level_index=0, nit="1", sector="comercio"))
    client.post("/api/public/diagnostics",
                json=submission(level_index=3, nit="2", sector="manufactura", email="b@x.co"))
    get = lambda q: client.get(f"/api/companies?{q}", headers=admin_headers).json()["total"]
    assert get("sector=manufactura") == 1
    assert get("package=impulso_premium") == 1
    assert get("level=inicial") == 1
    assert get("search=pyme") == 2


def test_ml_export_has_no_personal_data(client, submission, admin_headers):
    client.post("/api/public/diagnostics", json=submission())
    r = client.get("/api/dashboard/export/ml-dataset.csv", headers=admin_headers)
    assert r.status_code == 200
    text = r.text
    assert "converted" in text.splitlines()[0]
    assert "ana@pyme.co" not in text and "Ana Pérez" not in text and "900123456" not in text


def test_guapicoco_demo_seed_fills_421_palms_and_is_idempotent(client):
    seeded = client.post("/api/guapicoco/seed-demo")
    assert seeded.status_code == 200
    assert seeded.json()["palms_created"] == 421

    palms = client.get("/api/guapicoco/palms").json()
    stats = client.get("/api/guapicoco/stats").json()
    assert len(palms) == stats["total_palms"] == 421
    assert sorted(stats["lots_summary"].values()) == [105, 105, 105, 106]
    assert stats["palms_density_per_ha"] == 105.2

    repeated = client.post("/api/guapicoco/seed-demo")
    assert repeated.json()["palms_created"] == 0
    assert repeated.json()["total"] == 421


def test_guapicoco_palm_photo_is_saved_and_retrievable(client):
    import base64

    image_data = b"\xff\xd8\xfftest-photo"
    payload = {
        "code": "GC-FOTO-001",
        "lot": "Lote 1 (Norte)",
        "latitude": 5.975,
        "longitude": -74.585,
        "photo_data_url": f"data:image/jpeg;base64,{base64.b64encode(image_data).decode()}",
    }
    created = client.post("/api/guapicoco/palms", json=payload)
    assert created.status_code == 201, created.text

    photo = client.get(f"/api/guapicoco/palms/{created.json()['id']}/photo")
    assert photo.status_code == 200
    assert photo.headers["content-type"] == "image/jpeg"
    assert photo.content == image_data
    assert "photo_data_url" not in created.json()
