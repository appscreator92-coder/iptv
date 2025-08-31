import logging

log_format = "[%(asctime)s] %(levelname)-8s %(message)-70s %(filename)s:%(lineno)d"

colors = {
    "DEBUG": "\033[37m",
    "INFO": "\033[32m",
    "WARNING": "\033[33m",
    "ERROR": "\033[31m",
    "CRITICAL": "\033[41m",
    "reset": "\033[0m",
}


class ColorFormatter(logging.Formatter):
    def format(self, record) -> str:
        color = colors.get(record.levelname, "")

        record.levelname = f"{color}{record.levelname}{colors['reset']}"

        return super().format(record)


def get_logger(name: str = __name__) -> logging.Logger:
    logger = logging.getLogger(name)

    if not logger.hasHandlers():
        handler = logging.StreamHandler()

        formatter = ColorFormatter(log_format, datefmt="%Y-%m-%d | %H:%M:%S")

        handler.setFormatter(formatter)

        logger.addHandler(handler)

        logger.setLevel(logging.INFO)

    return logger
