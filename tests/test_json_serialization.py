import unittest
import sys
import os
import json
import numpy as np

# Ensure project root is in path
sys.path.append(os.getcwd())

from performance_dashboard.logic.state_manager import StateManager

class TestJSONSerialization(unittest.TestCase):
    def setUp(self):
        self.state_manager = StateManager()
        self.state_manager.session_file_path = "test_sessions.json"
        self.state_manager.sessions = []

    def tearDown(self):
        if os.path.exists("test_sessions.json"):
            os.remove("test_sessions.json")

    def test_save_numpy_types(self):
        """Verify that StateManager can save numpy types without error."""
        # Create a session with numpy types
        numpy_session = {
            "file_name": "NumpySession.xlsx",
            "priority": "P0",
            "current_test_case_index": np.int64(42),
            "some_float": np.float64(3.14),
            "some_array": np.array([1, 2, 3])
        }
        self.state_manager.sessions.append(numpy_session)
        
        # Attempt to save
        try:
            self.state_manager.save_sessions()
        except TypeError as e:
            self.fail(f"save_sessions raised TypeError: {e}")

        # Verify file content
        with open("test_sessions.json", 'r') as f:
            data = json.load(f)
            saved_session = data[0]
            
            self.assertIsInstance(saved_session['current_test_case_index'], int)
            self.assertEqual(saved_session['current_test_case_index'], 42)
            self.assertIsInstance(saved_session['some_float'], float)
            self.assertAlmostEqual(saved_session['some_float'], 3.14)
            self.assertIsInstance(saved_session['some_array'], list)
            self.assertEqual(saved_session['some_array'], [1, 2, 3])

if __name__ == '__main__':
    unittest.main()
