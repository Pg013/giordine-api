from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, field_validator


class TurmaDoProfssor(BaseModel):
    id: int
    nome: str
    nivel: str
    cor: str
    qtd_alunos: int

    model_config = {"from_attributes": True}


class RecorrenciaRequest(BaseModel):
    dias_semana: List[int]  # 0=seg, 1=ter, 2=qua, 3=qui, 4=sex, 5=sáb, 6=dom
    ate: date

    @field_validator("dias_semana")
    @classmethod
    def validar_dias(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("dias_semana não pode ser vazio")
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("dias_semana deve conter valores entre 0 e 6")
        return list(set(v))


class CriarAulaRequest(BaseModel):
    turma_id: int
    titulo: str
    descricao: Optional[str] = None
    data_hora: datetime
    duracao_min: int = 60
    link_aula: Optional[str] = None
    recorrencia: Optional[RecorrenciaRequest] = None


class AtualizarAulaRequest(BaseModel):
    titulo: Optional[str] = None
    descricao: Optional[str] = None
    data_hora: Optional[datetime] = None
    duracao_min: Optional[int] = None
    link_aula: Optional[str] = None


class AulaCalendarioItem(BaseModel):
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

    model_config = {"from_attributes": True}


class CriarAulaResponse(BaseModel):
    criadas: int
    serie_id: Optional[str]
    aulas: List[AulaCalendarioItem]
