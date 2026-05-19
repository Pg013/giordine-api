from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class QueenTrainingNote(Base):
    """
    Regras globais que moldam o comportamento da Queen para TODOS os usuários.
    Apenas usuários com role=admin podem criar/remover.
    """
    __tablename__ = "queen_training_notes"

    id = Column(Integer, primary_key=True, index=True)
    rule = Column(String(500), nullable=False)
    criado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
