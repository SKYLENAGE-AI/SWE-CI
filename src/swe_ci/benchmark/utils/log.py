import sys
import logging
from tqdm import tqdm
from pathlib import Path



def empty_logger(
        name: str,
        *,
        level: int = logging.INFO,
        propagate: bool = False,
        ) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate
    for h in list(logger.handlers):
        logger.removeHandler(h)
        h.close()
    return logger


def file_handler(
        filepath: str | Path,
        *,
        level: int = logging.INFO,
        fmt: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt: str = "%Y-%m-%d %H:%M:%S",
        encoding: str = "utf-8",
        mode: str = "a",
        ) -> logging.Handler:
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch(exist_ok=True)
    h = logging.FileHandler(path, mode=mode, encoding=encoding)
    h.setLevel(level)
    h.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    return h


def console_handler(
        *,
        level: int = logging.INFO,
        fmt: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt: str = "%H:%M:%S",
        stream=None,
        ) -> logging.Handler:
    if stream is None:
        stream = sys.stdout
    h = logging.StreamHandler(stream)
    h.setLevel(level)
    h.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    return h


class TqdmLoggingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        if tqdm is None:
            sys.stdout.write(msg + "\n")
        else:
            tqdm.write(msg)


def tqdm_handler(
        *,
        level: int = logging.INFO,
        fmt: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt: str = "%H:%M:%S",
        ) -> logging.Handler:
    h = TqdmLoggingHandler()
    h.setLevel(level)
    h.setFormatter(logging.Formatter(fmt=fmt, datefmt=datefmt))
    return h


def add_handler(
        logger: logging.Logger, 
        handler: logging.Handler
        ) -> None:
    if handler not in logger.handlers:
        logger.addHandler(handler)


def remove_handler(
        logger: logging.Logger, 
        handler: logging.Handler,
        ) -> None:
    if handler in logger.handlers:
        logger.removeHandler(handler)
        handler.close()
