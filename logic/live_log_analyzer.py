from PyQt5.QtCore import QObject, pyqtSignal
import re


def process_log_line(line: str) -> dict:
    """
    This is a placeholder function to process a single log line.
    The user should replace this with their actual log analysis logic.
    """
    if "error" in line.lower():
        return {"type": "error", "content": line}
    if "warning" in line.lower():
        return {"type": "warning", "content": line}
    return None


class LiveLogAnalyzer(QObject):
    """
    Manages the live analysis of log data.
    """

    result_ready = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.buffer = ""
        self.is_active = False

    def start(self):
        """Activates the log analysis."""
        self.is_active = True

    def stop(self):
        """Deactivates the log analysis."""
        self.is_active = False

    def process_data(self, data: str):
        """
        Processes incoming data, which may contain partial lines.
        """
        if not self.is_active:
            return

        self.buffer += data
        lines = self.buffer.split("\n")
        self.buffer = lines.pop()  # Keep the last, possibly partial, line

        for line in lines:
            if line.strip():
                result = process_log_line(line)
                if result:
                    self.result_ready.emit(result)
