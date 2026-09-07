"""
Structured logging for AI Agent Bank.

Every log record gets a JSON shape with trace context injected from
``contextvars``:
    request_id, agent_id, task_id, transaction_request_id, decision

The request context is set per HTTP request by ``RequestContextMiddleware`` and
can also be set programmatically by long-running workers (agent runtime).

We do NOT log secrets or private keys — values are whitelisted by name.
"""

import json
import logging
from contextvars import ContextVar
from typing import Optional

# Context variables used to enrich every log line.
_request_id: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
_agent_id: ContextVar[Optional[str]] = ContextVar("agent_id", default=None)
_task_id: ContextVar[Optional[str]] = ContextVar("task_id", default=None)
_tx_request_id: ContextVar[Optional[str]] = ContextVar("tx_request_id", default=None)
_decision: ContextVar[Optional[str]] = ContextVar("decision", default=None)

_SAFE_FIELDS = (
    "request_id",
    "agent_id",
    "task_id",
    "transaction_request_id",
    "decision",
)


def set_trace_context(
    *,
    request_id: Optional[str] = None,
    agent_id: Optional[int] = None,
    task_id: Optional[int] = None,
    transaction_request_id: Optional[str] = None,
    decision: Optional[str] = None,
) -> None:
    if request_id is not None:
        _request_id.set(request_id)
    if agent_id is not None:
        _agent_id.set(str(agent_id))
    if task_id is not None:
        _task_id.set(str(task_id))
    if transaction_request_id is not None:
        _tx_request_id.set(transaction_request_id)
    if decision is not None:
        _decision.set(decision)


def reset_trace_context() -> None:
    _request_id.set(None)
    _agent_id.set(None)
    _task_id.set(None)
    _tx_request_id.set(None)
    _decision.set(None)


def _current_trace() -> dict:
    return {
        "request_id": _request_id.get(),
        "agent_id": _agent_id.get(),
        "task_id": _task_id.get(),
        "transaction_request_id": _tx_request_id.get(),
        "decision": _decision.get(),
    }


class TraceContextFilter(logging.Filter):
    """Attach trace context fields to every emitted log record."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003
        for field in _SAFE_FIELDS:
            setattr(record, field, _current_trace().get(field))
        return True


class JsonFormatter(logging.Formatter):
    """Serialize structured fields into a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _SAFE_FIELDS:
            value = getattr(record, field, None)
            if value:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: int = logging.INFO) -> None:
    """Install structured handlers on the root logger (idempotent)."""
    root = logging.getLogger()
    if getattr(root, "_aibank_configured", False):
        return
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    handler.addFilter(TraceContextFilter())
    root.handlers.clear()
    root.addHandler(handler)
    root._aibank_configured = True  # type: ignore[attr-defined]


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.addFilter(TraceContextFilter())
    return logger