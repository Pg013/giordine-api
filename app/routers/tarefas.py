from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.tarefa import Tarefa, CategoriaTarefa, StatusTarefa, CefrLevel
from app.models.tarefa_cefr_level import TarefaCefrLevel
from app.models.tarefa_turma import TarefaTurma
from app.models.turma import Turma
from app.models.usuario import Usuario
from app.schemas.tarefas import (
    CriarTarefaRequest,
    AtualizarTarefaRequest,
    TarefaListItem,
    TarefaDetalhe,
)
from app.utils.security import require_professor_or_admin

router = APIRouter(prefix="/tarefas", tags=["tarefas"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _build_detalhe(tarefa: Tarefa, db: Session) -> TarefaDetalhe:
    cefr_rows = (
        db.query(TarefaCefrLevel)
        .filter(TarefaCefrLevel.tarefa_id == tarefa.id)
        .all()
    )
    turma_rows = (
        db.query(TarefaTurma).filter(TarefaTurma.tarefa_id == tarefa.id).all()
    )
    return TarefaDetalhe(
        id=tarefa.id,
        categoria=tarefa.categoria,
        tipo=tarefa.tipo,
        titulo=tarefa.titulo,
        descricao=tarefa.descricao,
        conteudo=tarefa.conteudo,
        rubrica=tarefa.rubrica,
        pontos_disponiveis=tarefa.pontos_disponiveis,
        status=tarefa.status,
        data_entrega=tarefa.data_entrega,
        cefr_levels=[r.cefr_level for r in cefr_rows],
        turmas_alvo=[r.turma_id for r in turma_rows],
        criado_por=tarefa.criado_por,
        criado_em=tarefa.criado_em,
        publicado_em=tarefa.publicado_em,
        arquivado_em=tarefa.arquivado_em,
    )


def _validar_turmas_existem(db: Session, turmas_alvo: List[int]) -> None:
    if not turmas_alvo:
        return
    existentes = {
        t.id for t in db.query(Turma.id).filter(Turma.id.in_(turmas_alvo)).all()
    }
    invalidas = set(turmas_alvo) - existentes
    if invalidas:
        raise HTTPException(
            status_code=400,
            detail=f"Turmas não encontradas: {sorted(invalidas)}",
        )


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.post("", response_model=TarefaDetalhe, status_code=status.HTTP_201_CREATED)
def criar_tarefa(
    body: CriarTarefaRequest,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    _validar_turmas_existem(db, body.turmas_alvo)

    tarefa = Tarefa(
        categoria=body.categoria,
        tipo=body.tipo,
        titulo=body.titulo,
        descricao=body.descricao,
        conteudo=body.conteudo.model_dump(),
        rubrica=[c.model_dump() for c in body.rubrica] if body.rubrica else None,
        data_entrega=body.data_entrega,
        pontos_disponiveis=body.pontos_disponiveis,
        criado_por=user.id,
    )
    db.add(tarefa)
    db.flush()

    for cefr in body.cefr_levels:
        db.add(TarefaCefrLevel(tarefa_id=tarefa.id, cefr_level=cefr))
    for turma_id in body.turmas_alvo:
        db.add(TarefaTurma(tarefa_id=tarefa.id, turma_id=turma_id))

    db.commit()
    db.refresh(tarefa)
    return _build_detalhe(tarefa, db)


@router.get("", response_model=List[TarefaListItem])
def listar_tarefas(
    status_filter: Optional[StatusTarefa] = Query(None, alias="status"),
    categoria: Optional[CategoriaTarefa] = Query(None),
    cefr_level: Optional[CefrLevel] = Query(None),
    turma_id: Optional[int] = Query(None),
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Tarefa)
    if status_filter:
        query = query.filter(Tarefa.status == status_filter)
    if categoria:
        query = query.filter(Tarefa.categoria == categoria)
    if cefr_level:
        query = query.join(TarefaCefrLevel).filter(
            TarefaCefrLevel.cefr_level == cefr_level
        )
    if turma_id:
        query = query.join(TarefaTurma).filter(TarefaTurma.turma_id == turma_id)

    tarefas = query.order_by(Tarefa.criado_em.desc()).all()
    if not tarefas:
        return []

    tarefa_ids = [t.id for t in tarefas]
    cefr_map: dict = {}
    for r in (
        db.query(TarefaCefrLevel)
        .filter(TarefaCefrLevel.tarefa_id.in_(tarefa_ids))
        .all()
    ):
        cefr_map.setdefault(r.tarefa_id, []).append(r.cefr_level)
    turma_map: dict = {}
    for r in (
        db.query(TarefaTurma).filter(TarefaTurma.tarefa_id.in_(tarefa_ids)).all()
    ):
        turma_map.setdefault(r.tarefa_id, []).append(r.turma_id)

    return [
        TarefaListItem(
            id=t.id,
            categoria=t.categoria,
            tipo=t.tipo,
            titulo=t.titulo,
            descricao=t.descricao,
            pontos_disponiveis=t.pontos_disponiveis,
            status=t.status,
            data_entrega=t.data_entrega,
            cefr_levels=cefr_map.get(t.id, []),
            turmas_alvo=turma_map.get(t.id, []),
            criado_em=t.criado_em,
            publicado_em=t.publicado_em,
        )
        for t in tarefas
    ]


@router.get("/{tarefa_id}", response_model=TarefaDetalhe)
def get_tarefa(
    tarefa_id: int,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    return _build_detalhe(tarefa, db)


@router.patch("/{tarefa_id}", response_model=TarefaDetalhe)
def atualizar_tarefa(
    tarefa_id: int,
    body: AtualizarTarefaRequest,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    if tarefa.status != StatusTarefa.draft:
        raise HTTPException(
            status_code=409,
            detail="Tarefa só pode ser editada em status 'draft'",
        )

    if body.turmas_alvo is not None:
        _validar_turmas_existem(db, body.turmas_alvo)

    if body.titulo is not None:
        tarefa.titulo = body.titulo
    if body.descricao is not None:
        tarefa.descricao = body.descricao
    if body.conteudo is not None:
        tarefa.conteudo = body.conteudo.model_dump()
    if body.rubrica is not None:
        tarefa.rubrica = [c.model_dump() for c in body.rubrica]
    if body.data_entrega is not None:
        tarefa.data_entrega = body.data_entrega
    if body.pontos_disponiveis is not None:
        tarefa.pontos_disponiveis = body.pontos_disponiveis

    if body.cefr_levels is not None:
        db.query(TarefaCefrLevel).filter(
            TarefaCefrLevel.tarefa_id == tarefa_id
        ).delete()
        for cefr in body.cefr_levels:
            db.add(TarefaCefrLevel(tarefa_id=tarefa_id, cefr_level=cefr))

    if body.turmas_alvo is not None:
        db.query(TarefaTurma).filter(TarefaTurma.tarefa_id == tarefa_id).delete()
        for tid in body.turmas_alvo:
            db.add(TarefaTurma(tarefa_id=tarefa_id, turma_id=tid))

    db.commit()
    db.refresh(tarefa)
    return _build_detalhe(tarefa, db)


@router.post("/{tarefa_id}/publicar", response_model=TarefaDetalhe)
def publicar_tarefa(
    tarefa_id: int,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if tarefa.status != StatusTarefa.draft:
        raise HTTPException(
            status_code=409,
            detail=f"Tarefa em status '{tarefa.status.value}' não pode ser publicada",
        )

    has_cefr = (
        db.query(TarefaCefrLevel)
        .filter(TarefaCefrLevel.tarefa_id == tarefa_id)
        .count()
    )
    has_turma = (
        db.query(TarefaTurma).filter(TarefaTurma.tarefa_id == tarefa_id).count()
    )
    if not has_cefr and not has_turma:
        raise HTTPException(
            status_code=409,
            detail="Tarefa precisa ter pelo menos 1 cefr_level ou turma_alvo antes de publicar",
        )

    tarefa.status = StatusTarefa.published
    tarefa.publicado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tarefa)
    return _build_detalhe(tarefa, db)


@router.post("/{tarefa_id}/arquivar", response_model=TarefaDetalhe)
def arquivar_tarefa(
    tarefa_id: int,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if tarefa.status != StatusTarefa.published:
        raise HTTPException(
            status_code=409,
            detail=f"Tarefa em status '{tarefa.status.value}' não pode ser arquivada",
        )

    tarefa.status = StatusTarefa.archived
    tarefa.arquivado_em = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tarefa)
    return _build_detalhe(tarefa, db)


@router.delete("/{tarefa_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_tarefa(
    tarefa_id: int,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    tarefa = db.query(Tarefa).filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")
    if tarefa.status != StatusTarefa.draft:
        raise HTTPException(
            status_code=409,
            detail="Só tarefas em status 'draft' podem ser deletadas. Use 'arquivar' para tarefas publicadas.",
        )
    db.delete(tarefa)
    db.commit()
