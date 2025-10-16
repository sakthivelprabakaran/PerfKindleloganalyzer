from PyQt5.QtWidgets import QWidget, QVBoxLayout
from logic.state_manager import StateManager
from .ui.execution_dashboard import ExecutionDashboard
import os

class MainWindow(QWidget):
    """A container widget for the Performance Dashboard application."""
    def __init__(self, notification_manager=None):
        super().__init__()
        self.state_manager = StateManager()
        self.notification_manager = notification_manager

        # Main layout for this container widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Create and add the main dashboard
        self.execution_dashboard = ExecutionDashboard(self.state_manager, self.notification_manager)
        main_layout.addWidget(self.execution_dashboard)