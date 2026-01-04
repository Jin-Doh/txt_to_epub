import logging


class ExtraFieldFormatter(logging.Formatter):
    """Custom formatter that includes extra fields in the log output."""

    def format(self, record: logging.LogRecord) -> str:
        # Format the basic message first
        formatted = super().format(record)

        # Attributes that are considered part of the standard LogRecord
        standard_attrs = {
            "name",
            "msg",
            "args",
            "levelname",
            "levelno",
            "pathname",
            "filename",
            "module",
            "exc_info",
            "exc_text",
            "stack_info",
            "lineno",
            "funcName",
            "created",
            "msecs",
            "relativeCreated",
            "thread",
            "threadName",
            "processName",
            "process",
            "message",
            "asctime",
        }

        # Collect extra fields (anything not in standard_attrs)
        extras = {
            k: v
            for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_") and v is not None
        }
        if extras:
            # Append a readable representation of extras, sorted by key for stable output
            extra_parts = ", ".join(f"{k}={v!r}" for k, v in sorted(extras.items()))
            formatted = f"{formatted} | extra: {extra_parts}"
        return formatted


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Set up and return a logger with the specified name and level.
    The formatter will include any extra fields passed via the `extra` kwarg
    (e.g. logger.info("msg", extra={"user_id": 123}))."""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.hasHandlers():
        ch = logging.StreamHandler()
        ch.setLevel(level)

        formatter = ExtraFieldFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        ch.setFormatter(formatter)

        logger.addHandler(ch)

    return logger


if __name__ == "__main__":
    # Example usage
    _logger = setup_logger("my_logger", logging.DEBUG)
    _logger.info("This is an info message", extra={"user_id": 42, "operation": "test"})
    _logger.debug("This is a debug message", extra={"debug_mode": True})
