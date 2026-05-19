from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.utils.rate_limit import limiter

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.queen_message import QueenMessage
from app.models.queen_training_note import QueenTrainingNote
from app.schemas.queen import (
    QueenMessageItem,
    SendMessageRequest,
    SendMessageResponse,
    TrainingNoteItem,
    CreateTrainingNoteRequest,
)
from app.utils.security import get_current_user, require_admin
from app.utils.ai_service import ask_queen, is_error_reply

router = APIRouter(prefix="/queen", tags=["queen"])

# Quantidade de mensagens mais recentes enviadas como contexto pra IA.
# Mantém custos previsíveis e evita estourar context window.
CONTEXT_WINDOW = 20


# ── Mensagens (chat individual por usuário) ─────────────────────────────────


@router.get("/messages", response_model=List[QueenMessageItem])
def listar_mensagens(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retorna todas as mensagens do usuário logado, em ordem cronológica."""
    msgs = (
        db.query(QueenMessage)
        .filter(QueenMessage.usuario_id == user.id)
        .order_by(QueenMessage.criado_em.asc())
        .all()
    )
    return msgs


@router.post("/messages", response_model=SendMessageResponse)
@limiter.limit("20/minute;200/day")  # controla custo da IA + abuso
def enviar_mensagem(
    request: Request,
    body: SendMessageRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Envia uma mensagem do usuário, chama a IA e retorna ambas as mensagens persistidas.
    Inclui suggestion (regra sugerida pela IA) se houver — só relevante pra admin no frontend.
    """
    # 1) Salva mensagem do user
    user_msg = QueenMessage(usuario_id=user.id, role="user", content=body.content)
    db.add(user_msg)
    db.flush()  # garantir id e criado_em sem fechar a transação

    # 2) Carrega contexto (últimas N msgs DESTE user, em ordem cronológica)
    historico_db = (
        db.query(QueenMessage)
        .filter(QueenMessage.usuario_id == user.id, QueenMessage.id != user_msg.id)
        .order_by(QueenMessage.criado_em.desc())
        .limit(CONTEXT_WINDOW)
        .all()
    )
    historico_db.reverse()
    historico = [{"role": m.role, "content": m.content} for m in historico_db]

    # 3) Carrega training notes globais (regras aprovadas por admins)
    notes_rows = db.query(QueenTrainingNote.rule).order_by(QueenTrainingNote.criado_em.asc()).all()
    training_notes = [r.rule for r in notes_rows]

    # 4) Chama a IA
    response_text, suggestion = ask_queen(body.content, historico, training_notes)

    # 5) Salva resposta — exceto se for mensagem de erro de fallback
    # (essas não devem poluir o histórico em chamadas futuras)
    if is_error_reply(response_text):
        # Mantém a msg do user no banco, mas retorna a resposta de erro sem persistir
        db.commit()
        db.refresh(user_msg)
        from datetime import datetime, timezone
        ephemeral_assistant = QueenMessage(
            id=0,  # id fake (não foi persistido)
            usuario_id=user.id,
            role="assistant",
            content=response_text,
            criado_em=datetime.now(timezone.utc),
        )
        return SendMessageResponse(
            user_message=user_msg,
            assistant_message=ephemeral_assistant,
            suggestion=None,
        )

    assistant_msg = QueenMessage(usuario_id=user.id, role="assistant", content=response_text)
    db.add(assistant_msg)
    db.commit()
    db.refresh(user_msg)
    db.refresh(assistant_msg)

    return SendMessageResponse(
        user_message=user_msg,
        assistant_message=assistant_msg,
        # Sugestões só aparecem pro admin no frontend, mas backend sempre retorna se houver
        suggestion=suggestion if user.role == RoleEnum.admin else None,
    )


@router.delete("/messages", status_code=status.HTTP_204_NO_CONTENT)
def limpar_mensagens(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Apaga todo o histórico de chat do usuário logado."""
    db.query(QueenMessage).filter(QueenMessage.usuario_id == user.id).delete()
    db.commit()


# ── Training notes (regras globais — admin only para escrita) ───────────────


@router.get("/training-notes", response_model=List[TrainingNoteItem])
def listar_notas(
    _: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Qualquer usuário autenticado pode ver as notas (transparência)."""
    return db.query(QueenTrainingNote).order_by(QueenTrainingNote.criado_em.asc()).all()


@router.post("/training-notes", response_model=TrainingNoteItem, status_code=status.HTTP_201_CREATED)
def criar_nota(
    body: CreateTrainingNoteRequest,
    admin: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    nota = QueenTrainingNote(rule=body.rule, criado_por_id=admin.id)
    db.add(nota)
    db.commit()
    db.refresh(nota)
    return nota


@router.delete("/training-notes/{nota_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_nota(
    nota_id: int,
    _: Usuario = Depends(require_admin),
    db: Session = Depends(get_db),
):
    nota = db.query(QueenTrainingNote).filter(QueenTrainingNote.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    db.delete(nota)
    db.commit()
