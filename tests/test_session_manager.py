import threading
import time
import unittest

from fastled_wasm_server.session_manager import SessionManager


class TestSessionManager(unittest.TestCase):
    def setUp(self):
        # Use a short expiry time for testing and disable background cleanup
        self.session_manager = SessionManager(expiry_seconds=2, check_expiry=False)

    def test_session_creation(self):
        """Test that new sessions are created with unique IDs."""
        session_id1 = self.session_manager.generate_session_id()
        session_id2 = self.session_manager.generate_session_id()

        self.assertIsInstance(session_id1, int)
        self.assertIsInstance(session_id2, int)
        self.assertNotEqual(session_id1, session_id2)

        # Verify both sessions are active
        self.assertTrue(self.session_manager.touch_session(session_id1))
        self.assertTrue(self.session_manager.touch_session(session_id2))

    def test_session_info(self):
        """Test session info messages."""
        # Test with no session
        info = self.session_manager.get_session_info(None)
        self.assertEqual(info, "No session ID provided - treating as new session")

        # Test with new session
        session_id = self.session_manager.generate_session_id()
        info = self.session_manager.get_session_info(session_id)
        self.assertEqual(info, f"Using existing session {session_id}")

        # Test with invalid session
        invalid_id = 12345
        info = self.session_manager.get_session_info(invalid_id)
        self.assertEqual(info, f"Session {invalid_id} not found - expired or invalid")

    def test_session_expiration(self):
        """Test that sessions expire after the specified time."""
        # Create a session
        session_id = self.session_manager.generate_session_id()
        self.assertTrue(self.session_manager.touch_session(session_id))

        # Wait for expiration
        time.sleep(3)  # Wait longer than expiry_seconds

        # Session should be expired when touched
        self.assertFalse(self.session_manager.touch_session(session_id))
        self.assertEqual(
            self.session_manager.get_session_info(session_id),
            f"Session {session_id} not found - expired or invalid",
        )

    def test_session_touch_extends_lifetime(self):
        """Test that touching a session extends its lifetime."""
        session_id = self.session_manager.generate_session_id()

        # Touch session multiple times over a period longer than expiry
        for _ in range(3):
            time.sleep(1)  # Wait half the expiry time
            self.assertTrue(self.session_manager.touch_session(session_id))

        # Session should still be valid
        self.assertTrue(self.session_manager.touch_session(session_id))

    def test_concurrent_access(self):
        """Test that concurrent access to sessions is thread-safe."""
        session_id = self.session_manager.generate_session_id()
        num_threads = 10
        iterations_per_thread = 100
        errors = []

        def worker():
            try:
                for _ in range(iterations_per_thread):
                    self.assertTrue(self.session_manager.touch_session(session_id))
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
        self.assertTrue(self.session_manager.touch_session(session_id))

    def test_manual_cleanup(self):
        """Test manual cleanup of expired sessions."""
        # Create multiple sessions
        sessions = [self.session_manager.generate_session_id() for _ in range(3)]
        for sid in sessions:
            self.assertTrue(self.session_manager.touch_session(sid))

        # Wait for expiration
        time.sleep(3)

        # Clean up expired sessions
        cleaned = self.session_manager.cleanup_expired()
        self.assertEqual(cleaned, 3)

        # Verify all sessions are expired
        for sid in sessions:
            self.assertFalse(self.session_manager.touch_session(sid))


if __name__ == "__main__":
    unittest.main()
