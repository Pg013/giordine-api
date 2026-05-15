from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from app.database import Base


class Comunicado(Base):
    __tablename__ = "comunicados"

    id = Column(Integer, primary_key=True, index=True)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String, nullable=False)
    mensagem = Column(Text, nullable=False)
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=True)
    enviado_email = Column(Boolean, nullable=False, default=False, server_default="false")
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
