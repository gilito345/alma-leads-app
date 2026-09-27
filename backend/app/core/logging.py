import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    # Uvicorn's access log duplicates what a reverse proxy records; keep it quieter.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
