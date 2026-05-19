from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True, index=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expira_em = Column(DateTime(timezone=True), nullable=False)
    usado_em = Column(DateTime(timezone=True), nullable=True)
