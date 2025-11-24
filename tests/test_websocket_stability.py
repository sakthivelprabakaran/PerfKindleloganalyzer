#!/usr/bin/env python
"""
WebSocket Stability Test Script
Tests reconnection logic, error handling, and connection states.
"""
import socketio
import time
import subprocess
import signal
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import SERVER_URL, DEFAULT_PASSWORD
import requests

class WebSocketTester:
    def __init__(self):
        self.sio = socketio.Client()
        self.connected = False
        self.disconnected_count = 0
        self.connect_count = 0
        
        # Event handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('connect_error', self.on_connect_error)
    
    def on_connect(self):
        self.connected = True
        self.connect_count += 1
        print(f"✅ Connected (attempt {self.connect_count})")
    
    def on_disconnect(self):
        self.connected = False
        self.disconnected_count += 1
        print(f"❌ Disconnected (total: {self.disconnected_count})")
    
    def on_connect_error(self, error):
        print(f"⚠️ Connection Error: {error}")
    
    def connect(self, token):
        """Connect to the server."""
        try:
            self.sio.connect(SERVER_URL, auth={'token': token}, wait_timeout=10)
            return True
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server."""
        if self.sio.connected:
            self.sio.disconnect()

def get_test_token():
    """Get authentication token for testing."""
    try:
        response = requests.post(f"{SERVER_URL}/login", 
                                json={"username": "admin", "password": DEFAULT_PASSWORD})
        if response.status_code == 200:
            return response.json()["access_token"]
    except Exception as e:
        print(f"Failed to get token: {e}")
    return None

def test_normal_connection():
    """Test 1: Normal connection and disconnection."""
    print("\n" + "="*60)
    print("TEST 1: Normal Connection")
    print("="*60)
    
    token = get_test_token()
    if not token:
        print("❌ FAILED: Could not get auth token")
        return False
    
    tester = WebSocketTester()
    
    if tester.connect(token):
        print("✅ PASSED: Successfully connected")
        time.sleep(2)
        tester.disconnect()
        time.sleep(1)
        
        if not tester.connected:
            print("✅ PASSED: Successfully disconnected")
            return True
        else:
            print("❌ FAILED: Still connected after disconnect")
            return False
    else:
        print("❌ FAILED: Could not connect")
        return False

def test_reconnection_after_server_restart():
    """Test 2: Client reconnects after server restart (manual)."""
    print("\n" + "="*60)
    print("TEST 2: Server Restart Reconnection (Manual)")
    print("="*60)
    print("This test requires manual intervention:")
    print("1. Connect to server")
    print("2. You will have 10 seconds to RESTART the server")
    print("3. Verify client reconnects automatically")
    print("\nPress Enter to start...")
    input()
    
    token = get_test_token()
    if not token:
        print("❌ FAILED: Could not get auth token")
        return False
    
    tester = WebSocketTester()
    
    if not tester.connect(token):
        print("❌ FAILED: Initial connection failed")
        return False
    
    print("✅ Connected. NOW RESTART THE SERVER (you have 10 seconds)...")
    time.sleep(10)
    
    print("Waiting 30 seconds for reconnection...")
    time.sleep(30)
    
    if tester.connect_count > 1:
        print(f"✅ PASSED: Reconnected successfully ({tester.connect_count} total connections)")
        return True
    else:
        print(f"❌ FAILED: No reconnection detected ({tester.connect_count} total connections)")
        return False

def test_invalid_token():
    """Test 3: Connection with invalid token."""
    print("\n" + "="*60)
    print("TEST 3: Invalid Token Handling")
    print("="*60)
    
    tester = WebSocketTester()
    
    if tester.connect("invalid_token_12345"):
        print("❌ FAILED: Connected with invalid token (should have failed)")
        return False
    else:
        print("✅ PASSED: Correctly rejected invalid token")
        return True

def main():
    print("WebSocket Stability Test Suite")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(("Normal Connection", test_normal_connection()))
    results.append(("Invalid Token", test_invalid_token()))
    results.append(("Server Restart Reconnection", test_reconnection_after_server_restart()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
