"""Telemetry scaffolding for CaseyOS."""
from typing import Any, Dict
from datetime import datetime
import json

from src.logger import get_logger

_logger = get_logger("telemetry")


async def log_event(event: str, properties: Dict[str, Any]) -> None:
    payload = {
        "event": event,
        "timestamp": datetime.utcnow().isoformat(),
        "properties": properties,
    }
    _logger.info(json.dumps(payload))
