import enum
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.sql import func
from app.database import Base


class LeadStatus(str, enum.Enum):
    novo = "novo"               # acabou de chegar, ainda não respondi
    em_contato = "em_contato"   # já conversei, aguardando resposta
    trial = "trial"             # fazendo aula experimental
    convertido = "convertido"   # virou aluno (cria conta automaticamente)
    descartado = "descartado"   # não rolou — registra motivo


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)

    # Obrigatórios (do form público)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    whatsapp = Column(String, nullable=False)

    # Opcionais (sanfona no form)
    como_conheceu = Column(String, nullable=True)      # instagram, whatsapp, indicacao, google, outro
    nivel_ingles = Column(String, nullable=True)       # iniciante, basico, intermediario, avancado, nao_sei
    objetivo = Column(String, nullable=True)            # viagem, trabalho, estudos, conversacao, outro
    mensagem = Column(Text, nullable=True)

    # Pipeline
    status = Column(
        Enum(LeadStatus, name="lead_status_enum"),
        nullable=False,
        default=LeadStatus.novo,
        server_default="novo",
        index=True,
    )
    motivo_descarte = Column(String, nullable=True)     # quando status=descartado

    # Notas internas do admin
    notas = Column(Text, nullable=True)

    # Lembrete pra retomar contato
    lembrete_em = Column(DateTime(timezone=True), nullable=True)

    # Quando virou aluno
    aluno_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    convertido_em = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    atualizado_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
