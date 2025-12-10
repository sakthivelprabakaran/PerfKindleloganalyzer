import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QCheckBox
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtCore import Qt

from ui.login_window import LoginWindow
from ui.universal_launcher import UniversalLauncher
from ui.main_window import FinalKindleLogAnalyzer
from performance_dashboard.main_window import MainWindow as PerformanceDashboard
from performance_dashboard.ui.audit_window import AuditWindow
from performance_dashboard.ui.task_assignment_window import TaskAssignmentWindow
from config import APP_NAME, APP_ICON_PATH

class ApplicationContainer(QMainWindow):
    """
    The main container that holds and manages all applications (screens).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setGeometry(50, 50, 1600, 1000)

        self.dark_mode = False
        
        # User authentication state
        self.current_user = None
        self.user_role = None
        self.user_full_name = None

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Applications will be instantiated after successful login
        self.universal_launcher = None
        self.log_analyzer = None
        self.exec_dashboard = None
        self.audit_window = None
        self.task_assignment_window = None

        self.load_stylesheet()

    def init_main_app_screens(self):
        """Initializes and adds all main application screens to the stacked widget after login."""
        if self.universal_launcher: # Avoid re-initializing if already done
            return

        # Use stored user info
        user_role = self.user_role or "guest"
        auth_token = self.auth_token

        # Instantiate all the applications/screens
        self.universal_launcher = UniversalLauncher(
            self.launch_log_analyzer,
            self.launch_exec_dashboard,
            self.launch_audit_report,
            self.launch_task_assignment,
            self.toggle_dark_mode,
            user_role=user_role
        )
        # Pass token to FinalKindleLogAnalyzer
        self.log_analyzer = FinalKindleLogAnalyzer(back_to_launcher_callback=self.back_to_launcher, auth_token=auth_token)
        # Pass user context (including username, role, token) to PerformanceDashboard
        user_context = {
            "username": self.current_user,
            "role": self.user_role,
            "full_name": self.user_full_name,
            "auth_token": self.auth_token
        }
        self.exec_dashboard = PerformanceDashboard(back_to_launcher_callback=self.back_to_launcher, user_context=user_context)
        self.audit_window = AuditWindow(return_callback=self.back_to_launcher, auth_token=self.auth_token, user_context=user_context)
        self.task_assignment_window = TaskAssignmentWindow(
            return_callback=self.back_to_launcher,
            auth_token=self.auth_token
        )

        # Add them to the stack
        self.stacked_widget.addWidget(self.universal_launcher)
        self.stacked_widget.addWidget(self.log_analyzer)
        self.stacked_widget.addWidget(self.exec_dashboard)
        self.stacked_widget.addWidget(self.audit_window)
        self.stacked_widget.addWidget(self.task_assignment_window)

        # Set the initial screen
        self.stacked_widget.setCurrentWidget(self.universal_launcher)
        self.load_stylesheet()

    def launch_log_analyzer(self):
        """Switches the view to the Kindle Log Analyzer."""
        self.setWindowTitle("Final Kindle Log Analyzer")
        self.stacked_widget.setCurrentWidget(self.log_analyzer)

    def launch_exec_dashboard(self):
        """Switches the view to the Performance Execution Dashboard."""
        self.setWindowTitle("Performance Execution Dashboard")
        self.stacked_widget.setCurrentWidget(self.exec_dashboard)

    def launch_audit_report(self):
        """Switches the view to the Audit & Report Window."""
        self.setWindowTitle("Audit & Report Generation")
        self.stacked_widget.setCurrentWidget(self.audit_window)

    def launch_task_assignment(self):
        """Switches the view to the Task Assignment Dashboard."""
        self.setWindowTitle("Task Assignment Dashboard (Admin)")
        self.stacked_widget.setCurrentWidget(self.task_assignment_window)

    def back_to_launcher(self):
        """Switches the view back to the universal launcher."""
        self.setWindowTitle("Kindle Test Engineering Tools")
        self.stacked_widget.setCurrentWidget(self.universal_launcher)
    
    def on_login_success(self, username, role, full_name, token):
        """Called when user successfully logs in."""
        self.current_user = username
        self.user_role = role
        self.user_full_name = full_name
        self.auth_token = token # Store the token
        
        # Initialize the main app screens now that we have the user info
        self.init_main_app_screens()
        
        # Update window title with user info
        self.setWindowTitle(f"Kindle Test Engineering Tools - {full_name} ({role})")
        
        # Update launcher with user role (redundant if init_main_app_screens does it, but safe)
        if self.universal_launcher:
            self.universal_launcher.set_user_role(role)
        
        # Show main application
        self.show()
    
    def show_login(self):
        """Show login window."""
        login_window = LoginWindow(self.on_login_success)
        login_window.show()
        return login_window

    def toggle_dark_mode(self, checked):
        """Toggles the application's theme."""
        self.dark_mode = checked
        self.load_stylesheet()

    def load_stylesheet(self):
        """Loads the appropriate stylesheet based on the theme."""
        theme = "dark" if self.dark_mode else "light"
        stylesheet_path = os.path.join("assets", "stylesheets", f"{theme}_mode.qss")
        if os.path.exists(stylesheet_path):
            with open(stylesheet_path, "r") as f:
                self.setStyleSheet(f.read())

    # Removed set_app_icon method as icon is now set globally in __main__
    # def set_app_icon(self):
    #     """Sets the application icon based on the platform."""
    #     try:
    #         # Determine the correct icon file based on platform
    #         if sys.platform == "darwin":  # macOS
    #             icon_path = os.path.join("assets", "icons", "Mac.icns")
    #         elif sys.platform == "win32":  # Windows
    #             icon_path = os.path.join("assets", "icons", "win.ico")
    #         else:  # Linux and others
    #             icon_path = os.path.join("assets", "icons", "win.ico")
            
    #         if os.path.exists(icon_path):
    #             self.setWindowIcon(QIcon(icon_path))
    #         else:
    #             print(f"Warning: Icon file not found at {icon_path}")
    #     except Exception as e:
    #         print(f"Error setting app icon: {e}")

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont("Arial", 10)
    app.setFont(font)
    
    # Set application icon (for Dock/taskbar)
    try:
        if os.path.exists(APP_ICON_PATH):
            app.setWindowIcon(QIcon(APP_ICON_PATH))
            print(f"✓ Icon loaded: {APP_ICON_PATH}")
        else:
            print(f"⚠ Icon not found: {APP_ICON_PATH}")
    except Exception as e:
        print(f"✗ Error loading icon: {e}")

    # Create container (but don't show yet)
    container = ApplicationContainer()
    
    # Show login window first
    login_window = container.show_login()

    sys.exit(app.exec_())