from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, 
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QMessageBox, QFrame,
    QTabWidget, QLineEdit, QRadioButton, QButtonGroup, QComboBox, QPlainTextEdit, QShortcut,
    QApplication, QCheckBox
)
from PyQt5.QtGui import QColor, QFont, QKeySequence
from PyQt5.QtCore import Qt
import pandas as pd
import os
from performance_dashboard.logic.audit_manager import AuditManager
import io

from performance_dashboard.ui.live_audit_window import LiveAuditWindow

class AuditWindow(QWidget):
    """
    Window for the Audit and Report feature.
    Allows selecting Current and Reference files, generating comparison, and exporting reports.
    """
    def __init__(self, return_callback=None, auth_token=None, user_context=None):
        super().__init__()
        self.return_callback = return_callback
        self.auth_token = auth_token
        self.user_context = user_context if user_context else {}
        self.audit_manager = AuditManager()
        self.current_file_path = ""
        self.reference_file_path = ""
        self.single_file_path = ""
        self.report_df = pd.DataFrame()
        self.live_window = None # Keep reference
        
        # For My Assignments functionality
        self.username = ""
        self.server_url = "http://localhost:8000"
        self.my_assignments = []
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.clicked.connect(self.return_callback)
        back_btn.setFixedWidth(100)
        
        title_label = QLabel("Audit & Report Generation")
        title_label.setFont(QFont("Arial", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        # Live Monitor button (top bar) - opens general monitor without filters
        live_btn = QPushButton("🔴 Live Monitor")
        live_btn.setStyleSheet("background-color: #dc3545; color: white; padding: 8px; font-weight: bold;")
        live_btn.clicked.connect(lambda: self.open_general_live_monitor())
        
        header_layout.addWidget(back_btn)
        header_layout.addWidget(live_btn)
        header_layout.addWidget(title_label)
        header_layout.addWidget(live_btn)
        layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_file_import_tab(), "File Import")
        self.tabs.addTab(self.create_manual_input_tab(), "Manual Input / Paste")
        self.tabs.addTab(self.create_my_assignments_tab(), "👤 My Assignments")
        layout.addWidget(self.tabs)
        
        # Summary Stats Area (Redesigned)
        self.stats_group = QGroupBox("Summary Statistics")
        self.stats_group.setVisible(False)
        stats_layout = QVBoxLayout(self.stats_group)
        
        # Stats Table
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(2)
        self.stats_table.setHorizontalHeaderLabels(["Category", "Count"])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.verticalHeader().setVisible(False)
        self.stats_table.setRowCount(5) # Green, Yellow, Red, Blocked, Total
        self.stats_table.setFixedHeight(180) # Compact height
        self.stats_table.setFixedWidth(500) # Fixed width for compactness
        
        # Initialize rows
        categories = [
            ("Green (Improved)", "#d4edda", "#155724"),
            ("Yellow (Acceptable)", "#fff3cd", "#856404"),
            ("Red (Regression)", "#f8d7da", "#721c24"),
            ("Blocked / NA", "#e2e3e5", "#383d41"),
            ("Total Scenarios", "#ffffff", "#000000")
        ]
        
        for i, (name, bg, fg) in enumerate(categories):
            name_item = QTableWidgetItem(name)
            name_item.setBackground(QColor(bg))
            name_item.setForeground(QColor(fg))
            name_item.setFlags(Qt.ItemIsEnabled)
            name_item.setFont(QFont("Arial", 12, QFont.Bold))
            
            count_item = QTableWidgetItem("0")
            count_item.setBackground(QColor(bg))
            count_item.setForeground(QColor(fg))
            count_item.setFlags(Qt.ItemIsEnabled)
            count_item.setTextAlignment(Qt.AlignCenter)
            count_item.setFont(QFont("Arial", 12, QFont.Bold))
            
            self.stats_table.setItem(i, 0, name_item)
            self.stats_table.setItem(i, 1, count_item)
            
        stats_layout.addWidget(self.stats_table)
        
        # Center the Stats Group
        stats_container = QHBoxLayout()
        stats_container.addStretch()
        stats_container.addWidget(self.stats_group)
        stats_container.addStretch()
        layout.addLayout(stats_container)
        
        # Filters
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter Results:"))
        
        self.chk_green = QCheckBox("Green (Improved)")
        self.chk_green.setChecked(True)
        self.chk_green.stateChanged.connect(self.filter_results)
        
        self.chk_yellow = QCheckBox("Yellow (Acceptable)")
        self.chk_yellow.setChecked(True)
        self.chk_yellow.stateChanged.connect(self.filter_results)
        
        self.chk_red = QCheckBox("Red (Regression)")
        self.chk_red.setChecked(True)
        self.chk_red.stateChanged.connect(self.filter_results)
        
        self.chk_blocked = QCheckBox("Blocked / NA")
        self.chk_blocked.setChecked(True)
        self.chk_blocked.stateChanged.connect(self.filter_results)
        
        filter_layout.addWidget(self.chk_green)
        filter_layout.addWidget(self.chk_yellow)
        filter_layout.addWidget(self.chk_red)
        filter_layout.addWidget(self.chk_blocked)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # Detailed Results Table (Shared)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(6)
        self.results_table.setHorizontalHeaderLabels([
            "Test Case ID", "Test Case Name", "Current Avg", "Ref Avg", "Deviation %", "Category"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)
        
        # Export Button (Shared)
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        self.export_btn = QPushButton("Export Report to Excel")
        self.export_btn.clicked.connect(self.export_report)
        self.export_btn.setEnabled(False)
        self.export_btn.setFixedWidth(300) # Fixed width
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:disabled {
                background-color: #B0BEC5;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        export_layout.addWidget(self.export_btn)
        export_layout.addStretch()
        layout.addLayout(export_layout)

    def create_file_import_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Single File Section (Now the only option)
        self.single_file_group = QGroupBox("Select Excel File")
        single_layout = QVBoxLayout(self.single_file_group)
        
        file_layout = QHBoxLayout()
        self.single_file_label = QLabel("File: Not Selected")
        single_btn = QPushButton("Select File")
        single_btn.clicked.connect(self.select_single_file)
        file_layout.addWidget(self.single_file_label)
        file_layout.addWidget(single_btn)
        single_layout.addLayout(file_layout)
        
        # Column Selectors
        cols_layout = QHBoxLayout()
        
        self.col_id_combo = QComboBox()
        self.col_ref_combo = QComboBox()
        self.col_curr_combo = QComboBox()
        self.col_notes_combo = QComboBox()
        
        cols_layout.addWidget(QLabel("ID Column:"))
        cols_layout.addWidget(self.col_id_combo)
        cols_layout.addWidget(QLabel("Reference (BRD):"))
        cols_layout.addWidget(self.col_ref_combo)
        cols_layout.addWidget(QLabel("Current:"))
        cols_layout.addWidget(self.col_curr_combo)
        cols_layout.addWidget(QLabel("Notes (Optional):"))
        cols_layout.addWidget(self.col_notes_combo)
        
        single_layout.addLayout(cols_layout)
        layout.addWidget(self.single_file_group)
        
        # Generate Button (Centered and Styled)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.generate_btn = QPushButton("Generate Audit Report")
        self.generate_btn.clicked.connect(self.generate_report_file)
        self.generate_btn.setEnabled(False)
        self.generate_btn.setFixedWidth(300) # Fixed width
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:disabled {
                background-color: #A5D6A7;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.generate_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        layout.addStretch()
        return tab

    def create_manual_input_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        layout.addWidget(QLabel("Paste data from Excel (Ctrl+V)."))
        layout.addWidget(QLabel("Columns: ID, Reference, Current, Notes (Optional)"))
        layout.addWidget(QLabel("Tip: You can type 'Blocked' or 'NA' directly in the 'Current Value' column."))
        
        self.manual_table = QTableWidget()
        self.manual_table.setColumnCount(4)
        self.manual_table.setHorizontalHeaderLabels(["Test Case ID", "Reference Value", "Current Value", "Notes"])
        self.manual_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Enable pasting
        self.paste_shortcut = QShortcut(QKeySequence.Paste, self.manual_table)
        self.paste_shortcut.activated.connect(self.paste_data)
        
        layout.addWidget(self.manual_table)
        
        # Analyze Button (Centered and Styled)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        analyze_btn = QPushButton("Analyze Manual Data")
        analyze_btn.clicked.connect(self.analyze_manual_data)
        analyze_btn.setFixedWidth(300) # Fixed width
        analyze_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                font-weight: bold; 
                padding: 10px; 
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        btn_layout.addWidget(analyze_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return tab

    def create_my_assignments_tab(self):
        """Creates the My Assignments tab for auditors."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Server Input only (username from logged-in user)
        input_layout = QHBoxLayout()
        input_layout.addWidget(QLabel("Server:"))
        self.auditor_server_input = QLineEdit(self.server_url)
        self.auditor_server_input.setFixedWidth(200)
        input_layout.addWidget(self.auditor_server_input)
        
        fetch_btn = QPushButton("🔄 Fetch My Assignments")
        fetch_btn.clicked.connect(self.fetch_my_assignments)
        fetch_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        input_layout.addWidget(fetch_btn)
        input_layout.addStretch()
        layout.addLayout(input_layout)
        
        # Assignments Table
        self.assignments_table = QTableWidget()
        self.assignments_table.setColumnCount(6)
        self.assignments_table.setHorizontalHeaderLabels([
            "Project", "Suite", "Executor", "BRD Status", "Actions", "Live Monitor"
        ])
        self.assignments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.assignments_table)
        
        return tab

    def select_single_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select File", "", "Excel Files (*.xlsx)")
        if file_path:
            self.single_file_path = file_path
            self.single_file_label.setText(f"File: {file_path.split('/')[-1]}")
            self.load_columns_for_single_file(file_path)
            self.check_ready()

    def load_columns_for_single_file(self, file_path):
        try:
            df = pd.read_excel(file_path)
            cols = df.columns.tolist()
            
            for combo in [self.col_id_combo, self.col_ref_combo, self.col_curr_combo, self.col_notes_combo]:
                combo.clear()
                combo.addItems(cols)
                
            # Try to auto-select smart defaults
            self.set_combo_text(self.col_id_combo, ["ID", "Test Case", "Name"])
            self.set_combo_text(self.col_ref_combo, ["Ref", "BRD", "Baseline"])
            self.set_combo_text(self.col_curr_combo, ["Curr", "Avg", "Average"])
            self.set_combo_text(self.col_notes_combo, ["Note", "Comment"])
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load columns: {e}")

    def set_combo_text(self, combo, keywords):
        for i in range(combo.count()):
            text = combo.itemText(i).lower()
            for kw in keywords:
                if kw.lower() in text:
                    combo.setCurrentIndex(i)
                    return

    def check_ready(self):
        self.generate_btn.setEnabled(bool(self.single_file_path))

    def paste_data(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if not text:
            return
            
        rows = text.split('\n')
        start_row = self.manual_table.currentRow()
        start_col = self.manual_table.currentColumn()
        
        if start_row < 0: start_row = 0
        if start_col < 0: start_col = 0
        
        # Add enough rows
        needed_rows = start_row + len(rows) - self.manual_table.rowCount()
        if needed_rows > 0:
            for _ in range(needed_rows):
                self.manual_table.insertRow(self.manual_table.rowCount())
                
        for i, row_text in enumerate(rows):
            if not row_text.strip(): continue
            cols = row_text.split('\t')
            for j, col_text in enumerate(cols):
                target_col = start_col + j
                if target_col < self.manual_table.columnCount(): # Ensure we don't go out of bounds
                    self.manual_table.setItem(start_row + i, target_col, QTableWidgetItem(col_text.strip()))

    def analyze_manual_data(self):
        data = []
        for i in range(self.manual_table.rowCount()):
            id_item = self.manual_table.item(i, 0)
            ref_item = self.manual_table.item(i, 1) # Reference Value
            curr_item = self.manual_table.item(i, 2) # Current Value
            note_item = self.manual_table.item(i, 3) # Notes
            
            # Check if essential items exist and are not empty
            tc_id = id_item.text().strip() if id_item else ""
            
            # If ID is empty, skip row
            if not tc_id:
                continue
                
            ref_val = ref_item.text().strip() if ref_item else ""
            curr_val = curr_item.text().strip() if curr_item else ""
            
            # We need at least ID. Ref and Curr can be empty (treated as 0 or handled by logic)
            # But usually we need them. Let's be lenient and pass empty strings if missing, 
            # allowing AuditManager to handle them (e.g. as Blocked/NA if non-numeric).
            
            data.append({
                'ID': tc_id,
                'Name': tc_id, # Use ID as Name since there's no dedicated Name column in manual input
                'Ref': ref_val,
                'Curr': curr_val,
                'Notes': note_item.text().strip() if note_item else ''
            })
        
        if not data:
            QMessageBox.warning(self, "No Data", "Please enter or paste data into the table.")
            return

        df = pd.DataFrame(data)
        self.report_df, stats = self.audit_manager.compare_dataframe_columns(df, 'ID', 'Ref', 'Curr', 'Notes', name_col='Name')
        self.display_results(stats)

    def generate_report_file(self):
        df = pd.read_excel(self.single_file_path)
        self.report_df, stats = self.audit_manager.compare_dataframe_columns(
            df, 
            self.col_id_combo.currentText(),
            self.col_ref_combo.currentText(),
            self.col_curr_combo.currentText(),
            self.col_notes_combo.currentText()
        )
            
        self.display_results(stats)

    def display_results(self, stats):
        if self.report_df.empty:
            QMessageBox.warning(self, "No Data", "Could not generate report.")
            return

        # Update Stats Table
        self.stats_table.item(0, 1).setText(str(stats['Green']))
        self.stats_table.item(1, 1).setText(str(stats['Yellow']))
        self.stats_table.item(2, 1).setText(str(stats['Red']))
        self.stats_table.item(3, 1).setText(str(stats['Blocked_NA']))
        self.stats_table.item(4, 1).setText(str(stats['Total']))
        
        self.stats_group.setVisible(True)
        
        # Update Table
        self.results_table.setRowCount(len(self.report_df))
        for i, row in self.report_df.iterrows():
            self.results_table.setItem(i, 0, QTableWidgetItem(str(row['Test Case ID'])))
            self.results_table.setItem(i, 1, QTableWidgetItem(str(row['Test Case Name'])))
            self.results_table.setItem(i, 2, QTableWidgetItem(str(row['Current Avg'])))
            self.results_table.setItem(i, 3, QTableWidgetItem(str(row['Reference Avg'])))
            self.results_table.setItem(i, 4, QTableWidgetItem(f"{row['Deviation %']}%"))
            self.results_table.setItem(i, 5, QTableWidgetItem(row['Category']))
            
            # Color Coding
            color = QColor(255, 255, 255)
            if row['Category'] == 'Green':
                color = QColor("#d4edda")
            elif row['Category'] == 'Yellow':
                color = QColor("#fff3cd")
            elif row['Category'] == 'Red':
                color = QColor("#f8d7da")
            elif row['Category'] == 'Blocked_NA':
                color = QColor("#e2e3e5")
            
            for j in range(6):
                item = self.results_table.item(i, j)
                if item: item.setBackground(color)

        self.export_btn.setEnabled(True)

    def filter_results(self):
        for i in range(self.results_table.rowCount()):
            category_item = self.results_table.item(i, 5)
            if not category_item:
                continue
                
            category = category_item.text()
            should_show = False
            
            if category == 'Green' and self.chk_green.isChecked():
                should_show = True
            elif category == 'Yellow' and self.chk_yellow.isChecked():
                should_show = True
            elif category == 'Red' and self.chk_red.isChecked():
                should_show = True
            elif category == 'Blocked_NA' and self.chk_blocked.isChecked():
                should_show = True
                
            self.results_table.setRowHidden(i, not should_show)

    def export_report(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save Report", "Audit_Report.xlsx", "Excel Files (*.xlsx)")
        if save_path:
            try:
                self.report_df.to_excel(save_path, index=False)
                QMessageBox.information(self, "Success", f"Report saved to {save_path}")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export report: {str(e)}")

    def fetch_my_assignments(self):
        """Fetches assigned audits for the current auditor from server."""
        # Get username from user context (logged-in user)
        username = self.user_context.get("username", "").strip()
        server_url = self.auditor_server_input.text().strip()
        
        if not username:
            QMessageBox.warning(self, "Error", "Could not determine logged-in username. Please re-login.")
            return
        
        try:
            import requests
            headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
            response = requests.get(f"{server_url}/my_audits/{username}", headers=headers, timeout=3)
            if response.status_code == 200:
                self.my_assignments = response.json()
                self.populate_assignments_table()
            else:
                QMessageBox.warning(self, "Error", f"Failed to fetch assignments: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Network Error", f"Could not connect to server: {e}")

    def populate_assignments_table(self):
        """Populates the assignments table with data."""
        self.assignments_table.setRowCount(len(self.my_assignments))
        
        for i, assignment in enumerate(self.my_assignments):
            # Project
            project_item = QTableWidgetItem(assignment['project'])
            project_item.setForeground(QColor("black"))
            self.assignments_table.setItem(i, 0, project_item)
            
            # Suite
            suite_item = QTableWidgetItem(assignment['suite'])
            suite_item.setForeground(QColor("black"))
            self.assignments_table.setItem(i, 1, suite_item)
            
            # Executor
            executor_item = QTableWidgetItem(assignment['executor_username'])
            executor_item.setForeground(QColor("black"))
            self.assignments_table.setItem(i, 2, executor_item)
            
            # BRD Status (check if BRD exists)
            try:
                import requests
                server_url = self.auditor_server_input.text().strip()
                response = requests.get(f"{server_url}/check_brd/{assignment['project']}/{assignment['suite']}", timeout=2)
                if response.status_code == 200 and response.json().get('exists'):
                    status_item = QTableWidgetItem("✓ Uploaded")
                    status_item.setForeground(QColor("#155724"))
                    status_item.setBackground(QColor("#d4edda"))
                else:
                    status_item = QTableWidgetItem("Not Uploaded")
                    status_item.setForeground(QColor("#856404"))
                    status_item.setBackground(QColor("#fff3cd"))
            except:
                status_item = QTableWidgetItem("Unknown")
                status_item.setForeground(QColor("#856404"))
                status_item.setBackground(QColor("#fff3cd"))
            
            self.assignments_table.setItem(i, 3, status_item)
            
            # Upload BRD Button
            upload_btn = QPushButton("📤 Upload BRD")
            upload_btn.clicked.connect(lambda checked, a=assignment: self.upload_brd(a))
            upload_btn.setStyleSheet("padding: 5px; background-color: #007bff; color: white;")
            self.assignments_table.setCellWidget(i, 4, upload_btn)
            
            # Live Monitor Button
            monitor_btn = QPushButton("🔴 Monitor")
            monitor_btn.clicked.connect(lambda checked, a=assignment: self.open_live_monitor_for_assignment(a))
            monitor_btn.setStyleSheet("padding: 5px; background-color: #dc3545; color: white;")
            self.assignments_table.setCellWidget(i, 5, monitor_btn)

    def upload_brd(self, assignment):
        """Handles BRD upload for a specific assignment."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            f"Upload BRD for {assignment['project']} {assignment['suite']}", 
            "", 
            "Excel Files (*.xlsx)"
        )
        
        if not file_path:
            return
        
        try:
            import requests
            server_url = self.auditor_server_input.text().strip()
            auditor_username = self.user_context.get("username", "").strip()
            
            # Send file to server
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                data = {
                    'auditor_username': auditor_username,
                    'project': assignment['project'],
                    'suite': assignment['suite'],
                    'token': self.auth_token # Pass token in body for Form data
                }
                # Note: For UploadFile + Form, we passed token in body as per server update
                # But we can also pass header if server supports it (OAuth2PasswordBearer usually looks at header)
                # Our server implementation checks Form('token') manually for upload_brd
                response = requests.post(f"{server_url}/upload_brd", files=files, data=data, timeout=10)
            
            if response.status_code == 200:
                QMessageBox.information(
                    self,
                    "BRD Uploaded",
                    f"BRD uploaded successfully!\n\n"
                    f"Project: {assignment['project']}\n"
                    f"Suite: {assignment['suite']}\n"
                    f"File: {os.path.basename(file_path)}\n\n"
                    f"Auto-comparison is now active for this suite."
                )
                # Refresh table to update status
                self.fetch_my_assignments()
            else:
                QMessageBox.warning(self, "Upload Failed", f"Server returned error: {response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Upload Error", f"Failed to upload BRD: {e}")

    def open_general_live_monitor(self):
        """Opens Live Monitor without any filters (shows all results)."""
        self.live_window = LiveAuditWindow(
            suite_filter=None,
            executor_filter=None,
            auth_token=self.auth_token,
            user_context=self.user_context
        )
        self.live_window.setWindowTitle("Live Monitor - All Results")
        self.live_window.show()

    def open_live_monitor_for_assignment(self, assignment):
        """Opens Live Monitor filtered for a specific assignment (suite + executor)."""
        suite_filter = assignment['suite']  # e.g., "P0", "P1", "P2"
        executor_filter = assignment.get('executor_username', '')  # Filter by specific executor
        self.live_window = LiveAuditWindow(
            suite_filter=suite_filter,
            executor_filter=executor_filter,
            auth_token=self.auth_token,
            user_context=self.user_context
        )
        self.live_window.setWindowTitle(f"Live Monitor - {assignment['project']} {suite_filter} - {executor_filter}")
        self.live_window.show()

    def open_live_monitor(self, project, suite):
        """Opens the live audit monitor for a specific assignment."""
        # suite_filter=suite to only show matching test cases
        self.live_window = LiveAuditWindow(suite_filter=suite, auth_token=self.auth_token, user_context=self.user_context)
        self.live_window.setWindowTitle(f"Live Monitor - {project} {suite}")
        self.live_window.show()
