from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario
from app.models.perfil_aluno import PerfilAluno
from app.schemas.alunos import (
    PerfilAlunoResponse,
    AtualizarPerfilRequest,
    AlterarSenhaRequest,
    AlterarFotoRequest,
)
from app.utils.security import get_current_user, verify_password, get_password_hash

router = APIRouter(prefix="/alunos", tags=["alunos"])


def _build_response(user: Usuario, perfil: PerfilAluno | None) -> PerfilAlunoResponse:
    return PerfilAlunoResponse(
        id=user.id,
        nome=user.nome,
        username=user.username,
        email=user.email,
        foto_url=perfil.foto_url if perfil else None,
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
    db.commit()


@router.patch("/foto", response_model=PerfilAlunoResponse)
def alterar_foto(
    body: AlterarFotoRequest,
    user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == user.id).first()
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    perfil.foto_url = body.foto_base64
    db.commit()

    return _build_response(user, perfil)
