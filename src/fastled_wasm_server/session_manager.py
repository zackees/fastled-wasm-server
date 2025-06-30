import random
import threading
import time
from typing import Dict, Optional


class SessionManager:
    def __init__(
        self, expiry_seconds: int = 3600, check_expiry: bool = True
    ):  # 1 hour default
        self._sessions: Dict[int, float] = {}  # session_id -> last_access_time
        self._lock = threading.Lock()
        self._expiry_seconds = expiry_seconds
        self._cleanup_thread = None
        if check_expiry:
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_expired_sessions, daemon=True
            )
            self._cleanup_thread.start()

    def generate_session_id(self) -> int:
        """Generate a new 64-bit random session ID."""
        while True:
            # Generate a random 64-bit integer
            session_id = random.getrandbits(64)
            with self._lock:
                # Make sure it's unique
                if session_id not in self._sessions:
                    self._sessions[session_id] = time.time()
                    return session_id

    def touch_session(self, session_id: int) -> bool:
        """Update the last access time of a session. Returns True if session exists."""
        current_time = time.time()
        with self._lock:
            if session_id in self._sessions:
                # Check if session has expired
                if current_time - self._sessions[session_id] > self._expiry_seconds:
                    del self._sessions[session_id]
                    return False
                self._sessions[session_id] = current_time
                return True
            return False

    def cleanup_expired(self) -> int:
        """Manually clean up expired sessions. Returns number of sessions cleaned up."""
        current_time = time.time()
        with self._lock:
            expired = [
                sid
                for sid, last_access in self._sessions.items()
                if current_time - last_access > self._expiry_seconds
            ]
            for sid in expired:
                del self._sessions[sid]
            return len(expired)

    def _cleanup_expired_sessions(self):
        """Background thread to clean up expired sessions."""
        while True:
            time.sleep(60)  # Check every minute
            cleaned = self.cleanup_expired()
            if cleaned:
                print(f"Cleaned up {cleaned} expired sessions")

    def get_session_info(self, session_id: Optional[int] = None) -> str:
        """Get information about whether this is a new or existing session."""
        if session_id is None:
            return "No session ID provided - treating as new session"

        exists = self.touch_session(session_id)
        if exists:
            return f"Using existing session {session_id}"
        return f"Session {session_id} not found - expired or invalid"
