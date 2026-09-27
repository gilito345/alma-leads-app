"""Entry point: `python -m app.worker`."""

import logging
import signal
import threading
from types import FrameType

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import get_sessionmaker
from app.services.email import build_email_sender
from app.worker.outbox import OutboxProcessor

logger = logging.getLogger("app.worker")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    sender = build_email_sender(settings)
    if not settings.resend_api_key:
        logger.warning("RESEND_API_KEY is not set: emails will be logged here, not delivered")

    processor = OutboxProcessor(get_sessionmaker(), sender, settings)
    stop = threading.Event()

    def request_stop(signum: int, _: FrameType | None) -> None:
        logger.info("Received signal %d, finishing current batch", signum)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)

    logger.info("Email worker started (poll every %ss)", settings.worker_poll_interval_seconds)
    while not stop.is_set():
        try:
            processed = processor.process_batch()
        except Exception:
            logger.exception("Outbox batch failed; will retry")
            processed = 0
        # Keep draining while there's a backlog; otherwise wait for the next poll.
        if processed < settings.worker_batch_size:
            stop.wait(settings.worker_poll_interval_seconds)
    logger.info("Email worker stopped")


if __name__ == "__main__":
    main()
