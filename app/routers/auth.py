import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.perfil_aluno import PerfilAluno
from app.models.refresh_token import RefreshToken
from app.models.aluno_turma import AlunoTurma
from app.models.comunicado import Comunicado
from app.models.comunicado_lido import ComunicadoLido
from app.models.password_reset_token import PasswordResetToken
from app.schemas.auth import (
    LoginRequest, TokenResponse, RefreshRequest, UsuarioResponse,
    ForgotPasswordRequest, ResetPasswordRequest,
    TotpSetupResponse, TotpVerifyRequest, TotpStatusResponse,
)
from app.utils.totp import (
    generate_secret as totp_generate_secret,
    build_provisioning_uri,
    build_qr_data_url,
    verify_code as totp_verify_code,
)
from app.utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.utils.email_service import send_password_reset_email
from app.utils.rate_limit import limiter
from app.utils.captcha import verify_turnstile, turnstile_enabled

router = APIRouter(prefix="/auth", tags=["auth"])

RESET_TOKEN_EXPIRE_HOURS = 1


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")  # anti brute-force
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Usuario).filter(Usuario.username == body.username).first()
    if not user or not verify_password(body.senha, user.senha_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")

    if not user.ativo:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário inativo")

    # 2FA: se o usuário ativou TOTP, exige código do app autenticador
    if user.totp_enabled and user.totp_secret:
        if not body.totp_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="totp_required",  # frontend usa esse marcador pra mostrar input de código
            )
        if not totp_verify_code(user.totp_secret, body.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="totp_invalid",
            )

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

    comunicados_nao_lidos = 0
    if user.role == RoleEnum.aluno:
        turma_id = (
            db.query(AlunoTurma.turma_id)
            .filter(AlunoTurma.aluno_id == user.id)
            .scalar()
        )
        comunicados_nao_lidos = (
            db.query(func.count(Comunicado.id))
            .outerjoin(
                ComunicadoLido,
                (ComunicadoLido.comunicado_id == Comunicado.id)
                & (ComunicadoLido.aluno_id == user.id),
            )
            .filter(
                or_(Comunicado.turma_id == None, Comunicado.turma_id == turma_id),
                ComunicadoLido.comunicado_id == None,
            )
            .scalar()
            or 0
        )

    return UsuarioResponse(
        id=user.id,
        nome=user.nome,
        username=user.username,
        email=user.email,
        role=user.role,
        nivel=perfil.nivel if perfil else None,
        foto_url=user.foto_url,
        idioma_portal=perfil.idioma_portal if perfil else "pt",
        acesso_liberado=perfil.acesso_liberado if perfil else True,
        comunicados_nao_lidos=comunicados_nao_lidos,
    )


# ── Esqueci minha senha ─────────────────────────────────────────────────────


@router.post("/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("5/minute;20/hour")  # anti email enumeration + spam
def forgot_password(request: Request, body: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Sempre retorna 204 — não revela se o email existe ou não (anti-enumeração).
    Se existir e estiver ativo, envia email com link de reset.
    """
    # Valida CAPTCHA se Turnstile estiver configurado
    if turnstile_enabled():
        client_ip = request.client.host if request.client else None
        if not verify_turnstile(body.captcha_token, client_ip):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha inválido")

    email_lower = body.email.strip().lower()
    user = db.query(Usuario).filter(func.lower(Usuario.email) == email_lower).first()

    if not user or not user.ativo:
        return  # 204 silencioso

    # Invalida tokens antigos não-usados do mesmo usuário
    db.query(PasswordResetToken).filter(
        PasswordResetToken.usuario_id == user.id,
        PasswordResetToken.usado_em.is_(None),
    ).update({"usado_em": datetime.now(timezone.utc)})

    # Gera novo token (raw → email, hash → DB)
    raw_token = secrets.token_urlsafe(32)
    expira = datetime.now(timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)

    db.add(PasswordResetToken(
        usuario_id=user.id,
        token_hash=_hash_token(raw_token),
        expira_em=expira,
    ))
    db.commit()

    send_password_reset_email(
        to=user.email,
        nome=user.nome,
        token=raw_token,
        expires_in_hours=RESET_TOKEN_EXPIRE_HOURS,
    )


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/hour")  # anti token brute-force
def reset_password(request: Request, body: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Valida o token, marca como usado e atualiza a senha do usuário.
    Invalida todos os refresh tokens ativos (força re-login em outros dispositivos).
    """
    token_hash = _hash_token(body.token)
    db_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash,
    ).first()

    if not db_token or db_token.usado_em is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido ou já utilizado")

    expira = db_token.expira_em
    if expira.tzinfo is None:
        expira = expira.replace(tzinfo=timezone.utc)
    if expira < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado")

    user = db.query(Usuario).filter(Usuario.id == db_token.usuario_id).first()
    if not user or not user.ativo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inválido")

    user.senha_hash = get_password_hash(body.nova_senha)
    db_token.usado_em = datetime.now(timezone.utc)

    # Invalida todos refresh tokens (logout em outros devices)
    db.query(RefreshToken).filter(RefreshToken.usuario_id == user.id).delete()

    db.commit()


# ── 2FA (TOTP) ──────────────────────────────────────────────────────────────


@router.get("/2fa/status", response_model=TotpStatusResponse)
def totp_status(user: Usuario = Depends(get_current_user)):
    """Retorna se o usuário logado tem 2FA ativado."""
    return TotpStatusResponse(enabled=bool(user.totp_enabled))


@router.post("/2fa/setup", response_model=TotpSetupResponse)
def totp_setup(user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Gera um novo segredo e retorna QR code pra escanear no app autenticador.
    O segredo é salvo no banco mas 2FA SÓ FICA ATIVO depois do /2fa/verify.
    Chamar de novo invalida o setup anterior.
    """
    if user.role == RoleEnum.aluno:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="2FA disponível apenas para admin/professor")

    secret = totp_generate_secret()
    user.totp_secret = secret
    user.totp_enabled = False  # ainda não ativo — precisa verificar
    db.commit()

    uri = build_provisioning_uri(user.username, secret)
    qr = build_qr_data_url(uri)
    return TotpSetupResponse(secret=secret, qr_data_url=qr, provisioning_uri=uri)


@router.post("/2fa/verify", status_code=status.HTTP_204_NO_CONTENT)
def totp_verify(
    body: TotpVerifyRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Confirma que o usuário escaneou o QR e o app está gerando códigos válidos."""
    if not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Setup not started")
    if not totp_verify_code(user.totp_secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido")
    user.totp_enabled = True
    db.commit()


@router.post("/2fa/disable", status_code=status.HTTP_204_NO_CONTENT)
def totp_disable(
    body: TotpVerifyRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Desativa 2FA. Exige código válido pra confirmar que é o dono do dispositivo.
    Limpa o secret pra forçar setup novo se quiser reativar.
    """
    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not enabled")
    if not totp_verify_code(user.totp_secret, body.code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido")
    user.totp_secret = None
    user.totp_enabled = False
    db.commit()
