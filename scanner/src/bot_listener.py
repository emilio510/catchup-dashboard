from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import httpx

from src.config import ScannerConfig

logger = logging.getLogger(__name__)

AUTHORIZED_USER_ID = 1744950707
KNOWN_COMMANDS = {"scan"}
OFFSET_FILE = Path.home() / ".catchup-bot-offset"
POLL_INTERVAL = 30  # seconds


def is_authorized(user_id: int) -> bool:
    return user_id == AUTHORIZED_USER_ID


def parse_command(update: dict) -> str | None:
    message = update.get("message")
    if not message:
        return None

    text = message.get("text", "")
    if not text.startswith("/"):
        return None

    # Strip @botname suffix (e.g. /scan@akgbaambot -> scan)
    command = text.split()[0].lstrip("/").split("@")[0].lower()

    if command in KNOWN_COMMANDS:
        return command
    return None


def read_offset() -> int:
    try:
        return int(OFFSET_FILE.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_offset(offset: int) -> None:
    OFFSET_FILE.write_text(str(offset))


async def send_bot_message(bot_token: str, chat_id: int, text: str) -> bool:
    async with httpx.AsyncClient(timeout=10.0) as http:
        try:
            resp = await http.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
            )
            if not resp.is_success:
                logger.error("Bot API error: status %d", resp.status_code)
            return resp.is_success
        except httpx.HTTPError:
            logger.error("HTTP error sending bot message")
            return False


async def run_scan(config_path: Path) -> tuple[bool, str]:
    """Run the scanner as a subprocess. Returns (success, summary_message)."""
    cmd = [sys.executable, "-m", "src.cli", "--config", str(config_path)]
    logger.info("Starting scan subprocess")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=str(config_path.parent),
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode == 0:
        return True, "Scan complete. Check the dashboard for results."
    else:
        error_tail = stderr.decode()[-500:] if stderr else "No error output"
        return False, f"Scan failed (exit code {proc.returncode}).\n{error_tail}"


async def poll_loop(config: ScannerConfig, config_path: Path) -> None:
    bot_token = config.output.digest_bot_token
    if not bot_token:
        logger.error("DIGEST_BOT_TOKEN not configured, cannot start bot listener")
        return

    offset = read_offset()
    scan_in_progress = False

    logger.info("Bot listener started (polling every %ds, offset=%d)", POLL_INTERVAL, offset)

    async with httpx.AsyncClient(timeout=30.0) as http:
        while True:
            try:
                try:
                    resp = await http.get(
                        f"https://api.telegram.org/bot{bot_token}/getUpdates",
                        params={"offset": offset, "timeout": 20},
                    )
                except httpx.HTTPError:
                    logger.error("HTTP error polling for updates")
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                if not resp.is_success:
                    logger.error("getUpdates error: status %d", resp.status_code)
                    await asyncio.sleep(POLL_INTERVAL)
                    continue

                data = resp.json()
                updates = data.get("result", [])

                for update in updates:
                    offset = update["update_id"] + 1
                    write_offset(offset)

                    message = update.get("message")
                    if not message:
                        continue

                    user_id = message.get("from", {}).get("id")
                    chat_id = message.get("chat", {}).get("id")

                    if not is_authorized(user_id):
                        logger.warning("Unauthorized user %s attempted command", user_id)
                        continue

                    command = parse_command(update)
                    if command == "scan":
                        if scan_in_progress:
                            await send_bot_message(bot_token, chat_id, "Scan already in progress.")
                            continue

                        await send_bot_message(bot_token, chat_id, "Starting scan...")
                        scan_in_progress = True
                        try:
                            success, summary = await run_scan(config_path)
                            await send_bot_message(bot_token, chat_id, summary)
                        except Exception:
                            logger.exception("Scan failed")
                            await send_bot_message(bot_token, chat_id, "Scan error. Check logs.")
                        finally:
                            scan_in_progress = False

            except Exception:
                logger.exception("Poll loop error")

            await asyncio.sleep(POLL_INTERVAL)


async def async_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Telegram bot listener for on-demand scans")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    config_path = args.config.resolve()
    config = ScannerConfig.from_yaml(config_path)
    await poll_loop(config, config_path)


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
