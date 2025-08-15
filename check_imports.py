import ui.main_window
import inspect
import re

# Check the source code of the module for any unusual patterns
source = inspect.getsource(ui.main_window)
lines = source.split('\n')

print("Checking for 'from util' or 'import util' patterns:")
for i, line in enumerate(lines, 1):
    if 'from util' in line or 'import util' in line:
        print(f'Line {i}: {line}')
        
print("\nChecking for incomplete imports:")
# Also check for any incomplete imports
for i, line in enumerate(lines, 1):
    if re.search(r'from\s+\w*\.\.*', line) or re.search(r'import\s+\w*\.\.*', line):
        print(f'Potential incomplete import at line {i}: {line}')
        
print("\nChecking for any lines with ellipsis or truncated imports:")
for i, line in enumerate(lines, 1):
    if '...' in line and ('from' in line or 'import' in line):
        print(f'Line with ellipsis at line {i}: {line}')