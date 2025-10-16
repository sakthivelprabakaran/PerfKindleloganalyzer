from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class UniversalLauncher(QWidget):
    """
    A central launcher screen to choose between the available applications.
    """
    def __init__(self, launch_log_analyzer_callback, launch_exec_dashboard_callback, toggle_dark_mode_callback):
        super().__init__()
        self.launch_log_analyzer = launch_log_analyzer_callback
        self.launch_exec_dashboard = launch_exec_dashboard_callback
        self.toggle_dark_mode = toggle_dark_mode_callback

        self.init_ui()

    def init_ui(self):
        """Initializes the UI layout and widgets."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Top layout for the toggle
        top_layout = QHBoxLayout()
        top_layout.addStretch()
        self.dark_mode_toggle = QCheckBox("Dark Mode")
        self.dark_mode_toggle.toggled.connect(self.toggle_dark_mode)
        top_layout.addWidget(self.dark_mode_toggle)
        main_layout.addLayout(top_layout)

        # Spacer
        main_layout.addStretch(1)

        # Title
        title = QLabel("Application Launcher")
        title_font = QFont("Arial", 28, QFont.Bold)
        title.setFont(title_font)
        main_layout.addWidget(title, alignment=Qt.AlignCenter)

        # Buttons layout
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(30)
        buttons_layout.setAlignment(Qt.AlignCenter)

        # Button to launch Kindle Log Analyzer
        log_analyzer_btn = QPushButton("Launch Kindle Log Analyzer")
        log_analyzer_btn.setFont(QFont("Arial", 16))
        log_analyzer_btn.setMinimumSize(400, 100)
        log_analyzer_btn.clicked.connect(self.launch_log_analyzer)
        buttons_layout.addWidget(log_analyzer_btn)

        # Button to launch Performance Execution Dashboard
        exec_dashboard_btn = QPushButton("Launch Performance Execution Dashboard")
        exec_dashboard_btn.setFont(QFont("Arial", 16))
        exec_dashboard_btn.setMinimumSize(400, 100)
        exec_dashboard_btn.clicked.connect(self.launch_exec_dashboard)
        buttons_layout.addWidget(exec_dashboard_btn)

        main_layout.addLayout(buttons_layout)
        main_layout.addStretch(2)