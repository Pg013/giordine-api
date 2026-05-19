import uuid
import calendar as cal_module
from datetime import datetime, timedelta, timezone, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.turma import Turma
from app.models.aluno_turma import AlunoTurma
from app.models.aula import Aula
from app.models.comunicado import Comunicado
from app.schemas.professores import (
    TurmaDoProfssor,
    CriarAulaRequest,
    AtualizarAulaRequest,
    AulaCalendarioItem,
    CriarAulaResponse,
)
from app.utils.security import require_professor_or_admin

router = APIRouter(prefix="/professores", tags=["professores"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _build_aula_item(aula: Aula, turmas: dict, professores: dict) -> AulaCalendarioItem:
    turma = turmas.get(aula.turma_id)
    return AulaCalendarioItem(
        id=aula.id,
        turma_id=aula.turma_id,
        turma_nome=turma.nome if turma else None,
        turma_cor=turma.cor if turma else None,
        professor_id=aula.professor_id,
        professor_nome=professores.get(aula.professor_id),
        titulo=aula.titulo,
        descricao=aula.descricao,
        data_hora=aula.data_hora,
        duracao_min=aula.duracao_min,
        link_aula=aula.link_aula,
        serie_id=aula.serie_id,
    )


def _gerar_datas_serie(data_hora: datetime, dias_semana: List[int], ate: date) -> List[datetime]:
    """Gera todas as ocorrências a partir de data_hora.date() até ate, nos dias da semana informados."""
    resultado = []
    current = data_hora.date()
    hora = data_hora.time()
    tz = data_hora.tzinfo

    # limita a 365 dias para evitar séries absurdas
    limite = min(ate, current + timedelta(days=365))

    while current <= limite:
        if current.weekday() in dias_semana:
            resultado.append(datetime.combine(current, hora, tzinfo=tz))
        current += timedelta(days=1)

    return resultado


def _criar_comunicado_auto(db: Session, turma_id: int, titulo: str, mensagem: str, autor_id: int) -> None:
    db.add(Comunicado(
        autor_id=autor_id,
        titulo=titulo,
        mensagem=mensagem,
        turma_id=turma_id,
    ))


# ── Turmas do professor ───────────────────────────────────────────────────────

@router.get("/turmas", response_model=List[TurmaDoProfssor])
def listar_minhas_turmas(
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Turma, func.count(AlunoTurma.aluno_id).label("qtd_alunos"))
        .outerjoin(AlunoTurma, AlunoTurma.turma_id == Turma.id)
        .filter(Turma.professor_id == user.id, Turma.ativo == True)
        .group_by(Turma.id)
        .all()
    )
    return [
        TurmaDoProfssor(id=t.id, nome=t.nome, nivel=t.nivel, cor=t.cor, qtd_alunos=qtd)
        for t, qtd in rows
    ]


# ── Calendário ───────────────────────────────────────────────────────────────

@router.get("/calendario", response_model=List[AulaCalendarioItem])
def get_calendario_professor(
    mes: str = Query(..., description="YYYY-MM"),
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    try:
        year, month = int(mes[:4]), int(mes[5:7])
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Formato inválido. Use YYYY-MM")

    inicio = datetime(year, month, 1, tzinfo=timezone.utc)
    last_day = cal_module.monthrange(year, month)[1]
    fim = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    # admin vê tudo; professor vê só suas turmas
    query = db.query(Aula).filter(Aula.data_hora >= inicio, Aula.data_hora <= fim)
    if user.role != RoleEnum.admin:
        minhas_turmas = [
            row.turma_id for row in db.query(Turma.id.label("turma_id"))
            .filter(Turma.professor_id == user.id, Turma.ativo == True)
            .all()
        ]
        if not minhas_turmas:
            return []
        query = query.filter(Aula.turma_id.in_(minhas_turmas))

    aulas = query.order_by(Aula.data_hora).all()

    turma_ids = {a.turma_id for a in aulas if a.turma_id}
    prof_ids = {a.professor_id for a in aulas if a.professor_id}
    turmas = {t.id: t for t in db.query(Turma).filter(Turma.id.in_(turma_ids)).all()} if turma_ids else {}
    professores = {u.id: u.nome for u in db.query(Usuario).filter(Usuario.id.in_(prof_ids)).all()} if prof_ids else {}

    return [_build_aula_item(a, turmas, professores) for a in aulas]


# ── Criar aula(s) ────────────────────────────────────────────────────────────

@router.post("/aulas", response_model=CriarAulaResponse, status_code=status.HTTP_201_CREATED)
def criar_aula(
    body: CriarAulaRequest,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    turma = db.query(Turma).filter(Turma.id == body.turma_id, Turma.ativo == True).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada ou inativa")

    # professor só pode criar aulas nas suas turmas; admin pode em qualquer uma
    if user.role != RoleEnum.admin and turma.professor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Turma não pertence a você")

    novas_aulas: List[Aula] = []
    serie_id: str | None = None

    if body.recorrencia:
        datas = _gerar_datas_serie(
            body.data_hora,
            body.recorrencia.dias_semana,
            body.recorrencia.ate,
        )
        if not datas:
            raise HTTPException(status_code=400, detail="Nenhuma data gerada com os parâmetros de recorrência informados")

        serie_id = str(uuid.uuid4())
        for dt in datas:
            novas_aulas.append(Aula(
                turma_id=body.turma_id,
                professor_id=user.id,
                titulo=body.titulo,
                descricao=body.descricao,
                data_hora=dt,
                duracao_min=body.duracao_min,
                link_aula=body.link_aula,
                serie_id=serie_id,
            ))
    else:
        novas_aulas.append(Aula(
            turma_id=body.turma_id,
            professor_id=user.id,
            titulo=body.titulo,
            descricao=body.descricao,
            data_hora=body.data_hora,
            duracao_min=body.duracao_min,
            link_aula=body.link_aula,
        ))

    for a in novas_aulas:
        db.add(a)
    db.commit()
    for a in novas_aulas:
        db.refresh(a)

    turmas_cache = {turma.id: turma}
    professores_cache = {user.id: user.nome}

    return CriarAulaResponse(
        criadas=len(novas_aulas),
        serie_id=serie_id,
        aulas=[_build_aula_item(a, turmas_cache, professores_cache) for a in novas_aulas],
    )


# ── Editar aula ──────────────────────────────────────────────────────────────

@router.patch("/aulas/{aula_id}", response_model=AulaCalendarioItem)
def editar_aula(
    aula_id: int,
    body: AtualizarAulaRequest,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    aula = db.query(Aula).filter(Aula.id == aula_id).first()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula não encontrada")

    if user.role != RoleEnum.admin and aula.professor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para editar esta aula")

    data_hora_anterior = aula.data_hora
    horario_mudou = body.data_hora is not None and body.data_hora != data_hora_anterior

    if body.titulo is not None:
        aula.titulo = body.titulo
    if body.descricao is not None:
        aula.descricao = body.descricao
    if body.data_hora is not None:
        aula.data_hora = body.data_hora
    if body.duracao_min is not None:
        aula.duracao_min = body.duracao_min
    if body.link_aula is not None:
        aula.link_aula = body.link_aula

    if horario_mudou and aula.turma_id:
        nova_data_fmt = body.data_hora.strftime("%d/%m/%Y às %H:%M")
        _criar_comunicado_auto(
            db,
            turma_id=aula.turma_id,
            titulo=f"Aula reagendada: {aula.titulo}",
            mensagem=f"A aula '{aula.titulo}' foi reagendada. Novo horário: {nova_data_fmt}.",
            autor_id=user.id,
        )

    db.commit()
    db.refresh(aula)

    turmas = {aula.turma_id: db.query(Turma).filter(Turma.id == aula.turma_id).first()} if aula.turma_id else {}
    professores = {aula.professor_id: db.query(Usuario.nome).filter(Usuario.id == aula.professor_id).scalar()} if aula.professor_id else {}
    return _build_aula_item(aula, turmas, professores)


# ── Cancelar aula ────────────────────────────────────────────────────────────

@router.delete("/aulas/{aula_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_aula(
    aula_id: int,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    aula = db.query(Aula).filter(Aula.id == aula_id).first()
    if not aula:
        raise HTTPException(status_code=404, detail="Aula não encontrada")

    if user.role != RoleEnum.admin and aula.professor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para cancelar esta aula")

    if aula.turma_id:
        data_fmt = aula.data_hora.strftime("%d/%m/%Y às %H:%M")
        _criar_comunicado_auto(
            db,
            turma_id=aula.turma_id,
            titulo=f"Aula cancelada: {aula.titulo}",
            mensagem=f"A aula '{aula.titulo}' prevista para {data_fmt} foi cancelada.",
            autor_id=user.id,
        )

    db.delete(aula)
    db.commit()


# ── Cancelar série inteira ───────────────────────────────────────────────────

@router.delete("/aulas/serie/{serie_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancelar_serie(
    serie_id: str,
    user: Usuario = Depends(require_professor_or_admin),
    db: Session = Depends(get_db),
):
    aulas = db.query(Aula).filter(Aula.serie_id == serie_id).all()
    if not aulas:
        raise HTTPException(status_code=404, detail="Série não encontrada")

    if user.role != RoleEnum.admin and any(a.professor_id != user.id for a in aulas):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para cancelar esta série")

    # um comunicado por turma afetada
    turmas_notificadas: set[int] = set()
    for aula in aulas:
        if aula.turma_id and aula.turma_id not in turmas_notificadas:
            _criar_comunicado_auto(
                db,
                turma_id=aula.turma_id,
                titulo=f"Série de aulas cancelada: {aula.titulo}",
                mensagem=f"Todas as aulas da série '{aula.titulo}' foram canceladas.",
                autor_id=user.id,
            )
            turmas_notificadas.add(aula.turma_id)

    db.query(Aula).filter(Aula.serie_id == serie_id).delete()
    db.commit()
