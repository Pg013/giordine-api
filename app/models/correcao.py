from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.database import Base


class Correcao(Base):
    __tablename__ = "correcoes"

    id = Column(Integer, primary_key=True, index=True)
    submissao_id = Column(
        Integer,
        ForeignKey("submissoes.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    professor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    score = Column(Integer, nullable=False)
    grade = Column(String, nullable=True)
    auto_score = Column(Integer, nullable=True)
    rubrica_scores = Column(JSONB, nullable=True)
    feedback = Column(Text, nullable=True)
    inline_notes = Column(JSONB, nullable=True)
    corrigido_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
