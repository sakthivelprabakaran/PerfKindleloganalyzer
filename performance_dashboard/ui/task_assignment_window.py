from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QComboBox, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox, QLineEdit, QTabWidget, QCheckBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont
import requests

# Dialog for Creating/Editing Users
class UserDialog(QDialog):
    def __init__(self, server_url, user_data=None, parent=None):
        super().__init__(parent)
        self.server_url = server_url
        self.user_data = user_data
        self.setWindowTitle("Add User" if not user_data else "Edit User")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.username_input = QLineEdit()
        self.fullname_input = QLineEdit()
        
        # Multiple roles selection
        self.role_executor = QCheckBox("Executor")
        self.role_auditor = QCheckBox("Auditor")
        self.role_admin = QCheckBox("Admin")
        
        role_layout = QVBoxLayout()
        role_layout.addWidget(self.role_executor)
        role_layout.addWidget(self.role_auditor)
        role_layout.addWidget(self.role_admin)
        
        if self.user_data:
            self.username_input.setText(self.user_data.get("username", ""))
            self.username_input.setReadOnly(True)
            self.fullname_input.setText(self.user_data.get("full_name", ""))
            
            # Parse existing roles
            roles = self.user_data.get("role", "").lower()
            if "executor" in roles:
                self.role_executor.setChecked(True)
            if "auditor" in roles:
                self.role_auditor.setChecked(True)
            if "admin" in roles:
                self.role_admin.setChecked(True)
        
        layout.addRow("Username:", self.username_input)
        layout.addRow("Full Name:", self.fullname_input)
        layout.addRow("Roles:", role_layout)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        roles = []
        if self.role_executor.isChecked():
            roles.append("executor")
        if self.role_auditor.isChecked():
            roles.append("auditor")
        if self.role_admin.isChecked():
            roles.append("admin")
        
        return {
            "username": self.username_input.text(),
            "full_name": self.fullname_input.text(),
            "role": ",".join(roles)  # Comma-separated roles
        }

# Dialog for Creating/Editing Projects
class ProjectDialog(QDialog):
    def __init__(self, server_url, project_data=None, parent=None):
        super().__init__(parent)
        self.server_url = server_url
        self.project_data = project_data
        self.setWindowTitle("Add Project" if not project_data else "Edit Project")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.description_input = QLineEdit()
        
        if self.project_data:
            self.name_input.setText(self.project_data.get("name", ""))
            self.name_input.setReadOnly(True)
            self.description_input.setText(self.project_data.get("description", ""))
        
        layout.addRow("Project Name:", self.name_input)
        layout.addRow("Description:", self.description_input)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "description": self.description_input.text()
        }

# Dialog for Creating/Editing Suites
class SuiteDialog(QDialog):
    def __init__(self, server_url, suite_data=None, parent=None):
        super().__init__(parent)
        self.server_url = server_url
        self.suite_data = suite_data
        self.setWindowTitle("Add Suite" if not suite_data else "Edit Suite")
        self.setMinimumWidth(400)
        self.init_ui()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.name_input = QLineEdit()
        self.description_input = QLineEdit()
        
        if self.suite_data:
            self.name_input.setText(self.suite_data.get("name", ""))
            self.name_input.setReadOnly(True)
            self.description_input.setText(self.suite_data.get("description", ""))
        
        layout.addRow("Suite Name:", self.name_input)
        layout.addRow("Description:", self.description_input)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def get_data(self):
        return {
            "name": self.name_input.text(),
            "description": self.description_input.text()
        }

# Dialog for Creating Task Assignment
class TaskAssignmentDialog(QDialog):
    def __init__(self, server_url, parent=None):
        super().__init__(parent)
        self.server_url = server_url
        self.setWindowTitle("Create Task Assignment")
        self.setMinimumWidth(400)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QFormLayout(self)
        
        self.project_combo = QComboBox()
        self.suite_combo = QComboBox()
        # Suites will be loaded dynamically in load_data()
        self.device_name_input = QLineEdit()
        self.device_name_input.setPlaceholderText("e.g., Kindle Paperwhite")
        self.executor_combo = QComboBox()
        self.auditor_combo = QComboBox()
        
        layout.addRow("Project:", self.project_combo)
        layout.addRow("Suite:", self.suite_combo)
        layout.addRow("Device Name:", self.device_name_input)
        layout.addRow("Executor:", self.executor_combo)
        layout.addRow("Auditor:", self.auditor_combo)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addRow(self.buttons)

    def load_data(self):
        try:
            # Load projects
            response = requests.get(f"{self.server_url}/projects", timeout=3)
            if response.status_code == 200:
                projects = response.json()
                self.project_combo.addItems([p['name'] for p in projects])
            
            # Load suites dynamically from server
            response = requests.get(f"{self.server_url}/suites", timeout=3)
            if response.status_code == 200:
                suites = response.json()
                self.suite_combo.addItems([s['name'] for s in suites])
            
            # Load executors
            response = requests.get(f"{self.server_url}/users/executors", timeout=3)
            if response.status_code == 200:
                executors = response.json()
                self.executor_combo.addItems([u['username'] for u in executors])
            
            # Load auditors
            response = requests.get(f"{self.server_url}/users/auditors", timeout=3)
            if response.status_code == 200:
                auditors = response.json()
                self.auditor_combo.addItems([u['username'] for u in auditors])
        except Exception as e:
            print(f"Error loading data: {e}")

    def get_data(self):
        return {
            "project": self.project_combo.currentText(),
            "suite": self.suite_combo.currentText(),
            "device_name": self.device_name_input.text(),
            "executor_username": self.executor_combo.currentText(),
            "auditor_username": self.auditor_combo.currentText()
        }

class TaskAssignmentWindow(QWidget):
    def __init__(self, return_callback=None, auth_token=None):
        super().__init__()
        self.setWindowTitle("Task Assignment Dashboard")
        self.resize(1000, 700)
        
        self.return_callback = return_callback
        self.server_url = "http://127.0.0.1:8000"
        self.auth_token = auth_token
        self.headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}
        
        self.init_ui()
        
        # Auto-refresh timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_all_tabs)
        self.timer.start(10000)
        
        # Initial load
        self.refresh_all_tabs()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header with back button
        top_header_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.return_callback)
        back_btn.setFixedWidth(100)
        
        title = QLabel("Task Assignment Dashboard (Admin)")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        
        top_header_layout.addWidget(back_btn)
        top_header_layout.addWidget(title)
        top_header_layout.addStretch()
        layout.addLayout(top_header_layout)
        
        # Server URL input and Manage Template button
        server_input_layout = QHBoxLayout()
        server_label = QLabel("Server:")
        self.server_input = QLineEdit(self.server_url)
        self.server_input.setFixedWidth(200)
        
        # Manage Template Button
        manage_template_btn = QPushButton("📄 Manage Template")
        manage_template_btn.setStyleSheet("font-weight: bold; padding: 5px 10px;")
        manage_template_btn.clicked.connect(self.manage_template)
        
        server_input_layout.addStretch()
        server_input_layout.addWidget(server_label)
        server_input_layout.addWidget(self.server_input)
        server_input_layout.addWidget(manage_template_btn)
        layout.addLayout(server_input_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_users_tab(), "👥 Users")
        self.tabs.addTab(self.create_projects_tab(), "📁 Projects")
        self.tabs.addTab(self.create_suites_tab(), "🎯 Suites")
        self.tabs.addTab(self.create_assignments_tab(), "📋 Task Assignments")
        layout.addWidget(self.tabs)

    def create_users_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add User")
        add_btn.clicked.connect(self.add_user)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Table
        self.users_table = QTableWidget()
        self.users_table.setColumnCount(4)
        self.users_table.setHorizontalHeaderLabels(["Username", "Full Name", "Role", "Actions"])
        self.users_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.users_table)
        
        return tab

    def create_projects_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Project")
        add_btn.clicked.connect(self.add_project)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Table
        self.projects_table = QTableWidget()
        self.projects_table.setColumnCount(3)
        self.projects_table.setHorizontalHeaderLabels(["Project Name", "Description", "Actions"])
        self.projects_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.projects_table)
        
        return tab

    def create_suites_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Buttons
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Add Suite")
        add_btn.clicked.connect(self.add_suite)
        btn_layout.addWidget(add_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Table
        self.suites_table = QTableWidget()
        self.suites_table.setColumnCount(4)
        self.suites_table.setHorizontalHeaderLabels(["ID", "Suite Name", "Description", "Actions"])
        self.suites_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.suites_table)
        
        return tab

    def create_assignments_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Buttons
        btn_layout = QHBoxLayout()
        create_btn = QPushButton("➕ Create New Task Assignment")
        create_btn.clicked.connect(self.create_assignment)
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.clicked.connect(self.refresh_all_tabs)
        
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(refresh_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Table
        self.assignments_table = QTableWidget()
        self.assignments_table.setColumnCount(7)
        self.assignments_table.setHorizontalHeaderLabels([
            "ID", "Project", "Suite", "Device", "Executor", "Auditor", "Status"
        ])
        self.assignments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.assignments_table)
        
        return tab

    def refresh_all_tabs(self):
        self.server_url = self.server_input.text().strip()
        self.refresh_users()
        self.refresh_projects()
        self.refresh_suites()
        self.refresh_assignments()

    def refresh_users(self):
        try:
            response = requests.get(f"{self.server_url}/users", timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.populate_users_table(data)
        except Exception as e:
            print(f"Error fetching users: {e}")

    def populate_users_table(self, data):
        self.users_table.setRowCount(len(data))
        for i, row in enumerate(data):
            username_item = QTableWidgetItem(row['username'])
            username_item.setForeground(QColor("black"))
            
            fullname_item = QTableWidgetItem(row['full_name'])
            fullname_item.setForeground(QColor("black"))
            
            role_item = QTableWidgetItem(row['role'])
            role_item.setForeground(QColor("black"))
            
            self.users_table.setItem(i, 0, username_item)
            self.users_table.setItem(i, 1, fullname_item)
            self.users_table.setItem(i, 2, role_item)
            
            # Edit button
            edit_btn = QPushButton("✏️ Edit")
            edit_btn.clicked.connect(lambda checked, user=row: self.edit_user(user))
            edit_btn.setStyleSheet("padding: 5px;")
            self.users_table.setCellWidget(i, 3, edit_btn)

    def refresh_projects(self):
        try:
            response = requests.get(f"{self.server_url}/projects", timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.populate_projects_table(data)
        except Exception as e:
            print(f"Error fetching projects: {e}")

    def populate_projects_table(self, data):
        self.projects_table.setRowCount(len(data))
        for i, row in enumerate(data):
            name_item = QTableWidgetItem(row['name'])
            name_item.setForeground(QColor("black"))
            
            desc_item = QTableWidgetItem(row['description'])
            desc_item.setForeground(QColor("black"))
            
            self.projects_table.setItem(i, 0, name_item)
            self.projects_table.setItem(i, 1, desc_item)
            self.projects_table.setItem(i, 2, QTableWidgetItem(""))

    def refresh_suites(self):
        try:
            response = requests.get(f"{self.server_url}/suites", timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.populate_suites_table(data)
        except Exception as e:
            print(f"Error fetching suites: {e}")

    def populate_suites_table(self, data):
        self.suites_table.setRowCount(len(data))
        for i, row in enumerate(data):
            id_item = QTableWidgetItem(str(row['id']))
            id_item.setForeground(QColor("black"))
            
            name_item = QTableWidgetItem(row['name'])
            name_item.setForeground(QColor("black"))
            
            desc_item = QTableWidgetItem(row['description'])
            desc_item.setForeground(QColor("black"))
            
            self.suites_table.setItem(i, 0, id_item)
            self.suites_table.setItem(i, 1, name_item)
            self.suites_table.setItem(i, 2, desc_item)
            
            # Delete button
            delete_btn = QPushButton("🗑️ Delete")
            delete_btn.clicked.connect(lambda checked, suite_id=row['id'], suite_name=row['name']: self.delete_suite(suite_id, suite_name))
            delete_btn.setStyleSheet("padding: 5px; background-color: #ffcccc;")
            self.suites_table.setCellWidget(i, 3, delete_btn)

    def refresh_assignments(self):
        try:
            response = requests.get(f"{self.server_url}/all_task_assignments", timeout=3)
            if response.status_code == 200:
                data = response.json()
                self.populate_assignments_table(data)
        except Exception as e:
            print(f"Error fetching assignments: {e}")

    def populate_assignments_table(self, data):
        self.assignments_table.setRowCount(len(data))
        for i, row in enumerate(data):
            id_item = QTableWidgetItem(str(row['id']))
            id_item.setForeground(QColor("black"))
            
            project_item = QTableWidgetItem(row['project'])
            project_item.setForeground(QColor("black"))
            
            suite_item = QTableWidgetItem(row['suite'])
            suite_item.setForeground(QColor("black"))
            
            device_item = QTableWidgetItem(row.get('device_name', ''))
            device_item.setForeground(QColor("black"))
            
            executor_item = QTableWidgetItem(row['executor_username'])
            executor_item.setForeground(QColor("black"))
            
            auditor_item = QTableWidgetItem(row['auditor_username'])
            auditor_item.setForeground(QColor("black"))
            
            status_item = QTableWidgetItem(row['status'])
            status_item.setForeground(QColor("black"))
            
            self.assignments_table.setItem(i, 0, id_item)
            self.assignments_table.setItem(i, 1, project_item)
            self.assignments_table.setItem(i, 2, suite_item)
            self.assignments_table.setItem(i, 3, device_item)
            self.assignments_table.setItem(i, 4, executor_item)
            self.assignments_table.setItem(i, 5, auditor_item)
            self.assignments_table.setItem(i, 6, status_item)
            
            # Color coding
            bg_color = QColor("white")
            if row['status'] == "Assigned":
                bg_color = QColor("#fff3cd")
            elif row['status'] == "In Progress":
                bg_color = QColor("#d1ecf1")
            elif row['status'] == "Completed":
                bg_color = QColor("#d4edda")
            
            for j in range(7):
                if self.assignments_table.item(i, j):
                    self.assignments_table.item(i, j).setBackground(bg_color)

    def add_user(self):
        dialog = UserDialog(self.server_url, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                response = requests.post(f"{self.server_url}/users", json=data, headers=self.headers, timeout=3)
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "User created successfully!")
                    self.refresh_users()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to create user: {response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Network error: {e}")

    def edit_user(self, user_data):
        dialog = UserDialog(self.server_url, user_data=user_data, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                response = requests.put(f"{self.server_url}/users/{user_data['username']}", json=data, timeout=3)
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "User updated successfully!")
                    self.refresh_users()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to update user: {response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Network error: {e}")

    def add_suite(self):
        dialog = SuiteDialog(self.server_url, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                response = requests.post(f"{self.server_url}/suites", json=data, headers=self.headers, timeout=3)
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Suite created successfully!")
                    self.refresh_suites()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to create suite: {response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Network error: {e}")

    def delete_suite(self, suite_id, suite_name):
        reply = QMessageBox.question(self, 'Confirm Delete',
                                     f"Are you sure you want to delete suite '{suite_name}'?\n\nNote: Suite cannot be deleted if referenced in task assignments.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                response = requests.delete(f"{self.server_url}/suites/{suite_id}", headers=self.headers, timeout=3)
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", f"Suite '{suite_name}' deleted successfully!")
                    self.refresh_suites()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to delete suite: {response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Network error: {e}")

    def add_project(self):
        dialog = ProjectDialog(self.server_url, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                response = requests.post(f"{self.server_url}/projects", json=data, headers=self.headers, timeout=3)
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Project created successfully!")
                    self.refresh_projects()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to create project: {response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Network error: {e}")

    def create_assignment(self):
        dialog = TaskAssignmentDialog(self.server_url, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            try:
                response = requests.post(f"{self.server_url}/task_assignments", json=data, headers=self.headers, timeout=3)
                if response.status_code == 200:
                    QMessageBox.information(self, "Success", "Task assignment created successfully!")
                    self.refresh_assignments()
                else:
                    QMessageBox.warning(self, "Error", f"Failed to create assignment: {response.text}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Network error: {e}")

    def manage_template(self):
        """Allows uploading a new master template to the server."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Master Template", "", "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return

        try:
            import os
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "Error", "File not found")
                return

            # Upload template
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                response = requests.post(f"{self.server_url}/template", files=files, headers=self.headers, timeout=60)

            if response.status_code == 200:
                QMessageBox.information(self, "Success", "✅ Template uploaded successfully!\n\nExecutors will download this template when creating new sessions.")
            else:
                QMessageBox.warning(self, "Error", f"Failed to upload template: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Network error: {e}")

