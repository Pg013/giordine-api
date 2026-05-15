from typing import Optional
from pydantic import BaseModel
from app.models.usuario import RoleEnum


class LoginRequest(BaseModel):
    username: str
    senha: str


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

    model_config = {"from_attributes": True}
