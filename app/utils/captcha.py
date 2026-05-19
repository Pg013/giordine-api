"""
Validação de token Cloudflare Turnstile (CAPTCHA invisível).

Configurar no painel Cloudflare → Turnstile → Add site, então setar no .env:
    TURNSTILE_SECRET_KEY=0x4AAA...

Se TURNSTILE_SECRET_KEY não estiver setada, o validador SEMPRE retorna True
(modo dev — sem CAPTCHA). Em produção, basta setar a env var pra ativar.
"""
import os
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def turnstile_enabled() -> bool:
    return bool(os.getenv("TURNSTILE_SECRET_KEY"))


def verify_turnstile(token: Optional[str], remote_ip: Optional[str] = None) -> bool:
    """
    Valida o token do widget Turnstile (frontend) com a API do Cloudflare.

    Retorno:
    - True  se TURNSTILE não configurado (modo dev), OU se token é válido
    - False se TURNSTILE configurado mas token ausente/inválido
    """
    secret = os.getenv("TURNSTILE_SECRET_KEY")
    if not secret:
        return True  # CAPTCHA desativado

    if not token:
        return False

    try:
        payload = {"secret": secret, "response": token}
        if remote_ip:
            payload["remoteip"] = remote_ip
        with httpx.Client(timeout=8.0) as client:
            r = client.post(VERIFY_URL, data=payload)
        if r.status_code != 200:
            logger.warning(f"Turnstile siteverify HTTP {r.status_code}")
            return False
        data = r.json()
        return bool(data.get("success"))
    except Exception as exc:
        logger.error(f"Turnstile verify failed: {exc}")
        # Fail closed em produção, fail open em dev
        return False
