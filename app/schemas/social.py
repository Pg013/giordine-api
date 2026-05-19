from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class EnviarDMRequest(BaseModel):
    destinatario_id: int
    conteudo: str


class EnviarGrupoRequest(BaseModel):
    conteudo: str


class MensagemItem(BaseModel):
    id: int
    remetente_id: int
    remetente_nome: str
    destinatario_id: Optional[int]
    turma_id: Optional[int]
    conteudo: str
    lida: bool
    criado_em: datetime

    model_config = {"from_attributes": True}


class ConversaItem(BaseModel):
    usuario_id: int
    nome: str
    foto_url: Optional[str]
    nao_lidas: int
    ultima_mensagem: Optional[str]
    ultima_mensagem_em: Optional[datetime]


class ConversasResponse(BaseModel):
    conversas: List[ConversaItem]


class ChatGrupoResponse(BaseModel):
    turma_id: int
    turma_nome: str
    turma_cor: str
    mensagens: List[MensagemItem]
