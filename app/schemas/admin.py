from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator
import re

from app.models.tarefa import CefrLevel


class CriarAlunoRequest(BaseModel):
    nome: str
    email: str
    username: str
    nivel: Optional[str] = None


class CriarAlunoResponse(BaseModel):
    id: int
    nome: str
    username: str
    email: str
    nivel: Optional[str]
    senha_temporaria: str

    model_config = {"from_attributes": True}


class TurmaInfo(BaseModel):
    id: int
    nome: str
    nivel: str

    model_config = {"from_attributes": True}


class AlunoListItem(BaseModel):
    id: int
    nome: str
    username: str
    email: str
    nivel: Optional[str]
    acesso_liberado: bool
    turma_atual: Optional[TurmaInfo]

    model_config = {"from_attributes": True}


class AcessoBody(BaseModel):
    acesso_liberado: bool


class NivelBody(BaseModel):
    nivel: str


class CefrLevelBody(BaseModel):
    cefr_level: Optional[CefrLevel] = None


class TurmaAlunoBody(BaseModel):
    turma_id: int


class CriarProfessorRequest(BaseModel):
    nome: str
    email: str
    username: str


class CriarProfessorResponse(BaseModel):
    id: int
    nome: str
    username: str
    email: str
    senha_temporaria: str

    model_config = {"from_attributes": True}


class CriarTurmaRequest(BaseModel):
    nome: str
    nivel: str
    professor_id: Optional[int] = None
    cor: str = "#3B82F6"

    @field_validator("cor")
    @classmethod
    def validar_cor(cls, v: str) -> str:
        if not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("cor deve ser um hex válido (#RRGGBB)")
        return v.upper()


class AtualizarTurmaRequest(BaseModel):
    nome: Optional[str] = None
    nivel: Optional[str] = None
    professor_id: Optional[int] = None
    cor: Optional[str] = None
    ativo: Optional[bool] = None

    @field_validator("cor")
    @classmethod
    def validar_cor(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r"^#[0-9A-Fa-f]{6}$", v):
            raise ValueError("cor deve ser um hex válido (#RRGGBB)")
        return v.upper() if v else v


class TurmaListItem(BaseModel):
    id: int
    nome: str
    nivel: str
    cor: str
    professor_id: Optional[int]
    professor_nome: Optional[str] = None
    ativo: bool
    qtd_alunos: int

    model_config = {"from_attributes": True}


class ProfessorBody(BaseModel):
    professor_id: int


class CriarComunicadoRequest(BaseModel):
    titulo: str
    mensagem: str
    turma_id: Optional[int] = None


class ComunicadoListItem(BaseModel):
    id: int
    autor_id: int
    titulo: str
    mensagem: str
    turma_id: Optional[int]
    enviado_email: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ────────────────────────────────────────────────────────────────

class UltimoAlunoItem(BaseModel):
    id: int
    nome: str
    username: str
    nivel: Optional[str]
    criado_em: datetime

    model_config = {"from_attributes": True}


class ComunicadoRecenteItem(BaseModel):
    id: int
    titulo: str
    criado_em: datetime
    turma_id: Optional[int]

    model_config = {"from_attributes": True}


class AcessoBloqueadoItem(BaseModel):
    id: int
    nome: str
    username: str
    nivel: Optional[str]

    model_config = {"from_attributes": True}


class ProfessorListItem(BaseModel):
    id: int
    nome: str
    username: str
    email: str

    model_config = {"from_attributes": True}


class AlunoTurmaItem(BaseModel):
    id: int
    nome: str
    username: str
    nivel: Optional[str]
    acesso_liberado: bool

    model_config = {"from_attributes": True}


class TurmaDetalhe(BaseModel):
    id: int
    nome: str
    nivel: str
    cor: str
    ativo: bool
    professor_id: Optional[int]
    professor_nome: Optional[str]
    alunos: List[AlunoTurmaItem]
    qtd_alunos: int


class DashboardData(BaseModel):
    total_alunos_ativos: int
    total_turmas_ativas: int
    total_professores: int
    comunicados_mes: int
    ultimos_alunos: List[UltimoAlunoItem]
    comunicados_recentes: List[ComunicadoRecenteItem]
    acessos_bloqueados: List[AcessoBloqueadoItem]


# ── Aulas (admin pode criar/editar aulas de qualquer professor) ───────────────

class CriarAulaAdminRequest(BaseModel):
    turma_id: Optional[int] = None
    professor_id: Optional[int] = None
    titulo: str
    descricao: Optional[str] = None
    data_hora: datetime
    duracao_min: int = 60
    link_aula: Optional[str] = None


class AtualizarAulaAdminRequest(BaseModel):
    turma_id: Optional[int] = None
    professor_id: Optional[int] = None
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    data_hora: Optional[datetime] = None
    duracao_min: Optional[int] = None
    link_aula: Optional[str] = None


class AulaAdminItem(BaseModel):
    id: int
    turma_id: Optional[int]
    turma_nome: Optional[str] = None
    turma_cor: Optional[str] = None
    professor_id: Optional[int]
    professor_nome: Optional[str] = None
    titulo: str
    descricao: Optional[str]
    data_hora: datetime
    duracao_min: int
    link_aula: Optional[str]
    serie_id: Optional[str]
    criado_em: datetime

    model_config = {"from_attributes": True}
