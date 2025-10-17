from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout, QMessageBox
from .logic.state_manager import StateManager
from .logic.data_manager import DataManager
from .ui.launch_page import LauncherScreen
from .ui.execution_dashboard import ExecutionDashboard
import os

class MainWindow(QWidget):
    """A container widget for the Performance Dashboard application."""
    def __init__(self, back_to_launcher_callback=None):
        super().__init__()
        self.back_to_launcher_callback = back_to_launcher_callback
        self.state_manager = StateManager()
        self.data_manager = None  # Instantiated when a session starts

        # Main layout for this container widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create and add screens
        self.launcher_screen = LauncherScreen(
            self.state_manager,
            self.switch_to_dashboard,
            self.back_to_launcher_callback
        )
        self.execution_dashboard = None  # Created when needed

        self.stacked_widget.addWidget(self.launcher_screen)

    def switch_to_dashboard(self, session_data):
        """Switches the view to the Execution Dashboard for the given session."""
        # First, ensure the session file exists or is created
        if not os.path.exists(os.path.join(session_data['project_path'], session_data['file_name'])):
            success, message = DataManager.create_session_file(session_data)
            if not success:
                QMessageBox.critical(self, "File Creation Error", message)
                return

        # Instantiate DataManager for the selected session
        self.data_manager = DataManager(session_data)

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
        """Saves the session to Excel and switches the view back to the Launcher screen."""
        if self.data_manager:
            success, message = self.data_manager.save_to_excel()
            if success:
                # Optionally, show a success message, or just log it.
                # For now, we'll keep it silent unless there's an error.
                pass
            else:
                QMessageBox.warning(self, "Save Error", message)

        self.launcher_screen.refresh_view()
        self.stacked_widget.setCurrentWidget(self.launcher_screen)
        if self.execution_dashboard:
            self.stacked_widget.removeWidget(self.execution_dashboard)
            self.execution_dashboard.deleteLater()
            self.execution_dashboard = None
        self.data_manager = None