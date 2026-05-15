from app.models.usuario import Usuario, RoleEnum
from app.models.perfil_aluno import PerfilAluno
from app.models.refresh_token import RefreshToken
from app.models.turma import Turma
from app.models.aluno_turma import AlunoTurma
from app.models.comunicado import Comunicado
from app.models.aula import Aula
from app.models.presenca import Presenca
from app.models.aula_extra import AulaExtra

__all__ = [
    "Usuario", "RoleEnum", "PerfilAluno", "RefreshToken",
    "Turma", "AlunoTurma", "Comunicado",
    "Aula", "Presenca", "AulaExtra",
]
