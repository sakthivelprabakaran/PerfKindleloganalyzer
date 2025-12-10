import unittest
import sys
import os
from unittest.mock import MagicMock, patch
from PyQt5.QtWidgets import QApplication, QComboBox

# Ensure project root is in path
sys.path.append(os.getcwd())

from performance_dashboard.ui.execution_dashboard import ExecutionDashboard
from performance_dashboard.logic.state_manager import StateManager
from performance_dashboard.logic.data_manager import DataManager

# Create a global QApplication instance
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class TestQuickSwitch(unittest.TestCase):
    def setUp(self):
        self.state_manager = StateManager()
        self.state_manager.sessions = [
            {'file_name': 'SessionA.xlsx', 'priority': 'P0', 'device_name': 'DevA'},
            {'file_name': 'SessionB.xlsx', 'priority': 'P1', 'device_name': 'DevB'}
        ]
        self.state_manager.current_session = self.state_manager.sessions[0]
        
        self.data_manager = DataManager({
            'priority': 'P0',
            'project_path': 'test_data',
            'file_name': 'SessionA.xlsx'
        })
        self.data_manager.get_sheet_data = MagicMock(return_value=MagicMock(empty=True)) # Mock empty sheet
        
        self.switch_callback = MagicMock()
        self.return_callback = MagicMock()

    def test_session_selector_population(self):
        """Verify the session selector is populated with sessions."""
        dashboard = ExecutionDashboard(
            self.state_manager, 
            self.data_manager, 
            self.return_callback, 
            self.switch_callback
        )
        
        # Mock load_sessions to avoid file I/O
        self.state_manager.load_sessions = MagicMock()
        
        dashboard.load_session_data()
        
        # Check if items are added
        self.assertEqual(dashboard.session_selector.count(), 2)
        self.assertEqual(dashboard.session_selector.itemText(0), "SessionA.xlsx (P0)")
        self.assertEqual(dashboard.session_selector.itemText(1), "SessionB.xlsx (P1)")

    def test_switch_trigger(self):
        """Verify selecting a new session triggers the callback."""
        dashboard = ExecutionDashboard(
            self.state_manager, 
            self.data_manager, 
            self.return_callback, 
            self.switch_callback
        )
        
        # Mock load_sessions to avoid file I/O and preserve setUp data
        self.state_manager.load_sessions = MagicMock()
        
        dashboard.load_session_data()
        
        # Mock get_session_by_filename to return valid data
        self.state_manager.get_session_by_filename = MagicMock(return_value={'file_name': 'SessionB.xlsx'})
        
        # Trigger change
        dashboard.session_selector.setCurrentIndex(1)
        
        # Verify callback called
        self.switch_callback.assert_called_once()
        args, _ = self.switch_callback.call_args
        self.assertEqual(args[0]['file_name'], 'SessionB.xlsx')

if __name__ == '__main__':
    unittest.main()
