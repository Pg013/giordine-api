from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.models.perfil_aluno import PerfilAluno
from app.models.historico_nivel import HistoricoNivel
from app.models.aluno_turma import AlunoTurma
from app.models.comunicado import Comunicado
from app.models.comunicado_lido import ComunicadoLido
from app.models.turma import Turma
from app.models.refresh_token import RefreshToken
from app.schemas.alunos import (
    PerfilAlunoResponse,
    AtualizarPerfilRequest,
    AlterarSenhaRequest,
    AlterarFotoRequest,
    HistoricoNivelItem,
    ProgressoResponse,
    ComunicadoAlunoItem,
    ComunicadosAlunoResponse,
)
from app.utils.security import get_current_user, verify_password, get_password_hash
from app.utils.cloudinary_upload import upload_foto_perfil

router = APIRouter(prefix="/alunos", tags=["alunos"])


def _build_response(user: Usuario, perfil: PerfilAluno | None) -> PerfilAlunoResponse:
    return PerfilAlunoResponse(
        id=user.id,
        nome=user.nome,
        username=user.username,
        email=user.email,
        foto_url=user.foto_url,
        aceita_email=perfil.aceita_email if perfil else True,
        nivel=perfil.nivel if perfil else None,
        idioma_portal=perfil.idioma_portal if perfil else "pt",
        acesso_liberado=perfil.acesso_liberado if perfil else True,
    )


@router.get("/me", response_model=PerfilAlunoResponse)
def get_meu_perfil(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()
    return _build_response(user, perfil)


@router.get("/check-username")
def check_username(
    username: str = Query(..., min_length=1),
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existe = (
        db.query(Usuario)
        .filter(Usuario.username == username, Usuario.id != user.id)
        .first()
    )
    return {"disponivel": existe is None}


@router.patch("/perfil", response_model=PerfilAlunoResponse)
def atualizar_perfil(
    body: AtualizarPerfilRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.username is not None and body.username != user.username:
        if db.query(Usuario).filter(Usuario.username == body.username, Usuario.id != user.id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username já está em uso")

    if body.email is not None and body.email != user.email:
        if db.query(Usuario).filter(Usuario.email == body.email, Usuario.id != user.id).first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já está em uso")

    if body.nome is not None:
        user.nome = body.nome
    if body.username is not None:
        user.username = body.username
    if body.email is not None:
        user.email = body.email

    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()
    if perfil is not None and body.aceita_email is not None:
        perfil.aceita_email = body.aceita_email

    db.commit()
    db.refresh(user)

    return _build_response(user, perfil)


@router.patch("/senha", status_code=status.HTTP_204_NO_CONTENT)
def alterar_senha(
    body: AlterarSenhaRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.senha_atual, user.senha_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha atual incorreta")

    if body.nova_senha == body.senha_atual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nova senha deve ser diferente da atual",
        )

    user.senha_hash = get_password_hash(body.nova_senha)
    db.query(RefreshToken).filter(RefreshToken.usuario_id == user.id).delete()
    db.commit()


@router.get("/progresso", response_model=ProgressoResponse)
def get_progresso(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()

    historico = (
        db.query(HistoricoNivel)
        .filter(HistoricoNivel.aluno_id == user.id)
        .order_by(HistoricoNivel.entrada_em.asc())
        .all()
    )

    now = datetime.now(timezone.utc)
    entrada = user.criado_em
    if entrada.tzinfo is None:
        entrada = entrada.replace(tzinfo=timezone.utc)

    meses = (now.year - entrada.year) * 12 + (now.month - entrada.month)

    return ProgressoResponse(
        entrada_no_curso=entrada,
        meses_no_curso=meses,
        nivel_atual=perfil.nivel if perfil else None,
        historico_niveis=[
            HistoricoNivelItem(nivel=h.nivel, entrada_em=h.entrada_em)
            for h in historico
        ],
        total_aulas_presentes=0,
        total_faltas=0,
        percentual_presenca=0.0,
    )


@router.get("/comunicados", response_model=ComunicadosAlunoResponse)
def get_comunicados(
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    turma_id = (
        db.query(AlunoTurma.turma_id)
        .filter(AlunoTurma.aluno_id == user.id)
        .scalar()
    )

    comunicados = (
        db.query(Comunicado)
        .filter(or_(Comunicado.turma_id == None, Comunicado.turma_id == turma_id))
        .order_by(Comunicado.criado_em.desc())
        .all()
    )

    lidos_ids = {
        row.comunicado_id
        for row in db.query(ComunicadoLido.comunicado_id)
        .filter(ComunicadoLido.aluno_id == user.id)
        .all()
    }

    turmas_cache: dict[int, str] = {}

    items = []
    for c in comunicados:
        turma_nome = None
        if c.turma_id is not None:
            if c.turma_id not in turmas_cache:
                turma = db.query(Turma.nome).filter(Turma.id == c.turma_id).first()
                turmas_cache[c.turma_id] = turma.nome if turma else f"Turma {c.turma_id}"
            turma_nome = turmas_cache[c.turma_id]

        items.append(
            ComunicadoAlunoItem(
                id=c.id,
                titulo=c.titulo,
                mensagem=c.mensagem,
                turma_id=c.turma_id,
                turma_nome=turma_nome,
                criado_em=c.criado_em,
                lido=c.id in lidos_ids,
            )
        )

    total_nao_lidos = sum(1 for item in items if not item.lido)
    return ComunicadosAlunoResponse(total_nao_lidos=total_nao_lidos, comunicados=items)


@router.post("/comunicados/{comunicado_id}/lido", status_code=status.HTTP_204_NO_CONTENT)
def marcar_comunicado_lido(
    comunicado_id: int,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comunicado = db.query(Comunicado).filter(Comunicado.id == comunicado_id).first()
    if not comunicado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comunicado não encontrado")

    if comunicado.turma_id is not None:
        pertence = db.query(AlunoTurma).filter(
            AlunoTurma.aluno_id == user.id,
            AlunoTurma.turma_id == comunicado.turma_id,
        ).first()
        if not pertence:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado")

    already = db.query(ComunicadoLido).filter(
        ComunicadoLido.aluno_id == user.id,
        ComunicadoLido.comunicado_id == comunicado_id,
    ).first()

    if not already:
        db.add(ComunicadoLido(aluno_id=user.id, comunicado_id=comunicado_id))
        db.commit()


@router.patch("/foto", response_model=PerfilAlunoResponse)
def alterar_foto(
    body: AlterarFotoRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        url = upload_foto_perfil(body.foto_base64, user.id)
    except Exception as exc:
        import logging
        logging.getLogger(__name__).error("Cloudinary upload falhou: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao fazer upload da imagem")

    user.foto_url = url
    db.commit()

    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()
    return _build_response(user, perfil)
