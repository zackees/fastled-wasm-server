import threading
import time
import unittest

from fastled_wasm_server.session_manager import SessionManager


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        # Use a short lease time for testing and disable background cleanup
        self.session_manager = SessionManager(
            worker_lease_seconds=2, gc_grace_period_seconds=4, check_expiry=False
        )

    def test_session_creation(self):
        """Test that new sessions are created with unique IDs."""
        session_id1 = self.session_manager.generate_session_id()
        session_id2 = self.session_manager.generate_session_id()

        self.assertIsInstance(session_id1, int)
        self.assertIsInstance(session_id2, int)
        self.assertNotEqual(session_id1, session_id2)

        # Verify both sessions are active
        reused_id1, was_reused1 = self.session_manager.get_or_create_session(
            session_id1
        )
        reused_id2, was_reused2 = self.session_manager.get_or_create_session(
            session_id2
        )
        self.assertEqual(reused_id1, session_id1)
        self.assertEqual(reused_id2, session_id2)
        self.assertTrue(was_reused1)
        self.assertTrue(was_reused2)

    def test_session_info(self):
        """Test session info messages."""
        # Test with no session
        info = self.session_manager.get_session_info(None)
        self.assertFalse(info["exists"])
        self.assertEqual(info["message"], "No session ID provided")

        # Test with new session
        session_id = self.session_manager.generate_session_id()
        info = self.session_manager.get_session_info(session_id)
        self.assertTrue(info["exists"])
        self.assertEqual(info["session_id"], session_id)

        # Test with invalid session
        invalid_id = 12345
        info = self.session_manager.get_session_info(invalid_id)
        self.assertFalse(info["exists"])
        self.assertEqual(info["message"], f"Session {invalid_id} not found")

    def test_session_expiration(self):
        """Test that sessions expire after the worker lease duration."""
        # Create a session
        session_id = self.session_manager.generate_session_id()
        reused_id, was_reused = self.session_manager.get_or_create_session(session_id)
        self.assertEqual(reused_id, session_id)
        self.assertTrue(was_reused)

        # Wait for expiration beyond worker_lease_seconds
        time.sleep(3)  # Wait longer than worker_lease_seconds (2s)

        # Session should not be reused - a new session should be created
        new_id, was_reused = self.session_manager.get_or_create_session(session_id)
        self.assertNotEqual(new_id, session_id)
        self.assertFalse(was_reused)

    def test_session_touch_extends_lifetime(self):
        """Test that using a session extends its lifetime."""
        session_id = self.session_manager.generate_session_id()

        # Use session multiple times over a period longer than worker lease
        for _ in range(3):
            time.sleep(1)  # Wait half the lease time
            reused_id, was_reused = self.session_manager.get_or_create_session(
                session_id
            )
            self.assertEqual(reused_id, session_id)
            self.assertTrue(was_reused)

        # Session should still be valid
        reused_id, was_reused = self.session_manager.get_or_create_session(session_id)
        self.assertEqual(reused_id, session_id)
        self.assertTrue(was_reused)

    def test_concurrent_access(self):
        """Test that concurrent access to sessions is thread-safe."""
        session_id = self.session_manager.generate_session_id()
        num_threads = 10
        iterations_per_thread = 100
        errors = []

        def worker():
            try:
                for _ in range(iterations_per_thread):
                    reused_id, was_reused = self.session_manager.get_or_create_session(
                        session_id
                    )
                    self.assertEqual(reused_id, session_id)
                    self.assertTrue(was_reused)
                    time.sleep(
                        0.001
                    )  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered errors: {errors}")
        reused_id, was_reused = self.session_manager.get_or_create_session(session_id)
        self.assertEqual(reused_id, session_id)
        self.assertTrue(was_reused)

    def test_manual_cleanup(self):
        """Test GC cleanup of expired sessions."""
        # Create multiple sessions
        sessions = [self.session_manager.generate_session_id() for _ in range(3)]
        for sid in sessions:
            reused_id, was_reused = self.session_manager.get_or_create_session(sid)
            self.assertEqual(reused_id, sid)
            self.assertTrue(was_reused)

        # Wait for GC grace period expiration
        time.sleep(5)  # Wait longer than gc_grace_period_seconds (4s)

        # Clean up expired sessions
        cleaned = self.session_manager._gc_cleanup_cycle()
        self.assertEqual(cleaned, 3)

        # Verify all sessions are gone - trying to reuse them should create new sessions
        for sid in sessions:
            new_id, was_reused = self.session_manager.get_or_create_session(sid)
            self.assertNotEqual(new_id, sid)
            self.assertFalse(was_reused)


if __name__ == "__main__":
    unittest.main()
