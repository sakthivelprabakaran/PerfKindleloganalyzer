import requests
from PyQt5.QtCore import QObject, pyqtSignal, QTimer

class NetworkManager(QObject):
    """
    Handles communication with the Live Audit Server.
    Uses QTimer for polling to avoid thread issues.
    """
    notification_received = pyqtSignal(str, str) # title, message

    def __init__(self, server_url="http://localhost:8000", executor_name="Executor"):
        super().__init__()
        self.server_url = server_url
        self.executor_name = executor_name
        self.timeout = 10  # 10 second timeout for all requests
        
        # Use QTimer instead of background thread
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self._poll_notifications)
        self.poll_timer.setInterval(10000) # 10 seconds
        
        self.seen_notification_ids = set() # Track which notifications we've already shown

    def start_polling(self):
        """Starts the polling timer."""
        if not self.poll_timer.isActive():
            self.poll_timer.start()

    def stop_polling(self):
        """Stops the polling timer."""
        self.poll_timer.stop()

    def submit_result(self, test_case_id, test_case_name, value):
        """Submits a test result to the server."""
        try:
            payload = {
                "test_case_id": str(test_case_id),
                "test_case_name": str(test_case_name),
                "executor_name": self.executor_name,
                "value": float(value) if isinstance(value, (int, float)) else 0.0
            }
            # Send immediately (synchronous is fine since it's fast)
            requests.post(f"{self.server_url}/submit_result", json=payload, timeout=self.timeout)
        except Exception as e:
            print(f"Failed to submit result: {e}")

    def _poll_notifications(self):
        """Polls for notifications (called by QTimer)."""
        try:
            response = requests.get(f"{self.server_url}/notifications/{self.executor_name}", timeout=self.timeout)
            if response.status_code == 200:
                notifications = response.json()
                for note in notifications:
                    note_id = note['id']
                    # Only show notifications we haven't seen yet
                    if note_id not in self.seen_notification_ids:
                        self.seen_notification_ids.add(note_id)
                        msg = f"Test Case '{note['test_case_name']}' was REJECTED.\\nComment: {note['auditor_comment']}"
                        self.notification_received.emit("Audit Alert", msg)
                        
                        # Mark as read
                        requests.post(f"{self.server_url}/mark_read/{note_id}", timeout=self.timeout)
        except Exception as e:
            print(f"Polling error: {e}")

    def fetch_dashboard_data(self):
        """Fetches all latest results for the Auditor dashboard."""
        try:
            response = requests.get(f"{self.server_url}/live_dashboard", timeout=self.timeout)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Fetch error: {e}")
        return []

    def update_status(self, result_id, status, comment):
        """Updates the status of a test result (Approve/Reject)."""
        try:
            payload = {"status": status, "auditor_comment": comment}
            requests.post(f"{self.server_url}/update_status/{result_id}", json=payload, timeout=self.timeout)
            return True
        except Exception as e:
            print(f"Update error: {e}")
            return False
