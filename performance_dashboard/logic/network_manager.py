import requests
import socketio
import threading
import time
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QMetaObject, Qt
from config import SERVER_URL, REQUEST_TIMEOUT

class NetworkManager(QObject):
    """
    Handles communication with the Live Audit Server using WebSockets.
    Includes automatic reconnection with exponential backoff.
    """
    # Signals for UI updates
    connection_status = pyqtSignal(str, str)  # state, message
    notification_received = pyqtSignal(dict)   # notification data
    dashboard_update = pyqtSignal(dict)        # new result data
    _schedule_reconnect_signal = pyqtSignal(int)  # Internal signal for thread-safe reconnection

    # Connection states
    STATE_DISCONNECTED = "disconnected"
    STATE_CONNECTING = "connecting"
    STATE_CONNECTED = "connected"
    STATE_FAILED = "failed"

    def __init__(self, executor_name, token=None):
        super().__init__()
        self.executor_name = executor_name
        self.token = token
        self.server_url = "http://localhost:8000"
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.timeout = REQUEST_TIMEOUT
        
        # Connection state management
        self.connection_state = self.STATE_DISCONNECTED
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 1  # Start with 1 second
        self.max_reconnect_delay = 30  # Max 30 seconds
        
        # Socket.IO Client
        self.sio = socketio.Client(reconnection=False)  # We'll handle reconnection manually
        
        # Setup Event Handlers
        self.sio.on('connect', self.on_connect)
        self.sio.on('disconnect', self.on_disconnect)
        self.sio.on('connect_error', self.on_connect_error)
        self.sio.on('status_update', self.on_status_update)
        self.sio.on('new_result', self.on_new_result)
        
        # Reconnection timer
        self.reconnect_timer = QTimer()
        self.reconnect_timer.setSingleShot(True)
        self.reconnect_timer.timeout.connect(self._attempt_reconnect)
        
        # Connect internal signal for thread-safe timer scheduling
        self._schedule_reconnect_signal.connect(self._start_reconnect_timer)
        
        # Start connection in a separate thread to avoid blocking UI
        # self.connect_thread = threading.Thread(target=self.connect_socket, daemon=True)
        # self.connect_thread.start()

    def connect(self):
        """Explicitly start the connection process."""
        if not hasattr(self, 'connect_thread') or not self.connect_thread.is_alive():
            self.connect_thread = threading.Thread(target=self.connect_socket, daemon=True)
            self.connect_thread.start()

    def log(self, message):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] NetworkManager: {message}")

    def connect_socket(self):
        """Establishes WebSocket connection."""
        if self.connection_state == self.STATE_CONNECTING:
            return  # Already connecting
            
        self.connection_state = self.STATE_CONNECTING
        self.connection_status.emit(self.STATE_CONNECTING, "Connecting to server...")
        self.log("Attempting to connect...")
        
        try:
            # Pass token in auth dictionary
            auth_data = {'token': self.token} if self.token else {}
            self.sio.connect(self.server_url, auth=auth_data, wait_timeout=10)
        except Exception as e:
            self.log(f"Connection failed: {e}")
            self.on_connect_error(str(e))

    def on_connect(self):
        """Called when WebSocket connects successfully."""
        self.log("✅ Connected successfully")
        self.connection_state = self.STATE_CONNECTED
        self.reconnect_attempts = 0  # Reset counter on successful connection
        self.reconnect_delay = 1  # Reset delay
        self.connection_status.emit(self.STATE_CONNECTED, "Connected")

    def on_disconnect(self):
        """Called when WebSocket disconnects."""
        self.log("❌ Disconnected from server")
        
        if self.connection_state == self.STATE_CONNECTED:
            # Unexpected disconnect - attempt to reconnect
            self.connection_state = self.STATE_DISCONNECTED
            self.connection_status.emit(self.STATE_DISCONNECTED, "Connection lost")
            self.schedule_reconnect()
        else:
            self.connection_state = self.STATE_DISCONNECTED
            self.connection_status.emit(self.STATE_DISCONNECTED, "Disconnected")

    def on_connect_error(self, error):
        """Handle connection errors."""
        self.log(f"⚠️ Connection error: {error}")
        self.connection_state = self.STATE_DISCONNECTED
        
        if self.reconnect_attempts < self.max_reconnect_attempts:
            self.connection_status.emit(self.STATE_DISCONNECTED, f"Connection failed - retrying...")
            self.schedule_reconnect()
        else:
            self.connection_state = self.STATE_FAILED
            self.connection_status.emit(
                self.STATE_FAILED, 
                f"Connection failed after {self.max_reconnect_attempts} attempts. Please check server and try again."
            )
            self.log(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) reached")

    def schedule_reconnect(self):
        """Schedule reconnection with exponential backoff."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            return
            
        self.reconnect_attempts += 1
        delay_ms = min(self.reconnect_delay * 1000, self.max_reconnect_delay * 1000)
        
        self.log(f"🔄 Scheduling reconnect attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} in {self.reconnect_delay}s")
        
        # Emit signal to start timer (thread-safe)
        self._schedule_reconnect_signal.emit(int(delay_ms))
        
        # Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay)
    
    def _start_reconnect_timer(self, delay_ms):
        """Start the reconnect timer (called in main thread via signal)."""
        self.reconnect_timer.start(delay_ms)

    def _attempt_reconnect(self):
        """Internal method to attempt reconnection (called by timer)."""
        self.log("Attempting reconnection...")
        self.connect_thread = threading.Thread(target=self.connect_socket, daemon=True)
        self.connect_thread.start()

    def on_status_update(self, data):
        """Handle status update (Rejection/Approval) from server."""
        try:
            self.log(f"📩 Received status update: {data.get('test_case_name', 'Unknown')} - {data.get('status')}")
            
            if data.get('status') == 'Rejected':
                msg = f"Test Case '{data.get('test_case_name')}' was REJECTED.\nComment: {data.get('auditor_comment')}"
                
                # Emit full notification object for the panel
                self.notification_received.emit({
                    "title": "Audit Alert",
                    "message": msg,
                    "timestamp": data.get('timestamp', datetime.now().isoformat()),
                    "status": "Rejected",
                    "details": data
                })
        except Exception as e:
            self.log(f"Error handling status_update: {e}")

    def on_new_result(self, data):
        """Handle new result broadcast (for Auditor Dashboard)."""
        try:
            self.log(f"📊 New result received: {data.get('test_case_name', 'Unknown')}")
            self.dashboard_update.emit(data)
        except Exception as e:
            self.log(f"Error handling new_result: {e}")

    def join_assignment_room(self, project, suite):
        """Join a specific assignment room to receive updates."""
        if self.connection_state == self.STATE_CONNECTED:
            try:
                self.sio.emit('join_assignment_room', {'project': project, 'suite': suite})
                self.log(f"Joined room: {project}_{suite}")
            except Exception as e:
                self.log(f"Error joining room: {e}")

    def stop_polling(self):
        """Disconnects the socket (legacy name kept for compatibility)."""
        self.log("Disconnecting...")
        self.reconnect_timer.stop()  # Stop any pending reconnection
        
        # Set state to DISCONNECTED to prevent on_disconnect from triggering reconnect
        self.connection_state = self.STATE_DISCONNECTED
        
        if self.sio.connected:
            try:
                self.sio.disconnect()
            except Exception as e:
                self.log(f"Error during disconnect: {e}")

    def submit_result(self, test_case_id, test_case_name, value, suite_name="Performance", project_name="KindleLogAnalyzer"):
        """Submits a test result to the server."""
        try:
            # Ensure value is a float string
            value_float = float(value)
            
            data = {
                "test_case_id": test_case_id,
                "test_case_name": test_case_name,
                "value": value_float,
                "executor_name": self.executor_name,
                "project_name": project_name,
                "suite_name": suite_name
            }
            
            self.log(f"Submitting result: {test_case_name} = {value_float} (suite: {suite_name})")
            response = requests.post(
                f"{self.server_url}/submit_result", 
                json=data,
                headers=self.headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.log(f"✅ Submitted result: {test_case_id}")
                return True
            else:
                self.log(f"❌ Submission failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.log(f"❌ Error submitting result: {e}")
            return False

    def fetch_notifications(self):
        """Fetches missed notifications (Rejected/Unread) from server."""
        try:
            url = f"{self.server_url}/notifications/{self.executor_name}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                notifications = response.json()
                self.log(f"Fetched {len(notifications)} missed notifications")
                return notifications
            else:
                self.log(f"Failed to fetch notifications: {response.status_code}")
                return []
        except Exception as e:
            self.log(f"Error fetching notifications: {e}")
            return []

    def mark_read(self, result_id):
        """Marks a notification as read."""
        try:
            url = f"{self.server_url}/mark_read/{result_id}"
            response = requests.post(url, headers=self.headers, timeout=self.timeout)
            response.raise_for_status() # Raise an exception for bad status codes
            self.log(f"✅ Marked notification {result_id} as read")
        except Exception as e:
            self.log(f"❌ Error marking result {result_id} as read: {e}")

    def fetch_dashboard_data(self):
        """Fetches initial dashboard data via REST."""
        try:
            response = requests.get(
                f"{self.server_url}/live_dashboard", 
                headers=self.headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log(f"Error fetching dashboard data: {e}")
            return []

    def update_status(self, result_id, status, comment):
        """Updates the status of a test result (Approve/Reject) via REST."""
        try:
            payload = {"status": status, "auditor_comment": comment}
            response = requests.post(
                f"{self.server_url}/update_status/{result_id}", 
                json=payload, 
                headers=self.headers, 
                timeout=self.timeout
            )
            response.raise_for_status()
            self.log(f"✅ Updated status for result {result_id}: {status}")
            return True
        except Exception as e:
            self.log(f"❌ Error updating status: {e}")
            return False
