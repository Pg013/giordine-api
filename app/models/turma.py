from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Turma(Base):
    __tablename__ = "turmas"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    nivel = Column(String, nullable=False)
    professor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    cor = Column(String(7), nullable=False, default="#3B82F6", server_default="'#3B82F6'")
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
