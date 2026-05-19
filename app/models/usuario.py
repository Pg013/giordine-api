import enum
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from app.database import Base


class RoleEnum(str, enum.Enum):
    aluno = "aluno"
    professor = "professor"
    admin = "admin"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    senha_hash = Column(String, nullable=False)
    foto_url = Column(String, nullable=True)
    role = Column(
        Enum(RoleEnum, name="role_enum"),
        nullable=False,
        default=RoleEnum.aluno,
        server_default="aluno",
    )
    ativo = Column(Boolean, nullable=False, default=True, server_default="true")
    criado_em = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    # 2FA TOTP (Google Authenticator / Authy) — recomendado pra admin/professor
    totp_secret = Column(String, nullable=True)
    totp_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
