import re
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.aluno_turma import AlunoTurma
from app.models.correcao import Correcao
from app.models.ganho_pontos import GanhoPontos
from app.models.perfil_aluno import PerfilAluno
from app.models.rascunho_submissao import RascunhoSubmissao
from app.models.submissao import Submissao, StatusSubmissao
from app.models.tarefa import Tarefa, CategoriaTarefa, StatusTarefa
from app.models.tarefa_cefr_level import TarefaCefrLevel
from app.models.tarefa_turma import TarefaTurma
from app.models.usuario import Usuario
from app.schemas.tarefas import (
    AutosaveRascunhoRequest,
    CorrecaoAlunoResponse,
    MinhaSubmissaoResponse,
    RascunhoResponse,
    SubmeterTarefaRequest,
    TarefaAlunoDetalhe,
    TarefaAlunoListItem,
)
from app.utils.security import require_aluno

router = APIRouter(prefix="/alunos/tarefas", tags=["alunos-tarefas"])


# ── Helpers ──────────────────────────────────────────────────────────────────


def _sanitizar_conteudo(conteudo: dict, tipo: str) -> dict:
    """Remove gabaritos antes de retornar conteúdo ao aluno."""
    if not conteudo:
        return conteudo

    if tipo == "fib":
        s = dict(conteudo)
        s["sentences"] = [
            {k: v for k, v in sent.items() if k != "answer"}
            for sent in s.get("sentences", [])
        ]
        return s

    if tipo == "mc":
        s = dict(conteudo)
        s["questions"] = [
            {k: v for k, v in q.items() if k != "correct_letter"}
            for q in s.get("questions", [])
        ]
        return s

    if tipo == "match":
        s = dict(conteudo)
        s.pop("correct_pairs", None)
        return s

    if tipo == "reading":
        s = dict(conteudo)
        s["questions"] = [_sanitize_reading_q(q) for q in s.get("questions", [])]
        return s

    if tipo == "notes":
        s = dict(conteudo)
        # Remove `audio_transcript` se backend não deveria mostrar (mas no MVP
        # texto-only o aluno LÊ a transcrição — então mantemos). Apenas tira `correct`.
        s["note_template"] = [_sanitize_note_line(line) for line in s.get("note_template", [])]
        return s

    if tipo == "tsent":
        s = dict(conteudo)
        s["sentences"] = [
            {k: v for k, v in sent.items() if k != "target_hint"}
            for sent in s.get("sentences", [])
        ]
        return s

    # essay, role — sem gabarito sensível, retorna como está
    return conteudo


def _sanitize_reading_q(q: dict) -> dict:
    """Remove gabaritos das questões de reading conforme o subtipo."""
    qtype = q.get("type")
    cleaned = dict(q)
    if qtype == "tfng":
        cleaned.pop("correct", None)
    elif qtype == "mc":
        cleaned.pop("correct_letter", None)
        if "options" in cleaned and isinstance(cleaned["options"], list):
            cleaned["options"] = [
                {k: v for k, v in o.items() if k != "is_correct"}
                for o in cleaned["options"]
            ]
    elif qtype == "heads":
        cleaned.pop("correct_pairs", None)
    # short answer não tem gabarito objetivo
    return cleaned


def _sanitize_note_line(line: dict) -> dict:
    """Remove gabarito de cada linha de note template."""
    cleaned = dict(line)
    cleaned.pop("correct", None)
    if cleaned.get("type") == "list" and isinstance(cleaned.get("items"), list):
        cleaned["items"] = [
            {k: v for k, v in item.items() if k != "correct"}
            for item in cleaned["items"]
        ]
    return cleaned


def _query_tarefas_visiveis(db: Session, aluno: Usuario):
    """Retorna query SQLAlchemy de tarefas published visíveis ao aluno
    (match por cefr_level OU por turma). Retorna None se o aluno não
    tem nenhum alvo configurado (perfil sem cefr_level e sem turma).
    """
    perfil = db.query(PerfilAluno).filter(PerfilAluno.usuario_id == aluno.id).first()
    aluno_cefr = perfil.cefr_level if perfil else None

    turma_ids = [
        row.turma_id
        for row in db.query(AlunoTurma.turma_id)
        .filter(AlunoTurma.aluno_id == aluno.id)
        .all()
    ]

    conditions = []
    if aluno_cefr:
        cefr_subq = db.query(TarefaCefrLevel.tarefa_id).filter(
            TarefaCefrLevel.cefr_level == aluno_cefr
        )
        conditions.append(Tarefa.id.in_(cefr_subq))
    if turma_ids:
        turma_subq = db.query(TarefaTurma.tarefa_id).filter(
            TarefaTurma.turma_id.in_(turma_ids)
        )
        conditions.append(Tarefa.id.in_(turma_subq))

    if not conditions:
        return None

    return db.query(Tarefa).filter(
        Tarefa.status == StatusTarefa.published,
        or_(*conditions),
    )


def _auto_corrigir_fib(conteudo: dict, respostas: dict) -> Optional[int]:
    """Calcula score sugerido (0-100) comparando respostas com gabarito FIB.
    Retorna None se a tarefa não tem sentenças.

    Regras:
    - `case_insensitive=true` (default): compara em lowercase
    - `multiple_answers=true`: gabarito separado por "|" — aluno acerta com qualquer opção
    """
    sentences = conteudo.get("sentences", [])
    case_ins = conteudo.get("case_insensitive", True)
    multi = conteudo.get("multiple_answers", False)

    answers_by_id = {
        a["sentence_id"]: a["answer"]
        for a in respostas.get("answers", [])
    }

    total = len(sentences)
    if total == 0:
        return None

    corretos = 0
    for s in sentences:
        gabarito = s.get("answer", "")
        aluno_resp = answers_by_id.get(s.get("id"), "")

        if case_ins:
            aluno_resp = aluno_resp.lower().strip()
            gabarito_norm = gabarito.lower()
        else:
            aluno_resp = aluno_resp.strip()
            gabarito_norm = gabarito

        if multi:
            opcoes = [o.strip() for o in gabarito_norm.split("|")]
            if aluno_resp in opcoes:
                corretos += 1
        else:
            if aluno_resp == gabarito_norm.strip():
                corretos += 1

    return int(round((corretos / total) * 100))


def _auto_corrigir_mc(conteudo: dict, respostas: dict) -> Optional[int]:
    """Compara `selected_letter` com `correct_letter` em cada question."""
    questions = conteudo.get("questions", [])
    total = len(questions)
    if total == 0:
        return None

    by_idx = {a["question_idx"]: a.get("selected_letter", "") for a in respostas.get("answers", [])}
    corretos = sum(
        1 for i, q in enumerate(questions)
        if (by_idx.get(i) or "").strip().upper() == (q.get("correct_letter") or "").strip().upper()
    )
    return int(round((corretos / total) * 100))


def _auto_corrigir_match(conteudo: dict, respostas: dict) -> Optional[int]:
    """Compara pares (left_id, right_id) com correct_pairs."""
    correct_pairs = conteudo.get("correct_pairs", [])
    total = len(correct_pairs)
    if total == 0:
        return None

    correct_set = {(p[0], p[1]) for p in correct_pairs if len(p) >= 2}
    aluno_set = {
        (p.get("left_id"), p.get("right_id"))
        for p in respostas.get("pairs", [])
        if p.get("left_id") and p.get("right_id")
    }
    corretos = len(correct_set & aluno_set)
    return int(round((corretos / total) * 100))


def _auto_corrigir_reading(conteudo: dict, respostas: dict) -> Optional[int]:
    """Auto-correção PARCIAL: só tfng e mc têm gabarito objetivo.

    Calcula percentual baseado nas questions objetivas. Se não houver
    nenhuma objetiva, retorna None (deixa pro professor).
    """
    questions = conteudo.get("questions", [])
    objetivas = [q for q in questions if q.get("type") in ("tfng", "mc")]
    total = len(objetivas)
    if total == 0:
        return None

    by_n = {a.get("n"): a for a in respostas.get("answers", [])}
    corretos = 0
    for q in objetivas:
        a = by_n.get(q.get("n"))
        if not a:
            continue
        val = (a.get("value") or "")
        if q["type"] == "tfng":
            if str(val).strip().lower() == str(q.get("correct", "")).strip().lower():
                corretos += 1
        elif q["type"] == "mc":
            if str(val).strip().upper() == str(q.get("correct_letter", "")).strip().upper():
                corretos += 1

    return int(round((corretos / total) * 100))


def _auto_corrigir_speak_repeat(conteudo: dict, respostas: dict) -> Optional[int]:
    """Fuzzy match palavra-a-palavra entre transcript do aluno e text_to_say.
    - Tokeniza ignorando pontuação
    - Lowercase
    - Compara como sets (não importa ordem, mas peso pelas únicas esperadas)
    - Acima de `match_threshold` → frase contada como correta
    - Skipped não conta (não é erro nem acerto, vai pro professor)
    """
    sentences = conteudo.get("sentences", [])
    threshold = conteudo.get("match_threshold", 60)
    total = len(sentences)
    if total == 0:
        return None

    by_id = {a["sentence_id"]: a for a in respostas.get("answers", [])}

    avaliadas = 0
    corretas = 0
    for s in sentences:
        ans = by_id.get(s["id"])
        if not ans or ans.get("skipped"):
            continue
        transcript = (ans.get("transcript") or "").lower().strip()
        expected = (s.get("text_to_say") or "").lower().strip()

        exp_words = set(re.findall(r"\w+", expected))
        got_words = set(re.findall(r"\w+", transcript))

        if not exp_words:
            continue

        match_pct = len(exp_words & got_words) / len(exp_words) * 100
        avaliadas += 1
        if match_pct >= threshold:
            corretas += 1

    if avaliadas == 0:
        return None  # tudo skipped — manual

    return int(round((corretas / avaliadas) * 100))


def _auto_corrigir_notes(conteudo: dict, respostas: dict) -> Optional[int]:
    """Compara cada lacuna do note_template contra a resposta do aluno.
    Estratégia: indexa lacunas em ordem (flat) e bate com respostas por `idx`.
    """
    template = conteudo.get("note_template", [])
    # Coleta gabaritos em ordem (flat)
    gabaritos = []
    for line in template:
        ltype = line.get("type")
        if ltype == "fill":
            gabaritos.append(line.get("correct"))
        elif ltype == "list":
            for item in line.get("items", []):
                gabaritos.append(item.get("correct"))

    total = sum(1 for g in gabaritos if g)  # só conta lacunas com gabarito
    if total == 0:
        return None

    by_idx = {a.get("idx"): (a.get("answer") or "").strip().lower() for a in respostas.get("answers", [])}
    corretos = 0
    for i, gab in enumerate(gabaritos):
        if not gab:
            continue
        if by_idx.get(i) == str(gab).strip().lower():
            corretos += 1

    return int(round((corretos / total) * 100))


# Dispatch — mapeia tipo → função (None para tipos sem auto-correção objetiva)
_AUTO_CORRECT_DISPATCH = {
    "fib":   _auto_corrigir_fib,
    "mc":    _auto_corrigir_mc,
    "match": _auto_corrigir_match,
    "reading": _auto_corrigir_reading,
    "notes": _auto_corrigir_notes,
    "speak_repeat": _auto_corrigir_speak_repeat,
    # essay, role, tsent — manual (professor avalia)
}


def _auto_corrigir(tipo: str, conteudo: dict, respostas: dict) -> Optional[int]:
    fn = _AUTO_CORRECT_DISPATCH.get(tipo)
    if not fn:
        return None
    try:
        return fn(conteudo or {}, respostas or {})
    except Exception:
        # auto-correção é best-effort; se algo der errado, professor avalia manualmente
        return None


def _calcular_atrasada(data_entrega: Optional[datetime]) -> bool:
    if not data_entrega:
        return False
    agora = datetime.now(timezone.utc)
    entrega = data_entrega
    if entrega.tzinfo is None:
        entrega = entrega.replace(tzinfo=timezone.utc)
    return agora > entrega


def _submissao_original(db: Session, tarefa_id: int, aluno_id: int) -> Optional[Submissao]:
    """Busca a submissão original (eh_repeticao=false) do aluno pra uma tarefa."""
    return (
        db.query(Submissao)
        .filter(
            Submissao.tarefa_id == tarefa_id,
            Submissao.aluno_id == aluno_id,
            Submissao.eh_repeticao == False,
        )
        .first()
    )


def _build_submissao_response(db: Session, submissao: Submissao) -> MinhaSubmissaoResponse:
    """Monta resposta da submissão. Inclui `correcao` se status=reviewed."""
    correcao_resp: Optional[CorrecaoAlunoResponse] = None
    if submissao.status == StatusSubmissao.reviewed:
        correcao = (
            db.query(Correcao)
            .filter(Correcao.submissao_id == submissao.id)
            .first()
        )
        if correcao:
            ganho = (
                db.query(GanhoPontos)
                .filter(GanhoPontos.submissao_id == submissao.id)
                .first()
            )
            pontos = ganho.pontos if ganho else 0
            correcao_resp = CorrecaoAlunoResponse(
                score=correcao.score,
                grade=correcao.grade,
                rubrica_scores=correcao.rubrica_scores,
                feedback=correcao.feedback,
                inline_notes=correcao.inline_notes,
                corrigido_em=correcao.corrigido_em,
                pontos_ganhos=pontos,
            )

    return MinhaSubmissaoResponse(
        id=submissao.id,
        tarefa_id=submissao.tarefa_id,
        respostas=submissao.respostas,
        status=submissao.status.value,
        submetido_em=submissao.submetido_em,
        tempo_gasto_seg=submissao.tempo_gasto_seg,
        atrasada=submissao.atrasada,
        eh_repeticao=submissao.eh_repeticao,
        correcao=correcao_resp,
    )


# ── GET: lista e detalhe da tarefa ────────────────────────────────────────


@router.get("", response_model=List[TarefaAlunoListItem])
def listar_minhas_tarefas(
    categoria: Optional[CategoriaTarefa] = Query(None),
    aluno: Usuario = Depends(require_aluno),
    db: Session = Depends(get_db),
):
    query = _query_tarefas_visiveis(db, aluno)
    if query is None:
        return []

    if categoria:
        query = query.filter(Tarefa.categoria == categoria)

    tarefas = query.order_by(Tarefa.publicado_em.desc()).all()
    if not tarefas:
        return []

    tarefa_ids = [t.id for t in tarefas]
    submissoes_map = {
        s.tarefa_id: s.status.value
        for s in db.query(Submissao)
        .filter(
            Submissao.aluno_id == aluno.id,
            Submissao.tarefa_id.in_(tarefa_ids),
            Submissao.eh_repeticao == False,
        )
        .all()
    }

    return [
        TarefaAlunoListItem(
            id=t.id,
            categoria=t.categoria,
            tipo=t.tipo,
            titulo=t.titulo,
            descricao=t.descricao,
            pontos_disponiveis=t.pontos_disponiveis,
            data_entrega=t.data_entrega,
            publicado_em=t.publicado_em,
            submissao_status=submissoes_map.get(t.id, "pending"),
        )
        for t in tarefas
    ]


@router.get("/{tarefa_id}", response_model=TarefaAlunoDetalhe)
def get_minha_tarefa(
    tarefa_id: int,
    aluno: Usuario = Depends(require_aluno),
    db: Session = Depends(get_db),
):
    query = _query_tarefas_visiveis(db, aluno)
    if query is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    tarefa = query.filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    submissao = _submissao_original(db, tarefa_id, aluno.id)
    sub_status = submissao.status.value if submissao else "pending"
    sub_response = _build_submissao_response(db, submissao) if submissao else None

    return TarefaAlunoDetalhe(
        id=tarefa.id,
        categoria=tarefa.categoria,
        tipo=tarefa.tipo,
        titulo=tarefa.titulo,
        descricao=tarefa.descricao,
        conteudo=_sanitizar_conteudo(tarefa.conteudo, tarefa.tipo),
        rubrica=tarefa.rubrica,
        pontos_disponiveis=tarefa.pontos_disponiveis,
        data_entrega=tarefa.data_entrega,
        publicado_em=tarefa.publicado_em,
        submissao_status=sub_status,
        submissao=sub_response,
    )


# ── Rascunho (autosave) ───────────────────────────────────────────────────


@router.put("/{tarefa_id}/rascunho", response_model=RascunhoResponse)
def autosave_rascunho(
    tarefa_id: int,
    body: AutosaveRascunhoRequest,
    aluno: Usuario = Depends(require_aluno),
    db: Session = Depends(get_db),
):
    query = _query_tarefas_visiveis(db, aluno)
    if query is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    tarefa = query.filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    if _submissao_original(db, tarefa_id, aluno.id):
        raise HTTPException(
            status_code=409,
            detail="Tarefa já submetida — rascunho não disponível",
        )

    rascunho = (
        db.query(RascunhoSubmissao)
        .filter(
            RascunhoSubmissao.tarefa_id == tarefa_id,
            RascunhoSubmissao.aluno_id == aluno.id,
        )
        .first()
    )

    if rascunho:
        rascunho.respostas = body.respostas
        rascunho.progresso = body.progresso
    else:
        rascunho = RascunhoSubmissao(
            tarefa_id=tarefa_id,
            aluno_id=aluno.id,
            respostas=body.respostas,
            progresso=body.progresso,
        )
        db.add(rascunho)

    db.commit()
    db.refresh(rascunho)

    return RascunhoResponse(
        tarefa_id=rascunho.tarefa_id,
        respostas=rascunho.respostas,
        progresso=rascunho.progresso,
        atualizado_em=rascunho.atualizado_em,
    )


@router.get("/{tarefa_id}/rascunho", response_model=RascunhoResponse)
def get_rascunho(
    tarefa_id: int,
    aluno: Usuario = Depends(require_aluno),
    db: Session = Depends(get_db),
):
    rascunho = (
        db.query(RascunhoSubmissao)
        .filter(
            RascunhoSubmissao.tarefa_id == tarefa_id,
            RascunhoSubmissao.aluno_id == aluno.id,
        )
        .first()
    )
    if not rascunho:
        raise HTTPException(status_code=404, detail="Rascunho não encontrado")

    return RascunhoResponse(
        tarefa_id=rascunho.tarefa_id,
        respostas=rascunho.respostas,
        progresso=rascunho.progresso,
        atualizado_em=rascunho.atualizado_em,
    )


# ── Submissão ──────────────────────────────────────────────────────────────


@router.post(
    "/{tarefa_id}/submissoes",
    response_model=MinhaSubmissaoResponse,
    status_code=status.HTTP_201_CREATED,
)
def submeter_tarefa(
    tarefa_id: int,
    body: SubmeterTarefaRequest,
    aluno: Usuario = Depends(require_aluno),
    db: Session = Depends(get_db),
):
    query = _query_tarefas_visiveis(db, aluno)
    if query is None:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    tarefa = query.filter(Tarefa.id == tarefa_id).first()
    if not tarefa:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada")

    if body.respostas.tipo != tarefa.tipo:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Tipo das respostas ({body.respostas.tipo}) não bate com "
                f"tipo da tarefa ({tarefa.tipo})"
            ),
        )

    if _submissao_original(db, tarefa_id, aluno.id):
        raise HTTPException(status_code=409, detail="Tarefa já submetida")

    respostas_dict = body.respostas.model_dump()

    auto_score: Optional[int] = _auto_corrigir(tarefa.tipo, tarefa.conteudo, respostas_dict)

    submissao = Submissao(
        tarefa_id=tarefa_id,
        aluno_id=aluno.id,
        respostas=respostas_dict,
        tempo_gasto_seg=body.tempo_gasto_seg,
        atrasada=_calcular_atrasada(tarefa.data_entrega),
        eh_repeticao=False,
        auto_score=auto_score,
    )
    db.add(submissao)

    db.query(RascunhoSubmissao).filter(
        RascunhoSubmissao.tarefa_id == tarefa_id,
        RascunhoSubmissao.aluno_id == aluno.id,
    ).delete()

    db.commit()
    db.refresh(submissao)

    return _build_submissao_response(db, submissao)


@router.get("/{tarefa_id}/submissao", response_model=MinhaSubmissaoResponse)
def get_minha_submissao(
    tarefa_id: int,
    aluno: Usuario = Depends(require_aluno),
    db: Session = Depends(get_db),
):
    submissao = _submissao_original(db, tarefa_id, aluno.id)
    if not submissao:
        raise HTTPException(status_code=404, detail="Submissão não encontrada")
    return _build_submissao_response(db, submissao)
