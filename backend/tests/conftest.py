import os
import tempfile
from pathlib import Path

# Base de datos aislada para pruebas (debe configurarse ANTES de importar la app)
_TEST_DB = Path(tempfile.gettempdir()) / "impulso_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB.as_posix()}"
os.environ["FIRST_ADMIN_EMAIL"] = "admin@test.co"
os.environ["FIRST_ADMIN_PASSWORD"] = "Admin123*"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app, init_db  # noqa: E402
from app.services.questionnaire import QUESTIONS  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    init_db()
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str, password: str) -> dict:
    r = client.post("/api/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client):
    return _login(client, "admin@test.co", "Admin123*")


@pytest.fixture()
def make_user(client, admin_headers):
    def _make(email: str, role: str = "comercial", password: str = "Clave1234*") -> dict:
        r = client.post(
            "/api/users",
            json={"email": email, "full_name": email.split("@")[0], "password": password,
                  "role": role},
            headers=admin_headers,
        )
        assert r.status_code == 201, r.text
        return {"id": r.json()["id"], "headers": _login(client, email, password)}

    return _make


def answers_with(level_index: int) -> dict[str, str]:
    """Responde todas las preguntas con la opción N (0 = peor, 3 = mejor)."""
    return {q.code: q.options[level_index].value for q in QUESTIONS}


@pytest.fixture()
def submission():
    def _make(level_index: int = 0, sector: str = "comercio", employees: int = 10,
              nit: str | None = "900123456", email: str = "ana@pyme.co", **extra) -> dict:
        payload = {
            "company": {"name": "Pyme Test SAS", "nit": nit, "sector": sector,
                        "city": "Bogotá", "employees": employees},
            "contact": {"full_name": "Ana Pérez", "email": email, "phone": "3001234567"},
            "answers": answers_with(level_index),
            "data_consent": True,
        }
        payload.update(extra)
        return payload

    return _make
