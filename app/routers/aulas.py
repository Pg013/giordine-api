import calendar as cal_module
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.usuario import Usuario
from app.models.aula import Aula
from app.models.presenca import Presenca
from app.models.aula_extra import AulaExtra
from app.models.aluno_turma import AlunoTurma
from app.schemas.aulas import AulaItem, AulaExtraItem, SolicitarAulaExtraRequest
from app.utils.security import get_current_user

router_aulas = APIRouter(prefix="/aulas", tags=["aulas"])
router_aulas_extra = APIRouter(prefix="/aulas-extra", tags=["aulas-extra"])


# ── Aulas ────────────────────────────────────────────────────────────────────


@router_aulas.get("", response_model=List[AulaItem])
def listar_aulas(
    mes: str = Query(..., description="YYYY-MM"),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        year, month = int(mes[:4]), int(mes[5:7])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Formato inválido. Use YYYY-MM")

    inicio = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = cal_module.monthrange(year, month)[1]
    fim = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    turma_ids = [
        at.turma_id
        for at in db.query(AlunoTurma).filter(AlunoTurma.aluno_id == user.id).all()
    ]

    if not turma_ids:
        return []

    aulas = (
        db.query(Aula)
        .filter(
            Aula.turma_id.in_(turma_ids),
            Aula.data_hora >= inicio,
            Aula.data_hora <= fim,
        )
        .order_by(Aula.data_hora)
        .all()
    )

    aula_ids = [a.id for a in aulas]
    presencas = {
        p.aula_id: p.confirmado
        for p in db.query(Presenca).filter(
            Presenca.aluno_id == user.id,
            Presenca.aula_id.in_(aula_ids),
        ).all()
    } if aula_ids else {}

    professor_ids = {a.professor_id for a in aulas if a.professor_id}
    professores = {
        u.id: u.nome
        for u in db.query(Usuario).filter(Usuario.id.in_(professor_ids)).all()
    } if professor_ids else {}

    return [
        AulaItem(
            id=a.id,
            titulo=a.titulo,
            descricao=a.descricao,
            data_hora=a.data_hora,
            duracao_min=a.duracao_min,
            professor_nome=professores.get(a.professor_id),
            link_aula=a.link_aula,  # INCERTO — Meet, Zoom ou outro
            presenca_confirmada=presencas.get(a.id, False),
        )
        for a in aulas
    ]


@router_aulas.post("/{aula_id}/confirmar", status_code=status.HTTP_204_NO_CONTENT)
def confirmar_presenca(
    aula_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    aula = db.query(Aula).filter(Aula.id == aula_id).first()
    if not aula:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aula não encontrada")

    presenca = db.query(Presenca).filter(
        Presenca.aula_id == aula_id,
        Presenca.aluno_id == user.id,
    ).first()

    if presenca:
        presenca.confirmado = True
        presenca.confirmado_em = datetime.now(timezone.utc)
    else:
        db.add(Presenca(
            aula_id=aula_id,
            aluno_id=user.id,
            confirmado=True,
            confirmado_em=datetime.now(timezone.utc),
        ))
    db.commit()


# ── Aulas Extra ──────────────────────────────────────────────────────────────


@router_aulas_extra.get("", response_model=List[AulaExtraItem])
def listar_aulas_extra(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(AulaExtra)
        .filter(AulaExtra.aluno_id == user.id)
        .order_by(AulaExtra.criado_em.desc())
        .all()
    )


@router_aulas_extra.post("", response_model=AulaExtraItem, status_code=status.HTTP_201_CREATED)
def solicitar_aula_extra(
    body: SolicitarAulaExtraRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nova = AulaExtra(
        aluno_id=user.id,
        data_sugerida=body.data_sugerida,
        motivo=body.motivo,
        status="pendente",
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova
