from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, 
    QTableWidgetItem, QHeaderView, QGroupBox, QLineEdit, QMessageBox, QDialog,
    QFormLayout, QDialogButtonBox
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QFont
from performance_dashboard.logic.network_manager import NetworkManager

class CommentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Reject Reason")
        self.layout = QVBoxLayout(self)
        self.comment_input = QLineEdit()
        self.comment_input.setPlaceholderText("Enter reason for rejection...")
        self.layout.addWidget(QLabel("Reason:"))
        self.layout.addWidget(self.comment_input)
        
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_comment(self):
        return self.comment_input.text()

class LiveAuditWindow(QWidget):
    def __init__(self, suite_filter=None, executor_filter=None, auth_token=None, user_context=None):
        super().__init__()
        self.setWindowTitle("Live Audit Monitor")
        self.resize(1000, 600)
        
        self.suite_filter = suite_filter  # e.g., "P0", "P1", etc.
        self.executor_filter = executor_filter  # Filter by specific executor username
        self.auth_token = auth_token
        self.user_context = user_context if user_context else {}
        
        # Network Manager - created lazily when needed
        self.network_manager = None
        self.data = []
        
        self.init_ui()
        
        # Poll timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_data)
        self.timer.start(5000) # Refresh every 5 seconds

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<b>Live Audit Dashboard</b>"))
        
        self.server_input = QLineEdit("http://localhost:8000")
        self.server_input.setPlaceholderText("Server URL")
        self.server_input.setFixedWidth(200)
        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self.connect_to_server)
        
        header_layout.addStretch()
        header_layout.addWidget(QLabel("Server:"))
        header_layout.addWidget(self.server_input)
        header_layout.addWidget(connect_btn)
        layout.addLayout(header_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "ID", "Test Case", "Executor", "Value (s)", "BRD Ref", "Deviation %", "Status", "Actions"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Legend
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("Legend: "))
        lbl_pending = QLabel(" Pending ")
        lbl_pending.setStyleSheet("background-color: #fff3cd; border: 1px solid gray;")
        lbl_approved = QLabel(" Approved ")
        lbl_approved.setStyleSheet("background-color: #d4edda; border: 1px solid gray;")
        lbl_rejected = QLabel(" Rejected ")
        lbl_rejected.setStyleSheet("background-color: #f8d7da; border: 1px solid gray;")
        
        legend_layout.addWidget(lbl_pending)
        legend_layout.addWidget(lbl_approved)
        legend_layout.addWidget(lbl_rejected)
        legend_layout.addStretch()
        layout.addLayout(legend_layout)
    
    def ensure_network_manager(self):
        """Lazily initialize NetworkManager when needed."""
        if self.network_manager is None:
            from performance_dashboard.logic.network_manager import NetworkManager
            # Pass username for WebSocket authentication
            username = self.user_context.get("username", "auditor")
            self.network_manager = NetworkManager(executor_name=username, token=self.auth_token)
            # Connect dashboard_update signal for real-time updates
            if hasattr(self.network_manager, 'dashboard_update'):
                self.network_manager.dashboard_update.connect(self.on_new_result)
            
            # Start connection explicitly
            self.network_manager.connect()

    def on_new_result(self, result_data):
        """Handle real-time result updates via WebSocket."""
        # Refresh the table to show new result
        self.refresh_data()

    def connect_to_server(self):
        self.ensure_network_manager()
        url = self.server_input.text().strip()
        if url:
            self.network_manager.server_url = url
            self.refresh_data()
            QMessageBox.information(self, "Connected", f"Polling {url}...")

    def refresh_data(self):
        self.ensure_network_manager()
        data = self.network_manager.fetch_dashboard_data()
        self.populate_table(data)

    def populate_table(self, data):
        # Filter data if suite_filter or executor_filter is set
        filtered_data = data
        
        if self.suite_filter:
            # Filter by suite_name field (not test_case_id prefix!)
            print(f"🔍 DEBUG: Filtering by suite: '{self.suite_filter}'")
            print(f"🔍 DEBUG: Before suite filter: {len(filtered_data)} results")
            # Show sample suite_name values for debugging
            if len(filtered_data) > 0:
                sample_suites = set([row.get('suite_name', 'MISSING') for row in filtered_data[:5]])
                print(f"🔍 DEBUG: Sample suite_name values in data: {sample_suites}")
            filtered_data = [row for row in filtered_data if row.get('suite_name', '') == self.suite_filter]
            print(f"🔍 DEBUG: After suite filter: {len(filtered_data)} results")
            if len(filtered_data) > 0:
                print(f"🔍 DEBUG: Sample suite_name: '{filtered_data[0].get('suite_name', 'N/A')}'")
        
        if self.executor_filter:
            # Filter by executor username
            print(f"🔍 DEBUG: Filtering by executor: '{self.executor_filter}'")
            print(f"🔍 DEBUG: Before executor filter: {len(filtered_data)} results")
            filtered_data = [row for row in filtered_data if row.get('executor_name', '') == self.executor_filter]
            print(f"🔍 DEBUG: After executor filter: {len(filtered_data)} results")
            if len(filtered_data) > 0:
                print(f"🔍 DEBUG: Sample executor_name: '{filtered_data[0].get('executor_name', 'N/A')}'")
        
        self.table.setRowCount(len(filtered_data))
        for i, row in enumerate(filtered_data):
            # Create items with explicit text color
            id_item = QTableWidgetItem(str(row['test_case_id']))
            id_item.setForeground(QColor("black"))
            
            name_item = QTableWidgetItem(str(row['test_case_name']))
            name_item.setForeground(QColor("black"))
            
            executor_item = QTableWidgetItem(str(row['executor_name']))
            executor_item.setForeground(QColor("black"))
            
            value_item = QTableWidgetItem(f"{row['value']:.3f}")
            value_item.setForeground(QColor("black"))
            
            # BRD Reference
            if row.get('brd_reference'):
                brd_item = QTableWidgetItem(f"{row['brd_reference']:.3f}")
            else:
                brd_item = QTableWidgetItem("N/A")
            brd_item.setForeground(QColor("black"))
            
            # Deviation %
            if row.get('deviation_percent') is not None:
                dev_val = row['deviation_percent']
                dev_item = QTableWidgetItem(f"{dev_val:+.2f}%")
                # Color code based on deviation
                if abs(dev_val) == 0:
                    dev_item.setBackground(QColor("#d4edda"))  # Green
                elif abs(dev_val) < 10:
                    dev_item.setBackground(QColor("#fff3cd"))  # Yellow
                else:
                    dev_item.setBackground(QColor("#f8d7da"))  # Red
            else:
                dev_item = QTableWidgetItem("N/A")
            dev_item.setForeground(QColor("black"))
            
            status_item = QTableWidgetItem(row['status'])
            status_item.setForeground(QColor("black"))
            
            self.table.setItem(i, 0, id_item)
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, executor_item)
            self.table.setItem(i, 3, value_item)
            self.table.setItem(i, 4, brd_item)
            self.table.setItem(i, 5, dev_item)
            self.table.setItem(i, 6, status_item)
            
            # Color coding for status column
            bg_color = QColor("white")
            if row['status'] == "Pending":
                bg_color = QColor("#fff3cd") # Yellow
            elif row['status'] == "Approved":
                bg_color = QColor("#d4edda") # Green
            elif row['status'] == "Rejected":
                bg_color = QColor("#f8d7da") # Red
            
            status_item.setBackground(bg_color)
            
            # Actions
            if row['status'] == "Pending":
                btn_widget = QWidget()
                btn_layout = QHBoxLayout(btn_widget)
                btn_layout.setContentsMargins(0, 0, 0, 0)
                
                approve_btn = QPushButton("✓")
                approve_btn.setStyleSheet("color: green; font-weight: bold;")
                approve_btn.clicked.connect(lambda _, r=row: self.approve_result(r))
                
                reject_btn = QPushButton("✗")
                reject_btn.setStyleSheet("color: red; font-weight: bold;")
                reject_btn.clicked.connect(lambda _, r=row: self.reject_result(r))
                
                btn_layout.addWidget(approve_btn)
                btn_layout.addWidget(reject_btn)
                self.table.setCellWidget(i, 7, btn_widget)
            else:
                # Clear buttons if status changed
                self.table.removeCellWidget(i, 7)
                if row['status'] == "Rejected":
                    comment_item = QTableWidgetItem(f"Reason: {row['auditor_comment']}")
                    comment_item.setForeground(QColor("black"))

    def approve_result(self, row_data):
        self.ensure_network_manager()
        self.network_manager.update_status(row_data['id'], "Approved", "Looks good")
        self.refresh_data()

    def reject_result(self, row_data):
        self.ensure_network_manager()
        dialog = CommentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            comment = dialog.get_comment()
            if comment:
                self.network_manager.update_status(row_data['id'], "Rejected", comment)
                self.refresh_data()

    def approve_selected(self):
        """Approves the selected result."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            return
        
        self.ensure_network_manager()
        row_data = self.table_data[selected_row]
        self.network_manager.update_status(row_data['id'], "Approved", "Looks good")
        self.refresh_data()

    def reject_selected(self):
        """Rejects the selected result with a comment."""
        selected_row = self.table.currentRow()
        if selected_row < 0:
            return
        
        self.ensure_network_manager()
        from PyQt5.QtWidgets import QInputDialog
        comment, ok = QInputDialog.getText(self, "Reject Result", "Enter rejection comment:")
        
        if ok and comment:
            row_data = self.table_data[selected_row]
            self.network_manager.update_status(row_data['id'], "Rejected", comment)
            self.refresh_data()
