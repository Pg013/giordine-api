from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class PerfilAluno(Base):
    __tablename__ = "perfis_alunos"

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    foto_url = Column(String, nullable=True)
    nivel = Column(String, nullable=True)
    aceita_email = Column(Boolean, nullable=False, default=True, server_default="true")
    idioma_portal = Column(String, nullable=False, default="pt", server_default="pt")
    acesso_liberado = Column(Boolean, nullable=False, default=True, server_default="true")
    atualizado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
