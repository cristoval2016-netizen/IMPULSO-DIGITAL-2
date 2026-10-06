"""Punto de entrada de la API FastAPI."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import get_settings
from app.database import Base, SessionLocal, engine
from app.models import User, UserRole
from app.routers import auth, companies, dashboard, freelancers, guapicoco, portal, public
from app.security import hash_password

settings = get_settings()


def init_db() -> None:
    # MVP: create_all. En producción usar migraciones con Alembic.
    Base.metadata.create_all(bind=engine)
    try:
        with engine.connect() as conn:
            cols = [row[1] for row in conn.exec_driver_sql("PRAGMA table_info(companies)").fetchall()]
            if cols:
                if "is_deleted" not in cols:
                    conn.exec_driver_sql("ALTER TABLE companies ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
                if "deleted_at" not in cols:
                    conn.exec_driver_sql("ALTER TABLE companies ADD COLUMN deleted_at DATETIME")
                if "deleted_by_id" not in cols:
                    conn.exec_driver_sql("ALTER TABLE companies ADD COLUMN deleted_by_id INTEGER REFERENCES users(id)")
                if "delete_reason" not in cols:
                    conn.exec_driver_sql("ALTER TABLE companies ADD COLUMN delete_reason TEXT")
                conn.commit()
    except Exception:
        pass

    with SessionLocal() as db:
        if db.scalar(select(User).where(User.role == UserRole.ADMIN)) is None:
            db.add(
                User(
                    email=settings.first_admin_email,
                    full_name="Administrador",
                    role=UserRole.ADMIN,
                    hashed_password=hash_password(settings.first_admin_password),
                )
            )
            db.commit()



@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Diagnóstico gratuito de madurez digital para Pymes y CRM comercial.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


app.include_router(public.router)
app.include_router(auth.router)
app.include_router(companies.router)
app.include_router(dashboard.router)
app.include_router(portal.router)
app.include_router(freelancers.router, prefix="/api")
app.include_router(guapicoco.router)


@app.get("/api/health", tags=["Sistema"])
def health() -> dict:
    return {"status": "ok"}
