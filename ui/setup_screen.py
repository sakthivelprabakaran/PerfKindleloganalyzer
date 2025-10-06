import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QGroupBox, QFileDialog, QSpinBox
)
from PyQt5.QtCore import Qt

class SetupScreen(QWidget):
    """A screen for setting up a new test execution session."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Sets up the UI of the widget."""
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        setup_group = QGroupBox("🚀 New Test Execution Session")
        setup_group.setFixedWidth(500)
        setup_layout = QVBoxLayout(setup_group)

        # Back Button
        back_layout = QHBoxLayout()
        self.back_btn = QPushButton("<< Back to Launcher")
        back_layout.addWidget(self.back_btn)
        back_layout.addStretch()
        setup_layout.addLayout(back_layout)
        setup_layout.addSpacing(10)

        # Working Directory
        dir_layout = QHBoxLayout()
        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Select a folder for this week's tests...")
        self.browse_btn = QPushButton("Browse...")
        dir_layout.addWidget(QLabel("Working Directory:"))
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.browse_btn)
        setup_layout.addLayout(dir_layout)

        # Device Name
        device_layout = QHBoxLayout()
        self.device_input = QLineEdit()
        self.device_input.setPlaceholderText("e.g., Kindle Scribe")
        device_layout.addWidget(QLabel("Device Name:"))
        device_layout.addWidget(self.device_input)
        setup_layout.addLayout(device_layout)

        # Week Number
        week_layout = QHBoxLayout()
        self.week_input = QSpinBox()
        self.week_input.setRange(1, 52)
        week_layout.addWidget(QLabel("Week Number:"))
        week_layout.addWidget(self.week_input)
        week_layout.addStretch()
        setup_layout.addLayout(week_layout)

        # Build Details
        build_layout = QHBoxLayout()
        self.build_input = QLineEdit()
        self.build_input.setPlaceholderText("e.g., KOS 5.16.2.1.1")
        build_layout.addWidget(QLabel("Build Details:"))
        build_layout.addWidget(self.build_input)
        setup_layout.addLayout(build_layout)

        # Test Suite
        suite_layout = QHBoxLayout()
        self.suite_combo = QComboBox()
        self.suite_combo.addItems(["P0", "P1", "P2", "P3", "HWR", "GEN AI"])
        suite_layout.addWidget(QLabel("Test Suite:"))
        suite_layout.addWidget(self.suite_combo)
        suite_layout.addStretch()
        setup_layout.addLayout(suite_layout)

        # Action Buttons
        setup_layout.addSpacing(20)
        self.start_btn = QPushButton("Start Execution")
        self.start_btn.setStyleSheet("font-size: 16px; padding: 10px;")
        setup_layout.addWidget(self.start_btn)

        main_layout.addWidget(setup_group)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    screen = SetupScreen()
    screen.show()
    sys.exit(app.exec_())