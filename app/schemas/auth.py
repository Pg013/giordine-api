from typing import Optional
from pydantic import BaseModel, field_validator, model_validator
from app.models.usuario import RoleEnum


class LoginRequest(BaseModel):
    username: str
    senha: str
    totp_code: Optional[str] = None  # 6 dígitos quando o usuário tem 2FA ativado


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    username: str
    email: str
    role: RoleEnum
    nivel: Optional[str]
    foto_url: Optional[str]
    idioma_portal: str
    acesso_liberado: bool
    comunicados_nao_lidos: int = 0

    model_config = {"from_attributes": True}


class ForgotPasswordRequest(BaseModel):
    email: str
    captcha_token: Optional[str] = None  # Cloudflare Turnstile, opcional se CAPTCHA desativado


class ResetPasswordRequest(BaseModel):
    token: str
    nova_senha: str
    confirmar_senha: str

    @field_validator("nova_senha")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Nova senha deve ter ao menos 8 caracteres")
        return v

    @model_validator(mode="after")
    def senhas_coincidem(self) -> "ResetPasswordRequest":
        if self.nova_senha != self.confirmar_senha:
            raise ValueError("Senhas não coincidem")
        return self


# ── 2FA TOTP ─────────────────────────────────────────────────────────────────

class TotpSetupResponse(BaseModel):
    """Retornado ao iniciar setup: usuário escaneia QR no app autenticador."""
    secret: str           # base32 (mostrar como backup caso não consiga escanear)
    qr_data_url: str      # PNG inline pra <img src=...>
    provisioning_uri: str # otpauth://...


class TotpVerifyRequest(BaseModel):
    code: str  # 6 dígitos do app


class TotpStatusResponse(BaseModel):
    enabled: bool
