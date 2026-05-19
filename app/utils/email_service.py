"""
Camada de envio de emails via Resend.

Configuração via env:
- RESEND_API_KEY: chave do Resend
- FROM_EMAIL: remetente (ex: "English Hive <onboarding@resend.dev>")
- FRONTEND_URL: usado para montar links nos emails

Se RESEND_API_KEY não estiver setada, os emails são logados no console
em vez de enviados — útil pra dev local sem fazer chamada externa.
"""
import os
import logging
from typing import Optional

import resend

logger = logging.getLogger(__name__)

_FROM_DEFAULT = "English Hive <onboarding@resend.dev>"


def _configured() -> bool:
    key = os.getenv("RESEND_API_KEY")
    if not key:
        return False
    resend.api_key = key
    return True


def _from_email() -> str:
    return os.getenv("FROM_EMAIL", _FROM_DEFAULT)


def _frontend_url() -> str:
    return os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")


def _send(to: str, subject: str, html: str) -> Optional[str]:
    """Retorna o id do email enviado ou None se modo dev (sem API key)."""
    if not _configured():
        logger.warning("RESEND_API_KEY não configurada — email NÃO enviado.")
        logger.info(f"[DEV-EMAIL] to={to} | subject={subject}\n{html}")
        return None
    try:
        result = resend.Emails.send({
            "from": _from_email(),
            "to": [to],
            "subject": subject,
            "html": html,
        })
        return result.get("id")
    except Exception as exc:
        logger.error(f"Falha ao enviar email para {to}: {exc}")
        return None


# ── Templates ────────────────────────────────────────────────────────────────


def _wrap(body_html: str) -> str:
    """Envolve o body num shell de email com header e footer."""
    return f"""<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:'Helvetica Neue',Arial,sans-serif;color:#f0ece4;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#0a0a0a;">
    <tr>
      <td align="center" style="padding:32px 16px;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#13131a;border:1px solid #2a2a35;border-radius:8px;overflow:hidden;">
          <tr>
            <td style="padding:24px 32px;border-bottom:1px solid #2a2a35;">
              <span style="font-size:14px;letter-spacing:0.18em;text-transform:uppercase;color:#f3c969;font-weight:700;">English Hive</span>
            </td>
          </tr>
          <tr>
            <td style="padding:32px;color:#d8d4cc;font-size:15px;line-height:1.65;">
              {body_html}
            </td>
          </tr>
          <tr>
            <td style="padding:20px 32px;border-top:1px solid #2a2a35;color:#7c7c89;font-size:12px;line-height:1.5;">
              Methodology GN · Professor Giordine<br/>
              Se você não esperava este email, ignore-o.
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_welcome_email(
    to: str,
    nome: str,
    username: str,
    senha_temporaria: str,
) -> Optional[str]:
    login_url = f"{_frontend_url()}/portal"
    body = f"""
      <h1 style="font-family:'Georgia',serif;font-size:24px;color:#f0ece4;margin:0 0 16px;">Bem-vindo(a) à colmeia, {nome.split(' ')[0]}.</h1>
      <p>Seu acesso ao portal do aluno foi criado pelo Professor Giordine.</p>
      <p style="margin:24px 0;padding:16px 20px;background:rgba(243,201,105,0.08);border:1px solid rgba(243,201,105,0.25);border-radius:6px;">
        <strong style="color:#f0ece4;display:block;margin-bottom:8px;">Suas credenciais:</strong>
        <span style="display:block;margin:4px 0;">Usuário: <code style="background:#0a0a0a;padding:2px 6px;border-radius:3px;color:#f3c969;">{username}</code></span>
        <span style="display:block;margin:4px 0;">Senha temporária: <code style="background:#0a0a0a;padding:2px 6px;border-radius:3px;color:#f3c969;">{senha_temporaria}</code></span>
      </p>
      <p>Recomendamos trocar a senha após o primeiro acesso. Você pode fazer isso em <em>Perfil → Alterar senha</em>.</p>
      <p style="margin:28px 0;">
        <a href="{login_url}" style="display:inline-block;padding:12px 24px;background:#f3c969;color:#0a0a0a;text-decoration:none;border-radius:4px;font-weight:700;letter-spacing:0.04em;">Acessar o portal</a>
      </p>
      <p style="color:#8a8a9a;font-size:13px;margin-top:24px;">Qualquer dúvida, responda este email ou fale com o professor pelo WhatsApp.</p>
    """
    return _send(to, "Acesso ao portal · English Hive", _wrap(body))


def send_password_reset_email(
    to: str,
    nome: str,
    token: str,
    expires_in_hours: int = 1,
) -> Optional[str]:
    reset_url = f"{_frontend_url()}/portal/redefinir-senha/{token}"
    body = f"""
      <h1 style="font-family:'Georgia',serif;font-size:24px;color:#f0ece4;margin:0 0 16px;">Redefinição de senha</h1>
      <p>Olá, {nome.split(' ')[0]}.</p>
      <p>Recebemos uma solicitação para redefinir a senha do seu acesso ao portal. Para criar uma nova senha, clique no botão abaixo:</p>
      <p style="margin:28px 0;">
        <a href="{reset_url}" style="display:inline-block;padding:12px 24px;background:#f3c969;color:#0a0a0a;text-decoration:none;border-radius:4px;font-weight:700;letter-spacing:0.04em;">Redefinir senha</a>
      </p>
      <p style="color:#8a8a9a;font-size:13px;">Este link expira em {expires_in_hours} hora{'s' if expires_in_hours != 1 else ''}.</p>
      <p style="color:#8a8a9a;font-size:13px;margin-top:24px;">Se você não solicitou a redefinição, pode ignorar este email — sua senha continua a mesma.</p>
    """
    return _send(to, "Redefinir senha · English Hive", _wrap(body))
