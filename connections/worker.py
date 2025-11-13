from PyQt5.QtCore import QThread, pyqtSignal
from connections.ssh_connection import SshConnection
import time


class ConnectionWorker(QThread):
    data_received = pyqtSignal(str)
    connection_error = pyqtSignal(str)
    connection_lost = pyqtSignal()

    def __init__(self, connection):
        super().__init__()
        self.connection = connection
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                if not self.connection.connected:
                    if isinstance(self.connection, SshConnection) and self.connection.profile.auto_reconnect:
                        self.data_received.emit("Connection lost. Attempting to reconnect...\n")
                        self.connection.connect()
                        if self.connection.connected:
                            self.data_received.emit("Reconnected.\n")
                        else:
                            time.sleep(5)
                    else:
                        self.connection_lost.emit()
                        self.running = False
                        continue

                data = self.connection.read()
                if data:
                    self.data_received.emit(data.decode("utf-8", errors="ignore"))
                else:
                    self.msleep(100)  # Small delay to prevent busy-waiting
            except Exception as e:
                self.connection_error.emit(str(e))
                self.running = False

    def stop(self):
        self.running = False
