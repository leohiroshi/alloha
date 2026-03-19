"""
Scheduled ingest runner.

Example:
  python -m app.ingest_runner
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys

from app.services.ingest_service import ingest_service


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def _run() -> int:
    result = await ingest_service.run(force_full=False)
    logger.info("Ingest result: %s", json.dumps(result.__dict__, ensure_ascii=False))
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(_run()))
