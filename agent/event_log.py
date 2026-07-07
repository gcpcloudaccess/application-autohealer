import threading
from collections import deque
from datetime import datetime, timezone


class EventLog:
    def __init__(self, maxlen: int = 200):
        self._events = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def add(self, agent: str, step: str, message: str, **meta) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "step": step,
            "message": message,
            **meta,
        }
        with self._lock:
            self._events.append(entry)

    def recent(self, limit: int = 100) -> list[dict]:
        with self._lock:
            items = list(self._events)[-limit:]
        return list(reversed(items))
