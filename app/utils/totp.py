"""
TOTP (Time-based One-Time Password) — RFC 6238.
Compatível com Google Authenticator, Authy, 1Password, etc.
"""
import io
import base64
import pyotp
import qrcode

ISSUER = "English Hive"


def generate_secret() -> str:
    """Gera um segredo base32 (16 chars) pra TOTP."""
    return pyotp.random_base32()


def build_provisioning_uri(username: str, secret: str) -> str:
    """
    URI no formato otpauth:// que o app autenticador escaneia.
    Ex: otpauth://totp/English%20Hive:Gabriel.correa?secret=ABC123&issuer=English%20Hive
    """
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER)


def build_qr_data_url(provisioning_uri: str) -> str:
    """
    Gera o QR code em PNG e retorna como data URL (base64) pra exibir no <img>.
    """
    qr = qrcode.QRCode(box_size=8, border=2)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def verify_code(secret: str, code: str, window: int = 1) -> bool:
    """
    Valida um código de 6 dígitos.
    window=1 aceita o código atual + anterior + próximo (tolerância a clock drift).
    """
    if not secret or not code:
        return False
    try:
        return pyotp.TOTP(secret).verify(code.strip(), valid_window=window)
    except Exception:
        return False
