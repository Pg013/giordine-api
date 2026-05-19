from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.aluno_turma import AlunoTurma
from app.models.perfil_aluno import PerfilAluno
from app.models.turma import Turma
from app.models.usuario import Usuario, RoleEnum
from app.utils.security import get_current_user

router = APIRouter(prefix="/alunos/ranking", tags=["ranking"])


class RankingItem(BaseModel):
    rank: int
    aluno_id: int
    nome: str
    foto_url: Optional[str]
    xp_total: int
    cefr_level: Optional[str]
    turma_nome: Optional[str]
    is_me: bool


@router.get("", response_model=List[RankingItem])
def listar_ranking(
    cefr_level: Optional[str] = Query(None, description="Filtrar por CEFR (A1..C2)"),
    turma_id: Optional[int] = Query(None, description="Filtrar por turma"),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista de alunos ordenada por xp_total descendente.

    Usado pra construir podium + lista no portal do aluno.
    Inclui alunos com `acesso_liberado=true` ordenados por XP total.
    """
    query = (
        db.query(Usuario, PerfilAluno, Turma)
        .filter(Usuario.role == RoleEnum.aluno, Usuario.ativo == True)
        .outerjoin(PerfilAluno, PerfilAluno.usuario_id == Usuario.id)
        .outerjoin(AlunoTurma, AlunoTurma.aluno_id == Usuario.id)
        .outerjoin(Turma, Turma.id == AlunoTurma.turma_id)
        .filter((PerfilAluno.acesso_liberado == True) | (PerfilAluno.acesso_liberado.is_(None)))
    )

    if cefr_level:
        query = query.filter(PerfilAluno.cefr_level == cefr_level)
    if turma_id:
        query = query.filter(AlunoTurma.turma_id == turma_id)

    rows = query.order_by(
        PerfilAluno.xp_total.desc().nullslast(),
        Usuario.nome.asc(),
    ).all()

    result: List[RankingItem] = []
    for idx, (u, p, t) in enumerate(rows):
        result.append(RankingItem(
            rank=idx + 1,
            aluno_id=u.id,
            nome=u.nome,
            foto_url=u.foto_url,
            xp_total=(p.xp_total if p else 0) or 0,
            cefr_level=(p.cefr_level.value if p and p.cefr_level else None),
            turma_nome=(t.nome if t else None),
            is_me=(u.id == user.id),
        ))
    return result
