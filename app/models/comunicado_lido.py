from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class ComunicadoLido(Base):
    __tablename__ = "comunicados_lidos"

    aluno_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    comunicado_id = Column(Integer, ForeignKey("comunicados.id"), primary_key=True)
    lido_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
