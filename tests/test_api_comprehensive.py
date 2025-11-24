#!/usr/bin/env python3
"""
Comprehensive API Test Suite for Live Audit Server
Tests all endpoints, BRD validation, username normalization, and error handling
"""

import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
import time
from datetime import datetime
import openpyxl
from openpyxl import Workbook
from config import SERVER_URL, DEFAULT_PASSWORD, REQUEST_TIMEOUT

# Configuration
# SERVER_URL imported from config
TEST_RESULTS = []

# Global tokens
ADMIN_TOKEN = None
EXECUTOR_TOKEN = None
AUDITOR_TOKEN = None

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def get_auth_token(username, password):
    """Helper to get JWT token."""
    try:
        response = requests.post(f"{SERVER_URL}/login", json={
            "username": username,
            "password": password
        }, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            print(f"DEBUG: Login failed for {username}. Status: {response.status_code}, Body: {response.text}")
    except Exception as e:
        print(f"DEBUG: Login exception for {username}: {e}")
    return None

def log_test(test_name, passed, message=""):
    """Log test result."""
    status = f"{Colors.GREEN}✓ PASS{Colors.END}" if passed else f"{Colors.RED}✗ FAIL{Colors.END}"
    print(f"{status} - {test_name}")
    if message:
        print(f"      {message}")
    TEST_RESULTS.append({"test": test_name, "passed": passed, "message": message})

def test_server_health():
    """Test 1: Server is running and responding."""
    try:
        response = requests.get(f"{SERVER_URL}/users", timeout=5)
        log_test("Server Health Check", response.status_code in [200, 404], 
                f"Status: {response.status_code}")
        return True
    except requests.exceptions.ConnectionError:
        log_test("Server Health Check", False, "Server not responding")
        return False

def test_create_user(username, role, password="password123"):
    """Test user creation endpoint."""
    global ADMIN_TOKEN
    
    # We need an admin token to create users. 
    # If we don't have one, we can't proceed.
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"} if ADMIN_TOKEN else {}
    
    payload = {
        "username": username,
        "full_name": f"Test {role.capitalize()}",
        "role": role,
        "password": password
    }
    try:
        response = requests.post(f"{SERVER_URL}/users", json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            log_test(f"Create User: {username}", True, f"Created (ID: {response.json()['id']})")
            return True
        elif response.status_code == 400:
            log_test(f"Create User: {username}", True, f"Status: 400 (Already exists - OK)")
            return True
        else:
            log_test(f"Create User: {username}", False, f"Status: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        log_test(f"Create User: {username}", False, str(e))
        return False

def test_create_users():
    """Test 2: User creation with various usernames."""
    global ADMIN_TOKEN, EXECUTOR_TOKEN, AUDITOR_TOKEN
    
    test_users = [
        {"username": "TestExecutor1", "full_name": "Test Executor One", "role": "executor"},
        {"username": "testauditor1", "full_name": "Test Auditor One", "role": "auditor"},
        {"username": "ADMIN_USER", "full_name": "Admin User", "role": "admin"}
    ]

    # First, ensure an admin user exists and we have a token for it.
    # The server creates a default 'admin' user on startup.
    # We should use that to bootstrap.
    
    log_test("Bootstrap Admin Login", True, "Attempting to login as default 'admin'...")
    ADMIN_TOKEN = get_auth_token("admin", DEFAULT_PASSWORD)
    
    if not ADMIN_TOKEN:
        log_test("Bootstrap Admin Login", False, "Failed to login as default 'admin'. Tests will fail.")
        return

    log_test("Bootstrap Admin Login", True, "ADMIN_TOKEN obtained.")

    # Now create other users using the admin token
    test_create_user("TestExecutor1", "executor", DEFAULT_PASSWORD)
    test_create_user("testauditor1", "auditor", DEFAULT_PASSWORD)
    # We don't need to create ADMIN_USER anymore, we use 'admin'
    
    # Get tokens for other users
    EXECUTOR_TOKEN = get_auth_token("TestExecutor1", DEFAULT_PASSWORD)
    AUDITOR_TOKEN = get_auth_token("testauditor1", DEFAULT_PASSWORD)

    if not EXECUTOR_TOKEN:
        log_test("Executor Login", False, "Failed to get EXECUTOR_TOKEN.")
    else:
        log_test("Executor Login", True, "EXECUTOR_TOKEN obtained.")

    if not AUDITOR_TOKEN:
        log_test("Auditor Login", False, "Failed to get AUDITOR_TOKEN.")
    else:
        log_test("Auditor Login", True, "AUDITOR_TOKEN obtained.")

def test_login_check():
    """Test login functionality."""
    # Valid Login
    try:
        response = requests.post(f"{SERVER_URL}/login", json={
            "username": "TestExecutor1",
            "password": DEFAULT_PASSWORD
        }, timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            log_test("Login (Valid)", True, "Authenticated successfully")
        else:
            log_test("Login (Valid)", False, f"Status: {response.status_code}, {response.text}")
    except Exception as e:
        log_test("Login (Valid)", False, str(e))

    # Test invalid password
    try:
        response = requests.post(f"{SERVER_URL}/login", json={
            "username": "ADMIN_USER",
            "password": "WrongPassword"
        }, timeout=5)
        success = response.status_code == 401
        log_test("Login (Invalid Password)", success, "Rejected correctly")
    except Exception as e:
        log_test("Login (Invalid Password)", False, str(e))

def test_username_normalization():
    """Test 3: Username normalization (case-insensitive)."""
    global EXECUTOR_TOKEN
    headers = {"Authorization": f"Bearer {EXECUTOR_TOKEN}"} if EXECUTOR_TOKEN else {}

    # Try fetching with different cases
    test_cases = [
        ("testexecutor1", "lowercase"),
        ("TestExecutor1", "mixed case"),
        ("TESTEXECUTOR1", "uppercase")
    ]
    
    for username, case_type in test_cases:
        try:
            # This endpoint might require authentication for the user whose tasks are being fetched
            response = requests.get(f"{SERVER_URL}/my_tasks/{username}", headers=headers, timeout=5)
            success = response.status_code == 200
            log_test(f"Username Normalization: {case_type}", success, 
                    f"Query '{username}' → Status: {response.status_code}")
        except Exception as e:
            log_test(f"Username Normalization: {case_type}", False, str(e))

def test_create_project():
    """Test 4: Project creation."""
    global ADMIN_TOKEN
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"} if ADMIN_TOKEN else {}

    project = {"name": "TestProject", "description": "Test project for automated testing"}
    
    try:
        response = requests.post(f"{SERVER_URL}/projects", json=project, headers=headers, timeout=5)
        # Success if 200 (created) or 400 (already exists)
        success = response.status_code in [200, 400]
        msg = f"Status: {response.status_code}"
        if response.status_code == 400:
            msg += " (Already exists - OK)"
            
        log_test("Create Project", success, msg)
        return success
    except Exception as e:
        log_test("Create Project", False, str(e))
        return False

def test_create_task_assignment():
    """Test 5: Task assignment creation."""
    global ADMIN_TOKEN
    headers = {"Authorization": f"Bearer {ADMIN_TOKEN}"} if ADMIN_TOKEN else {}

    assignment = {
        "project": "TestProject",
        "suite": "P0",
        "executor_username": "testexecutor1",  # lowercase to test normalization
        "auditor_username": "testauditor1"
    }
    
    try:
        response = requests.post(f"{SERVER_URL}/task_assignments", json=assignment, headers=headers, timeout=5)
        success = response.status_code == 200
        log_test("Create Task Assignment", success, f"Status: {response.status_code}")
        return success
    except Exception as e:
        log_test("Create Task Assignment", False, str(e))
        return False

def create_test_brd(filename="test_brd.xlsx"):
    """Create a valid test BRD Excel file."""
    wb = Workbook()
    ws = wb.active
    ws.title = "P0"
    
    # Headers
    ws['A1'] = 'Test Case ID'
    ws['B1'] = 'Test Case Name'
    ws['C1'] = 'Reference Value'
    
    # Test data
    test_cases = [
        ('P01', 'Wake-up time', 0.655),
        ('P03', 'Warm Book Open', 0.529),
        ('P05', 'Page Turn', 0.312),
    ]
    
    for idx, (tc_id, tc_name, ref_val) in enumerate(test_cases, start=2):
        ws[f'A{idx}'] = tc_id
        ws[f'B{idx}'] = tc_name
        ws[f'C{idx}'] = ref_val
    
    wb.save(filename)
    return filename

def create_invalid_brd(filename="invalid_brd.xlsx"):
    """Create an invalid BRD Excel file (wrong columns)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "P0"
    
    # Wrong headers
    ws['A1'] = 'TC ID'  # Wrong name
    ws['B1'] = 'Name'   # Wrong name
    ws['C1'] = 'Value'  # Wrong name
    
    wb.save(filename)
    return filename

def test_brd_upload_valid():
    """Test 6: Valid BRD upload."""
    global AUDITOR_TOKEN
    brd_file = create_test_brd()
    
    try:
        with open(brd_file, 'rb') as f:
            files = {'file': (brd_file, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            data = {
                'auditor_username': 'testauditor1',
                'project': 'TestProject',
                'suite': 'P0',
                'token': AUDITOR_TOKEN
            }
            response = requests.post(f"{SERVER_URL}/upload_brd", files=files, data=data, timeout=10)
            success = response.status_code == 200
            
            if success:
                result = response.json()
                version = result.get('version', 'unknown')
                log_test("BRD Upload (Valid)", success, f"Version: {version}")
            else:
                log_test("BRD Upload (Valid)", success, f"Status: {response.status_code}, {response.text}")
    except Exception as e:
        log_test("BRD Upload (Valid)", False, str(e))
    finally:
        if os.path.exists(brd_file):
            os.remove(brd_file)

def test_brd_upload_invalid():
    """Test 7: Invalid BRD upload (should be rejected)."""
    global AUDITOR_TOKEN
    brd_file = create_invalid_brd()
    
    try:
        with open(brd_file, 'rb') as f:
            files = {'file': (brd_file, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            data = {
                'auditor_username': 'testauditor1',
                'project': 'TestProject',
                'suite': 'P0',
                'token': AUDITOR_TOKEN # Pass token in body
            }
            response = requests.post(f"{SERVER_URL}/upload_brd", files=files, data=data, timeout=10)
            # Should fail with 400
            success = response.status_code == 400
            log_test("BRD Upload (Invalid - Should Reject)", success, 
                    f"Expected 400, got {response.status_code}")
    except Exception as e:
        log_test("BRD Upload (Invalid - Should Reject)", False, str(e))
    finally:
        if os.path.exists(brd_file):
            os.remove(brd_file)

def test_brd_versioning():
    """Test 8: BRD versioning (upload same suite twice)."""
    global AUDITOR_TOKEN
    brd_file = create_test_brd("test_brd_v2.xlsx")
    
    try:
        # Upload same BRD again
        with open(brd_file, 'rb') as f:
            files = {'file': (brd_file, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
            data = {
                'auditor_username': 'testauditor1',
                'project': 'TestProject',
                'suite': 'P0',
                'token': AUDITOR_TOKEN
            }
            response = requests.post(f"{SERVER_URL}/upload_brd", files=files, data=data, timeout=10)
            success = response.status_code == 200
            
            if success:
                result = response.json()
                version = result.get('version', 0)
                # Should be version 2 or higher
                version_incremented = version >= 2
                log_test("BRD Versioning", version_incremented, 
                        f"Version {version} (expected ≥2)")
            else:
                log_test("BRD Versioning", False, f"Status: {response.status_code}")
    except Exception as e:
        log_test("BRD Versioning", False, str(e))
    
    payload = {
        "test_case_id": "P0_001",
        "test_case_name": "Login Test",
        "executor_name": "TestExecutor1",
        "value": 1.55 # Slightly higher than ref 1.5
    }
    try:
        # Use EXECUTOR_TOKEN for submit_result
        headers = {"Authorization": f"Bearer {EXECUTOR_TOKEN}"} if EXECUTOR_TOKEN else {}
        response = requests.post(f"{SERVER_URL}/submit_result", json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            log_test("Submit Result with BRD Comparison", True, f"BRD: {data.get('brd_reference')}, Deviation: {data.get('deviation_percent')}%")
            return True
        else:
            log_test("Submit Result with BRD Comparison", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Submit Result with BRD Comparison", False, str(e))
        return False

def test_submit_result():
    """Test 9: Submit test result."""
    global EXECUTOR_TOKEN
    
    payload = {
        "test_case_id": "P0_001",
        "test_case_name": "Login Test",
        "executor_name": "TestExecutor1",
        "value": 1.55 # Slightly higher than ref 1.5
    }
    try:
        # Use EXECUTOR_TOKEN for submit_result
        headers = {"Authorization": f"Bearer {EXECUTOR_TOKEN}"} if EXECUTOR_TOKEN else {}
        response = requests.post(f"{SERVER_URL}/submit_result", json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
        if response.status_code == 200:
            data = response.json()
            log_test("Submit Result with BRD Comparison", True, f"BRD: {data.get('brd_reference')}, Deviation: {data.get('deviation_percent')}%")
            return True
        else:
            log_test("Submit Result with BRD Comparison", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Submit Result with BRD Comparison", False, str(e))
        return False

def test_live_dashboard():
    """Test 10: Live dashboard endpoint."""
    try:
        response = requests.get(f"{SERVER_URL}/live_dashboard", timeout=5)
        success = response.status_code == 200
        
        if success:
            data = response.json()
            count = len(data)
            log_test("Live Dashboard", success, f"Retrieved {count} results")
        else:
            log_test("Live Dashboard", success, f"Status: {response.status_code}")
    except Exception as e:
        log_test("Live Dashboard", False, str(e))

def test_network_timeout():
    """Test 11: Network timeout handling (should complete within 10s)."""
    try:
        start = time.time()
        response = requests.get(f"{SERVER_URL}/users", timeout=10)
        elapsed = time.time() - start
        
        # Should respond quickly (< 1s for local)
        success = elapsed < 5.0
        log_test("Network Response Time", success, f"{elapsed:.2f}s (< 5s expected)")
    except Exception as e:
        log_test("Network Response Time", False, str(e))

def test_get_assignments():
    """Test 12: Get assignments for executor and auditor."""
    test_cases = [
        ("my_tasks/testexecutor1", "Executor Tasks"),
        ("my_audits/testauditor1", "Auditor Tasks"),
    ]
    
    for endpoint, name in test_cases:
        try:
            response = requests.get(f"{SERVER_URL}/{endpoint}", timeout=5)
            success = response.status_code == 200
            
            if success:
                data = response.json()
                count = len(data)
                log_test(f"Get {name}", success, f"Found {count} tasks")
            else:
                log_test(f"Get {name}", success, f"Status: {response.status_code}")
        except Exception as e:
            log_test(f"Get {name}", False, str(e))

def print_summary():
    """Print test summary."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}TEST SUMMARY{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")
    
    total = len(TEST_RESULTS)
    passed = sum(1 for r in TEST_RESULTS if r['passed'])
    failed = total - passed
    pass_rate = (passed / total * 100) if total > 0 else 0
    
    print(f"\n{Colors.GREEN}✓ Passed: {passed}{Colors.END}")
    print(f"{Colors.RED}✗ Failed: {failed}{Colors.END}")
    print(f"Pass Rate: {pass_rate:.1f}%")
    
    if failed > 0:
        print(f"\n{Colors.RED}Failed Tests:{Colors.END}")
        for result in TEST_RESULTS:
            if not result['passed']:
                print(f"  - {result['test']}")
                if result['message']:
                    print(f"    {result['message']}")
    
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}\n")
    
    return passed, failed

def main():
    """Run all tests."""
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}LIVE AUDIT SERVER - COMPREHENSIVE API TEST SUITE{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}\n")
    print(f"Server: {SERVER_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Run tests
    if not test_server_health():
        print(f"\n{Colors.RED}✗ Server not responding. Please start the server first.{Colors.END}\n")
        return
    
    print(f"\n{Colors.YELLOW}Running tests...{Colors.END}\n")
    
    test_create_users()
    test_login_check()
    test_username_normalization()
    test_create_project()
    test_create_task_assignment()
    test_brd_upload_valid()
    test_brd_upload_invalid()
    test_brd_versioning()
    test_submit_result()
    test_live_dashboard()
    test_network_timeout()
    test_get_assignments()
    
    # Summary
    passed, failed = print_summary()
    
    # Exit code
    exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    main()
