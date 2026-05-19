from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class HistoricoNivel(Base):
    __tablename__ = "historico_niveis"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    nivel = Column(String, nullable=False)
    entrada_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
