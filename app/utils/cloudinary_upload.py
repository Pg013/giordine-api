import os

import cloudinary
import cloudinary.uploader

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return

    # Suporta CLOUDINARY_URL (formato url) ou variáveis separadas
    url = os.environ.get("CLOUDINARY_URL")
    if url:
        cloudinary.config(cloudinary_url=url)
    else:
        cloudinary.config(
            cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
            api_key=os.environ["CLOUDINARY_API_KEY"],
            api_secret=os.environ["CLOUDINARY_API_SECRET"],
        )

    _configured = True


def upload_foto_perfil(base64_data: str, user_id: int) -> str:
    _ensure_configured()
    result = cloudinary.uploader.upload(
        base64_data,
        folder="giordine/fotos_perfil",
        public_id=f"user_{user_id}",
        overwrite=True,
        resource_type="image",
        transformation=[
            {"width": 400, "height": 400, "crop": "fill", "gravity": "face"},
            {"fetch_format": "auto", "quality": "auto"},
        ],
    )
    return result["secure_url"]
