from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class AulaItem(BaseModel):
    id: int
    titulo: str
    descricao: Optional[str]
    data_hora: datetime
    duracao_min: int
    professor_nome: Optional[str]
    link_aula: Optional[str]  # INCERTO — Meet, Zoom ou outro
    presenca_confirmada: bool


class AulaExtraItem(BaseModel):
    id: int
    data_sugerida: date
    motivo: str
    status: str
    resposta_admin: Optional[str]
    criado_em: datetime

    model_config = {"from_attributes": True}


class SolicitarAulaExtraRequest(BaseModel):
    data_sugerida: date
    motivo: str
