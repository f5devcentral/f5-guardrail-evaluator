import logging
import re

SENSITIVE_KEYS = {"authorization", "token", "api_key", "apikey", "password", "secret", "f5_token"}


def redact(value, token=""):
    """Preserve diagnostic structure while removing configured credentials."""
    if isinstance(value, dict):
        return {
            redact(str(k), token): "[REDACTED]" if str(k).lower() in SENSITIVE_KEYS else redact(v, token)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v, token) for v in value]
    if isinstance(value, str):
        if token:
            value = value.replace(token, "[REDACTED]")
        return re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
    return value


class RedactingFilter(logging.Filter):
    def __init__(self, token=""):
        super().__init__()
        self.token = token

    def filter(self, record):
        record.msg = redact(record.getMessage(), self.token)
        record.args = ()
        return True


def configure_logging():
    # HTTP debug logs can contain customer URLs; application logs contain IDs/counts only.
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.WARNING)
    logger = logging.getLogger("guardrail_evaluator")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.addFilter(RedactingFilter())
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
