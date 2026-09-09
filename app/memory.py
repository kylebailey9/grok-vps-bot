from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, List


class ConversationMemory:
    """In-memory per-chat history. Restarting the process clears it."""

    def __init__(self, max_turns: int = 20) -> None:
        self.max_turns = max_turns
        self._store: Dict[str, Deque[dict]] = defaultdict(deque)
        self._lock = Lock()

    def get(self, chat_id: str) -> List[dict]:
        with self._lock:
            return list(self._store[chat_id])

    def append(self, chat_id: str, role: str, content: str) -> None:
        with self._lock:
            hist = self._store[chat_id]
            hist.append({"role": role, "content": content})
            while len(hist) > self.max_turns * 2:
                hist.popleft()

    def reset(self, chat_id: str) -> None:
        with self._lock:
            self._store.pop(chat_id, None)
