from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.sql import func
from app.database import Base


class GanhoPontos(Base):
    __tablename__ = "ganhos_pontos"

    id = Column(Integer, primary_key=True, index=True)
    aluno_id = Column(
        Integer,
        ForeignKey("usuarios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submissao_id = Column(
        Integer,
        ForeignKey("submissoes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pontos = Column(Integer, nullable=False)
    criado_em = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
