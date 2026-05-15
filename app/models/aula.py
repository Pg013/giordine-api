from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Aula(Base):
    __tablename__ = "aulas"

    id = Column(Integer, primary_key=True, index=True)
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=True)
    professor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    titulo = Column(String, nullable=False)
    descricao = Column(Text, nullable=True)
    data_hora = Column(DateTime(timezone=True), nullable=False)
    duracao_min = Column(Integer, nullable=False, default=60, server_default="60")
    link_aula = Column(String, nullable=True)  # INCERTO — Meet, Zoom ou outro
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
