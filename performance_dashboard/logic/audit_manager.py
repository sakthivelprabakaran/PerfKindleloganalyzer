import pandas as pd
import os

class AuditManager:
    """
    Handles logic for comparing two session files (Current vs Reference/BRD)
    and generating audit statistics.
    """

    def __init__(self):
        pass

    def load_session_data(self, file_path):
        """
        Loads the Excel file and consolidates all sheets into a single DataFrame.
        Returns a DataFrame with columns: ['Test Case ID', 'Test Case Name', 'Average', 'Notes']
        """
        try:
            xls = pd.read_excel(file_path, sheet_name=None, keep_default_na=False)
            all_data = []
            
            for sheet_name, df in xls.items():
                # Ensure required columns exist
                required_cols = ['Test Case ID', 'Test Case Name', 'Average']
                if not all(col in df.columns for col in required_cols):
                    continue
                
                # Add Sheet Name for context if needed, though ID should be unique
                df['Sheet'] = sheet_name
                
                # Handle Notes if present, else empty
                if 'Notes' not in df.columns:
                    df['Notes'] = ''
                
                all_data.append(df[['Test Case ID', 'Test Case Name', 'Average', 'Notes', 'Sheet']])
            
            if not all_data:
                return pd.DataFrame()
                
            return pd.concat(all_data, ignore_index=True)
        except Exception as e:
            print(f"Error loading file {file_path}: {e}")
            return pd.DataFrame()

    def compare_sessions(self, current_path, reference_path):
        """
        Compares the current session against the reference session.
        Returns a DataFrame with comparison results and a stats dictionary.
        """
        current_df = self.load_session_data(current_path)
        ref_df = self.load_session_data(reference_path)

        if current_df.empty or ref_df.empty:
            return pd.DataFrame(), {}

        # Merge on Test Case ID
        # Suffixes: _curr, _ref
        merged_df = pd.merge(
            current_df, 
            ref_df[['Test Case ID', 'Average']], 
            on='Test Case ID', 
            how='inner', 
            suffixes=('_curr', '_ref')
        )

        comparison_results = []
        
        stats = {
            'Green': 0,
            'Yellow': 0,
            'Red': 0,
            'Blocked_NA': 0,
            'Total': 0
        }

        for _, row in merged_df.iterrows():
            tc_id = row['Test Case ID']
            name = row['Test Case Name']
            curr_avg = row['Average_curr']
            ref_avg = row['Average_ref']
            notes = str(row['Notes']).lower()
            
            # Check for Blocked/NA in Notes first
            if 'blocked' in notes or 'na' in notes or 'n/a' in notes:
                status = 'Blocked/NA'
                deviation = 0.0
                category = 'Blocked_NA'
                stats['Blocked_NA'] += 1
            else:
                # Parse values
                try:
                    curr_val = float(curr_avg)
                    ref_val = float(ref_avg)
                    
                    if ref_val == 0:
                        deviation = 0.0 # Avoid division by zero
                    else:
                        deviation = ((curr_val - ref_val) / ref_val) * 100
                    
                    # Categorize
                    if deviation < 0:
                        category = 'Green'
                        stats['Green'] += 1
                    elif 0 <= deviation <= 10:
                        category = 'Yellow'
                        stats['Yellow'] += 1
                    else:
                        category = 'Red'
                        stats['Red'] += 1
                        
                except (ValueError, TypeError):
                    # If values are missing or not numbers, treat as Blocked/NA or skip?
                    # Let's treat as Blocked/NA for safety if we can't compare
                    category = 'Blocked_NA'
                    deviation = 0.0
                    stats['Blocked_NA'] += 1

            comparison_results.append({
                'Test Case ID': tc_id,
                'Test Case Name': name,
                'Current Avg': curr_avg,
                'Reference Avg': ref_avg,
                'Deviation %': round(deviation, 2),
                'Category': category,
                'Notes': row['Notes']
            })
            stats['Total'] += 1

        return pd.DataFrame(comparison_results), stats

    def compare_dataframe_columns(self, df, id_col, ref_col, curr_col, notes_col=None, name_col=None):
        """
        Compares two columns within the same DataFrame.
        """
        comparison_results = []
        stats = {
            'Green': 0,
            'Yellow': 0,
            'Red': 0,
            'Blocked_NA': 0,
            'Total': 0
        }

        for _, row in df.iterrows():
            tc_id = row.get(id_col, 'Unknown')
            name = row.get(name_col, tc_id) if name_col else tc_id 
            
            curr_raw = row.get(curr_col, 0)
            ref_raw = row.get(ref_col, 0)
            notes = str(row.get(notes_col, '')) if notes_col else ''
            
            # Check for Blocked/NA in Notes OR in the Value itself
            curr_str = str(curr_raw).lower()
            if 'blocked' in notes.lower() or 'na' in notes.lower() or 'n/a' in notes.lower() or \
               'blocked' in curr_str or 'na' in curr_str or 'n/a' in curr_str:
                category = 'Blocked_NA'
                deviation = 0.0
                stats['Blocked_NA'] += 1
            else:
                try:
                    curr_val = float(curr_raw)
                    ref_val = float(ref_raw)
                    
                    if ref_val == 0:
                        deviation = 0.0
                    else:
                        deviation = ((curr_val - ref_val) / ref_val) * 100
                    
                    if deviation < 0:
                        category = 'Green'
                        stats['Green'] += 1
                    elif 0 <= deviation <= 10:
                        category = 'Yellow'
                        stats['Yellow'] += 1
                    else:
                        category = 'Red'
                        stats['Red'] += 1
                        
                except (ValueError, TypeError):
                    category = 'Blocked_NA'
                    deviation = 0.0
                    stats['Blocked_NA'] += 1

            comparison_results.append({
                'Test Case ID': tc_id,
                'Test Case Name': name,
                'Current Avg': curr_raw,
                'Reference Avg': ref_raw,
                'Deviation %': round(deviation, 2),
                'Category': category,
                'Notes': notes
            })
            stats['Total'] += 1
            
        return pd.DataFrame(comparison_results), stats
