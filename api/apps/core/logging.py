from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

_SENSITIVE = ("password", "token", "secret", "authorization", "credential")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "context", None)
        if isinstance(extra, dict):
            payload["context"] = {
                k: v for k, v in extra.items()
                if not any(s in k.lower() for s in _SENSITIVE)
            }
        return json.dumps(payload, default=str)
