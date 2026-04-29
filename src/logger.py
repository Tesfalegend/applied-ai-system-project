import logging
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "agent.log")

os.makedirs(LOG_DIR, exist_ok=True)

_fmt = "%(asctime)s | %(levelname)s | %(step)s | %(message)s"
_datefmt = "%Y-%m-%dT%H:%M:%S"

_logger = logging.getLogger("agent")
_logger.setLevel(logging.DEBUG)

if not _logger.handlers:
    _fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    _fh.setFormatter(logging.Formatter(_fmt, datefmt=_datefmt))
    _logger.addHandler(_fh)

    _ch = logging.StreamHandler()
    _ch.setFormatter(logging.Formatter(_fmt, datefmt=_datefmt))
    _logger.addHandler(_ch)


def _log(level: str, step: str, message: str) -> None:
    extra = {"step": step}
    if level == "INFO":
        _logger.info(message, extra=extra)
    elif level == "WARN":
        _logger.warning(message, extra=extra)
    elif level == "ERROR":
        _logger.error(message, extra=extra)


def info(step: str, message: str) -> None:
    _log("INFO", step, message)


def warn(step: str, message: str) -> None:
    _log("WARN", step, message)


def error(step: str, message: str) -> None:
    _log("ERROR", step, message)
