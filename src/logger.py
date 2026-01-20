"""Structured JSON logging configuration."""
import json
import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# Context variable for trace_id
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")


class TraceIDFilter(logging.Filter):
    """Add trace_id to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Add trace_id from context or generate new one."""
        trace_id = trace_id_var.get()
        if not trace_id:
            trace_id = str(uuid.uuid4())
            trace_id_var.set(trace_id)
        record.trace_id = trace_id
        return True


class SafeFormatter(logging.Formatter):
    """Formatter that handles missing fields gracefully."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format the record, adding trace_id if missing."""
        if not hasattr(record, 'trace_id'):
            record.trace_id = '-'
        return super().format(record)


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Configure structured logging."""
    if log_format == "json":
        # Configure structlog for JSON output
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.processors.JSONRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # Plain text logging
        structlog.configure(
            processors=[
                structlog.stdlib.filter_by_level,
                structlog.stdlib.add_logger_name,
                structlog.stdlib.add_log_level,
                structlog.stdlib.PositionalArgumentsFormatter(),
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.StackInfoRenderer(),
                structlog.processors.format_exc_info,
                structlog.processors.UnicodeDecoder(),
                structlog.dev.ConsoleRenderer(),
            ],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Add trace_id filter
    trace_filter = TraceIDFilter()
    root_logger.addFilter(trace_filter)

    # Add handler if not already present
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        if log_format == "json":
            formatter = SafeFormatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
                '"logger": "%(name)s", "trace_id": "%(trace_id)s", '
                '"message": "%(message)s", "module": "%(module)s"}'
            )
        else:
            formatter = SafeFormatter(
                "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)d] "
                "[trace_id=%(trace_id)s] %(message)s"
            )
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)


def get_logger(name: str) -> structlog.typing.FilteringBoundLogger:
    """Get a structlog logger instance."""
    return structlog.get_logger(name)


def set_trace_id(trace_id: str) -> None:
    """Set the trace_id for the current context."""
    trace_id_var.set(trace_id)


def get_trace_id() -> str:
    """Get the trace_id from the current context."""
    return trace_id_var.get()
