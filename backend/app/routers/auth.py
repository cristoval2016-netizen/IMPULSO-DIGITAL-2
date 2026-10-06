"""Autenticación del personal interno y gestión de usuarios."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Token, UserCreate, UserOut
from app.security import (
    create_access_token,
    get_current_user,
    hash_password,
    require_admin,
    verify_password,
)

router = APIRouter(prefix="/api", tags=["Autenticación y usuarios"])


@router.post("/auth/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    user = db.scalar(select(User).where(func.lower(User.email) == form.username.lower()))
    if user is None or not user.is_active or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Correo o contraseña incorrectos")

    from app.security import log_audit

    log_audit(
        db,
        action="LOGIN_USUARIO",
        details=f"Inicio de sesión exitoso ({user.role.value})",
        user=user,
        company_id=user.company_id,
    )
    db.commit()
    return Token(
        access_token=create_access_token(user),
        role=user.role,
        full_name=user.full_name,
        company_id=user.company_id,
    )


@router.get("/auth/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_admin)])
def list_users(db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.full_name)))


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_user(data: UserCreate, db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(func.lower(User.email) == data.email.lower())):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese correo")
    user = User(
        email=data.email.lower(),
        full_name=data.full_name,
        role=data.role,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    return user
