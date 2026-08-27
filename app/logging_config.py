"""
app/logging_config.py
─────────────────────
Structured JSON logging via structlog.
• Outputs JSON in production (Vercel) for log aggregators.
• Sanitizes / masks all session cookies from every log record.
• Attaches trace_id context so requests can be correlated end-to-end.
"""

import logging
import uuid
from contextvars import ContextVar

import structlog

# ── Context variable: set once per request ────────────────────────────────────
_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

_SENSITIVE_KEYS = frozenset({"li_at", "jsessionid", "cookie", "authorization"})


def _mask_sensitive(logger, method, event_dict):  # noqa: ARG001
    """Structlog processor: replace sensitive values with '***REDACTED***'."""
    for key in list(event_dict.keys()):
        if key.lower() in _SENSITIVE_KEYS:
            event_dict[key] = "***REDACTED***"
    return event_dict


def _inject_trace_id(logger, method, event_dict):  # noqa: ARG001
    """Structlog processor: inject current request trace_id."""
    event_dict.setdefault("trace_id", _trace_id_var.get() or "no-trace")
    return event_dict


def configure_logging(log_level: str = "INFO") -> None:
    """
    Call once at application startup.
    Configures structlog for JSON output with cookie sanitization.
    """
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        _inject_trace_id,
        _mask_sensitive,
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(log_level)
        ),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processor=structlog.processors.JSONRenderer(),
        foreign_pre_chain=shared_processors,
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)


def new_trace_id() -> str:
    """Generate and store a fresh trace ID for the current async context."""
    tid = uuid.uuid4().hex
    _trace_id_var.set(tid)
    return tid


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Return a structlog logger bound to *name*."""
    return structlog.get_logger(name)
