from __future__ import annotations

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


load_dotenv()


class ScanConfig(BaseModel):
    window_days: int = 7
    messages_per_chat: int = 20
    batch_size: int = 5
    max_dialogs: int | None = None


class TelegramConfig(BaseModel):
    session_name: str = "akgemilio"
    blacklist: list[str] = Field(default_factory=list)
    bot_whitelist: list[str] = Field(default_factory=list)
    api_id: int = 0
    api_hash: str = ""


class ClassificationConfig(BaseModel):
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    rate_limit_rpm: int = 30
    user_context: str = ""
    api_key: str = ""


class OutputConfig(BaseModel):
    telegram_digest: bool = True
    json_file: str = "scan_results.json"


class ScannerConfig(BaseModel):
    scan: ScanConfig = Field(default_factory=ScanConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def from_yaml(cls, path: Path) -> ScannerConfig:
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        # Overlay env vars into data dict before construction
        telegram_data = data.get("telegram", {})
        telegram_data["api_id"] = int(os.environ.get("TELEGRAM_API_ID", "0"))
        telegram_data["api_hash"] = os.environ.get("TELEGRAM_API_HASH", "")
        data["telegram"] = telegram_data

        classification_data = data.get("classification", {})
        classification_data["api_key"] = os.environ.get("ANTHROPIC_API_KEY", "")
        data["classification"] = classification_data

        config = cls(**data)

        # Validate required secrets
        missing = []
        if not config.telegram.api_id:
            missing.append("TELEGRAM_API_ID")
        if not config.telegram.api_hash:
            missing.append("TELEGRAM_API_HASH")
        if not config.classification.api_key:
            missing.append("ANTHROPIC_API_KEY")
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return config

    def is_blacklisted(self, chat_name: str) -> bool:
        lower_name = chat_name.lower()
        return any(b.lower() == lower_name for b in self.telegram.blacklist)
