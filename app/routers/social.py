from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.perfil_aluno import PerfilAluno
from app.models.turma import Turma
from app.models.aluno_turma import AlunoTurma
from app.models.mensagem import Mensagem
from app.schemas.social import (
    EnviarDMRequest,
    EnviarGrupoRequest,
    MensagemItem,
    ConversaItem,
    ConversasResponse,
    ChatGrupoResponse,
)
from app.utils.security import get_current_user

router = APIRouter(prefix="/social", tags=["social"])


# ── helpers ──────────────────────────────────────────────────────────────────

def _pode_dm(user: Usuario, outro_id: int, db: Session) -> bool:
    """Verifica se user pode trocar DMs com outro_id."""
    if user.role == RoleEnum.admin:
        return True

    outro = db.query(Usuario).filter(Usuario.id == outro_id).first()
    if not outro:
        return False

    # professor ↔ aluno: deve compartilhar turma
    if user.role == RoleEnum.professor:
        minha_turma_ids = [
            r.id for r in db.query(Turma.id).filter(Turma.professor_id == user.id).all()
        ]
        return db.query(AlunoTurma).filter(
            AlunoTurma.aluno_id == outro_id,
            AlunoTurma.turma_id.in_(minha_turma_ids),
        ).first() is not None

    # aluno ↔ professor da sua turma ou admin
    if user.role == RoleEnum.aluno:
        minha_turma = db.query(AlunoTurma.turma_id).filter(AlunoTurma.aluno_id == user.id).scalar()
        if not minha_turma:
            return False
        turma = db.query(Turma).filter(Turma.id == minha_turma).first()
        return outro.id == turma.professor_id or outro.role == RoleEnum.admin

    return False


def _pode_acessar_turma_chat(user: Usuario, turma_id: int, db: Session) -> bool:
    """Verifica se user pode acessar o chat de grupo da turma."""
    if user.role == RoleEnum.admin:
        return True
    if user.role == RoleEnum.professor:
        return db.query(Turma).filter(Turma.id == turma_id, Turma.professor_id == user.id).first() is not None
    if user.role == RoleEnum.aluno:
        return db.query(AlunoTurma).filter(
            AlunoTurma.aluno_id == user.id, AlunoTurma.turma_id == turma_id
        ).first() is not None
    return False


def _build_mensagem(m: Mensagem, nomes: dict) -> MensagemItem:
    return MensagemItem(
        id=m.id,
        remetente_id=m.remetente_id,
        remetente_nome=nomes.get(m.remetente_id, "Desconhecido"),
        destinatario_id=m.destinatario_id,
        turma_id=m.turma_id,
        conteudo=m.conteudo,
        lida=m.lida,
        criado_em=m.criado_em,
    )


# ── DM — conversas ───────────────────────────────────────────────────────────

@router.get("/conversas", response_model=ConversasResponse)
def listar_conversas(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista todas as conversas DM do usuário, com contagem de não lidas."""
    # mensagens onde user é remetente ou destinatário (DMs individuais)
    mensagens = (
        db.query(Mensagem)
        .filter(
            Mensagem.turma_id == None,
            or_(
                Mensagem.remetente_id == user.id,
                Mensagem.destinatario_id == user.id,
            ),
        )
        .order_by(Mensagem.criado_em.desc())
        .all()
    )

    # agrupa por interlocutor
    conversas: dict[int, dict] = {}
    for m in mensagens:
        outro_id = m.destinatario_id if m.remetente_id == user.id else m.remetente_id
        if outro_id not in conversas:
            conversas[outro_id] = {
                "ultima_mensagem": m.conteudo,
                "ultima_mensagem_em": m.criado_em,
                "nao_lidas": 0,
            }
        if m.destinatario_id == user.id and not m.lida:
            conversas[outro_id]["nao_lidas"] += 1

    if not conversas:
        return ConversasResponse(conversas=[])

    usuarios = {
        u.id: u
        for u in db.query(Usuario).filter(Usuario.id.in_(conversas.keys())).all()
    }
    perfis = {
        p.usuario_id: p
        for p in db.query(PerfilAluno).filter(PerfilAluno.usuario_id.in_(conversas.keys())).all()
    }

    items = []
    for outro_id, dados in conversas.items():
        u = usuarios.get(outro_id)
        if not u:
            continue
        perfil = perfis.get(outro_id)
        items.append(ConversaItem(
            usuario_id=outro_id,
            nome=u.nome,
            foto_url=perfil.foto_url if perfil else None,
            nao_lidas=dados["nao_lidas"],
            ultima_mensagem=dados["ultima_mensagem"],
            ultima_mensagem_em=dados["ultima_mensagem_em"],
        ))

    return ConversasResponse(conversas=items)


@router.get("/mensagens", response_model=List[MensagemItem])
def get_dm(
    usuario_id: int = Query(..., description="ID do interlocutor"),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna o histórico de DMs entre o usuário logado e usuario_id."""
    if not _pode_dm(user, usuario_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para acessar esta conversa")

    mensagens = (
        db.query(Mensagem)
        .filter(
            Mensagem.turma_id == None,
            or_(
                and_(Mensagem.remetente_id == user.id, Mensagem.destinatario_id == usuario_id),
                and_(Mensagem.remetente_id == usuario_id, Mensagem.destinatario_id == user.id),
            ),
        )
        .order_by(Mensagem.criado_em.asc())
        .all()
    )

    # marca como lidas as mensagens recebidas
    ids_para_marcar = [m.id for m in mensagens if m.destinatario_id == user.id and not m.lida]
    if ids_para_marcar:
        db.query(Mensagem).filter(Mensagem.id.in_(ids_para_marcar)).update({"lida": True})
        db.commit()

    remetente_ids = {m.remetente_id for m in mensagens}
    nomes = {u.id: u.nome for u in db.query(Usuario).filter(Usuario.id.in_(remetente_ids)).all()}

    return [_build_mensagem(m, nomes) for m in mensagens]


@router.post("/mensagens", response_model=MensagemItem, status_code=status.HTTP_201_CREATED)
def enviar_dm(
    body: EnviarDMRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.destinatario_id == user.id:
        raise HTTPException(status_code=400, detail="Não é possível enviar mensagem para si mesmo")

    if not _pode_dm(user, body.destinatario_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para enviar mensagem a este usuário")

    m = Mensagem(
        remetente_id=user.id,
        destinatario_id=body.destinatario_id,
        turma_id=None,
        conteudo=body.conteudo,
        lida=False,
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    return _build_mensagem(m, {user.id: user.nome})


# ── Chat de grupo (turma) ────────────────────────────────────────────────────

@router.get("/turmas/{turma_id}/chat", response_model=ChatGrupoResponse)
def get_chat_grupo(
    turma_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _pode_acessar_turma_chat(user, turma_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para acessar este chat")

    turma = db.query(Turma).filter(Turma.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")

    mensagens = (
        db.query(Mensagem)
        .filter(Mensagem.turma_id == turma_id, Mensagem.destinatario_id == None)
        .order_by(Mensagem.criado_em.asc())
        .all()
    )

    remetente_ids = {m.remetente_id for m in mensagens}
    nomes = {u.id: u.nome for u in db.query(Usuario).filter(Usuario.id.in_(remetente_ids)).all()} if remetente_ids else {}

    return ChatGrupoResponse(
        turma_id=turma.id,
        turma_nome=turma.nome,
        turma_cor=turma.cor,
        mensagens=[_build_mensagem(m, nomes) for m in mensagens],
    )


@router.post("/turmas/{turma_id}/chat", response_model=MensagemItem, status_code=status.HTTP_201_CREATED)
def enviar_grupo(
    turma_id: int,
    body: EnviarGrupoRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not _pode_acessar_turma_chat(user, turma_id, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem permissão para enviar neste chat")

    turma = db.query(Turma).filter(Turma.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=404, detail="Turma não encontrada")

    m = Mensagem(
        remetente_id=user.id,
        destinatario_id=None,
        turma_id=turma_id,
        conteudo=body.conteudo,
        lida=True,  # mensagens de grupo não têm controle de lida individual
    )
    db.add(m)
    db.commit()
    db.refresh(m)

    return _build_mensagem(m, {user.id: user.nome})


@router.post("/mensagens/{mensagem_id}/lida", status_code=status.HTTP_204_NO_CONTENT)
def marcar_lida(
    mensagem_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca um DM individual como lido. Só o destinatário pode marcar."""
    m = db.query(Mensagem).filter(
        Mensagem.id == mensagem_id,
        Mensagem.destinatario_id == user.id,
    ).first()
    if not m:
        raise HTTPException(status_code=404, detail="Mensagem não encontrada")
    m.lida = True
    db.commit()
