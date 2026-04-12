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
    database_url: str | None = None
    dashboard_url: str | None = None
    digest_chat_id: int | None = None
    digest_bot_token: str | None = None  # Bot API token for sending digest AS the bot


class CalendarConfig(BaseModel):
    enabled: bool = False
    credentials_path: str = "credentials.json"
    token_path: str = "token.json"
    days_ahead: int = 7


class EscalationConfig(BaseModel):
    P0: int | None = 24   # hours before reminder, None = no reminder
    P1: int | None = 48
    P2: int | None = None
    P3: int | None = None


class ScannerConfig(BaseModel):
    scan: ScanConfig = Field(default_factory=ScanConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    classification: ClassificationConfig = Field(default_factory=ClassificationConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    calendar: CalendarConfig = Field(default_factory=CalendarConfig)
    escalation: EscalationConfig = Field(default_factory=EscalationConfig)

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

        output_data = data.get("output", {})
        db_url = os.environ.get("DATABASE_URL", "")
        if db_url:
            output_data["database_url"] = db_url
        bot_token = os.environ.get("DIGEST_BOT_TOKEN", "")
        if bot_token:
            output_data["digest_bot_token"] = bot_token
        data["output"] = output_data

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
