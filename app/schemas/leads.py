import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator


# ── Público (form de contato) ───────────────────────────────────────────────


class LeadCreatePublic(BaseModel):
    nome: str
    email: str
    whatsapp: str
    # Opcionais
    como_conheceu: Optional[str] = None
    nivel_ingles: Optional[str] = None
    objetivo: Optional[str] = None
    mensagem: Optional[str] = None
    # Anti-spam (opcional, validado se TURNSTILE configurado)
    captcha_token: Optional[str] = None

    @field_validator("nome", "whatsapp")
    @classmethod
    def nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Campo obrigatório")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("E-mail inválido")
        return v.lower()


# ── Admin (CRUD) ────────────────────────────────────────────────────────────


class LeadListItem(BaseModel):
    id: int
    nome: str
    email: str
    whatsapp: str
    status: str
    como_conheceu: Optional[str]
    nivel_ingles: Optional[str]
    criado_em: datetime
    aluno_id: Optional[int]

    model_config = {"from_attributes": True}


class LeadDetalhe(BaseModel):
    id: int
    nome: str
    email: str
    whatsapp: str
    como_conheceu: Optional[str]
    nivel_ingles: Optional[str]
    objetivo: Optional[str]
    mensagem: Optional[str]
    status: str
    motivo_descarte: Optional[str]
    notas: Optional[str]
    lembrete_em: Optional[datetime]
    aluno_id: Optional[int]
    convertido_em: Optional[datetime]
    criado_em: datetime
    atualizado_em: datetime

    model_config = {"from_attributes": True}


class LeadUpdate(BaseModel):
    status: Optional[str] = None
    motivo_descarte: Optional[str] = None
    notas: Optional[str] = None
    lembrete_em: Optional[datetime] = None

    @field_validator("status")
    @classmethod
    def status_valido(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if v not in {"novo", "em_contato", "trial", "convertido", "descartado"}:
            raise ValueError("Status inválido")
        return v


class LeadConvertResponse(BaseModel):
    aluno_id: int
    username: str
    senha_temporaria: str


class LeadStats(BaseModel):
    total: int
    por_status: dict[str, int]
    novos_ultimos_7d: int
    convertidos_ultimos_30d: int
