from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base
from app.models.tarefa import CefrLevel


class PerfilAluno(Base):
    __tablename__ = "perfis_alunos"

    usuario_id = Column(Integer, ForeignKey("usuarios.id"), primary_key=True)
    nivel = Column(String, nullable=True)
    cefr_level = Column(
        Enum(CefrLevel, name="cefr_level_enum", create_type=False),
        nullable=True,
    )
    xp_total = Column(Integer, nullable=False, default=0, server_default="0")
    aceita_email = Column(Boolean, nullable=False, default=True, server_default="true")
    idioma_portal = Column(String, nullable=False, default="pt", server_default="pt")
    acesso_liberado = Column(Boolean, nullable=False, default=True, server_default="true")
    atualizado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
