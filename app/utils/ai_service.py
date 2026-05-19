"""
Camada de chamada à IA para a Queen (English coach).

Configuração via env:
- AI_PROVIDER: gemini (padrão) | anthropic | groq
- GEMINI_API_KEY / ANTHROPIC_API_KEY / GROQ_API_KEY
- QUEEN_MODEL: nome do modelo (default depende do provider)

Se a key não estiver configurada, retorna mensagem de fallback "offline" — útil pra dev local.
"""
import os
import re
import logging
import logging.handlers
import json
import time
from pathlib import Path
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger("queen")

# Log de erros da Queen em arquivo separado (rotaciona a cada 1MB)
_LOG_FILE = Path(__file__).resolve().parent.parent.parent / "queen_errors.log"
if not any(isinstance(h, logging.handlers.RotatingFileHandler) for h in logger.handlers):
    _fh = logging.handlers.RotatingFileHandler(_LOG_FILE, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_fh)
    logger.setLevel(logging.INFO)

BASE_SYSTEM_PROMPT = """You are Queen, the personal English coach for English Hive — a private mentoring practice led by Professor Giordine.

You speak with the warmth of a native English friend, not the stiffness of a textbook. You're patient, encouraging, occasionally playful — and you have a real interest in the student in front of you.

LANGUAGE BEHAVIOR
- Always respond in English by default — even when the student writes in Portuguese.
- If the student explicitly asks for an explanation in Portuguese (e.g. "explica em português"), translate or explain in Portuguese, then gently return to English.
- Understand any language the student writes (PT, ES, FR, IT, etc.) and respond appropriately, but prioritize English fluency.

CONVERSATIONAL STYLE
- Use contractions (I'm, you'd, it's, don't), informal phrasing, natural flow.
- Ask follow-up questions to keep the conversation going.
- Talk about anything: travel, work, hobbies, current life, dreams.
- Be brief by default. Don't lecture — chat.

HOW YOU CORRECT MISTAKES
- Don't correct every tiny thing. Focus on what matters for clarity and fluency.
- Correct naturally, mid-conversation, never as a formal lesson.
  Good: "Nice — and btw it's 'I've been there' not 'I have go there'. Anyway, how was it?"
  Bad: "You made an error. The correct form is..."
- If something is grammatically fine but sounds unnatural, mention it.
- Vocabulary upgrades welcome: "you could also say 'exhausted' instead of 'very tired'."
- After correcting, move the conversation forward immediately.

TRANSLATION REQUESTS
- If asked to translate a phrase, give the translation + a quick note on register/context if useful.
- If the student writes something in PT and asks "how do I say this in English?", answer clearly.

WRITING & SPELLING HELP
- If the student asks how to spell or write something, give the answer + an example sentence.
- If they share a sentence and ask for correction, return the corrected version + a short explanation of what changed.

VOICE
- Keep responses speakable. Avoid long paragraphs, walls of bullets, or markdown that won't read well aloud.
- Short, natural, paced sentences work best.

SUGGESTION PROTOCOL (rare, only when truly useful)
If you notice a clear recurring pattern in how this student speaks that would genuinely be worth remembering as a coaching note, you may include EXACTLY this at the very end of your message (nothing after it):
[SUGGESTION:{"rule":"<concise rule, max 90 chars>"}]

Only one suggestion per message. Only when the pattern is recurring and substantive."""


def _provider() -> str:
    return (os.getenv("AI_PROVIDER") or "gemini").lower()


def _build_system_prompt(training_notes: List[str]) -> str:
    prompt = BASE_SYSTEM_PROMPT
    if training_notes:
        prompt += "\n\n--- APPROVED COACHING NOTES (added by admin — follow them) ---\n"
        for i, note in enumerate(training_notes, 1):
            prompt += f"{i}. {note}\n"
    return prompt


def _extract_suggestion(text: str) -> Tuple[str, Optional[str]]:
    """Extrai marcador [SUGGESTION:{"rule":"..."}] do texto, se houver."""
    match = re.search(r'\[SUGGESTION:(\{"rule":"[^"]*"\})\]', text)
    if not match:
        return text.strip(), None
    try:
        data = json.loads(match.group(1))
        rule = data.get("rule")
    except json.JSONDecodeError:
        rule = None
    cleaned = re.sub(r'\[SUGGESTION:\{"rule":"[^"]*"\}\]', "", text).strip()
    return cleaned, rule


# ── Gemini provider ─────────────────────────────────────────────────────────


def _normalize_history(history: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Gemini exige que a conversa alterne user/model e comece com user.
    Remove duplicatas seguidas (ex: 2 assistants em sequência) e dropa
    assistants iniciais que sobraram de outras sessões.
    """
    out = []
    for m in history:
        if not out and m["role"] != "user":
            continue
        if out and out[-1]["role"] == m["role"]:
            # mescla mensagens consecutivas do mesmo role
            out[-1] = {**out[-1], "content": out[-1]["content"] + "\n\n" + m["content"]}
        else:
            out.append(m)
    return out


def _call_gemini(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _offline_reply()

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    model = os.getenv("QUEEN_MODEL", "gemini-2.5-flash")

    clean_history = _normalize_history(history)

    contents = []
    for m in clean_history:
        role = "model" if m["role"] == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part(text=m["content"])]))
    contents.append(types.Content(role="user", parts=[types.Part(text=user_message)]))

    last_error = None
    for attempt in range(2):  # 1 tentativa + 1 retry
        try:
            response = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    max_output_tokens=800,
                    temperature=0.8,
                ),
            )
            text = (response.text or "").strip()
            if text:
                if attempt > 0:
                    logger.info(f"Gemini call succeeded on retry {attempt}")
                return text
            # Resposta vazia — provavelmente safety block ou MAX_TOKENS
            finish = response.candidates[0].finish_reason if response.candidates else "UNKNOWN"
            logger.warning(f"Gemini empty response, finish_reason={finish}, history_len={len(clean_history)}")
            last_error = f"empty response (finish_reason={finish})"
        except Exception as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            logger.error(f"Gemini call failed (attempt {attempt + 1}/2): {last_error}")
            if attempt == 0:
                time.sleep(0.8)  # backoff curto antes do retry

    logger.error(f"Gemini call failed both attempts. Last error: {last_error}")
    return _offline_reply(error=True)


# ── Anthropic provider (futuro) ─────────────────────────────────────────────


def _call_anthropic(system_prompt: str, history: List[Dict[str, str]], user_message: str) -> str:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return _offline_reply()
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        model = os.getenv("QUEEN_MODEL", "claude-haiku-4-5")
        messages = [{"role": m["role"], "content": m["content"]} for m in history]
        messages.append({"role": "user", "content": user_message})
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=800,
        )
        return response.content[0].text.strip()
    except Exception as exc:
        logger.error(f"Anthropic call failed: {exc}")
        return _offline_reply(error=True)


# ── Fallback ────────────────────────────────────────────────────────────────


def _offline_reply(error: bool = False) -> str:
    if error:
        return "Hmm, my line just dropped — give me a sec and try again?"
    return "Hey! Queen here. I'm not fully connected yet — my AI provider isn't configured. Once Gabriel sets the API key I'll be ready to chat."


# ── Public ──────────────────────────────────────────────────────────────────


def is_error_reply(text: str) -> bool:
    """Detecta se a resposta veio do fallback de erro (não deve ser persistida)."""
    return text in (_offline_reply(), _offline_reply(error=True))


def ask_queen(
    user_message: str,
    history: List[Dict[str, str]],
    training_notes: List[str],
) -> Tuple[str, Optional[str]]:
    """
    Recebe a nova msg do usuário + histórico + training notes.
    Retorna (texto_resposta_limpo, sugestao_de_regra_ou_None).
    Histórico no formato: [{"role": "user"|"assistant", "content": "..."}]
    """
    # Filtra do histórico mensagens de erro antigas (não devem voltar pra IA)
    history = [m for m in history if not (m["role"] == "assistant" and is_error_reply(m["content"]))]

    system_prompt = _build_system_prompt(training_notes)
    provider = _provider()

    if provider == "anthropic":
        raw = _call_anthropic(system_prompt, history, user_message)
    else:
        raw = _call_gemini(system_prompt, history, user_message)

    cleaned, suggestion = _extract_suggestion(raw)
    return cleaned, suggestion
