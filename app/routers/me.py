import logging
from sqlalchemy import or_, func
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.perfil_aluno import PerfilAluno
from app.models.refresh_token import RefreshToken
from app.models.aluno_turma import AlunoTurma
from app.models.comunicado import Comunicado
from app.models.comunicado_lido import ComunicadoLido
from app.schemas.me import MePerfilUpdate
from app.schemas.alunos import AlterarSenhaRequest, AlterarFotoRequest
from app.schemas.auth import UsuarioResponse
from app.utils.security import (
    get_current_user,
    verify_password,
    get_password_hash,
)
from app.utils.cloudinary_upload import upload_foto_perfil

router = APIRouter(prefix="/me", tags=["me"])


def _build_response(user: Usuario, db: Session) -> UsuarioResponse:
    """Mesmo shape de /auth/me — mantém um único contrato para o usuário logado."""
    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()

    comunicados_nao_lidos = 0
    if user.role == RoleEnum.aluno:
        turma_id = (
            db.query(AlunoTurma.turma_id)
            .filter(AlunoTurma.aluno_id == user.id)
            .scalar()
        )
        comunicados_nao_lidos = (
            db.query(func.count(Comunicado.id))
            .outerjoin(
                ComunicadoLido,
                (ComunicadoLido.comunicado_id == Comunicado.id)
                & (ComunicadoLido.aluno_id == user.id),
            )
            .filter(
                or_(Comunicado.turma_id == None, Comunicado.turma_id == turma_id),
                ComunicadoLido.comunicado_id == None,
            )
            .scalar()
            or 0
        )

    return UsuarioResponse(
        id=user.id,
        nome=user.nome,
        username=user.username,
        email=user.email,
        role=user.role,
        nivel=perfil.nivel if perfil else None,
        foto_url=user.foto_url,
        idioma_portal=perfil.idioma_portal if perfil else "pt",
        acesso_liberado=perfil.acesso_liberado if perfil else True,
        comunicados_nao_lidos=comunicados_nao_lidos,
    )


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


@router.patch("/perfil", response_model=UsuarioResponse)
def atualizar_perfil(
    body: MePerfilUpdate,
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

    db.commit()
    db.refresh(user)

    return _build_response(user, db)


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


@router.patch("/foto", response_model=UsuarioResponse)
def alterar_foto(
    body: AlterarFotoRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        url = upload_foto_perfil(body.foto_base64, user.id)
    except Exception as exc:
        logging.getLogger(__name__).error("Cloudinary upload falhou: %s", exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Falha ao fazer upload da imagem")

    user.foto_url = url
    db.commit()
    db.refresh(user)

    return _build_response(user, db)
