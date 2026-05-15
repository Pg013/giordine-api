import re
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class PerfilAlunoResponse(BaseModel):
    id: int
    nome: str
    username: str
    email: str
    foto_url: Optional[str] = None
    aceita_email: bool
    nivel: Optional[str] = None
    idioma_portal: str
    acesso_liberado: bool

    model_config = {"from_attributes": True}


class AtualizarPerfilRequest(BaseModel):
    nome: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    aceita_email: Optional[bool] = None

    @field_validator("nome")
    @classmethod
    def nome_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) == 0:
            raise ValueError("Nome não pode ser vazio")
        return v.strip() if v else v

    @field_validator("username")
    @classmethod
    def username_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) < 3:
            raise ValueError("Username deve ter ao menos 3 caracteres")
        return v.strip() if v else v

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v.strip()):
                raise ValueError("E-mail inválido")
            return v.strip()
        return v


class AlterarSenhaRequest(BaseModel):
    senha_atual: str
    nova_senha: str
    confirmar_senha: str

    @field_validator("nova_senha")
    @classmethod
    def senha_minima(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Nova senha deve ter ao menos 8 caracteres")
        return v

    @model_validator(mode="after")
    def senhas_coincidem(self) -> "AlterarSenhaRequest":
        if self.nova_senha != self.confirmar_senha:
            raise ValueError("Senhas não coincidem")
        return self


class AlterarFotoRequest(BaseModel):
    foto_base64: str
