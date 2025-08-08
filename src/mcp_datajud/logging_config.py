from __future__ import annotations

import json
import logging
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record: Dict[str, Any] = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
        }
        # Extras comuns
        for key in ("tool_name", "params", "duration_ms"):
            value = getattr(record, key, None)
            if value is not None:
                log_record[key] = value
        return json.dumps(log_record, ensure_ascii=False)


def get_json_logger(name: str = "mcp_datajud", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
