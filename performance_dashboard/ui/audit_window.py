from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, 
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox, QMessageBox, QFrame,
    QTabWidget, QRadioButton, QButtonGroup, QComboBox, QPlainTextEdit, QShortcut,
    QApplication, QCheckBox
)
from PyQt5.QtGui import QColor, QFont, QKeySequence
from PyQt5.QtCore import Qt
import pandas as pd
from performance_dashboard.logic.audit_manager import AuditManager
import io

from performance_dashboard.ui.live_audit_window import LiveAuditWindow

class AuditWindow(QWidget):
    """
    Window for the Audit and Report feature.
    Allows selecting Current and Reference files, generating comparison, and exporting reports.
    """
    def __init__(self, return_callback):
        super().__init__()
        self.return_callback = return_callback
        self.audit_manager = AuditManager()
        self.current_file_path = ""
        self.reference_file_path = ""
        self.single_file_path = ""
        self.report_df = pd.DataFrame()
        self.live_window = None # Keep reference
        
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
        
        live_btn = QPushButton("🔴 Live Monitor")
        live_btn.clicked.connect(self.open_live_monitor)
        live_btn.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        
        header_layout.addWidget(back_btn)
        header_layout.addWidget(title_label)
        header_layout.addWidget(live_btn)
        layout.addLayout(header_layout)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_file_import_tab(), "File Import")
        self.tabs.addTab(self.create_manual_input_tab(), "Manual Input / Paste")
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
                QMessageBox.critical(self, "Error", f"Failed to save report: {e}")

    def open_live_monitor(self):
        if self.live_window is None:
            self.live_window = LiveAuditWindow()
        self.live_window.show()
