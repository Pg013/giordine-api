from app.models.usuario import Usuario, RoleEnum
from app.models.tarefa import Tarefa, CategoriaTarefa, StatusTarefa, CefrLevel
from app.models.perfil_aluno import PerfilAluno
from app.models.refresh_token import RefreshToken
from app.models.turma import Turma
from app.models.aluno_turma import AlunoTurma
from app.models.comunicado import Comunicado
from app.models.comunicado_lido import ComunicadoLido
from app.models.aula import Aula
from app.models.presenca import Presenca
from app.models.aula_extra import AulaExtra
from app.models.historico_nivel import HistoricoNivel
from app.models.mensagem import Mensagem
from app.models.password_reset_token import PasswordResetToken
from app.models.queen_message import QueenMessage
from app.models.queen_training_note import QueenTrainingNote
from app.models.lead import Lead, LeadStatus
from app.models.tarefa_cefr_level import TarefaCefrLevel
from app.models.tarefa_turma import TarefaTurma
from app.models.submissao import Submissao, StatusSubmissao
from app.models.rascunho_submissao import RascunhoSubmissao
from app.models.correcao import Correcao
from app.models.ganho_pontos import GanhoPontos

__all__ = [
    "Usuario", "RoleEnum", "PerfilAluno", "RefreshToken",
    "Turma", "AlunoTurma", "Comunicado", "ComunicadoLido",
    "Aula", "Presenca", "AulaExtra",
    "HistoricoNivel", "Mensagem", "PasswordResetToken",
    "QueenMessage", "QueenTrainingNote",
    "Lead", "LeadStatus",
    "Tarefa", "CategoriaTarefa", "StatusTarefa", "CefrLevel",
    "TarefaCefrLevel", "TarefaTurma",
    "Submissao", "StatusSubmissao", "RascunhoSubmissao",
    "Correcao", "GanhoPontos",
]
