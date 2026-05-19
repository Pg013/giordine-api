import re
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator, model_validator, ConfigDict


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

    @field_validator("foto_base64")
    @classmethod
    def validar_foto(cls, v: str) -> str:
        tipos_permitidos = ("data:image/jpeg", "data:image/png", "data:image/webp")
        if not v.startswith(tipos_permitidos):
            raise ValueError("Formato inválido. Use JPEG, PNG ou WebP")
        # base64 de 5 MB ≈ 6.8 MB de string
        if len(v) > 7_000_000:
            raise ValueError("Imagem muito grande. Máximo 5 MB")
        return v


class ComunicadoAlunoItem(BaseModel):
    id: int
    titulo: str
    mensagem: str
    turma_id: Optional[int]
    turma_nome: Optional[str]
    criado_em: datetime
    lido: bool

    model_config = ConfigDict(from_attributes=True)


class ComunicadosAlunoResponse(BaseModel):
    total_nao_lidos: int
    comunicados: List[ComunicadoAlunoItem]


class HistoricoNivelItem(BaseModel):
    nivel: str
    entrada_em: datetime

    model_config = {"from_attributes": True}


class ProgressoResponse(BaseModel):
    entrada_no_curso: datetime
    meses_no_curso: int
    nivel_atual: Optional[str]
    historico_niveis: List[HistoricoNivelItem]
    total_aulas_presentes: int
    total_faltas: int
    percentual_presenca: float
