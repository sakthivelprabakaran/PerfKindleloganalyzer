import traceback
import sys

try:
    from ui.main_window import FinalKindleLogAnalyzer
    print('Import successful')
except Exception as e:
    print('Error type:', type(e).__name__)
    print('Error message:', str(e))
    traceback.print_exc()