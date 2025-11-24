import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QLineEdit,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class LauncherScreen(QWidget):
    """
    The initial screen for the Performance Execution Dashboard.
    Provides options to create a new session or open a saved one.
    """
    def __init__(self, state_manager, switch_to_dashboard_callback, open_audit_callback, back_to_launcher_callback=None):
        super().__init__()
        self.state = state_manager
        self.switch_to_dashboard = switch_to_dashboard_callback
        self.open_audit_callback = open_audit_callback
        self.back_to_launcher_callback = back_to_launcher_callback
        self.init_ui()
        self.load_priorities()
        self.load_session_table()

    def init_ui(self):
        """Initializes the UI layout and widgets."""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Left Column Layout
        left_column = QVBoxLayout()
        
        # New Session Creation
        left_panel = self.create_left_panel()
        left_column.addWidget(left_panel)
        
        # Tools Section
        tools_group = QGroupBox("Tools")
        tools_layout = QVBoxLayout(tools_group)
        audit_btn = QPushButton("📊 Audit & Report")
        audit_btn.setStyleSheet("font-size: 14px; padding: 8px;")
        audit_btn.clicked.connect(self.open_audit_callback)
        tools_layout.addWidget(audit_btn)
        left_column.addWidget(tools_group)
        
        left_column.addStretch()
        main_layout.addLayout(left_column, 1) # 50% width

        # Right Panel: Saved Sessions
        right_panel = self.create_right_panel()
        main_layout.addWidget(right_panel, 1) # 50% width

    def create_left_panel(self):
        """Creates the left panel for new session creation."""
        panel = QGroupBox("New Session Creation")
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Username Input (NEW)
        layout.addWidget(QLabel("Your Username:"))
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username...")
        self.username_input.textChanged.connect(self.on_username_changed)
        layout.addWidget(self.username_input)

        # Server URL Input (NEW)
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("Server:"))
        self.server_url_input = QLineEdit("http://localhost:8000")
        self.server_url_input.setFixedWidth(200)
       
        server_layout.addWidget(self.server_url_input)
        layout.addLayout(server_layout)

        # My Assigned Tasks (NEW)
        layout.addWidget(QLabel("My Assigned Tasks:"))
        task_selection_layout = QHBoxLayout()
        self.assigned_tasks_combo = QComboBox()
        self.assigned_tasks_combo.addItem("-- Select Task or Create Manually --")
        self.assigned_tasks_combo.currentIndexChanged.connect(self.on_task_selected)
        task_selection_layout.addWidget(self.assigned_tasks_combo)
        
        refresh_tasks_btn = QPushButton("🔄")
        refresh_tasks_btn.setFixedWidth(40)
        refresh_tasks_btn.setToolTip("Refresh my assigned tasks")
        refresh_tasks_btn.clicked.connect(self.fetch_assigned_tasks)
        task_selection_layout.addWidget(refresh_tasks_btn)
        layout.addLayout(task_selection_layout)

        # Separator
        separator = QLabel("─" * 40)
        layout.addWidget(separator)

        # Project Path
        path_layout = QHBoxLayout()
        self.project_path_input = QLineEdit()
        self.project_path_input.setPlaceholderText("Select a folder to save the session file...")
        self.project_path_input.setReadOnly(True)
        path_layout.addWidget(self.project_path_input)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.select_project_path)
        path_layout.addWidget(browse_btn)
        layout.addWidget(QLabel("Project Path:"))
        layout.addLayout(path_layout)

        # Device Name
        layout.addWidget(QLabel("Device Name:"))
        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("e.g., Kindle Paperwhite")
        layout.addWidget(self.device_name_input)

        # Week
        layout.addWidget(QLabel("Week:"))
        self.week_combo = QComboBox()
        self.week_combo.addItems([f"Week {i}" for i in range(1, 53)])
        layout.addWidget(self.week_combo)

        # Build Details
        layout.addWidget(QLabel("Build Details:"))
        self.build_details_input = QLineEdit()
        self.build_details_input.setPlaceholderText("e.g., KOS 5.16.2.1-20240101")
        layout.addWidget(self.build_details_input)

        # Priority
        layout.addWidget(QLabel("Priority:"))
        self.priority_combo = QComboBox()
        layout.addWidget(self.priority_combo)

        layout.addStretch()

        # Start Execution Button
        self.start_execution_btn = QPushButton("Start Execution")
        self.start_execution_btn.setStyleSheet("font-size: 16px; padding: 10px;")
        self.start_execution_btn.clicked.connect(self.start_new_session)
        layout.addWidget(self.start_execution_btn)

        # Store task data for later use
        self.current_task_data = None
        self.tasks_data = {}  # Initialize empty dict to prevent AttributeError

        return panel

    def create_right_panel(self):
        """Creates the right panel for displaying and managing saved sessions."""
        panel = QGroupBox("📝 New Session")
        layout = QVBoxLayout()
        
        # Header with back button
        if self.back_to_launcher_callback:
            header_layout = QHBoxLayout()
            back_btn = QPushButton("← Back")
            back_btn.clicked.connect(self.back_to_launcher_callback)
            back_btn.setFixedWidth(100)
            
            title_label = QLabel("Performance Execution Dashboard")
            title_label.setFont(QFont("Arial", 14, QFont.Bold))
            title_label.setAlignment(Qt.AlignCenter)
            
            header_layout.addWidget(back_btn)
            header_layout.addWidget(title_label)
            header_layout.addStretch()
            layout.addLayout(header_layout)
            
            # Separator
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setFrameShadow(QFrame.Sunken)
            layout.addWidget(separator)
        panel.setLayout(layout)

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search sessions by device, week, priority, etc...")
        self.search_input.textChanged.connect(self.filter_sessions)
        layout.addWidget(self.search_input)

        # Session Table
        self.session_table = QTableWidget()
        self.session_table.setColumnCount(6)
        self.session_table.setHorizontalHeaderLabels(
            ["Device Name", "Week", "Build Details", "Priority", "File Name", "Status"]
        )
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.session_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.session_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.session_table.setSortingEnabled(True)
        self.session_table.cellDoubleClicked.connect(self.open_selected_session)
        layout.addWidget(self.session_table)

        # Buttons Layout
        buttons_layout = QHBoxLayout()
        open_session_btn = QPushButton("Open Selected")
        open_session_btn.clicked.connect(self.open_selected_session)
        remove_session_btn = QPushButton("Remove Selected")
        remove_session_btn.clicked.connect(self.remove_selected_session)

        buttons_layout.addWidget(open_session_btn)
        buttons_layout.addWidget(remove_session_btn)
        layout.addLayout(buttons_layout)

        return panel

    def select_project_path(self):
        """Opens a dialog to select a directory for the project."""
        path = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if path:
            self.project_path_input.setText(path)

    def load_session_table(self):
        """Populates the session table with data from the state manager."""
        self.state.load_sessions()
        self.session_table.setRowCount(0) # Clear the table first
        for session in self.state.sessions:
            row_position = self.session_table.rowCount()
            self.session_table.insertRow(row_position)
            self.session_table.setItem(row_position, 0, QTableWidgetItem(session.get("device_name", "")))
            self.session_table.setItem(row_position, 1, QTableWidgetItem(str(session.get("week", ""))))
            self.session_table.setItem(row_position, 2, QTableWidgetItem(session.get("build_details", "")))
            self.session_table.setItem(row_position, 3, QTableWidgetItem(session.get("priority", "")))
            self.session_table.setItem(row_position, 4, QTableWidgetItem(session.get("file_name", "")))
            self.session_table.setItem(row_position, 5, QTableWidgetItem(session.get("status", "")))
        self.session_table.resizeColumnsToContents()

    def start_new_session(self):
        """Validates input and starts a new execution session."""
        project_path = self.project_path_input.text()
        device_name = self.device_name_input.text()
        week = self.week_combo.currentText()
        build_details = self.build_details_input.text()
        priority = self.priority_combo.currentText()

        if not all([project_path, device_name, week, build_details, priority]):
            QMessageBox.warning(self, "Input Error", "All fields must be filled out to start a new session.")
            return

        # Create the session in the state manager
        session_data = self.state.create_new_session(
            project_path, device_name, week, build_details, priority
        )

        # Add task assignment data if a task was selected
        if self.current_task_data:
            session_data['task_assignment'] = self.current_task_data
            session_data['username'] = self.username_input.text().strip()
            session_data['server_url'] = self.server_url_input.text().strip()

        # The data manager will be instantiated in the main window
        # For now, we just switch views
        self.switch_to_dashboard(session_data)

    def filter_sessions(self):
        """Hides or shows rows based on the search text."""
        search_text = self.search_input.text().lower()
        for i in range(self.session_table.rowCount()):
            match = False
            for j in range(self.session_table.columnCount()):
                item = self.session_table.item(i, j)
                if item and search_text in item.text().lower():
                    match = True
                    break
            self.session_table.setRowHidden(i, not match)

    def remove_selected_session(self):
        """Removes the selected session from the list (not the file)."""
        selected_rows = self.session_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Error", "Please select a session to remove.")
            return

        selected_row_index = selected_rows[0].row()

        # Get the unique file name to identify the session in the state manager
        file_name_item = self.session_table.item(selected_row_index, 4)
        if not file_name_item:
            return # Should not happen

        reply = QMessageBox.question(self, 'Confirm Removal',
                                     f"Are you sure you want to remove the session '{file_name_item.text()}' from the list?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            session_removed = self.state.remove_session_by_filename(file_name_item.text())
            if session_removed:
                self.session_table.removeRow(selected_row_index)
                QMessageBox.information(self, "Success", "Session removed from the list.")
            else:
                QMessageBox.warning(self, "Error", "Could not find the session to remove.")

    def open_selected_session(self):
        """Opens an existing session from the table."""
        selected_rows = self.session_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Selection Error", "Please select a session to open.")
            return

        selected_row_index = selected_rows[0].row()
        file_name_item = self.session_table.item(selected_row_index, 4)
        if not file_name_item:
            return

        # Find the session data from the state manager using the unique file name
        session_data = self.state.get_session_by_filename(file_name_item.text())
        if session_data:
            self.state.set_current_session(session_data)
            self.switch_to_dashboard(session_data)
        else:
            QMessageBox.warning(self, "Error", "Could not find session data.")

    def refresh_view(self):
        """Refreshes the view, e.g., when returning to the launcher."""
        self.load_session_table()
        self.project_path_input.clear()
        self.device_name_input.clear()
        self.build_details_input.clear()
        self.week_combo.setCurrentIndex(0)
        self.priority_combo.setCurrentIndex(0)

    def load_priorities(self):
        """Loads priorities from the template excel file."""
        try:
            template_path = "performance_dashboard/assets/template_test_cases.xlsx"
            xls = pd.ExcelFile(template_path)
            self.priority_combo.addItems(xls.sheet_names)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not load priorities from template: {e}")
            # Add default priorities as a fallback
            self.priority_combo.addItems(["P0", "P1", "P2"])

    def on_username_changed(self):
        """Called when username changes - auto-fetch tasks"""
        if len(self.username_input.text()) >= 3:  # Minimum 3 characters
            self.fetch_assigned_tasks()

    def fetch_assigned_tasks(self):
        """Fetches assigned tasks for the current username from server"""
        username = self.username_input.text().strip()
        server_url = self.server_url_input.text().strip()
        
        if not username:
            return
        
        try:
            import requests
            response = requests.get(f"{server_url}/my_tasks/{username}", timeout=3)
            if response.status_code == 200:
                tasks = response.json()
                
                # Clear and repopulate dropdown
                self.assigned_tasks_combo.clear()
                self.assigned_tasks_combo.addItem("-- Select Task or Create Manually --")
                
                # Store tasks for later use
                self.tasks_data = {}
                
                for task in tasks:
                    # Format display: "Kindle P0 → Alice (Auditor)"
                    display_text = f"{task['project']} {task['suite']} → {task['auditor_username']} (Auditor)"
                    self.assigned_tasks_combo.addItem(display_text)
                    self.tasks_data[display_text] = task
                    
                if len(tasks) > 0:
                    self.assigned_tasks_combo.setStyleSheet("background-color: #d4edda;")  # Green hint
            else:
                self.assigned_tasks_combo.clear()
                self.assigned_tasks_combo.addItem("-- No tasks assigned --")
        except Exception as e:
            print(f"Error fetching tasks: {e}")
            self.assigned_tasks_combo.clear()
            self.assigned_tasks_combo.addItem("-- Server not available --")

    def on_task_selected(self, index):
        """Called when a task is selected from dropdown - auto-fill session details"""
        if index == 0:  # "Select Task or Create Manually"
            self.current_task_data = None
            self.assigned_tasks_combo.setStyleSheet("")
            return
        
        selected_text = self.assigned_tasks_combo.currentText()
        if selected_text in self.tasks_data:
            task = self.tasks_data[selected_text]
            self.current_task_data = task
            
            # Auto-fill session fields from task
            self.device_name_input.setText(task['project'])  # Use project as device
            self.priority_combo.setCurrentText(task['suite'])  # P0, P1, etc.
            
            # Visual feedback
            self.assigned_tasks_combo.setStyleSheet("background-color: #d1ecf1;")  # Blue - selected
            
            QMessageBox.information(
                self, 
                "Task Selected",
                f"Auto-filled session from task assignment:\n\n"
                f"Project: {task['project']}\n"
                f"Suite: {task['suite']}\n"
                f"Auditor: {task['auditor_username']}\n\n"
                f"Live Audit Mode will be auto-enabled with {task['auditor_username']}."
            )