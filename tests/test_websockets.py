import socketio
import time
import requests
import sys
import os

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SERVER_URL, DEFAULT_PASSWORD

# --- Setup ---
sio_executor = socketio.Client()
sio_auditor = socketio.Client()

executor_token = None
auditor_token = None
executor_username = "TestExecutorWS"
auditor_username = "TestAuditorWS"

def get_token(username, role):
    # 1. Create user (if not exists) - using admin token
    # First get admin token
    admin_resp = requests.post(f"{SERVER_URL}/login", json={"username": "admin", "password": DEFAULT_PASSWORD})
    if admin_resp.status_code != 200:
        print("❌ Failed to login as admin")
        return None
    admin_token = admin_resp.json()["access_token"]
    
    # Create user
    requests.post(f"{SERVER_URL}/users", 
                  json={"username": username, "full_name": f"{username} Full", "role": role, "password": DEFAULT_PASSWORD},
                  headers={"Authorization": f"Bearer {admin_token}"})
                  
    # 2. Login to get token
    resp = requests.post(f"{SERVER_URL}/login", json={"username": username, "password": DEFAULT_PASSWORD})
    if resp.status_code == 200:
        return resp.json()["access_token"]
    else:
        print(f"❌ Failed to login as {username}: {resp.text}")
        return None

# --- Event Handlers ---
@sio_executor.event
def connect():
    print("✅ Executor Connected")

@sio_executor.event
def status_update(data):
    print(f"📩 Executor received status update: {data}")
    if data['status'] == 'Rejected':
        print("✅ SUCCESS: Executor received REJECTION notification!")

@sio_auditor.event
def connect():
    print("✅ Auditor Connected")

@sio_auditor.event
def new_result(data):
    print(f"📊 Auditor received new result: {data}")
    # Auto-reject for testing
    result_id = data['id']
    print(f"🚫 Auditor rejecting result {result_id}...")
    requests.post(f"{SERVER_URL}/update_status/{result_id}", 
                  json={"status": "Rejected", "auditor_comment": "WebSocket Test Rejection"},
                  headers={"Authorization": f"Bearer {auditor_token}"})

# --- Main Test Flow ---
def run_test():
    global executor_token, auditor_token
    
    print("1️⃣  Getting Tokens...")
    executor_token = get_token(executor_username, "executor")
    auditor_token = get_token(auditor_username, "auditor")
    
    if not executor_token or not auditor_token:
        return

    print("2️⃣  Connecting WebSockets...")
    sio_executor.connect(SERVER_URL, auth={'token': executor_token})
    sio_auditor.connect(SERVER_URL, auth={'token': auditor_token})
    
    time.sleep(1)
    
    print("3️⃣  Executor Submitting Result...")
    # Submit via REST (as per design)
    requests.post(f"{SERVER_URL}/submit_result", 
                  json={
                      "test_case_id": "WS-001",
                      "test_case_name": "WebSocket Test Case",
                      "executor_name": executor_username,
                      "value": 99.9
                  },
                  headers={"Authorization": f"Bearer {executor_token}"})
                  
    print("⏳ Waiting for events...")
    time.sleep(5) # Wait for events to propagate
    
    print("4️⃣  Disconnecting...")
    sio_executor.disconnect()
    sio_auditor.disconnect()
    print("✅ Test Complete")

if __name__ == "__main__":
    run_test()
