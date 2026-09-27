"""Thread-safe in-memory context store with versioning and idempotency."""

from __future__ import annotations
import threading
from typing import Dict, Tuple, Optional, Any, List
from datetime import datetime, timezone


class ContextStore:
    def __init__(self):
        self._lock = threading.RLock()
        # Key: (scope, context_id) -> {"version": int, "payload": dict, "stored_at": str}
        self._store: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def push_context(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Store context payload.
        Returns: (accepted, reason, current_version)
        If version is <= existing version, reject with stale_version (idempotency/version conflict).
        If version > existing version or new, accept and store.
        """
        key = (scope, context_id)
        with self._lock:
            existing = self._store.get(key)
            if existing is not None:
                current_ver = existing["version"]
                if current_ver >= version:
                    return False, "stale_version", current_ver

            self._store[key] = {
                "version": version,
                "payload": payload,
                "stored_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            }
            return True, None, version

    def get_context(self, scope: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve payload for a given scope and context_id."""
        with self._lock:
            entry = self._store.get((scope, context_id))
            if entry:
                return entry["payload"]
            return None

    def get_version(self, scope: str, context_id: str) -> Optional[int]:
        with self._lock:
            entry = self._store.get((scope, context_id))
            return entry["version"] if entry else None

    def counts_by_scope(self) -> Dict[str, int]:
        """Return counts of loaded contexts by scope."""
        counts = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        with self._lock:
            for (scope, _), _ in self._store.items():
                counts[scope] = counts.get(scope, 0) + 1
        return counts

    def get_all_by_scope(self, scope: str) -> Dict[str, Dict[str, Any]]:
        """Get all payloads for a specific scope."""
        with self._lock:
            return {
                cid: entry["payload"]
                for (s, cid), entry in self._store.items()
                if s == scope
            }

    def clear(self):
        """Clear the store."""
        with self._lock:
            self._store.clear()
