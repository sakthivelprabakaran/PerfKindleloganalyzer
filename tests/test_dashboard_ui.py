import unittest
import sys
import os
from PyQt5.QtWidgets import QApplication, QPushButton

# Ensure project root is in path
sys.path.append(os.getcwd())

from performance_dashboard.ui.execution_dashboard import ExecutionDashboard
from performance_dashboard.logic.state_manager import StateManager
from performance_dashboard.logic.data_manager import DataManager

# Create a global QApplication instance for tests if it doesn't exist
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class TestDashboardUI(unittest.TestCase):
    def setUp(self):
        # Mock dependencies
        self.state_manager = StateManager()
        session_info = {
            'project_path': 'test_data',
            'file_name': 'test.xlsx',
            'priority': 'P0'
        }
        self.data_manager = DataManager(session_info)
        
        self.dashboard = ExecutionDashboard(
            self.state_manager, 
            self.data_manager, 
            lambda: None # Dummy callback
        )

    def test_ui_components_exist(self):
        """Verify that new UI components are present."""
        # Check Status Bar
        self.assertTrue(hasattr(self.dashboard, 'status_bar'))
        self.assertIsNotNone(self.dashboard.status_bar)
        
        # Check Save Button
        buttons = self.dashboard.findChildren(QPushButton)
        save_btn_found = False
        for btn in buttons:
            if "Save" in btn.text() and "Return" not in btn.text():
                save_btn_found = True
                break
        self.assertTrue(save_btn_found, "Save button not found")

if __name__ == '__main__':
    unittest.main()
