import pandas as pd
import shutil
import os
from PyQt5.QtCore import QThread, pyqtSignal, QObject

class SaveThread(QThread):
    """
    Background thread for saving Excel files to prevent UI freezing.
    """
    finished_signal = pyqtSignal(bool, str)

    def __init__(self, file_path, workbook_data):
        super().__init__()
        self.file_path = file_path
        self.workbook_data = workbook_data

    def run(self):
        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in self.workbook_data.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            self.finished_signal.emit(True, "Session saved successfully.")
        except Exception as e:
            self.finished_signal.emit(False, f"Failed to save session: {e}")

class DataManager:
    """
    Handles all Excel data operations for the Execution Dashboard.
    This version works with an in-memory DataFrame for performance.
    """

    def __init__(self, session_info):
        self.session_info = session_info
        self.file_path = os.path.join(session_info['project_path'], session_info['file_name'])
        self.workbook = None # This will hold a dictionary of DataFrames (one for each sheet)
        self.load_data()

    @staticmethod
    def create_session_file(session_info):
        """
        Creates a new session file in the project path containing only the sheet
        for the selected priority.
        """
        template_path = "performance_dashboard/assets/template_test_cases.xlsx"
        destination_path = os.path.join(session_info['project_path'], session_info['file_name'])
        priority = session_info.get('priority')

        if not os.path.exists(session_info['project_path']):
            os.makedirs(session_info['project_path'])

        try:
            # Read only the specific sheet for the selected priority
            priority_df = pd.read_excel(template_path, sheet_name=priority)

            # Write this single sheet to the new session file
            with pd.ExcelWriter(destination_path, engine='openpyxl') as writer:
                priority_df.to_excel(writer, sheet_name=priority, index=False)

            return True, f"Session file for priority '{priority}' created at {destination_path}"
        except Exception as e:
            return False, f"Error creating session file: {e}"

    def load_data(self):
        """Loads all sheets from the Excel file into an in-memory workbook."""
        try:
            self.workbook = pd.read_excel(self.file_path, sheet_name=None, keep_default_na=False)
        except FileNotFoundError:
            self.workbook = None
            print(f"Error: File not found at {self.file_path}")

    def get_sheet_data(self, sheet_name):
        """Returns the DataFrame for a specific sheet from the in-memory workbook."""
        if self.workbook and sheet_name in self.workbook:
            return self.workbook[sheet_name]
        return pd.DataFrame()

    def get_test_case(self, sheet_name, index):
        """Retrieves a single test case by its index from the specified sheet."""
        sheet_data = self.get_sheet_data(sheet_name)
        if not sheet_data.empty and 0 <= index < len(sheet_data):
            return sheet_data.iloc[index].fillna('')
        return None

    def get_test_case_count(self, sheet_name):
        """Returns the total number of test cases in a sheet."""
        sheet_data = self.get_sheet_data(sheet_name)
        return len(sheet_data)

    def save_iteration_time(self, sheet_name, test_case_index, iteration, time, build_info):
        """Saves a single iteration time and the current build info to the in-memory DataFrame."""
        if not (1 <= iteration <= 5):
            print("Error: Iteration must be between 1 and 5.")
            return None

        try:
            df = self.get_sheet_data(sheet_name)
            if df.empty:
                return None

            # Update the specific iteration value and build
            df.loc[test_case_index, f"Iteration{iteration}"] = time
            self.save_build_info(sheet_name, test_case_index, build_info)

            # Recalculate average if all iterations are present
            iteration_cols = [f"Iteration{i}" for i in range(1, 6)]
            iteration_values = pd.to_numeric(df.loc[test_case_index, iteration_cols], errors='coerce').dropna()

            if len(iteration_values) == 5:
                average = iteration_values.mean()
                df.loc[test_case_index, "Average"] = average

            # Return the updated row (test case)
            self.save_to_excel_async() # Auto-save
            return self.get_test_case(sheet_name, test_case_index)

        except Exception as e:
            print(f"Error saving time to in-memory DataFrame: {e}")
            return None

    def save_notes(self, sheet_name, test_case_index, notes, build_info=None):
        """Saves notes to the Notes column and optionally updates build info."""
        df = self.get_sheet_data(sheet_name)
        if df.empty or not (0 <= test_case_index < len(df)):
            return None

        # Check if 'Notes' column exists
        if 'Notes' not in df.columns:
            df['Notes'] = ''

        df.at[test_case_index, 'Notes'] = notes
        self.workbook[sheet_name] = df
        
        if build_info:
            self.save_build_info(sheet_name, test_case_index, build_info)
        
        # Auto-save after notes update
        self.save_to_excel_async()
        
        return self.get_test_case(sheet_name, test_case_index)

    def save_baseline_results(self, sheet_name, test_case_index, baseline_data):
        """Saves baseline results to the Baseline Results column.
        
        Args:
            sheet_name: Name of the sheet
            test_case_index: Index of the test case
            baseline_data: Dict with keys 'iterations' (list of 5 times), 'average', 'build'
        """
        df = self.get_sheet_data(sheet_name)
        if df.empty or not (0 <= test_case_index < len(df)):
            return

        # Check if 'Baseline Results' column exists, if not create it
        if 'Baseline Results' not in df.columns:
            df['Baseline Results'] = ''

        # Format the result string
        iterations_str = ', '.join([str(t) for t in baseline_data['iterations']])
        result_string = f"Baseline - ({iterations_str} = {baseline_data['average']}), Build used - {baseline_data['build']}"
        
        df.at[test_case_index, 'Baseline Results'] = result_string
        self.workbook[sheet_name] = df
        
        # Auto-save after baseline update
        self.save_to_excel_async() # Auto-save

    def save_build_info(self, sheet_name, test_case_index, build_info):
        """Saves the build string to the 'Build' column for a specific test case."""
        try:
            df = self.get_sheet_data(sheet_name)
            if df.empty or 'Build' not in df.columns:
                return

            df.loc[test_case_index, "Build"] = build_info
        except Exception as e:
            print(f"Error saving build info: {e}")

    def save_to_excel(self):
        """Writes the entire in-memory workbook back to the Excel file (Blocking)."""
        if not self.workbook:
            print("Error: No workbook data to save.")
            return False, "No data to save."
        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in self.workbook.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True, "Session saved successfully."
        except Exception as e:
            print(f"Error writing to Excel file: {e}")
            return False, f"Failed to save session: {e}"

    def save_to_excel_async(self):
        """
        Saves the workbook data to Excel synchronously.
        Changed from async to avoid thread destruction issues.
        """
        if not self.workbook:
            return None

        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in self.workbook.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
        except Exception as e:
            print(f"Error saving Excel file: {e}")
        
        return None

    def get_all_results(self, sheet_name):
        """Retrieves results for all test cases from a sheet for the Results tab."""
        sheet_data = self.get_sheet_data(sheet_name)
        if not sheet_data.empty:
            results_columns = [
                "Test Case Name", "Iteration1", "Iteration2", "Iteration3",
                "Iteration4", "Iteration5", "Average", "Baseline Results", "Notes"
            ]
            # Ensure all required columns exist, fill missing with ''
            for col in results_columns:
                if col not in sheet_data.columns:
                    sheet_data[col] = ''

            return sheet_data[results_columns].fillna('')
        return pd.DataFrame()

    def get_unique_components(self, sheet_name):
        """Returns a list of unique values from the 'Component' column."""
        sheet_data = self.get_sheet_data(sheet_name)
        if not sheet_data.empty and "Component" in sheet_data.columns:
            return sheet_data["Component"].unique().tolist()
        return []

    def get_all_test_case_identifiers(self, sheet_name, dataframe=None):
        """
        Returns a list of 'ID: Name' strings for all test cases for search functionality.
        If a DataFrame is provided, it will be used instead of the full sheet data.
        """
        if dataframe is None:
            sheet_data = self.get_sheet_data(sheet_name)
        else:
            sheet_data = dataframe

        if not sheet_data.empty and "Test Case ID" in sheet_data.columns and "Test Case Name" in sheet_data.columns:
            # Combine 'Test Case ID' and 'Test Case Name' for a user-friendly identifier
            return sheet_data.apply(
                lambda row: f"{row['Test Case ID']}: {row['Test Case Name']}",
                axis=1
            ).tolist()
        return []

    def clear_test_case_results(self, sheet_name, test_case_index):
        """Clears the iteration and average results for a specific test case."""
        try:
            df = self.get_sheet_data(sheet_name)
            if df.empty:
                return None

            # Clear iteration and average values
            for i in range(1, 6):
                df.loc[test_case_index, f"Iteration{i}"] = ""
            df.loc[test_case_index, "Average"] = ""

            return self.get_test_case(sheet_name, test_case_index)
        except Exception as e:
            print(f"Error clearing test case results: {e}")
            return None