from datetime import datetime
from typing import Annotated, Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.tarefa import CategoriaTarefa, StatusTarefa, CefrLevel


# ════════════════════════════════════════════════════════════════════════════
# CONTEÚDO POR TIPO (discriminado por `tipo`)
# ════════════════════════════════════════════════════════════════════════════

# ── 1. Fill-in-the-blanks (fib) — Grammar/Vocabulary ───────────────────────


class FibSentence(BaseModel):
    id: int
    text: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)


class ConteudoFib(BaseModel):
    tipo: Literal["fib"]
    sentences: List[FibSentence] = Field(..., min_length=1)
    case_insensitive: bool = True
    multiple_answers: bool = False
    show_hint: bool = False


# ── 2. Multiple choice (mc) — Grammar ──────────────────────────────────────


class McOption(BaseModel):
    letter: str = Field(..., min_length=1, max_length=2)
    text: str = Field(..., min_length=1)


class McQuestion(BaseModel):
    prompt: str = Field(..., min_length=1)
    options: List[McOption] = Field(..., min_length=2)
    correct_letter: str


class ConteudoMc(BaseModel):
    tipo: Literal["mc"]
    questions: List[McQuestion] = Field(..., min_length=1)


# ── 3. Matching (match) — Vocabulary ───────────────────────────────────────


class MatchItem(BaseModel):
    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)


class ConteudoMatch(BaseModel):
    tipo: Literal["match"]
    left_items: List[MatchItem] = Field(..., min_length=2)
    right_items: List[MatchItem] = Field(..., min_length=2)
    # Pares como [["L1","R3"], ["L2","R1"], ...]
    correct_pairs: List[List[str]] = Field(..., min_length=1)


# ── 4. Reading (reading) — Reading composto: TFNG + MC + short + heads ─────
# Para reading, `questions` é List[dict] pra suportar 4 sub-tipos sem
# complicar com Union aninhado. Validação fica leve.


class ConteudoReading(BaseModel):
    tipo: Literal["reading"]
    passage: str = Field(..., min_length=1)
    questions: List[dict] = Field(..., min_length=1)


# ── 5. Essay (essay) — Writing ─────────────────────────────────────────────


class ConteudoEssay(BaseModel):
    tipo: Literal["essay"]
    prompt: str = Field(..., min_length=1)
    min_words: int = Field(0, ge=0)
    max_words: int = Field(1000, gt=0)
    target_time: Optional[str] = None
    show_rubric_to_student: bool = False
    suggest_structure: bool = False


# ── 6. Listening Note completion (notes) — texto-only no MVP ───────────────


class ConteudoNotes(BaseModel):
    tipo: Literal["notes"]
    audio_transcript: str = Field(..., min_length=1)
    # Cada linha: {type: 'p'|'fill'|'list', text?, label?, correct?, items?}
    note_template: List[dict] = Field(..., min_length=1)
    max_playcount: int = Field(5, gt=0)


# ── 7. Speaking Role play (role) — texto-only no MVP ───────────────────────


class RoleSide(BaseModel):
    name: str = Field(..., min_length=1)
    context: str = Field(..., min_length=1)


class ConteudoRole(BaseModel):
    tipo: Literal["role"]
    scenario: str = Field(..., min_length=1)
    your_role: RoleSide
    other_role: RoleSide
    target_duration: Optional[str] = None


# ── 8. Translate sentences (tsent) — PT ⇄ EN ───────────────────────────────


class TranslateSentence(BaseModel):
    id: int
    src: str = Field(..., min_length=1)
    hint: Optional[str] = None
    target_hint: Optional[str] = None  # gabarito sugerido (não auto-validado)


class ConteudoTsent(BaseModel):
    tipo: Literal["tsent"]
    direction: Literal["pt_en", "en_pt"]
    sentences: List[TranslateSentence] = Field(..., min_length=1)


# ── 9. Speak & Repeat (speak_repeat) — Speaking estilo Duolingo ────────────
# Aluno vê uma frase, repete em voz alta. Web Speech API transcreve.
# Auto-correção fuzzy compara % de palavras que bateram.


class SpeakRepeatSentence(BaseModel):
    id: int
    text_to_say: str = Field(..., min_length=1)


class ConteudoSpeakRepeat(BaseModel):
    tipo: Literal["speak_repeat"]
    sentences: List[SpeakRepeatSentence] = Field(..., min_length=1)
    lang: str = "en-US"
    match_threshold: int = Field(60, ge=0, le=100)  # % mínimo de palavras pra contar como correto


# ── Union discriminado ─────────────────────────────────────────────────────

ConteudoTarefa = Annotated[
    Union[
        ConteudoFib,
        ConteudoMc,
        ConteudoMatch,
        ConteudoReading,
        ConteudoEssay,
        ConteudoNotes,
        ConteudoRole,
        ConteudoTsent,
        ConteudoSpeakRepeat,
    ],
    Field(discriminator="tipo"),
]


# ── Rubrica (opcional para qualquer tipo) ──────────────────────────────────


class CriterioRubrica(BaseModel):
    criterio: str = Field(..., min_length=1)
    pontos_max: int = Field(..., gt=0)


# ── Tipos suportados ──────────────────────────────────────────────────────

TIPOS_SUPORTADOS = {"fib", "mc", "match", "reading", "essay", "notes", "role", "tsent", "speak_repeat"}


# ════════════════════════════════════════════════════════════════════════════
# REQUESTS (criar/editar tarefa)
# ════════════════════════════════════════════════════════════════════════════


class CriarTarefaRequest(BaseModel):
    categoria: CategoriaTarefa
    tipo: str
    titulo: str = Field(..., min_length=1, max_length=200)
    descricao: Optional[str] = None
    conteudo: ConteudoTarefa
    rubrica: Optional[List[CriterioRubrica]] = None
    data_entrega: Optional[datetime] = None
    pontos_disponiveis: int = Field(..., gt=0)
    cefr_levels: List[CefrLevel] = Field(default_factory=list)
    turmas_alvo: List[int] = Field(default_factory=list)

    @field_validator("tipo")
    @classmethod
    def validar_tipo_suportado(cls, v: str) -> str:
        if v not in TIPOS_SUPORTADOS:
            raise ValueError(
                f"Tipo '{v}' não suportado. Suportados: {sorted(TIPOS_SUPORTADOS)}"
            )
        return v

    @model_validator(mode="after")
    def validar_consistencia(self):
        if self.tipo != self.conteudo.tipo:
            raise ValueError(
                f"Campo 'tipo' ({self.tipo}) não bate com conteudo.tipo ({self.conteudo.tipo})"
            )
        if not self.cefr_levels and not self.turmas_alvo:
            raise ValueError(
                "Tarefa precisa ter pelo menos um cefr_level ou uma turma_alvo"
            )
        return self


class AtualizarTarefaRequest(BaseModel):
    titulo: Optional[str] = Field(None, min_length=1, max_length=200)
    descricao: Optional[str] = None
    conteudo: Optional[ConteudoTarefa] = None
    rubrica: Optional[List[CriterioRubrica]] = None
    data_entrega: Optional[datetime] = None
    pontos_disponiveis: Optional[int] = Field(None, gt=0)
    cefr_levels: Optional[List[CefrLevel]] = None
    turmas_alvo: Optional[List[int]] = None


# ════════════════════════════════════════════════════════════════════════════
# RESPONSES — visão do admin/professor
# ════════════════════════════════════════════════════════════════════════════


class TarefaListItem(BaseModel):
    id: int
    categoria: CategoriaTarefa
    tipo: str
    titulo: str
    descricao: Optional[str]
    pontos_disponiveis: int
    status: StatusTarefa
    data_entrega: Optional[datetime]
    cefr_levels: List[CefrLevel]
    turmas_alvo: List[int]
    criado_em: datetime
    publicado_em: Optional[datetime]


class TarefaDetalhe(BaseModel):
    id: int
    categoria: CategoriaTarefa
    tipo: str
    titulo: str
    descricao: Optional[str]
    conteudo: dict
    rubrica: Optional[List[CriterioRubrica]]
    pontos_disponiveis: int
    status: StatusTarefa
    data_entrega: Optional[datetime]
    cefr_levels: List[CefrLevel]
    turmas_alvo: List[int]
    criado_por: int
    criado_em: datetime
    publicado_em: Optional[datetime]
    arquivado_em: Optional[datetime]


# ════════════════════════════════════════════════════════════════════════════
# RESPONSES — visão do aluno
# ════════════════════════════════════════════════════════════════════════════


SubmissaoStatusAluno = Literal["pending", "submitted", "reviewed"]


class TarefaAlunoListItem(BaseModel):
    id: int
    categoria: CategoriaTarefa
    tipo: str
    titulo: str
    descricao: Optional[str]
    pontos_disponiveis: int
    data_entrega: Optional[datetime]
    publicado_em: Optional[datetime]
    submissao_status: SubmissaoStatusAluno = "pending"


class TarefaAlunoDetalhe(BaseModel):
    """Conteúdo vem sanitizado (gabaritos removidos)."""
    id: int
    categoria: CategoriaTarefa
    tipo: str
    titulo: str
    descricao: Optional[str]
    conteudo: dict
    rubrica: Optional[List[CriterioRubrica]]
    pontos_disponiveis: int
    data_entrega: Optional[datetime]
    publicado_em: Optional[datetime]
    submissao_status: SubmissaoStatusAluno = "pending"
    submissao: Optional["MinhaSubmissaoResponse"] = None


# ════════════════════════════════════════════════════════════════════════════
# RESPOSTAS DO ALUNO (discriminado por `tipo`)
# ════════════════════════════════════════════════════════════════════════════


# ── 1. FIB ──────────────────────────────────────────────────────────────────


class FibAnswer(BaseModel):
    sentence_id: int
    answer: str


class RespostasFib(BaseModel):
    tipo: Literal["fib"]
    answers: List[FibAnswer]


# ── 2. MC ───────────────────────────────────────────────────────────────────


class McAnswer(BaseModel):
    question_idx: int = Field(..., ge=0)  # 0-based
    selected_letter: str


class RespostasMc(BaseModel):
    tipo: Literal["mc"]
    answers: List[McAnswer]


# ── 3. Matching ─────────────────────────────────────────────────────────────


class MatchPair(BaseModel):
    left_id: str
    right_id: str


class RespostasMatch(BaseModel):
    tipo: Literal["match"]
    pairs: List[MatchPair]


# ── 4. Reading ──────────────────────────────────────────────────────────────


class ReadingAnswer(BaseModel):
    n: int  # número da questão (1-based, casa com question.n)
    type: str  # tfng | mc | short | heads
    value: Any  # depende do tipo


class RespostasReading(BaseModel):
    tipo: Literal["reading"]
    answers: List[ReadingAnswer]


# ── 5. Essay ────────────────────────────────────────────────────────────────


class RespostasEssay(BaseModel):
    tipo: Literal["essay"]
    content: str
    word_count: int = Field(0, ge=0)


# ── 6. Notes (Listening) ────────────────────────────────────────────────────


class NoteAnswer(BaseModel):
    # `idx` identifica posição da lacuna no template (interpretado pelo player)
    idx: int = Field(..., ge=0)
    answer: str


class RespostasNotes(BaseModel):
    tipo: Literal["notes"]
    answers: List[NoteAnswer]


# ── 7. Role (Speaking texto-only) ──────────────────────────────────────────


class RespostasRole(BaseModel):
    tipo: Literal["role"]
    response_text: str = Field(..., min_length=1)


# ── 8. Translate sentences ─────────────────────────────────────────────────


class TranslateAnswer(BaseModel):
    sentence_id: int
    target: str


class RespostasTsent(BaseModel):
    tipo: Literal["tsent"]
    answers: List[TranslateAnswer]


# ── 9. Speak & Repeat ──────────────────────────────────────────────────────


class SpeakRepeatAnswer(BaseModel):
    sentence_id: int
    transcript: str = ""  # vazio se skipped=true ou se browser não transcreveu
    skipped: bool = False


class RespostasSpeakRepeat(BaseModel):
    tipo: Literal["speak_repeat"]
    answers: List[SpeakRepeatAnswer]


# ── Union discriminado ─────────────────────────────────────────────────────

RespostasTarefa = Annotated[
    Union[
        RespostasFib,
        RespostasMc,
        RespostasMatch,
        RespostasReading,
        RespostasEssay,
        RespostasNotes,
        RespostasRole,
        RespostasTsent,
        RespostasSpeakRepeat,
    ],
    Field(discriminator="tipo"),
]


# ════════════════════════════════════════════════════════════════════════════
# REQUESTS — autosave e submissão do aluno
# ════════════════════════════════════════════════════════════════════════════


class SubmeterTarefaRequest(BaseModel):
    respostas: RespostasTarefa
    tempo_gasto_seg: Optional[int] = Field(None, ge=0)


class AutosaveRascunhoRequest(BaseModel):
    """Aceita estrutura parcial — validação rigorosa só no submit."""
    respostas: dict
    progresso: Optional[dict] = None


class RascunhoResponse(BaseModel):
    tarefa_id: int
    respostas: dict
    progresso: Optional[dict]
    atualizado_em: datetime


class MinhaSubmissaoResponse(BaseModel):
    id: int
    tarefa_id: int
    respostas: dict
    status: Literal["submitted", "reviewed"]
    submetido_em: datetime
    tempo_gasto_seg: Optional[int]
    atrasada: bool
    eh_repeticao: bool
    correcao: Optional["CorrecaoAlunoResponse"] = None


# ════════════════════════════════════════════════════════════════════════════
# CORREÇÃO (professor) — schemas inalterados
# ════════════════════════════════════════════════════════════════════════════


GRADES_VALIDAS = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F"}


class RubricaScore(BaseModel):
    criterio_idx: int = Field(..., ge=0)
    awarded: int = Field(..., ge=0)


class InlineNote(BaseModel):
    line_num: int = Field(..., ge=0)
    text: str
    correction: Optional[str] = None


class CorrigirSubmissaoRequest(BaseModel):
    score: int = Field(..., ge=0, le=100)
    grade: Optional[str] = None
    rubrica_scores: Optional[List[RubricaScore]] = None
    feedback: Optional[str] = None
    inline_notes: Optional[List[InlineNote]] = None

    @field_validator("grade")
    @classmethod
    def validar_grade(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in GRADES_VALIDAS:
            raise ValueError(
                f"Grade '{v}' inválida. Aceitos: {sorted(GRADES_VALIDAS)}"
            )
        return v


class CorrecaoResponse(BaseModel):
    id: int
    submissao_id: int
    score: int
    grade: Optional[str]
    auto_score: Optional[int]
    rubrica_scores: Optional[List[RubricaScore]]
    feedback: Optional[str]
    inline_notes: Optional[List[InlineNote]]
    corrigido_em: datetime
    pontos_ganhos: int


class CorrecaoAlunoResponse(BaseModel):
    score: int
    grade: Optional[str]
    rubrica_scores: Optional[List[RubricaScore]]
    feedback: Optional[str]
    inline_notes: Optional[List[InlineNote]]
    corrigido_em: datetime
    pontos_ganhos: int


class SubmissaoPendenteItem(BaseModel):
    id: int
    tarefa_id: int
    tarefa_titulo: str
    tarefa_tipo: str
    aluno_id: int
    aluno_nome: str
    submetido_em: datetime
    atrasada: bool
    auto_score: Optional[int]


class SubmissaoCompletaProfessor(BaseModel):
    """tarefa_conteudo NÃO é sanitizado — professor vê gabaritos."""
    id: int
    tarefa_id: int
    tarefa_titulo: str
    tarefa_tipo: str
    tarefa_conteudo: dict
    tarefa_rubrica: Optional[List[CriterioRubrica]]
    tarefa_pontos_disponiveis: int
    aluno_id: int
    aluno_nome: str
    respostas: dict
    status: Literal["submitted", "reviewed"]
    submetido_em: datetime
    tempo_gasto_seg: Optional[int]
    atrasada: bool
    eh_repeticao: bool
    auto_score: Optional[int]
    correcao: Optional[CorrecaoResponse] = None


# Resolve forward refs
MinhaSubmissaoResponse.model_rebuild()
TarefaAlunoDetalhe.model_rebuild()
