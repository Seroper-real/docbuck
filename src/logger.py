import logging,sys

from config import LOG_FORMAT, LOG_DATEFMT, LOG_LEVEL, LOG_LEVEL_CORTEX, LOG_ONELINE, LOG_LEVEL_CHAIN


class _OneLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        return msg.replace("\n", "\\n")


def setup_logger() -> None:
    """Configure the root logger and specialized loggers using config settings."""
    handler = logging.StreamHandler(sys.stdout)
    formatter = _OneLineFormatter(LOG_FORMAT, datefmt=LOG_DATEFMT) if LOG_ONELINE else logging.Formatter(LOG_FORMAT,datefmt=LOG_DATEFMT)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.ERROR))
    root_logger.addHandler(handler)

    logging.getLogger("httpx").setLevel(logging.WARNING)

    cortex_logger = logging.getLogger("cortex")
    cortex_logger.setLevel(getattr(logging, LOG_LEVEL_CORTEX.upper(), logging.ERROR))
    cortex_logger = logging.getLogger("chain")
    cortex_logger.setLevel(getattr(logging, LOG_LEVEL_CHAIN.upper(), logging.ERROR))
