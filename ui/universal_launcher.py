from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class UniversalLauncher(QWidget):
    """
    A central launcher screen to choose between the available applications.
    """
    def __init__(self, launch_log_analyzer_callback, launch_exec_dashboard_callback):
        super().__init__()
        self.launch_log_analyzer = launch_log_analyzer_callback
        self.launch_exec_dashboard = launch_exec_dashboard_callback

        self.init_ui()

    def init_ui(self):
        """Initializes the UI layout and widgets."""
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)

        title = QLabel("Application Launcher")
        title_font = QFont("Arial", 28, QFont.Bold)
        title.setFont(title_font)
        layout.addWidget(title, alignment=Qt.AlignCenter)

        # Button to launch Kindle Log Analyzer
        log_analyzer_btn = QPushButton("Launch Kindle Log Analyzer")
        log_analyzer_btn.setFont(QFont("Arial", 16))
        log_analyzer_btn.setMinimumSize(400, 100)
        log_analyzer_btn.clicked.connect(self.launch_log_analyzer)
        layout.addWidget(log_analyzer_btn, alignment=Qt.AlignCenter)

        # Button to launch Performance Execution Dashboard
        exec_dashboard_btn = QPushButton("Launch Performance Execution Dashboard")
        exec_dashboard_btn.setFont(QFont("Arial", 16))
        exec_dashboard_btn.setMinimumSize(400, 100)
        exec_dashboard_btn.clicked.connect(self.launch_exec_dashboard)
        layout.addWidget(exec_dashboard_btn, alignment=Qt.AlignCenter)

        self.setStyleSheet("""
            QPushButton {
                background-color: #007BFF;
                color: white;
                border-radius: 8px;
                padding: 15px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QLabel {
                color: #333;
            }
        """)