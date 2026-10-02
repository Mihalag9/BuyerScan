from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    gigachat_credentials: str = os.getenv("GIGACHAT_CREDENTIALS", "").strip()
    gigachat_scope: str = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS").strip()
    gigachat_model: str = os.getenv("GIGACHAT_MODEL", "GigaChat-2-Pro").strip()
    gigachat_base_url: str = os.getenv("GIGACHAT_BASE_URL", "https://api.giga.chat/v1").strip()
    gigachat_verify_ssl: bool = _bool("GIGACHAT_VERIFY_SSL", False)

    analytics_url: str = os.getenv("ANALYTICS_URL", "http://127.0.0.1:5177").strip().rstrip("/")
    analytics_timeout: float = float(os.getenv("ANALYTICS_TIMEOUT", "180"))

    render_url: str = os.getenv("RENDER_URL", "http://127.0.0.1:5178").strip().rstrip("/")
    render_timeout: float = float(os.getenv("RENDER_TIMEOUT", "120"))

    port: int = int(os.getenv("PORT", "5000"))

    def validate(self) -> None:
        if not self.gigachat_credentials:
            raise RuntimeError(
                "GIGACHAT_CREDENTIALS не задан. Заполни .env: "
                "base64(client_id:client_secret)."
            )


settings = Settings()