import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QGroupBox, QFrame
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont

class LauncherScreen(QWidget):
    """The main launcher screen for the application."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Sets up the UI of the widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        title = QLabel("Kindle Log Analyzer & Execution Dashboard")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Main options layout
        options_layout = QHBoxLayout()
        options_layout.setSpacing(20)

        # Left side for actions
        actions_group = QGroupBox("Start Here")
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(15)

        self.log_analyzer_btn = QPushButton("Open Kindle Log Analyzer")
        self.log_analyzer_btn.setIconSize(QSize(32, 32))
        self.log_analyzer_btn.setMinimumHeight(60)

        self.new_session_btn = QPushButton("Start New Test Session")
        self.new_session_btn.setIconSize(QSize(32, 32))
        self.new_session_btn.setMinimumHeight(60)

        actions_layout.addWidget(self.log_analyzer_btn)
        actions_layout.addWidget(self.new_session_btn)
        actions_layout.addStretch()

        # Right side for recent sessions
        recent_group = QGroupBox("Recent Sessions")
        recent_layout = QVBoxLayout(recent_group)
        self.recent_sessions_list = QListWidget()
        recent_layout.addWidget(self.recent_sessions_list)

        options_layout.addWidget(actions_group, 1)
        options_layout.addWidget(recent_group, 1)

        main_layout.addLayout(options_layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    screen = LauncherScreen()
    # Add dummy data for testing
    screen.recent_sessions_list.addItem("P0 - Kindle Scribe - Week_01")
    screen.recent_sessions_list.addItem("P1 - Kindle Paperwhite - Week_01")
    screen.show()
    sys.exit(app.exec_())