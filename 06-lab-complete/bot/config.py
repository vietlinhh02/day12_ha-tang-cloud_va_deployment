from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_channel_ids() -> list[int]:
    raw = os.environ.get("TARGET_CHANNEL_IDS", "")
    if raw:
        return [int(cid.strip()) for cid in raw.split(",") if cid.strip()]
    single = os.environ.get("TARGET_CHANNEL_ID", "")
    if single:
        return [int(cid.strip()) for cid in single.split(",") if cid.strip()]
    return []


@dataclass(frozen=True)
class Settings:
    discord_token: str = field(default_factory=lambda: os.environ["DISCORD_TOKEN"])
    deepseek_api_key: str = field(default_factory=lambda: os.environ["DEEPSEEK_API_KEY"])
    deepseek_base_url: str = field(
        default_factory=lambda: os.environ.get(
            "DEEPSEEK_BASE_URL", "https://opencode.ai/zen/go/v1/chat/completions"
        )
    )
    target_channel_ids: list[int] = field(
        default_factory=lambda: _parse_channel_ids()
    )
    instructor_ids: list[str] = field(
        default_factory=lambda: [
            uid.strip()
            for uid in os.environ.get("INSTRUCTOR_IDS", "").split(",")
            if uid.strip()
        ]
    )
    model: str = "deepseek-v4-flash"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    corrections_file: str = "corrections.json"
    agent_max_steps: int = 5
    chunk_size: int = 1500
    chunk_overlap: int = 200
    top_k: int = 5
    relevance_threshold: float = 0.01
    auto_delete_seconds: int = field(
        default_factory=lambda: int(os.environ.get("AUTO_DELETE_SECONDS", "60"))
    )
    history_limit: int = field(
        default_factory=lambda: int(os.environ.get("HISTORY_LIMIT", "5000"))
    )
