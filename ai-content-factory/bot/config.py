from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class BotConfig:
    bot_token: str
    api_base_url: str
    whitelist: set[int]

    @classmethod
    def from_env(cls) -> "BotConfig":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is required")

        api_base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
        raw_ids = os.getenv("TELEGRAM_WHITELIST", "")
        whitelist = {
            int(item.strip())
            for item in raw_ids.split(",")
            if item.strip()
        }
        return cls(bot_token=token, api_base_url=api_base_url.rstrip("/"), whitelist=whitelist)
