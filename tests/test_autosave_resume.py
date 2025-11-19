import unittest
import sys
import os
from unittest.mock import MagicMock, patch
import pandas as pd

# Ensure project root is in path
sys.path.append(os.getcwd())

from performance_dashboard.ui.execution_dashboard import ExecutionDashboard
from performance_dashboard.logic.state_manager import StateManager
from performance_dashboard.logic.data_manager import DataManager
from PyQt5.QtWidgets import QApplication

# Create a global QApplication instance for tests if it doesn't exist
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

class TestAutoSaveResume(unittest.TestCase):
    def setUp(self):
        self.state_manager = StateManager()
        self.state_manager.current_session = {
            'file_name': 'test_session.xlsx',
            'active_sheet': 'P0',
            'current_test_case_index': 2 # Simulate saved index
        }
        
        self.data_manager = DataManager({
            'priority': 'P0',
            'project_path': 'test_data',
            'file_name': 'test_session.xlsx'
        })
        # Mock save_to_excel_async
        self.data_manager.save_to_excel_async = MagicMock()
        
        # Mock get_sheet_data to return dummy data
        self.dummy_data = pd.DataFrame({
            'Test Case ID': ['TC1', 'TC2', 'TC3'],
            'Iteration1': ['0.1', '0.2', '0.3'],
            'Iteration2': ['0.1', '0.2', ''],
            'Iteration3': ['0.1', '0.2', ''],
            'Iteration4': ['0.1', '0.2', ''],
            'Iteration5': ['0.1', '0.2', ''],
            'Average': ['0.1', '0.2', ''], # TC3 is incomplete
            'N-Points': [1, 1, 1],
            'Component': ['A', 'A', 'A']
        })
        self.data_manager.get_sheet_data = MagicMock(return_value=self.dummy_data)
        self.data_manager.get_test_case_count = MagicMock(return_value=3)
        self.data_manager.get_unique_components = MagicMock(return_value=['A'])
        self.data_manager.get_all_test_case_identifiers = MagicMock(return_value=['TC1', 'TC2', 'TC3'])
        self.data_manager.get_test_case = MagicMock(return_value=self.dummy_data.iloc[0])

    def test_auto_save_trigger(self):
        """Verify save_to_excel_async is called after saving iteration."""
        self.data_manager.save_iteration_time('P0', 0, 1, 0.5, 'Build1')
        self.data_manager.save_to_excel_async.assert_called_once()

    def test_session_resume(self):
        """Verify dashboard loads the saved test case index."""
        # Mock apply_filters to capture the index passed to it
        with patch.object(ExecutionDashboard, 'apply_filters') as mock_apply_filters:
            with patch.object(ExecutionDashboard, 'check_incomplete_test_cases'): # Suppress warning
                dashboard = ExecutionDashboard(self.state_manager, self.data_manager, lambda: None)
                dashboard.load_session_data()
                # Check if apply_filters was called with the saved index (2)
                mock_apply_filters.assert_called_with(selected_index=2)

    def test_incomplete_warning_detection(self):
        """Verify check_incomplete_test_cases identifies incomplete rows."""
        dashboard = ExecutionDashboard(self.state_manager, self.data_manager, lambda: None)
        
        # We need to capture the warning message box or check the logic
        # Since we can't easily check QMessageBox, let's verify the logic by inspecting the method
        # We can mock QMessageBox.warning
        with patch('PyQt5.QtWidgets.QMessageBox.warning') as mock_warning:
            dashboard.load_session_data()
            
            # TC3 is incomplete (Iteration1 has data, Average is empty)
            # So warning should be called
            mock_warning.assert_called_once()
            args, _ = mock_warning.call_args
            self.assertIn("TC3", args[2]) # Message should contain the ID

if __name__ == '__main__':
    unittest.main()
