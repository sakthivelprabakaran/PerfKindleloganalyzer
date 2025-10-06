from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QApplication
from .logic.state_manager import StateManager
from .logic.data_manager import DataManager
from .ui.launch_page import LauncherScreen
from .ui.execution_dashboard import ExecutionDashboard
import os

class MainWindow(QMainWindow):
    """The main application window that manages different screens."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Performance Execution Dashboard")
        self.setGeometry(100, 100, 1200, 800)

        self.state_manager = StateManager()
        self.data_manager = None # Instantiated when a session starts

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Create and add screens
        self.launcher_screen = LauncherScreen(self.state_manager, self.switch_to_dashboard)
        self.execution_dashboard = None # Created when needed

        self.stacked_widget.addWidget(self.launcher_screen)

        self.load_styles()

    def load_styles(self):
        """Loads the application's stylesheet."""
        # Simple style switching for now, can be enhanced with a toggle
        light_mode_path = "performance_dashboard/assets/light_mode.qss"
        if os.path.exists(light_mode_path):
            with open(light_mode_path, "r") as f:
                self.setStyleSheet(f.read())

    def switch_to_dashboard(self, session_data):
        """Switches the view to the Execution Dashboard for the given session."""
        # First, ensure the session file exists or is created
        if not os.path.exists(os.path.join(session_data['project_path'], session_data['file_name'])):
            success, message = DataManager.create_session_file(session_data)
            if not success:
                # If file creation fails, show an error and stay on the launcher
                # (A QMessageBox is shown in LauncherScreen, but a more robust error could be here)
                print(f"Error: {message}") # Logging the error
                return

        # Instantiate DataManager for the selected session
        self.data_manager = DataManager(session_data, self.state_manager)

        # If the dashboard for this session doesn't exist, create it
        if self.execution_dashboard:
            self.stacked_widget.removeWidget(self.execution_dashboard)
            self.execution_dashboard.deleteLater()

        self.execution_dashboard = ExecutionDashboard(
            self.state_manager, self.data_manager, self.switch_to_launcher
        )

        self.stacked_widget.addWidget(self.execution_dashboard)
        self.stacked_widget.setCurrentWidget(self.execution_dashboard)

        # Load the session data into the dashboard UI
        self.execution_dashboard.load_session_data()

    def switch_to_launcher(self):
        """Switches the view back to the Launcher screen."""
        self.launcher_screen.refresh_view()
        self.stacked_widget.setCurrentWidget(self.launcher_screen)
        if self.execution_dashboard:
            self.stacked_widget.removeWidget(self.execution_dashboard)
            self.execution_dashboard.deleteLater()
            self.execution_dashboard = None
        self.data_manager = None