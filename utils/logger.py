"""
Logging utility for the video automation system
"""
import logging
import sys
import queue
import threading
from datetime import datetime
from typing import Optional
import contextvars

# Context variable used to tag every log line with the active session id
_session_context: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "video_automation_session_id", default=None
)


class SessionContextFilter(logging.Filter):
    """Attach session id from the current context to every log record."""

    def filter(self, record):
        record.session_id = _session_context.get()
        return True


class SessionLogBroadcaster:
    """
    Broadcast log records to listeners (used by the SSE endpoint for live logs).
    """

    def __init__(self):
        self._listeners = []
        self._lock = threading.Lock()

    def register_listener(self, session_id: Optional[str] = None):
        listener = {
            "queue": queue.Queue(maxsize=500),
            "session_id": session_id or None,
        }
        with self._lock:
            self._listeners.append(listener)
        return listener

    def unregister_listener(self, listener):
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def publish(self, payload):
        with self._lock:
            listeners = list(self._listeners)

        for listener in listeners:
            required_session = listener["session_id"]
            if required_session and payload.get("session_id") != required_session:
                continue
            q = listener["queue"]
            try:
                q.put_nowait(payload)
            except queue.Full:
                try:
                    q.get_nowait()
                except queue.Empty:
                    pass
                q.put_nowait(payload)


_broadcaster = SessionLogBroadcaster()


class BroadcastLogHandler(logging.Handler):
    """Custom handler that pushes formatted log lines to the broadcaster."""

    def emit(self, record):
        try:
            payload = {
                "session_id": getattr(record, "session_id", None),
                "level": record.levelname,
                "message": record.getMessage(),
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "formatted": self.format(record),
            }
            _broadcaster.publish(payload)
        except Exception:
            self.handleError(record)


def set_session_context(session_id: Optional[str]):
    """Set the active session id for downstream log entries."""
    _session_context.set(session_id)


def clear_session_context():
    """Reset the active session for log records."""
    _session_context.set(None)


def register_log_listener(session_id: Optional[str] = None):
    """Register a listener for live logs (used by SSE endpoint)."""
    return _broadcaster.register_listener(session_id)


def unregister_log_listener(listener):
    """Remove a previously registered listener."""
    _broadcaster.unregister_listener(listener)


def setup_logger(name="VideoAutomation", log_file=None):
    """
    Set up and return a logger with file, console, and broadcast handlers.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Avoid adding handlers multiple times
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger.addFilter(SessionContextFilter())

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    broadcast_handler = BroadcastLogHandler()
    broadcast_handler.setLevel(logging.INFO)
    broadcast_handler.setFormatter(formatter)
    logger.addHandler(broadcast_handler)

    return logger
