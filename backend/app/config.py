"""Configuración central de la aplicación (variables de entorno / .env)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Impulso Digital - Diagnóstico y CRM"
    environment: str = "development"

    # PostgreSQL en producción, p.ej.:
    #   postgresql+psycopg://impulso:impulso@localhost:5432/impulso
    # SQLite solo como respaldo para desarrollo local sin Postgres.
    database_url: str = "sqlite:///./impulso_dev.db"

    # Seguridad (JWT)
    secret_key: str = "CAMBIAR-ESTA-CLAVE-EN-PRODUCCION"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 8

    # CORS (frontend React/Vite)
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Usuario administrador inicial (se crea al arrancar si no existe)
    first_admin_email: str = "admin@impulsodigital.co"
    first_admin_password: str = "Admin123*"

    # Meta de negocio: conversión de diagnósticos a clientes pagos
    conversion_target: float = 0.24

    # Versión de la política de tratamiento de datos (Ley 1581 de 2012)
    privacy_policy_version: str = "2026-01"


@lru_cache
def get_settings() -> Settings:
    return Settings()
