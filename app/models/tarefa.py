import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class CategoriaTarefa(str, enum.Enum):
    gramatica = "gramatica"
    vocabulario = "vocabulario"
    leitura = "leitura"
    escrita = "escrita"
    escuta = "escuta"
    fala = "fala"
    traducao = "traducao"


class StatusTarefa(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class CefrLevel(str, enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class Tarefa(Base):
    __tablename__ = "tarefas"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(
        Enum(CategoriaTarefa, name="categoria_tarefa_enum"),
        nullable=False,
        index=True,
    )
    tipo = Column(String, nullable=False, index=True)
    titulo = Column(String, nullable=False)
    descricao = Column(Text, nullable=True)
    conteudo = Column(JSONB, nullable=False)
    rubrica = Column(JSONB, nullable=True)
    data_entrega = Column(DateTime(timezone=True), nullable=True)
    pontos_disponiveis = Column(Integer, nullable=False)
    status = Column(
        Enum(StatusTarefa, name="status_tarefa_enum"),
        nullable=False,
        default=StatusTarefa.draft,
        server_default="draft",
        index=True,
    )
    criado_por = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    publicado_em = Column(DateTime(timezone=True), nullable=True)
    arquivado_em = Column(DateTime(timezone=True), nullable=True)
