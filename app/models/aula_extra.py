from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class AulaExtra(Base):
    __tablename__ = "aulas_extra"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    data_sugerida = Column(Date, nullable=False)
    motivo = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pendente", server_default="pendente")
    resposta_admin = Column(Text, nullable=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
