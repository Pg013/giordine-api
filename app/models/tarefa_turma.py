from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base


class TarefaTurma(Base):
    __tablename__ = "tarefa_turmas"

    tarefa_id = Column(
        Integer,
        ForeignKey("tarefas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    turma_id = Column(
        Integer,
        ForeignKey("turmas.id", ondelete="CASCADE"),
        primary_key=True,
    )
