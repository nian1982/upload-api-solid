import logging
import os
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv(usecwd=True))

_LOG_DIR = os.getenv("LOG_DIR") or "logs"
_ENV = (os.getenv("APP_ENV") or "development").lower()
_LOG_LEVEL = (os.getenv("LOG_LEVEL") or "INFO").upper()

_ROOT_PACKAGE = os.getenv("ROOT_PACKAGE") or "solid"
_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

os.makedirs(_LOG_DIR, exist_ok=True)
_FILE_HANDLER = TimedRotatingFileHandler(
    filename=Path(_LOG_DIR) / "app.log",
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8",
)
_FILE_HANDLER.setFormatter(logging.Formatter(_FORMAT, _DATEFMT))
_FILE_HANDLER.setLevel(_LOG_LEVEL)


class _Logger:

    def __init__(self, name: str = "solid"):
        self._name = name
        self._loggers: dict[str, logging.Logger] = {}

    def __call__(self, name: str | None = None) -> logging.Logger:
        if name is None:
            frame = sys._getframe(1)
            name = frame.f_globals.get("__name__", self._name)
            if name.startswith(f"{_ROOT_PACKAGE}."):
                name = name.removeprefix(f"{_ROOT_PACKAGE}.")
        key = name
        if key in self._loggers:
            return self._loggers[key]

        logger = logging.getLogger(key)
        logger.setLevel(_LOG_LEVEL)
        logger.handlers.clear()

        formatter = logging.Formatter(_FORMAT, _DATEFMT)

        console = logging.StreamHandler(sys.stdout)
        console.setFormatter(formatter)
        if _ENV == "production":
            console.setLevel(logging.ERROR)
        else:
            console.setLevel(_LOG_LEVEL)
        logger.addHandler(console)

        logger.addHandler(_FILE_HANDLER)

        logger.propagate = False
        self._loggers[key] = logger
        return logger


log = _Logger()

__all__ = ["log"]
