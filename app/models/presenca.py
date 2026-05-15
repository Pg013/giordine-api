from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from app.database import Base


class Presenca(Base):
    __tablename__ = "presencas"

    id = Column(Integer, primary_key=True, index=True)
    aula_id = Column(Integer, ForeignKey("aulas.id"), nullable=False)
    aluno_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    confirmado = Column(Boolean, nullable=False, default=False, server_default="false")
    confirmado_em = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("aula_id", "aluno_id", name="uq_presenca_aula_aluno"),
    )
