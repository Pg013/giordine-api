from sqlalchemy import Column, Integer, ForeignKey, Enum
from app.database import Base
from app.models.tarefa import CefrLevel


class TarefaCefrLevel(Base):
    __tablename__ = "tarefa_cefr_levels"

    tarefa_id = Column(
        Integer,
        ForeignKey("tarefas.id", ondelete="CASCADE"),
        primary_key=True,
    )
    cefr_level = Column(
        Enum(CefrLevel, name="cefr_level_enum", create_type=False),
        primary_key=True,
    )
