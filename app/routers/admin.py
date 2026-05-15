import secrets
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, aliased

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.perfil_aluno import PerfilAluno
from app.models.turma import Turma
from app.models.aluno_turma import AlunoTurma
from app.models.comunicado import Comunicado
from app.schemas.admin import (
    CriarAlunoRequest,
    CriarAlunoResponse,
    AlunoListItem,
    TurmaInfo,
    AcessoBody,
    NivelBody,
    TurmaAlunoBody,
    CriarTurmaRequest,
    TurmaListItem,
    TurmaDetalhe,
    AlunoTurmaItem,
    ProfessorBody,
    ProfessorListItem,
    CriarComunicadoRequest,
    ComunicadoListItem,
    UltimoAlunoItem,
    ComunicadoRecenteItem,
    AcessoBloqueadoItem,
    DashboardData,
)
from app.utils.security import get_password_hash, require_admin

router = APIRouter(prefix="/admin", tags=["admin"])

_NIVEIS_PT = {"básico", "básico_2", "básico_3"}


def _idioma_para_nivel(nivel: str) -> str:
    return "pt" if nivel in _NIVEIS_PT else "en"


# ── Alunos ──────────────────────────────────────────────────────────────────


@router.post("/alunos", response_model=CriarAlunoResponse, status_code=status.HTTP_201_CREATED)
def criar_aluno(
    body: CriarAlunoRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    if db.query(Usuario).filter(Usuario.email == body.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")
    if db.query(Usuario).filter(Usuario.username == body.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username já cadastrado")

    senha_temporaria = secrets.token_urlsafe(10)

    novo_usuario = Usuario(
        nome=body.nome,
        email=body.email,
        username=body.username,
        senha_hash=get_password_hash(senha_temporaria),
        role=RoleEnum.aluno,
        ativo=True,
    )
    db.add(novo_usuario)
    db.flush()

    idioma = _idioma_para_nivel(body.nivel) if body.nivel else "pt"
    perfil = PerfilAluno(
        usuario_id=novo_usuario.id,
        nivel=body.nivel,
        idioma_portal=idioma,
        acesso_liberado=True,
    )
    db.add(perfil)
    db.commit()
    db.refresh(novo_usuario)

    return CriarAlunoResponse(
        id=novo_usuario.id,
        nome=novo_usuario.nome,
        username=novo_usuario.username,
        email=novo_usuario.email,
        nivel=body.nivel,
        senha_temporaria=senha_temporaria,
    )


@router.get("/alunos", response_model=List[AlunoListItem])
def listar_alunos(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    rows = (
        db.query(Usuario, PerfilAluno, Turma)
        .filter(Usuario.role == RoleEnum.aluno)
        .outerjoin(PerfilAluno, PerfilAluno.usuario_id == Usuario.id)
        .outerjoin(AlunoTurma, AlunoTurma.aluno_id == Usuario.id)
        .outerjoin(Turma, Turma.id == AlunoTurma.turma_id)
        .all()
    )

    result = []
    for usuario, perfil, turma in rows:
        turma_info = TurmaInfo(id=turma.id, nome=turma.nome, nivel=turma.nivel) if turma else None
        result.append(
            AlunoListItem(
                id=usuario.id,
                nome=usuario.nome,
                username=usuario.username,
                email=usuario.email,
                nivel=perfil.nivel if perfil else None,
                acesso_liberado=perfil.acesso_liberado if perfil else True,
                turma_atual=turma_info,
            )
        )
    return result


@router.patch("/alunos/{aluno_id}/acesso")
def alterar_acesso(
    aluno_id: int,
    body: AcessoBody,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    aluno = db.query(Usuario).filter(Usuario.id == aluno_id, Usuario.role == RoleEnum.aluno).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == aluno_id).first()
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    perfil.acesso_liberado = body.acesso_liberado
    db.commit()
    return {"acesso_liberado": perfil.acesso_liberado}


@router.patch("/alunos/{aluno_id}/nivel")
def alterar_nivel(
    aluno_id: int,
    body: NivelBody,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    aluno = db.query(Usuario).filter(Usuario.id == aluno_id, Usuario.role == RoleEnum.aluno).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == aluno_id).first()
    if not perfil:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado")

    perfil.nivel = body.nivel
    perfil.idioma_portal = _idioma_para_nivel(body.nivel)
    db.commit()
    return {"nivel": perfil.nivel, "idioma_portal": perfil.idioma_portal}


@router.patch("/alunos/{aluno_id}/turma")
def alterar_turma(
    aluno_id: int,
    body: TurmaAlunoBody,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    aluno = db.query(Usuario).filter(Usuario.id == aluno_id, Usuario.role == RoleEnum.aluno).first()
    if not aluno:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não encontrado")

    turma = db.query(Turma).filter(Turma.id == body.turma_id, Turma.ativo == True).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada ou inativa")

    db.query(AlunoTurma).filter(AlunoTurma.aluno_id == aluno_id).delete()
    db.add(AlunoTurma(aluno_id=aluno_id, turma_id=body.turma_id))
    db.commit()
    return {"aluno_id": aluno_id, "turma_id": body.turma_id}


# ── Turmas ──────────────────────────────────────────────────────────────────


@router.post("/turmas", response_model=TurmaListItem, status_code=status.HTTP_201_CREATED)
def criar_turma(
    body: CriarTurmaRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    if body.professor_id is not None:
        prof = db.query(Usuario).filter(
            Usuario.id == body.professor_id,
            Usuario.role.in_([RoleEnum.professor, RoleEnum.admin]),
        ).first()
        if not prof:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")

    nova_turma = Turma(nome=body.nome, nivel=body.nivel, professor_id=body.professor_id)
    db.add(nova_turma)
    db.commit()
    db.refresh(nova_turma)

    return TurmaListItem(
        id=nova_turma.id,
        nome=nova_turma.nome,
        nivel=nova_turma.nivel,
        professor_id=nova_turma.professor_id,
        professor_nome=prof.nome if body.professor_id is not None else None,
        ativo=nova_turma.ativo,
        qtd_alunos=0,
    )


@router.get("/turmas", response_model=List[TurmaListItem])
def listar_turmas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    Professor = aliased(Usuario)
    rows = (
        db.query(
            Turma,
            func.count(AlunoTurma.aluno_id).label("qtd_alunos"),
            Professor.nome.label("professor_nome"),
        )
        .outerjoin(AlunoTurma, AlunoTurma.turma_id == Turma.id)
        .outerjoin(Professor, Professor.id == Turma.professor_id)
        .filter(Turma.ativo == True)
        .group_by(Turma.id, Professor.nome)
        .all()
    )

    return [
        TurmaListItem(
            id=turma.id,
            nome=turma.nome,
            nivel=turma.nivel,
            professor_id=turma.professor_id,
            professor_nome=professor_nome,
            ativo=turma.ativo,
            qtd_alunos=qtd,
        )
        for turma, qtd, professor_nome in rows
    ]


@router.get("/turmas/{turma_id}", response_model=TurmaDetalhe)
def get_turma(
    turma_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    turma = db.query(Turma).filter(Turma.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")

    professor = None
    if turma.professor_id:
        professor = db.query(Usuario).filter(Usuario.id == turma.professor_id).first()

    alunos_rows = (
        db.query(Usuario, PerfilAluno)
        .join(AlunoTurma, AlunoTurma.aluno_id == Usuario.id)
        .outerjoin(PerfilAluno, PerfilAluno.usuario_id == Usuario.id)
        .filter(AlunoTurma.turma_id == turma_id)
        .all()
    )
    alunos = [
        AlunoTurmaItem(
            id=u.id,
            nome=u.nome,
            username=u.username,
            nivel=p.nivel if p else None,
            acesso_liberado=p.acesso_liberado if p else True,
        )
        for u, p in alunos_rows
    ]

    return TurmaDetalhe(
        id=turma.id,
        nome=turma.nome,
        nivel=turma.nivel,
        ativo=turma.ativo,
        professor_id=turma.professor_id,
        professor_nome=professor.nome if professor else None,
        alunos=alunos,
        qtd_alunos=len(alunos),
    )


@router.delete("/turmas/{turma_id}/alunos/{aluno_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_aluno_turma(
    turma_id: int,
    aluno_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    entry = db.query(AlunoTurma).filter(
        AlunoTurma.turma_id == turma_id,
        AlunoTurma.aluno_id == aluno_id,
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aluno não está nesta turma")
    db.delete(entry)
    db.commit()


@router.patch("/turmas/{turma_id}/professor")
def atribuir_professor(
    turma_id: int,
    body: ProfessorBody,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    turma = db.query(Turma).filter(Turma.id == turma_id).first()
    if not turma:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")

    prof = db.query(Usuario).filter(
        Usuario.id == body.professor_id,
        Usuario.role.in_([RoleEnum.professor, RoleEnum.admin]),
    ).first()
    if not prof:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Professor não encontrado")

    turma.professor_id = body.professor_id
    db.commit()
    return {"turma_id": turma_id, "professor_id": turma.professor_id}


# ── Professores ─────────────────────────────────────────────────────────────


@router.get("/professores", response_model=List[ProfessorListItem])
def listar_professores(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    return (
        db.query(Usuario)
        .filter(Usuario.role.in_([RoleEnum.professor, RoleEnum.admin]))
        .order_by(Usuario.nome)
        .all()
    )


# ── Comunicados ─────────────────────────────────────────────────────────────


@router.post("/comunicados", response_model=ComunicadoListItem, status_code=status.HTTP_201_CREATED)
def criar_comunicado(
    body: CriarComunicadoRequest,
    db: Session = Depends(get_db),
    admin: Usuario = Depends(require_admin),
):
    if body.turma_id is not None:
        turma = db.query(Turma).filter(Turma.id == body.turma_id).first()
        if not turma:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Turma não encontrada")

    comunicado = Comunicado(
        autor_id=admin.id,
        titulo=body.titulo,
        mensagem=body.mensagem,
        turma_id=body.turma_id,
    )
    db.add(comunicado)
    db.commit()
    db.refresh(comunicado)
    return comunicado


@router.get("/comunicados", response_model=List[ComunicadoListItem])
def listar_comunicados(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    return db.query(Comunicado).order_by(Comunicado.criado_em.desc()).all()


@router.delete("/comunicados/{comunicado_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_comunicado(
    comunicado_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    comunicado = db.query(Comunicado).filter(Comunicado.id == comunicado_id).first()
    if not comunicado:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Comunicado não encontrado")
    db.delete(comunicado)
    db.commit()


# ── Dashboard ────────────────────────────────────────────────────────────────


@router.get("/dashboard", response_model=DashboardData)
def get_dashboard(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    now = datetime.now(timezone.utc)
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_alunos_ativos = (
        db.query(func.count(PerfilAluno.usuario_id))
        .filter(PerfilAluno.acesso_liberado == True)
        .scalar() or 0
    )

    total_turmas_ativas = (
        db.query(func.count(Turma.id))
        .filter(Turma.ativo == True)
        .scalar() or 0
    )

    total_professores = (
        db.query(func.count(Usuario.id))
        .filter(Usuario.role == RoleEnum.professor)
        .scalar() or 0
    )

    comunicados_mes = (
        db.query(func.count(Comunicado.id))
        .filter(Comunicado.criado_em >= inicio_mes)
        .scalar() or 0
    )

    ultimos_alunos_rows = (
        db.query(Usuario, PerfilAluno)
        .filter(Usuario.role == RoleEnum.aluno)
        .outerjoin(PerfilAluno, PerfilAluno.usuario_id == Usuario.id)
        .order_by(Usuario.criado_em.desc())
        .limit(5)
        .all()
    )
    ultimos_alunos = [
        UltimoAlunoItem(
            id=u.id,
            nome=u.nome,
            username=u.username,
            nivel=p.nivel if p else None,
            criado_em=u.criado_em,
        )
        for u, p in ultimos_alunos_rows
    ]

    comunicados_recentes = (
        db.query(Comunicado)
        .order_by(Comunicado.criado_em.desc())
        .limit(3)
        .all()
    )

    acessos_bloqueados_rows = (
        db.query(Usuario, PerfilAluno)
        .filter(Usuario.role == RoleEnum.aluno)
        .join(PerfilAluno, PerfilAluno.usuario_id == Usuario.id)
        .filter(PerfilAluno.acesso_liberado == False)
        .all()
    )
    acessos_bloqueados = [
        AcessoBloqueadoItem(id=u.id, nome=u.nome, username=u.username, nivel=p.nivel)
        for u, p in acessos_bloqueados_rows
    ]

    return DashboardData(
        total_alunos_ativos=total_alunos_ativos,
        total_turmas_ativas=total_turmas_ativas,
        total_professores=total_professores,
        comunicados_mes=comunicados_mes,
        ultimos_alunos=ultimos_alunos,
        comunicados_recentes=comunicados_recentes,
        acessos_bloqueados=acessos_bloqueados,
    )
