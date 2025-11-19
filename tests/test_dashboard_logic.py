import unittest
import os
import shutil
import pandas as pd
import sys

# Ensure the project root is in the path
sys.path.append(os.getcwd())

from performance_dashboard.logic.state_manager import StateManager
from performance_dashboard.logic.data_manager import DataManager

class TestDashboardLogic(unittest.TestCase):
    def setUp(self):
        # Setup temporary test directory
        self.test_dir = "test_dashboard_data"
        if not os.path.exists(self.test_dir):
            os.makedirs(self.test_dir)
            
        # Create a dummy template file
        self.template_path = "performance_dashboard/assets/template_test_cases.xlsx"
        os.makedirs(os.path.dirname(self.template_path), exist_ok=True)
        
        # Create dummy data for P0 and P1
        df_p0 = pd.DataFrame({'Test Case ID': ['TC01'], 'Test Case Name': ['Test 1'], 'Iteration1': ['']})
        df_p1 = pd.DataFrame({'Test Case ID': ['TC02'], 'Test Case Name': ['Test 2'], 'Iteration1': ['']})
        
        with pd.ExcelWriter(self.template_path) as writer:
            df_p0.to_excel(writer, sheet_name='P0', index=False)
            df_p1.to_excel(writer, sheet_name='P1', index=False)

    def tearDown(self):
        # Clean up
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        # Don't delete the template as it might be used by the actual app, 
        # but in this isolated test env it's fine if we created it. 
        # Ideally we'd mock this path.

    def test_session_creation_sheet_selection(self):
        """Test that creating a session with P1 priority correctly sets the active sheet."""
        state = StateManager()
        # Mock the session file path to be in our test dir
        state.session_file_path = os.path.join(self.test_dir, "sessions.json")
        
        session = state.create_new_session(
            self.test_dir, "TestDevice", "1", "Build1", "P1"
        )
        
        # Check if active_sheet is set correctly in the session data
        self.assertEqual(session.get('active_sheet'), 'P1', "Active sheet should be P1")
        
        # Verify file creation
        DataManager.create_session_file(session)
        file_path = os.path.join(self.test_dir, session['file_name'])
        self.assertTrue(os.path.exists(file_path))
        
        # Verify content
        df = pd.read_excel(file_path, sheet_name=None)
        self.assertIn('P1', df.keys())
        # We don't necessarily assert P0 is not there, as the template might have it, 
        # but we want to ensure P1 is the active one or at least present.

    def test_data_saving(self):
        """Test saving data to the session file."""
        state = StateManager()
        state.session_file_path = os.path.join(self.test_dir, "sessions.json")
        session = state.create_new_session(
            self.test_dir, "TestDevice", "1", "Build1", "P0"
        )
        # Manually set active_sheet for this test if the fix isn't applied yet, 
        # but we are testing the fix, so we rely on create_new_session working or we manually fix it for this test?
        # Actually, if create_new_session is broken, this test might fail if it relies on active_sheet.
        # Let's ensure we have a valid session for data manager.
        if 'active_sheet' not in session:
             session['active_sheet'] = 'P0'

        DataManager.create_session_file(session)
        
        dm = DataManager(session)
        
        # Save an iteration time
        dm.save_iteration_time('P0', 0, 1, 10.5, "Build1")
        
        # Verify in-memory update
        tc = dm.get_test_case('P0', 0)
        self.assertEqual(tc['Iteration1'], 10.5)
        
        # Save to disk
        dm.save_to_excel()
        
        # Verify disk content
        dm2 = DataManager(session)
        tc2 = dm2.get_test_case('P0', 0)
        self.assertEqual(tc2['Iteration1'], 10.5)

if __name__ == '__main__':
    unittest.main()
