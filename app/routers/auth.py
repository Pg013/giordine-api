from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.models.perfil_aluno import PerfilAluno
from app.models.refresh_token import RefreshToken
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UsuarioResponse
from app.utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    REFRESH_TOKEN_EXPIRE_DAYS,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.username == body.username).first()
    if not user or not verify_password(body.senha, user.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo")

    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()
    if perfil and not perfil.acesso_liberado:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso bloqueado. Entre em contato com seu professor.",
        )

    token_data = {"sub": str(user.id)}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    expira_em = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db.add(RefreshToken(usuario_id=user.id, token=refresh_token, expira_em=expira_em))
    db.commit()

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    db_token = db.query(RefreshToken).filter(RefreshToken.token == body.refresh_token).first()
    if not db_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido")

    expiry = db_token.expira_em
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expirado")

    access_token = create_access_token({"sub": str(db_token.usuario_id)})
    return TokenResponse(access_token=access_token, refresh_token=body.refresh_token)


@router.post("/logout")
def logout(body: RefreshRequest, db: Session = Depends(get_db)):
    db_token = db.query(RefreshToken).filter(RefreshToken.token == body.refresh_token).first()
    if db_token:
        db.delete(db_token)
        db.commit()
    return {"message": "logged out"}


@router.get("/me", response_model=UsuarioResponse)
def me(user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()
    return UsuarioResponse(
        id=user.id,
        nome=user.nome,
        username=user.username,
        email=user.email,
        role=user.role,
        nivel=perfil.nivel if perfil else None,
        foto_url=perfil.foto_url if perfil else None,
        idioma_portal=perfil.idioma_portal if perfil else "pt",
        acesso_liberado=perfil.acesso_liberado if perfil else True,
    )
