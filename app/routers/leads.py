import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.usuario import Usuario, RoleEnum
from app.models.perfil_aluno import PerfilAluno
from app.models.lead import Lead, LeadStatus
from app.schemas.leads import (
    LeadCreatePublic,
    LeadListItem,
    LeadDetalhe,
    LeadUpdate,
    LeadConvertResponse,
    LeadStats,
)
from app.utils.security import get_password_hash, require_admin
from app.utils.email_service import send_welcome_email
from app.utils.captcha import verify_turnstile, turnstile_enabled
from app.utils.rate_limit import limiter

router = APIRouter(tags=["leads"])


# ── Público (form de contato) ───────────────────────────────────────────────


@router.post("/leads", status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute;20/hour")
def criar_lead_publico(
    request: Request,
    body: LeadCreatePublic,
    db: Session = Depends(get_db),
):
    """
    Endpoint público — formulário de contato. Anti-spam:
    - Rate limit por IP (5/min, 20/h)
    - CAPTCHA Turnstile se configurado
    """
    if turnstile_enabled():
        client_ip = request.client.host if request.client else None
        if not verify_turnstile(body.captcha_token, client_ip):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha inválido")

    lead = Lead(
        nome=body.nome,
        email=body.email,
        whatsapp=body.whatsapp,
        como_conheceu=body.como_conheceu,
        nivel_ingles=body.nivel_ingles,
        objetivo=body.objetivo,
        mensagem=body.mensagem,
        status=LeadStatus.novo,
    )
    db.add(lead)
    db.commit()
    return {"ok": True}


# ── Admin (gestão) ──────────────────────────────────────────────────────────


@router.get("/admin/leads", response_model=List[LeadListItem])
def listar_leads(
    status_filtro: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    q = db.query(Lead)
    if status_filtro and status_filtro != "all":
        q = q.filter(Lead.status == status_filtro)
    return q.order_by(Lead.criado_em.desc()).all()


@router.get("/admin/leads/stats", response_model=LeadStats)
def stats_leads(
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    total = db.query(func.count(Lead.id)).scalar() or 0

    por_status_rows = (
        db.query(Lead.status, func.count(Lead.id))
        .group_by(Lead.status)
        .all()
    )
    por_status = {s.value if hasattr(s, "value") else str(s): c for s, c in por_status_rows}
    # garante que todos os status apareçam (mesmo com 0)
    for s in ("novo", "em_contato", "trial", "convertido", "descartado"):
        por_status.setdefault(s, 0)

    agora = datetime.now(timezone.utc)
    novos_7d = (
        db.query(func.count(Lead.id))
        .filter(Lead.criado_em >= agora - timedelta(days=7))
        .scalar() or 0
    )
    conv_30d = (
        db.query(func.count(Lead.id))
        .filter(Lead.convertido_em >= agora - timedelta(days=30))
        .scalar() or 0
    )

    return LeadStats(
        total=total,
        por_status=por_status,
        novos_ultimos_7d=novos_7d,
        convertidos_ultimos_30d=conv_30d,
    )


@router.get("/admin/leads/{lead_id}", response_model=LeadDetalhe)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado")
    return lead


@router.patch("/admin/leads/{lead_id}", response_model=LeadDetalhe)
def atualizar_lead(
    lead_id: int,
    body: LeadUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado")

    if body.status is not None:
        lead.status = LeadStatus(body.status)
    if body.motivo_descarte is not None:
        lead.motivo_descarte = body.motivo_descarte
    if body.notas is not None:
        lead.notas = body.notas
    if body.lembrete_em is not None:
        lead.lembrete_em = body.lembrete_em

    db.commit()
    db.refresh(lead)
    return lead


@router.post("/admin/leads/{lead_id}/convert", response_model=LeadConvertResponse)
def converter_lead_em_aluno(
    lead_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    """
    Converte um lead em aluno: cria usuário + perfil, marca lead como convertido,
    envia email de boas-vindas com senha temporária.

    Username é gerado automaticamente a partir do email (parte antes do @, sanitizada).
    Se já existir, sufixa com número.
    """
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado")

    if lead.status == LeadStatus.convertido and lead.aluno_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lead já convertido")

    # Verifica se email já tem conta
    existing = db.query(Usuario).filter(Usuario.email == lead.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe conta com email {lead.email} (usuário: {existing.username})",
        )

    # Gera username a partir do email
    base = lead.email.split("@")[0]
    base = "".join(ch if ch.isalnum() or ch in "._-" else "" for ch in base) or "aluno"
    username = base
    n = 1
    while db.query(Usuario).filter(Usuario.username == username).first():
        n += 1
        username = f"{base}{n}"

    senha_temporaria = secrets.token_urlsafe(10)

    # Mapeia nivel_ingles do lead pro enum do PerfilAluno
    nivel_map = {
        "iniciante": "básico",
        "basico": "básico",
        "intermediario": "intermediário",
        "avancado": "avançado",
    }
    nivel = nivel_map.get((lead.nivel_ingles or "").lower())

    novo = Usuario(
        nome=lead.nome,
        email=lead.email,
        username=username,
        senha_hash=get_password_hash(senha_temporaria),
        role=RoleEnum.aluno,
        ativo=True,
    )
    db.add(novo)
    db.flush()

    perfil = PerfilAluno(
        usuario_id=novo.id,
        nivel=nivel,
        idioma_portal="pt" if nivel and nivel.startswith("básico") else "en",
        acesso_liberado=True,
    )
    db.add(perfil)

    lead.status = LeadStatus.convertido
    lead.aluno_id = novo.id
    lead.convertido_em = datetime.now(timezone.utc)

    db.commit()
    db.refresh(novo)

    # Envia email de boas-vindas (best-effort)
    send_welcome_email(
        to=novo.email,
        nome=novo.nome,
        username=novo.username,
        senha_temporaria=senha_temporaria,
    )

    return LeadConvertResponse(
        aluno_id=novo.id,
        username=novo.username,
        senha_temporaria=senha_temporaria,
    )


@router.delete("/admin/leads/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def deletar_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead não encontrado")
    db.delete(lead)
    db.commit()
