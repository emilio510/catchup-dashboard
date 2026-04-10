from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from telethon import TelegramClient
from telethon.tl.types import User, Chat, Channel

from src.config import ScannerConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DialogInfo:
    chat_id: int
    name: str
    is_channel: bool
    is_bot: bool
    last_message_sender_is_me: bool
    last_message_date: datetime | None


@dataclass(frozen=True)
class ChatMessage:
    sender_name: str
    sender_id: int
    text: str
    date: datetime
    message_id: int
    is_me: bool

    def format(self) -> str:
        tag = " (me)" if self.is_me else ""
        ts = self.date.strftime("%Y-%m-%d %H:%M")
        return f"[{ts}] {self.sender_name}{tag}: {self.text}"


@dataclass(frozen=True)
class ConversationData:
    dialog: DialogInfo
    messages: list[ChatMessage]
    chat_type: str  # "dm" or "group"


def should_filter_dialog(dialog: DialogInfo, config: ScannerConfig) -> bool:
    if config.is_blacklisted(dialog.name):
        return True
    if dialog.is_channel:
        return True
    if dialog.is_bot and dialog.name not in config.telegram.bot_whitelist:
        return True
    if dialog.last_message_sender_is_me:
        return True
    return False


class TelegramReader:
    def __init__(self, config: ScannerConfig) -> None:
        self._config = config
        self._client: TelegramClient | None = None
        self._me_id: int | None = None
        self._me_name: str = "Me"

    @property
    def me_name(self) -> str:
        return self._me_name

    async def connect(self) -> None:
        self._client = TelegramClient(
            self._config.telegram.session_name,
            self._config.telegram.api_id,
            self._config.telegram.api_hash,
        )
        await self._client.start()
        me = await self._client.get_me()
        self._me_id = me.id
        self._me_name = me.first_name or "Me"
        logger.info("Connected as %s (ID: %s)", me.first_name, me.id)

    async def send_to_saved_messages(self, text: str) -> None:
        assert self._client is not None
        await self._client.send_message("me", text)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()

    async def list_dialogs(self) -> list[DialogInfo]:
        assert self._client is not None
        dialogs = []
        async for d in self._client.iter_dialogs():
            entity = d.entity
            is_channel = isinstance(entity, Channel) and entity.broadcast
            is_bot = isinstance(entity, User) and bool(entity.bot)

            last_msg = d.message
            last_sender_is_me = (
                last_msg is not None and last_msg.sender_id == self._me_id
            )
            last_date = last_msg.date if last_msg else None

            dialogs.append(
                DialogInfo(
                    chat_id=d.id,
                    name=d.name or str(d.id),
                    is_channel=is_channel,
                    is_bot=is_bot,
                    last_message_sender_is_me=last_sender_is_me,
                    last_message_date=last_date,
                )
            )
        return dialogs

    async def filter_dialogs(
        self, dialogs: list[DialogInfo]
    ) -> tuple[list[DialogInfo], int]:
        kept = [d for d in dialogs if not should_filter_dialog(d, self._config)]

        # Apply max_dialogs limit (most recently active first)
        max_dialogs = self._config.scan.max_dialogs
        if max_dialogs is not None and len(kept) > max_dialogs:
            kept.sort(
                key=lambda d: d.last_message_date or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            kept = kept[:max_dialogs]
        filtered_count = len(dialogs) - len(kept)
        logger.info(
            "Filtered %d/%d dialogs (kept %d)",
            filtered_count, len(dialogs), len(kept),
        )
        return kept, filtered_count

    async def deep_read(self, dialog: DialogInfo) -> ConversationData:
        assert self._client is not None
        cutoff = datetime.now(timezone.utc) - timedelta(
            days=self._config.scan.window_days
        )
        messages: list[ChatMessage] = []

        async for msg in self._client.iter_messages(
            dialog.chat_id,
            limit=self._config.scan.messages_per_chat,
            offset_date=cutoff,
            reverse=True,
        ):
            if not msg.text:
                continue
            sender_name = "unknown"
            sender_id = msg.sender_id or 0
            if msg.sender:
                if isinstance(msg.sender, User):
                    parts = [msg.sender.first_name or "", msg.sender.last_name or ""]
                    sender_name = " ".join(p for p in parts if p) or str(sender_id)
                elif isinstance(msg.sender, (Chat, Channel)):
                    sender_name = msg.sender.title or str(sender_id)

            messages.append(
                ChatMessage(
                    sender_name=sender_name,
                    sender_id=sender_id,
                    text=msg.text,
                    date=msg.date,
                    message_id=msg.id,
                    is_me=sender_id == self._me_id,
                )
            )

        entity = await self._client.get_entity(dialog.chat_id)
        chat_type = "dm" if isinstance(entity, User) else "group"

        return ConversationData(
            dialog=dialog, messages=messages, chat_type=chat_type
        )

    async def read_all(self) -> tuple[list[ConversationData], int, int]:
        all_dialogs = await self.list_dialogs()
        kept, filtered_count = await self.filter_dialogs(all_dialogs)

        conversations = []
        for dialog in kept:
            try:
                conv = await self.deep_read(dialog)
                if conv.messages:
                    conversations.append(conv)
            except Exception:
                logger.exception("Failed to read dialog: %s", dialog.name)

        return conversations, len(all_dialogs), filtered_count
