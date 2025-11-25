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
        
        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("🔍 Search:"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by Test Case ID, Name, Executor, or Status...")
        self.search_input.textChanged.connect(self.filter_table)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Table
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(12)  # Increased from 10 to 12
        self.table.setHorizontalHeaderLabels([
            "ID", "Test Case", "Executor", "Value (s)", "BRD Ref", "Deviation %", 
            "Prev Value", "Deviation % (Prev)", "Notes", "Baseline", "Status", "Actions"
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
        
        # Report Section
        report_layout = QHBoxLayout()
        report_btn = QPushButton("📊 Generate Report")
        report_btn.clicked.connect(self.generate_report)
        report_layout.addWidget(report_btn)
        
        # Stats Display (hidden by default)
        self.stats_label = QLabel("")
        self.stats_label.setStyleSheet("font-weight: bold; padding: 10px; background-color: #f0f0f0; border-radius: 5px;")
        self.stats_label.setVisible(False)
        report_layout.addWidget(self.stats_label)
        
        report_layout.addStretch()
        layout.addLayout(report_layout)
    
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
        # Save the raw data for report generation
        self.data = data
        
        # Filter data if suite_filter or executor_filter is set
        filtered_data = data
        
        if self.suite_filter:
            # Filter by suite_name field (not test_case_id prefix!)
            filtered_data = [row for row in filtered_data if row.get('suite_name', '') == self.suite_filter]
        
        if self.executor_filter:
            # Filter by executor username
            filtered_data = [row for row in filtered_data if row.get('executor_name', '') == self.executor_filter]
        
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
                # Color code based on deviation (NOT using abs!)
                if dev_val < 0:
                    dev_item.setBackground(QColor("#d4edda"))  # Green (performance improved)
                elif 0 <= dev_val <= 10:
                    dev_item.setBackground(QColor("#fff3cd"))  # Yellow (acceptable range)
                else:
                    dev_item.setBackground(QColor("#f8d7da"))  # Red (needs attention)
            else:
                dev_item = QTableWidgetItem("N/A")
            dev_item.setForeground(QColor("black"))
            
            # Previous Value
            if row.get('previous_value'):
                prev_item = QTableWidgetItem(f"{row['previous_value']:.3f}")
            else:
                prev_item = QTableWidgetItem("N/A")
            prev_item.setForeground(QColor("black"))
            
            # Deviation % from Previous
            if row.get('deviation_from_previous') is not None:
                dev_prev_val = row['deviation_from_previous']
                dev_prev_item = QTableWidgetItem(f"{dev_prev_val:+.2f}%")
                # Same color coding as BRD deviation
                if dev_prev_val < 0:
                    dev_prev_item.setBackground(QColor("#d4edda"))  # Green (performance improved)
                elif 0 <= dev_prev_val <= 10:
                    dev_prev_item.setBackground(QColor("#fff3cd"))  # Yellow (acceptable range)
                else:
                    dev_prev_item.setBackground(QColor("#f8d7da"))  # Red (regression detected!)
            else:
                dev_prev_item = QTableWidgetItem("N/A")
            dev_prev_item.setForeground(QColor("black"))
            
            # Notes
            notes_text = row.get('notes', '')
            notes_item = QTableWidgetItem(notes_text)
            notes_item.setToolTip(notes_text)  # Show full text on hover
            notes_item.setForeground(QColor("black"))
            
            # Baseline
            baseline_text = row.get('baseline', '')
            baseline_item = QTableWidgetItem(baseline_text)
            baseline_item.setToolTip(baseline_text)  # Show full text on hover
            baseline_item.setForeground(QColor("black"))
            
            status_item = QTableWidgetItem(row['status'])
            status_item.setForeground(QColor("black"))
            
            self.table.setItem(i, 0, id_item)
            self.table.setItem(i, 1, name_item)
            self.table.setItem(i, 2, executor_item)
            self.table.setItem(i, 3, value_item)
            self.table.setItem(i, 4, brd_item)
            self.table.setItem(i, 5, dev_item)
            self.table.setItem(i, 6, prev_item)
            self.table.setItem(i, 7, dev_prev_item)
            self.table.setItem(i, 8, notes_item)
            self.table.setItem(i, 9, baseline_item)
            self.table.setItem(i, 10, status_item)
            
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
                self.table.setCellWidget(i, 11, btn_widget)  # Changed from 9 to 11
            else:
                # Clear buttons if status changed
                self.table.removeCellWidget(i, 11)  # Changed from 9 to 11
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
    
    def filter_table(self):
        """Filters table rows based on search input."""
        search_text = self.search_input.text().lower()
        
        # Show all rows if search is empty
        if not search_text:
            for row in range(self.table.rowCount()):
                self.table.setRowHidden(row, False)
            return
        
        # Hide rows that don't match search
        for row in range(self.table.rowCount()):
            # Check Test Case ID (column 0)
            test_case_id = self.table.item(row, 0).text().lower() if self.table.item(row, 0) else ""
            # Check Test Case Name (column 1)
            test_case_name = self.table.item(row, 1).text().lower() if self.table.item(row, 1) else ""
            # Check Executor (column 2)
            executor = self.table.item(row, 2).text().lower() if self.table.item(row, 2) else ""
            # Check Status (column 6)
            status = self.table.item(row, 6).text().lower() if self.table.item(row, 6) else ""
            
            # Show row if search text matches any column
            matches = (search_text in test_case_id or 
                      search_text in test_case_name or 
                      search_text in executor or 
                      search_text in status)
            
            self.table.setRowHidden(row, not matches)
    
    def generate_report(self):
        """Generate audit report from current Live Monitor data."""
        # Ensure we have a network manager and fetch fresh data if needed
        self.ensure_network_manager()
        
        if not self.data:
            # Try to fetch data first
            self.refresh_data()
            
        if not self.data:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Data", "No test results available. Make sure the server is connected and has test data.")
            return
        
        # Get filtered data (respecting current suite and executor filters)
        filtered_data = self.data
        
        if self.suite_filter:
            filtered_data = [row for row in filtered_data if row.get('suite_name', '') == self.suite_filter]
        
        if self.executor_filter:
            filtered_data = [row for row in filtered_data if row.get('executor_name', '') == self.executor_filter]
        
        if not filtered_data:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "No Data", "No test results match the current filters.")
            return
        
        # Initialize stats
        stats = {
            'Green': 0,      # Current < Reference (improved performance)
            'Yellow': 0,     # 0% <= deviation <= 10% (acceptable)
            'Red': 0,        # deviation > 10% (needs attention)
            'Blocked_NA': 0, # No reference or blocked
            'Total': 0
        }
        
        # Analyze each result using the same logic as manual audit
        for row in filtered_data:
            curr_val = row.get('value', 0)
            ref_val = row.get('brd_reference')
            status = row.get('status', 'Pending')
            
            # Check if Blocked/NA
            if ref_val is None or ref_val == 'N/A':
                stats['Blocked_NA'] += 1
            else:
                try:
                    curr = float(curr_val)
                    ref = float(ref_val)
                    
                    if ref == 0:
                        deviation = 0.0
                    else:
                        deviation = ((curr - ref) / ref) * 100
                    
                    # Categorize based on deviation
                    if deviation < 0:
                        stats['Green'] += 1  # Performance improved
                    elif 0 <= deviation <= 10:
                        stats['Yellow'] += 1  # Within acceptable range
                    else:
                        stats['Red'] += 1  # Needs attention
                        
                except (ValueError, TypeError):
                    stats['Blocked_NA'] += 1
            
            stats['Total'] += 1
        
        # Display stats
        stats_text = (
            f"📊 <b>Report Summary:</b> "
            f"<span style='color: green;'>✅ Green: {stats['Green']}</span> | "
            f"<span style='color: #d4a00c;'>⚠️  Yellow: {stats['Yellow']}</span> | "
            f"<span style='color: red;'>❌ Red: {stats['Red']}</span> | "
            f"<span style='color: gray;'>🚫 Blocked/NA: {stats['Blocked_NA']}</span> | "
            f"<b>Total: {stats['Total']}</b>"
        )
        self.stats_label.setText(stats_text)
        self.stats_label.setVisible(True)
        
        # Optional: Apply color coding to table rows based on categories
        self.apply_color_coding()
    
    def apply_color_coding(self):
        """Apply color coding to table rows based on deviation categories."""
        for row in range(self.table.rowCount()):
            if self.table.isRowHidden(row):
                continue
            
            # Get values from table
            brd_ref_item = self.table.item(row, 4)  # BRD Ref column
            value_item = self.table.item(row, 3)     # Value column
            
            if not brd_ref_item or not value_item:
                continue
            
            brd_ref_text = brd_ref_item.text()
            value_text = value_item.text()
            
            # Determine color based on deviation
            color = None
            if brd_ref_text == 'N/A':
                color = QColor("#e2e3e5")  # Gray for Blocked/NA
            else:
                try:
                    curr = float(value_text)
                    ref = float(brd_ref_text)
                    
                    if ref == 0:
                        deviation = 0.0
                    else:
                        deviation = ((curr - ref) / ref) * 100
                    
                    if deviation < 0:
                        color = QColor("#d4edda")  # Green
                    elif 0 <= deviation <= 10:
                        color = QColor("#fff3cd")  # Yellow
                    else:
                        color = QColor("#f8d7da")  # Red
                except (ValueError, TypeError):
                    color = QColor("#e2e3e5")  # Gray for errors
            
            # Apply color to entire row
            if color:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        item.setBackground(color)
