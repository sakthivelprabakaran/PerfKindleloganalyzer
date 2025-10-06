import pandas as pd
import openpyxl
from openpyxl.utils.dataframe import dataframe_to_rows

class DataManager:
    """Handles all interactions with the test_cases.xlsx file."""

    def __init__(self, file_path="test_cases.xlsx"):
        self.file_path = file_path
        self.workbook = None
        self.data_frames = {}
        try:
            # Load all sheets into a dictionary of DataFrames
            self.data_frames = pd.read_excel(self.file_path, sheet_name=None)
            self.workbook = openpyxl.load_workbook(self.file_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"Error: The file '{self.file_path}' was not found.")
        except Exception as e:
            raise Exception(f"An error occurred while loading the Excel file: {e}")

    def get_sheet_names(self):
        """Returns a list of all sheet names in the Excel file."""
        return list(self.data_frames.keys())

    def get_sheet_data(self, sheet_name):
        """Returns the DataFrame for a specific sheet."""
        if sheet_name in self.data_frames:
            return self.data_frames[sheet_name]
        else:
            return None

    def update_cell(self, sheet_name, row_index, col_name, value):
        """Updates a specific cell in the DataFrame and the workbook."""
        if sheet_name not in self.data_frames:
            print(f"Error: Sheet '{sheet_name}' not found.")
            return False

        df = self.data_frames[sheet_name]

        # Validate row and column
        if row_index >= len(df):
            print(f"Error: Row index {row_index} is out of bounds for sheet '{sheet_name}'.")
            return False
        if col_name not in df.columns:
            print(f"Error: Column '{col_name}' not found in sheet '{sheet_name}'.")
            return False

        # Update DataFrame
        df.loc[row_index, col_name] = value

        # Update workbook
        try:
            worksheet = self.workbook[sheet_name]
            # Find the column index (1-based)
            col_index = list(df.columns).index(col_name) + 1
            # Update the cell (row_index is 0-based, so add 2 for 1-based index and header)
            worksheet.cell(row=row_index + 2, column=col_index, value=value)
            return True
        except Exception as e:
            print(f"Error updating cell in workbook: {e}")
            return False

    def save_data(self):
        """Saves the workbook to the file."""
        try:
            self.workbook.save(self.file_path)
            return True
        except Exception as e:
            print(f"Error saving Excel file: {e}")
            return False