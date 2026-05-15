from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


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


class TurmaAlunoBody(BaseModel):
    turma_id: int


class CriarTurmaRequest(BaseModel):
    nome: str
    nivel: str
    professor_id: Optional[int] = None


class TurmaListItem(BaseModel):
    id: int
    nome: str
    nivel: str
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
