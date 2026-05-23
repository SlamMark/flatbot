import asyncio
import logging

from flatbot.config import settings
from flatbot.logging_conf import configure_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    configure_logging(settings.log_level)
    logger.info("FlatBot bot service started (stub — full implementation in F7)")
    # PTB application setup goes here in F7
    await asyncio.Event().wait()


if __name__ == "__main__":
    asyncio.run(main())
