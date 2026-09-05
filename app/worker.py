import asyncio
import logging

from app.config import settings
from app.services.worker import run_once

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("social_studio.worker")


async def main():
    logger.info("Durable publishing worker started")
    while True:
        try:
            processed = await run_once()
        except Exception:
            logger.exception("Worker iteration failed")
            processed = False
        if not processed:
            await asyncio.sleep(settings.worker_poll_seconds)


if __name__ == "__main__":
    asyncio.run(main())
