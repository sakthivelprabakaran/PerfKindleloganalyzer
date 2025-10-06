import pandas as pd
import openpyxl
import numpy as np
import os

class DataManager:
    """Handles all interactions with the test_cases.xlsx file using pandas for robust data manipulation."""

    def __init__(self, file_path):
        self.file_path = file_path
        self.data_frames = {}
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"Error: The file '{self.file_path}' was not found.")
        try:
            # Load all sheets into a dictionary of DataFrames.
            # keep_default_na=False prevents pandas from interpreting empty strings as NaN.
            self.data_frames = pd.read_excel(self.file_path, sheet_name=None, keep_default_na=False, dtype=str)
            # Explicitly replace any numpy NaN types if they still appear
            for name, df in self.data_frames.items():
                self.data_frames[name] = df.replace({np.nan: ''})
        except Exception as e:
            raise Exception(f"An error occurred while loading the Excel file: {e}")

    def get_sheet_names(self):
        """Returns a list of all sheet names in the Excel file."""
        return list(self.data_frames.keys())

    def get_sheet_data(self, sheet_name):
        """Returns the DataFrame for a specific sheet."""
        return self.data_frames.get(sheet_name)

    def update_cell(self, sheet_name, row_index, col_name, value):
        """Updates a specific cell in the in-memory DataFrame."""
        if sheet_name not in self.data_frames:
            print(f"Error: Sheet '{sheet_name}' not found.")
            return False

        df = self.data_frames[sheet_name]

        if row_index >= len(df):
            print(f"Error: Row index {row_index} is out of bounds for sheet '{sheet_name}'.")
            return False

        # If the column doesn't exist, add it to the DataFrame and fill with empty strings.
        if col_name not in df.columns:
            df[col_name] = ""

        # Update DataFrame using .loc for safe assignment
        df.loc[row_index, col_name] = value
        return True

    def save_data(self):
        """Saves all modified DataFrames back to the Excel file."""
        try:
            with pd.ExcelWriter(self.file_path, engine='openpyxl') as writer:
                for sheet_name, df in self.data_frames.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            return True
        except Exception as e:
            print(f"Error saving Excel file: {e}")
            return False