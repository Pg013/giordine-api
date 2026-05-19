from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class RascunhoSubmissao(Base):
    __tablename__ = "rascunhos_submissao"

    tarefa_id = Column(
        Integer,
        ForeignKey("tarefas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    aluno_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        primary_key=True,
    )
    respostas = Column(JSONB, nullable=False)
    progresso = Column(JSONB, nullable=True)
    atualizado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
