import pandas as pd
import shutil
import os
from openpyxl import load_workbook

class DataManager:
    """Handles all Excel data operations for the Execution Dashboard."""

    def __init__(self, session_info, state_manager):
        self.session_info = session_info
        self.state = state_manager
        self.file_path = os.path.join(session_info['project_path'], session_info['file_name'])
        self.workbook = None
        self.load_data()

    @staticmethod
    def create_session_file(session_info):
        """Copies the master template to the project path to create a new session file."""
        template_path = "performance_dashboard/assets/template_test_cases.xlsx"
        destination_path = os.path.join(session_info['project_path'], session_info['file_name'])

        if not os.path.exists(session_info['project_path']):
            os.makedirs(session_info['project_path'])

        try:
            shutil.copy(template_path, destination_path)
            return True, f"Session file created at {destination_path}"
        except IOError as e:
            return False, f"Error creating session file: {e}"

    def load_data(self):
        """Loads the data from the current sheet into a pandas DataFrame."""
        try:
            # keep_default_na=False prevents pandas from reading empty cells as 'NaN'
            self.workbook = pd.read_excel(self.file_path, sheet_name=None, keep_default_na=False)
        except FileNotFoundError:
            self.workbook = None
            print(f"Error: File not found at {self.file_path}")

    def get_sheet_data(self, sheet_name):
        """Returns the DataFrame for a specific sheet."""
        if self.workbook and sheet_name in self.workbook:
            return self.workbook[sheet_name]
        return pd.DataFrame()

    def get_test_case(self, sheet_name, index):
        """Retrieves a single test case by its index from the specified sheet."""
        sheet_data = self.get_sheet_data(sheet_name)
        if not sheet_data.empty and 0 <= index < len(sheet_data):
            # Fill any remaining NA-like values just in case, for display
            return sheet_data.iloc[index].fillna('')
        return None

    def get_test_case_count(self, sheet_name):
        """Returns the total number of test cases in a sheet."""
        sheet_data = self.get_sheet_data(sheet_name)
        return len(sheet_data)

    def save_iteration_time(self, sheet_name, test_case_index, iteration, time):
        """Saves a single iteration time to the Excel file and recalculates the average."""
        if not (1 <= iteration <= 5):
            print("Error: Iteration must be between 1 and 5.")
            return

        try:
            # Use openpyxl to perform a targeted write to avoid rewriting the whole file
            wb = load_workbook(self.file_path)
            if sheet_name not in wb.sheetnames:
                print(f"Error: Sheet '{sheet_name}' not found.")
                return

            ws = wb[sheet_name]

            # Column mapping (assumes standard template)
            iteration_col = self.get_column_index_from_name(ws, f"Iteration{iteration}")
            avg_col = self.get_column_index_from_name(ws, "Average")

            # Write the new time (Excel rows are 1-based, plus 1 for the header)
            ws.cell(row=test_case_index + 2, column=iteration_col, value=float(time))

            # Recalculate and save the average
            iteration_times = []
            for i in range(1, 6):
                iter_col_idx = self.get_column_index_from_name(ws, f"Iteration{i}")
                cell_value = ws.cell(row=test_case_index + 2, column=iter_col_idx).value
                if isinstance(cell_value, (int, float)):
                    iteration_times.append(cell_value)

            if iteration_times:
                average = sum(iteration_times) / len(iteration_times)
                ws.cell(row=test_case_index + 2, column=avg_col, value=average)

            wb.save(self.file_path)

            # Reload data in pandas to reflect changes
            self.load_data()

        except Exception as e:
            print(f"Error saving time to Excel: {e}")

    def save_notes(self, sheet_name, test_case_index, notes):
        """Saves notes for a specific test case."""
        try:
            wb = load_workbook(self.file_path)
            if sheet_name not in wb.sheetnames:
                print(f"Error: Sheet '{sheet_name}' not found.")
                return

            ws = wb[sheet_name]
            notes_col = self.get_column_index_from_name(ws, "Notes")
            ws.cell(row=test_case_index + 2, column=notes_col, value=notes)
            wb.save(self.file_path)
            self.load_data() # Refresh pandas dataframe

        except Exception as e:
            print(f"Error saving notes to Excel: {e}")

    def get_column_index_from_name(self, worksheet, column_name):
        """Finds the 1-based index of a column from its header name."""
        for cell in worksheet[1]: # Iterate over the first row (header)
            if cell.value == column_name:
                return cell.column
        raise ValueError(f"Column '{column_name}' not found in the worksheet.")

    def get_all_results(self, sheet_name):
        """Retrieves results for all test cases from a sheet for the Results tab."""
        sheet_data = self.get_sheet_data(sheet_name)
        if not sheet_data.empty:
            results_columns = [
                "Test Case Name", "Iteration1", "Iteration2", "Iteration3",
                "Iteration4", "Iteration5", "Average"
            ]
            # Ensure all required columns exist, fill missing with None
            for col in results_columns:
                if col not in sheet_data.columns:
                    sheet_data[col] = ''

            # Return a copy and fill any remaining NaNs for display
            return sheet_data[results_columns].fillna('')
        return pd.DataFrame()