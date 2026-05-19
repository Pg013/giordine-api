from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class Mensagem(Base):
    __tablename__ = "mensagens"

    id = Column(Integer, primary_key=True, index=True)
    remetente_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    # null = mensagem de grupo (turma)
    destinatario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    # null = DM individual
    turma_id = Column(Integer, ForeignKey("turmas.id"), nullable=True, index=True)
    conteudo = Column(Text, nullable=False)
    lida = Column(Boolean, nullable=False, default=False, server_default="false")
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
