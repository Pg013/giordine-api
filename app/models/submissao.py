import enum
from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class StatusSubmissao(str, enum.Enum):
    submitted = "submitted"
    reviewed = "reviewed"


class Submissao(Base):
    __tablename__ = "submissoes"

    id = Column(Integer, primary_key=True, index=True)
    tarefa_id = Column(
        Integer,
        ForeignKey("tarefas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    aluno_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    respostas = Column(JSONB, nullable=False)
    status = Column(
        Enum(StatusSubmissao, name="status_submissao_enum"),
        nullable=False,
        default=StatusSubmissao.submitted,
        server_default="submitted",
    )
    submetido_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    tempo_gasto_seg = Column(Integer, nullable=True)
    atrasada = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    eh_repeticao = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    auto_score = Column(Integer, nullable=True)
