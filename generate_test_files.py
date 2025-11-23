import pandas as pd

def generate_files():
    # 1. Reference / BRD File
    ref_data = {
        'Test Case ID': ['TC_001', 'TC_002', 'TC_003', 'TC_004', 'TC_005'],
        'Test Case Name': [
            'App Launch Cold', 
            'Page Turn Forward', 
            'Search Query', 
            'Menu Open', 
            'Library Scroll'
        ],
        'Average': [5.0, 1.0, 2.0, 0.5, 3.0], # Seconds
        'Notes': ['', '', '', '', '']
    }
    ref_df = pd.DataFrame(ref_data)
    ref_df.to_excel("Reference_BRD.xlsx", index=False)
    print("Created Reference_BRD.xlsx")

    # 2. Current Session File
    curr_data = {
        'Test Case ID': ['TC_001', 'TC_002', 'TC_003', 'TC_004', 'TC_005'],
        'Test Case Name': [
            'App Launch Cold', 
            'Page Turn Forward', 
            'Search Query', 
            'Menu Open', 
            'Library Scroll'
        ],
        'Average': [
            4.0,   # TC_001: 4.0 vs 5.0 (-20%) -> GREEN (Improved)
            1.05,  # TC_002: 1.05 vs 1.0 (+5%) -> YELLOW (Acceptable)
            3.0,   # TC_003: 3.0 vs 2.0 (+50%) -> RED (Regression)
            0.0,   # TC_004: Blocked
            0.0    # TC_005: NA
        ],
        'Notes': [
            'Optimized startup', 
            'Slight regression', 
            'Major regression detected', 
            'Blocked: Feature not ready', 
            'NA: Not applicable for this device'
        ]
    }
    curr_df = pd.DataFrame(curr_data)
    curr_df.to_excel("Current_Session.xlsx", index=False)
    print("Created Current_Session.xlsx")

if __name__ == "__main__":
    generate_files()
