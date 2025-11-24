from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QCheckBox, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class UniversalLauncher(QWidget):
    """
    A central launcher screen to choose between the available applications.
    Supports role-based button visibility (admin, executor, auditor).
    """
    def __init__(self, launch_log_analyzer_callback, launch_exec_dashboard_callback, 
                 launch_audit_report_callback, launch_task_assignment_callback, 
                 toggle_dark_mode_callback, user_role="admin"):
        super().__init__()
        self.launch_log_analyzer = launch_log_analyzer_callback
        self.launch_exec_dashboard = launch_exec_dashboard_callback
        self.launch_audit_report = launch_audit_report_callback
        self.launch_task_assignment = launch_task_assignment_callback
        self.toggle_dark_mode = toggle_dark_mode_callback
        self.user_role = user_role  # NEW: Store user role

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
        self.log_analyzer_btn = QPushButton("Launch Kindle Log Analyzer")
        self.log_analyzer_btn.setFont(QFont("Arial", 16))
        self.log_analyzer_btn.setMinimumSize(400, 100)
        self.log_analyzer_btn.clicked.connect(self.launch_log_analyzer)
        buttons_layout.addWidget(self.log_analyzer_btn)

        # Button to launch Performance Execution Dashboard
        self.exec_dashboard_btn = QPushButton("Performance Execution Dashboard")
        self.exec_dashboard_btn.setFont(QFont("Arial", 16))
        self.exec_dashboard_btn.setMinimumSize(400, 100)
        self.exec_dashboard_btn.clicked.connect(self.launch_exec_dashboard)
        buttons_layout.addWidget(self.exec_dashboard_btn)

        # Button to launch Audit and Report
        self.audit_report_btn = QPushButton("Audit & Report")
        self.audit_report_btn.setFont(QFont("Arial", 16))
        self.audit_report_btn.setMinimumSize(400, 100)
        self.audit_report_btn.clicked.connect(self.launch_audit_report)
        buttons_layout.addWidget(self.audit_report_btn)

        # Button to launch Task Assignment (Admin only)
        self.task_assignment_btn = QPushButton("Admin: Task Assignment")
        self.task_assignment_btn.setFont(QFont("Arial", 16))
        self.task_assignment_btn.setMinimumSize(400, 100)
        self.task_assignment_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF5722;
                color: white;
            }
            QPushButton:hover {
                background-color: #E64A19;
            }
        """)
        self.task_assignment_btn.clicked.connect(self.launch_task_assignment)
        buttons_layout.addWidget(self.task_assignment_btn)

        main_layout.addLayout(buttons_layout)

        # Spacer
        main_layout.addStretch(1)
        
        # Apply role-based visibility
        self.apply_role_permissions()

    def set_user_role(self, role):
        """Update user role and refresh button visibility."""
        self.user_role = role
        self.apply_role_permissions()
    
    def apply_role_permissions(self):
        """Show/hide buttons based on user role."""
        # Normalize role to lowercase
        role = self.user_role.lower() if self.user_role else "admin"
        
        # Check for role keywords in the role string (handles comma-separated roles)
        is_admin = "admin" in role
        is_executor = "executor" in role
        is_auditor = "auditor" in role
        
        # Admin: sees everything
        if is_admin:
            self.log_analyzer_btn.setVisible(True)
            self.exec_dashboard_btn.setVisible(True)
            self.audit_report_btn.setVisible(True)
            self.task_assignment_btn.setVisible(True)
        
        # Executor or Auditor (or both): show appropriate access
        else:
            # Kindle Log Analyzer: executor OR auditor
            self.log_analyzer_btn.setVisible(is_executor or is_auditor)
            
            # Performance Dashboard: executor OR auditor
            self.exec_dashboard_btn.setVisible(is_executor or is_auditor)
            
            # Audit & Report: auditor only
            self.audit_report_btn.setVisible(is_auditor)
            
            # Task Assignment: never (only admin)
            self.task_assignment_btn.setVisible(False)