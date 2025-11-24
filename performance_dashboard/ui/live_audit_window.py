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
    def __init__(self, suite_filter=None):
        super().__init__()
        self.setWindowTitle("Live Audit Monitor")
        self.resize(1000, 600)
        
        self.suite_filter = suite_filter  # e.g., "P0", "P1", etc.
        self.network_manager = NetworkManager()
        self.network_manager.server_url = "http://localhost:8000" # Default
        
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

    def connect_to_server(self):
        url = self.server_input.text().strip()
        if url:
            self.network_manager.server_url = url
            self.refresh_data()
            QMessageBox.information(self, "Connected", f"Polling {url}...")

    def refresh_data(self):
        data = self.network_manager.fetch_dashboard_data()
        self.populate_table(data)

    def populate_table(self, data):
        # Filter data if suite_filter is set
        if self.suite_filter:
            # Filter by test case ID prefix (e.g., "P0" filters "P03", "P01", etc.)
            filtered_data = [row for row in data if row['test_case_id'].startswith(self.suite_filter)]
        else:
            filtered_data = data
        
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
                    self.table.setItem(i, 7, comment_item)

    def approve_result(self, row_data):
        self.network_manager.update_status(row_data['id'], "Approved", "Looks good")
        self.refresh_data()

    def reject_result(self, row_data):
        dialog = CommentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            comment = dialog.get_comment()
            if comment:
                self.network_manager.update_status(row_data['id'], "Rejected", comment)
                self.refresh_data()
