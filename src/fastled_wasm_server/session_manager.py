import os
import random
import shutil
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class SessionInfo:
    """Information about a session."""

    session_id: int
    last_used: float
    created: float


class SessionManager:
    """
    Manages persistent build sessions with time-based lease guarantees.

    Time-Based Lease Strategy:
    - Worker Lease: Workers won't reuse sessions older than WORKER_LEASE_DURATION
    - GC Grace Period: GC won't delete sessions younger than GC_GRACE_PERIOD
    - Safety Gap: GC_GRACE_PERIOD - WORKER_LEASE_DURATION prevents collisions

    Configuration:
    - WORKER_LEASE_DURATION: 20 minutes (worker won't use older sessions)
    - GC_GRACE_PERIOD: 40 minutes (GC won't delete younger sessions)
    - Safety Gap: 20 minutes (prevents worker/GC collision)
    """

    def __init__(
        self,
        worker_lease_seconds: int = 20 * 60,  # 20 minutes
        gc_grace_period_seconds: int = 40 * 60,  # 40 minutes
        cleanup_interval_seconds: int = 60,  # Check every minute
        check_expiry: bool = True,
        session_root: Optional[Path] = None,
    ):
        # Time-based lease configuration
        self._worker_lease_duration = worker_lease_seconds
        self._gc_grace_period = gc_grace_period_seconds
        self._cleanup_interval = cleanup_interval_seconds

        # Session registry
        self._sessions: Dict[int, SessionInfo] = {}
        self._lock = threading.Lock()

        # Session directory root
        self._session_root = (
            session_root
            if session_root
            else Path(os.environ.get("ENV_SKETCH_BUILD_ROOT", "/sketch"))
        )
        self._session_root.mkdir(parents=True, exist_ok=True)

        # Start GC cleanup thread
        self._cleanup_thread = None
        if check_expiry:
            self._cleanup_thread = threading.Thread(
                target=self._gc_cleanup_loop, daemon=True
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
                    current_time = time.time()
                    self._sessions[session_id] = SessionInfo(
                        session_id=session_id,
                        last_used=current_time,
                        created=current_time,
                    )
                    return session_id

    def get_or_create_session(
        self, session_id_param: Optional[int] = None
    ) -> tuple[int, bool]:
        """
        Get an existing session or create a new one based on worker lease rules.

        Worker Lease Rule: Won't reuse sessions older than WORKER_LEASE_DURATION.

        Args:
            session_id_param: Optional session ID to attempt to reuse

        Returns:
            Tuple of (session_id, was_reused)
            - session_id: The session ID to use (reused or new)
            - was_reused: True if existing session was reused, False if new
        """
        current_time = time.time()

        with self._lock:
            # If no session provided, create new
            if session_id_param is None:
                return self._create_new_session_locked(current_time), False

            # Check if session exists
            session = self._sessions.get(session_id_param)
            if session is None:
                # Session not found - create new
                return self._create_new_session_locked(current_time), False

            # Check worker lease duration
            age = current_time - session.last_used
            if age > self._worker_lease_duration:
                # Session too old - worker won't use it
                # Create new session instead
                new_id = self._create_new_session_locked(current_time)
                print(
                    f"Session {session_id_param} too old ({age:.0f}s > {self._worker_lease_duration}s), "
                    f"creating new session {new_id}"
                )
                return new_id, False

            # Session is valid - reuse it
            session.last_used = current_time
            return session_id_param, True

    def _create_new_session_locked(self, current_time: float) -> int:
        """Create a new session. Must be called with lock held."""
        while True:
            session_id = random.getrandbits(64)
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionInfo(
                    session_id=session_id,
                    last_used=current_time,
                    created=current_time,
                )
                return session_id

    def _get_session_dir(self, session_id: int) -> Path:
        """Get the directory path for a session."""
        return self._session_root / f"session-{session_id}"

    def _gc_cleanup_loop(self):
        """
        Background GC thread that deletes old sessions.

        GC Grace Period Rule: Only deletes sessions older than GC_GRACE_PERIOD.
        This provides a safety gap from the worker lease duration.
        """
        while True:
            time.sleep(self._cleanup_interval)

            try:
                cleaned_count = self._gc_cleanup_cycle()
                if cleaned_count > 0:
                    print(
                        f"GC: Cleaned up {cleaned_count} sessions (older than {self._gc_grace_period}s)"
                    )
            except Exception as e:
                print(f"GC: Error during cleanup cycle: {e}")

    def _gc_cleanup_cycle(self) -> int:
        """
        Run one GC cleanup cycle.

        Returns:
            Number of sessions cleaned up
        """
        current_time = time.time()
        to_delete = []

        # Step 1: Find sessions eligible for GC (with lock)
        with self._lock:
            for session_id, session_info in list(self._sessions.items()):
                age = current_time - session_info.last_used
                if age > self._gc_grace_period:
                    # Old enough - safe to delete
                    to_delete.append(session_id)
                    del self._sessions[session_id]

        # Step 2: Delete directories (without lock - filesystem handles it)
        for session_id in to_delete:
            try:
                session_dir = self._get_session_dir(session_id)
                if session_dir.exists():
                    shutil.rmtree(session_dir)
                    print(f"GC: Deleted session {session_id} directory ({session_dir})")
            except Exception as e:
                print(f"GC: Error deleting session {session_id} directory: {e}")

        return len(to_delete)

    def get_session_info(self, session_id: Optional[int] = None) -> dict:
        """Get information about a session.

        Returns:
            Dictionary with session information
        """
        if session_id is None:
            return {"exists": False, "message": "No session ID provided"}

        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"exists": False, "message": f"Session {session_id} not found"}

            current_time = time.time()
            age = current_time - session.last_used

            return {
                "exists": True,
                "session_id": session_id,
                "age_seconds": age,
                "created": session.created,
                "last_used": session.last_used,
                "within_worker_lease": age < self._worker_lease_duration,
                "within_gc_grace": age < self._gc_grace_period,
            }

    def get_session_stats(self) -> dict:
        """Get statistics about all sessions.

        Returns:
            Dictionary with session statistics
        """
        current_time = time.time()

        with self._lock:
            total = len(self._sessions)
            active = sum(
                1
                for s in self._sessions.values()
                if (current_time - s.last_used) < self._worker_lease_duration
            )
            gc_pending = sum(
                1
                for s in self._sessions.values()
                if (current_time - s.last_used) > self._gc_grace_period
            )

            return {
                "total_sessions": total,
                "active_sessions": active,
                "gc_pending": gc_pending,
                "worker_lease_duration": self._worker_lease_duration,
                "gc_grace_period": self._gc_grace_period,
                "safety_gap": self._gc_grace_period - self._worker_lease_duration,
            }
