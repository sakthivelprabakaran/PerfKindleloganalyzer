from PyQt5.QtWidgets import QWidget, QStackedWidget, QVBoxLayout, QMessageBox, QFileDialog
from .logic.state_manager import StateManager
from .logic.data_manager import DataManager
from .ui.launch_page import LauncherScreen
from .ui.execution_dashboard import ExecutionDashboard
from .ui.audit_window import AuditWindow
import os

class MainWindow(QWidget):
    """A container widget for the Performance Dashboard application."""
    def __init__(self, back_to_launcher_callback=None, auth_token=None):
        super().__init__()
        self.back_to_launcher_callback = back_to_launcher_callback
        self.user_context = {"token": auth_token} if auth_token else None
        self.state_manager = StateManager()
        self.data_manager = None  # Instantiated when a session starts
        self.save_thread = None

        # Main layout for this container widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget)

        # Create and add screens
        self.launcher_screen = LauncherScreen(
            self.state_manager,
            self.switch_to_dashboard,
            self.switch_to_audit,
            self.back_to_launcher_callback
        )
        self.execution_dashboard = None  # Created when needed
        self.audit_window = None # Created when needed

        self.stacked_widget.addWidget(self.launcher_screen)

    def switch_to_audit(self):
        """Switches the view to the Audit Window."""
        if self.audit_window:
            self.stacked_widget.removeWidget(self.audit_window)
            self.audit_window.deleteLater()
            
        token = self.user_context.get("token") if self.user_context else None
        self.audit_window = AuditWindow(self.switch_to_launcher, auth_token=token)
        self.stacked_widget.addWidget(self.audit_window)
        self.stacked_widget.setCurrentWidget(self.audit_window)

    def switch_to_dashboard(self, session_data):
        """Switches the view to the Execution Dashboard for the given session."""
        # First, ensure the session file exists or is created
        project_path = session_data.get('project_path')
        
        # Handle missing project_path (legacy sessions)
        if not project_path:
            QMessageBox.warning(self, "Missing Path", "The project folder path is missing for this session.\nPlease select the project folder.")
            project_path = QFileDialog.getExistingDirectory(self, "Select Project Folder")
            if not project_path:
                return # User cancelled
            
            # Update session data and save
            session_data['project_path'] = project_path
            self.state_manager.set_current_session(session_data)
            self.state_manager.update_current_session('project_path', project_path)

        if not os.path.exists(os.path.join(project_path, session_data['file_name'])):
            # Ensure project_path is set in session_data for create_session_file
            session_data['project_path'] = project_path 
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
            self.state_manager, self.data_manager, self.switch_to_launcher, self.switch_to_dashboard, self.user_context
        )

        self.stacked_widget.addWidget(self.execution_dashboard)
        self.stacked_widget.setCurrentWidget(self.execution_dashboard)

        # Load the session data into the dashboard UI
        self.execution_dashboard.load_session_data()

    def switch_to_launcher(self):
        """Saves the session to Excel and switches the view back to the Launcher screen."""
        if self.data_manager:
            # Use async save to prevent UI freezing
            self.save_thread = self.data_manager.save_to_excel_async()
            if self.save_thread:
                self.save_thread.finished_signal.connect(self.on_save_finished)
                self.save_thread.start()

        self.launcher_screen.refresh_view()
        self.stacked_widget.setCurrentWidget(self.launcher_screen)
        if self.execution_dashboard:
            self.stacked_widget.removeWidget(self.execution_dashboard)
            self.execution_dashboard.deleteLater()
            self.execution_dashboard = None
        self.data_manager = None

    def on_save_finished(self, success, message):
        """Handle the completion of the background save operation."""
        if not success:
            QMessageBox.warning(self, "Save Error", message)
        # We could show a success message here, but it might pop up after the user is already doing something else.
        # For now, silent success is better for UX, or maybe a status bar update in the launcher if we had one.