from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.correcao import Correcao
from app.models.ganho_pontos import GanhoPontos
from app.models.perfil_aluno import PerfilAluno
from app.models.submissao import Submissao, StatusSubmissao
from app.models.tarefa import Tarefa
from app.models.usuario import Usuario, RoleEnum
from app.schemas.tarefas import (
    CorrecaoResponse,
    CorrigirSubmissaoRequest,
    SubmissaoCompletaProfessor,
    SubmissaoPendenteItem,
)
from app.utils.security import require_professor_or_admin

router = APIRouter(prefix="/correcoes", tags=["correcoes"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_correcao_response(correcao: Correcao, pontos_ganhos: int) -> CorrecaoResponse:
    return CorrecaoResponse(
        id=correcao.id,
        submissao_id=correcao.submissao_id,
        score=correcao.score,
        grade=correcao.grade,
        auto_score=correcao.auto_score,
        rubrica_scores=correcao.rubrica_scores,
        feedback=correcao.feedback,
        inline_notes=correcao.inline_notes,
        corrigido_em=correcao.corrigido_em,
        pontos_ganhos=pontos_ganhos,
    )


def _pode_corrigir(user: Usuario, tarefa: Tarefa) -> bool:
    """Admin corrige qualquer tarefa; professor só as que criou."""
    if user.role == RoleEnum.admin:
        return True
    return tarefa.criado_por == user.id


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/pendentes", response_model=List[SubmissaoPendenteItem])
def listar_pendentes(
    tarefa_id: Optional[int] = Query(None),
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    """Submissões com status=submitted aguardando correção.

    Admin vê todas; professor vê apenas submissões de tarefas que ele criou.
    """
    query = (
        db.query(Submissao, Tarefa, Usuario)
        .join(Tarefa, Tarefa.id == Submissao.tarefa_id)
        .join(Usuario, Usuario.id == Submissao.aluno_id)
        .filter(Submissao.status == StatusSubmissao.submitted)
    )

    if user.role != RoleEnum.admin:
        query = query.filter(Tarefa.criado_por == user.id)

    if tarefa_id:
        query = query.filter(Submissao.tarefa_id == tarefa_id)

    rows = query.order_by(Submissao.submetido_em.asc()).all()

    return [
        SubmissaoPendenteItem(
            id=submissao.id,
            tarefa_id=tarefa.id,
            tarefa_titulo=tarefa.titulo,
            tarefa_tipo=tarefa.tipo,
            aluno_id=aluno.id,
            aluno_nome=aluno.nome,
            submetido_em=submissao.submetido_em,
            atrasada=submissao.atrasada,
            auto_score=submissao.auto_score,
        )
        for submissao, tarefa, aluno in rows
    ]


@router.get("/submissoes/{submissao_id}", response_model=SubmissaoCompletaProfessor)
def get_submissao(
    submissao_id: int,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    """Detalhe completo da submissão pra corrigir.

    Inclui `tarefa_conteudo` SEM sanitização (professor precisa ver gabaritos).
    """
    submissao = db.query(Submissao).filter(Submissao.id == submissao_id).first()
    if not submissao:
        raise HTTPException(status_code=404, detail="Submissão não encontrada")

    tarefa = db.query(Tarefa).filter(Tarefa.id == submissao.tarefa_id).first()
    if not tarefa or not _pode_corrigir(user, tarefa):
        raise HTTPException(status_code=403, detail="Sem permissão")

    aluno = db.query(Usuario).filter(Usuario.id == submissao.aluno_id).first()

    correcao = (
        db.query(Correcao).filter(Correcao.submissao_id == submissao_id).first()
    )
    correcao_resp = None
    if correcao:
        ganho = (
            db.query(GanhoPontos)
            .filter(GanhoPontos.submissao_id == submissao_id)
            .first()
        )
        pontos = ganho.pontos if ganho else 0
        correcao_resp = _build_correcao_response(correcao, pontos)

    return SubmissaoCompletaProfessor(
        id=submissao.id,
        tarefa_id=tarefa.id,
        tarefa_titulo=tarefa.titulo,
        tarefa_tipo=tarefa.tipo,
        tarefa_conteudo=tarefa.conteudo,
        tarefa_rubrica=tarefa.rubrica,
        tarefa_pontos_disponiveis=tarefa.pontos_disponiveis,
        aluno_id=aluno.id,
        aluno_nome=aluno.nome,
        respostas=submissao.respostas,
        status=submissao.status.value,
        submetido_em=submissao.submetido_em,
        tempo_gasto_seg=submissao.tempo_gasto_seg,
        atrasada=submissao.atrasada,
        eh_repeticao=submissao.eh_repeticao,
        auto_score=submissao.auto_score,
        correcao=correcao_resp,
    )


@router.post(
    "/submissoes/{submissao_id}",
    response_model=CorrecaoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_correcao(
    submissao_id: int,
    body: CorrigirSubmissaoRequest,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    """Corrige a submissão em uma única transação atômica:

    1. INSERT em `correcoes`
    2. UPDATE `submissoes.status` → 'reviewed'
    3. Calcula pontos = round(pontos_disponiveis × score / 100)
       — se `eh_repeticao=true`, vale 50% (reciclagem)
    4. INSERT em `ganhos_pontos`
    5. UPDATE `perfis_alunos.xp_total` += pontos

    Todos os passos ocorrem antes do mesmo `db.commit()` —
    crash entre eles faz rollback de tudo, mantendo `xp_total` consistente.
    """
    submissao = db.query(Submissao).filter(Submissao.id == submissao_id).first()
    if not submissao:
        raise HTTPException(status_code=404, detail="Submissão não encontrada")

    if submissao.status == StatusSubmissao.reviewed:
        raise HTTPException(status_code=409, detail="Submissão já corrigida")

    tarefa = db.query(Tarefa).filter(Tarefa.id == submissao.tarefa_id).first()
    if not tarefa:
        raise HTTPException(
            status_code=500,
            detail="Tarefa associada não encontrada (estado inconsistente)",
        )

    if not _pode_corrigir(user, tarefa):
        raise HTTPException(
            status_code=403,
            detail="Sem permissão — você não criou esta tarefa",
        )

    correcao = Correcao(
        submissao_id=submissao.id,
        professor_id=user.id,
        score=body.score,
        grade=body.grade,
        auto_score=submissao.auto_score,
        rubrica_scores=(
            [r.model_dump() for r in body.rubrica_scores]
            if body.rubrica_scores
            else None
        ),
        feedback=body.feedback,
        inline_notes=(
            [n.model_dump() for n in body.inline_notes]
            if body.inline_notes
            else None
        ),
    )
    db.add(correcao)

    submissao.status = StatusSubmissao.reviewed

    pontos = int(round(tarefa.pontos_disponiveis * body.score / 100))
    if submissao.eh_repeticao:
        pontos = pontos // 2  # reciclagem 50%

    ganho = GanhoPontos(
        aluno_id=submissao.aluno_id,
        submissao_id=submissao.id,
        pontos=pontos,
    )
    db.add(ganho)

    perfil = (
        db.query(PerfilAluno)
        .filter(PerfilAluno.usuario_id == submissao.aluno_id)
        .first()
    )
    if perfil:
        perfil.xp_total = (perfil.xp_total or 0) + pontos

    db.commit()
    db.refresh(correcao)

    return _build_correcao_response(correcao, pontos)
