"""In-memory history of recent reviews (replace with a DB later if needed)."""
import threading
from collections import deque


class ReviewStore:
    def __init__(self, max_items: int = 50):
        self._items = deque(maxlen=max_items)
        self._lock = threading.Lock()

    def add(self, review: dict) -> None:
        with self._lock:
            self._items.appendleft(review)

    def recent(self, limit: int = 20) -> list:
        with self._lock:
            return list(self._items)[:limit]
