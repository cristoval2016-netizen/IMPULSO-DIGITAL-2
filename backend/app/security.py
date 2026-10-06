"""Seguridad: hash de contraseñas (bcrypt), JWT y dependencias de autorización por rol."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User, UserRole

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciales inválidas o sesión expirada",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_roles(*roles: UserRole):
    """Dependencia que restringe un endpoint a ciertos roles."""

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tiene permisos para esta acción")
        return user

    return checker


require_staff = require_roles(UserRole.ADMIN, UserRole.COMERCIAL)
require_admin = require_roles(UserRole.ADMIN)
require_client = require_roles(UserRole.CLIENTE)
require_freelancer = require_roles(UserRole.FREELANCER)
require_client_or_staff = require_roles(UserRole.ADMIN, UserRole.COMERCIAL, UserRole.CLIENTE)
require_freelancer_or_staff = require_roles(UserRole.ADMIN, UserRole.COMERCIAL, UserRole.FREELANCER)
require_any_user = require_roles(UserRole.ADMIN, UserRole.COMERCIAL, UserRole.CLIENTE, UserRole.FREELANCER)


def log_audit(
    db: Session,
    action: str,
    details: str,
    user: User | None = None,
    company_id: int | None = None,
    ip_address: str | None = None,
):
    from app.models import AuditLog

    cid = company_id if company_id is not None else (user.company_id if user else None)
    entry = AuditLog(
        action=action,
        details=details,
        user_id=user.id if user else None,
        company_id=cid,
        ip_address=ip_address,
    )
    db.add(entry)
    db.flush()
    return entry

