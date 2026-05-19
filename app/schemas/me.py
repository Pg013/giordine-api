import re
from typing import Optional
from pydantic import BaseModel, field_validator


class MePerfilUpdate(BaseModel):
    """Atualização de perfil genérica (admin, professor ou aluno).
    Sem `aceita_email` — esse campo é específico de aluno."""
    nome: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None

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
