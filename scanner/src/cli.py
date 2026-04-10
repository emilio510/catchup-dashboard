from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

from src.config import ScannerConfig
from src.scanner import Scanner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Catch-up Dashboard Scanner -- scan Telegram for unanswered messages"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config.yaml"),
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=None,
        help="Override scan window in days (default: from config)",
    )
    parser.add_argument(
        "--no-digest",
        action="store_true",
        help="Skip sending Telegram digest",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Override output JSON path",
    )
    parser.add_argument(
        "--max-dialogs",
        type=int,
        default=None,
        help="Limit number of dialogs to scan (most recently active first)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def async_main() -> None:
    args = parse_args()

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    config = ScannerConfig.from_yaml(args.config)

    # Apply CLI overrides (immutable)
    if args.window_days is not None:
        config = config.model_copy(
            update={"scan": config.scan.model_copy(update={"window_days": args.window_days})}
        )
    if args.no_digest:
        config = config.model_copy(
            update={"output": config.output.model_copy(update={"telegram_digest": False})}
        )
    if args.output is not None:
        config = config.model_copy(
            update={"output": config.output.model_copy(update={"json_file": str(args.output)})}
        )
    if args.max_dialogs is not None:
        config = config.model_copy(
            update={"scan": config.scan.model_copy(update={"max_dialogs": args.max_dialogs})}
        )

    scanner = Scanner(config)
    result = await scanner.run()

    print(f"\nScan complete: {result.stats.total} items found")
    print(f"  P0: {result.stats.by_priority.P0}")
    print(f"  P1: {result.stats.by_priority.P1}")
    print(f"  P2: {result.stats.by_priority.P2}")
    print(f"  P3: {result.stats.by_priority.P3}")
    print(f"\nResults saved to: {config.output.json_file}")


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
