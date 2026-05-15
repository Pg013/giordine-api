from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class AlunoTurma(Base):
    __tablename__ = "aluno_turma"

    aluno_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    turma_id = Column(Integer, ForeignKey("turmas.id"), primary_key=True)
    entrada_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
