"""
Rate limiting via slowapi (in-memory).

Para múltiplas instâncias (escalar horizontal no futuro), trocar pra Redis backend.
Por enquanto, in-memory cobre 1 instância na Render Starter — suficiente pra 100-300 alunos.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Chave: IP do cliente. Se atrás de proxy (Render), respeita X-Forwarded-For.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # baseline conservador, evita scraping
)
