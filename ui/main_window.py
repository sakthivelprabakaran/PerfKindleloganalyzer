import sys
import os
import re
import logging
from datetime import datetime
from pathlib import Path
import zipfile

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QPushButton, QLabel,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QSplitter, QGroupBox, QFileDialog, QProgressBar,
                             QLineEdit, QComboBox, QListWidget, QMessageBox,
                             QHeaderView, QAbstractItemView, QCheckBox, QGridLayout,
                             QFrame, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor, QBrush

from logic.log_processor import LogProcessor
from utils.pdf_export import PdfExporter
from utils.txt_export import TxtExporter
from utils.waveform_plot import WaveformVisualizer
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill


class FinalKindleLogAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.results = []
        self.current_iteration = 1
        self.all_iterations_data = ""
        self.test_case_title = ""
        self.batch_results = []
        self.loaded_files = []
        self.current_mode = "default"
        self.dark_mode = False
        self.processed_test_cases = set()

        logging.basicConfig(filename='kindle_log_analyzer.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        self.setup_ui()
        self.setup_styling()

    def setup_ui(self):
        self.setWindowTitle("Final Kindle Log Analyzer - PDF Export & Waveform Boxes")
        self.setGeometry(50, 50, 1600, 1000)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)

        # Create main splitter
        main_splitter = QSplitter(Qt.Horizontal)

        # Left panel - Enhanced with all features
        left_panel = self.create_enhanced_left_panel()

        # Right panel - Enhanced results with waveform boxes
        right_panel = self.create_enhanced_right_panel()

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 1200])

        main_layout.addWidget(main_splitter)

    def create_enhanced_left_panel(self):
        """Enhanced left panel with all requested features"""
        panel = QGroupBox("📁 Input & Processing")
        layout = QVBoxLayout()

        # Header with dark mode toggle
        header_layout = QHBoxLayout()

        title_label = QLabel("Kindle Log Analyzer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)

        self.dark_mode_toggle = QCheckBox("Dark Mode")
        self.dark_mode_toggle.toggled.connect(self.toggle_dark_mode)
        header_layout.addWidget(self.dark_mode_toggle)

        layout.addLayout(header_layout)

        # Test Case and Settings
        settings_group = QGroupBox("🔧 Configuration")
        settings_layout = QVBoxLayout()

        # Test case input
        test_case_layout = QHBoxLayout()
        test_case_layout.addWidget(QLabel("Test Case:"))
        self.test_case_input = QLineEdit()
        self.test_case_input.setPlaceholderText("e.g., Kindle_Performance_Test")
        test_case_layout.addWidget(self.test_case_input)
        settings_layout.addLayout(test_case_layout)

        # Calculation Mode selection with FIXED suspend
        calc_mode_layout = QHBoxLayout()
        calc_mode_layout.addWidget(QLabel("Mode:"))
        self.calc_mode_combo = QComboBox()
        self.calc_mode_combo.addItems([
            "Default (Button Up)",
            "Swipe (Button Down)",
            "Suspend (Power Button)"
        ])
        self.calc_mode_combo.currentIndexChanged.connect(self.on_calculation_mode_changed)
        calc_mode_layout.addWidget(self.calc_mode_combo)
        settings_layout.addLayout(calc_mode_layout)

        # Processing mode selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Processing:"))
        self.processing_mode = QComboBox()
        self.processing_mode.addItems(["Single Entry", "Batch Files"])
        self.processing_mode.currentTextChanged.connect(self.on_processing_mode_changed)
        mode_layout.addWidget(self.processing_mode)
        settings_layout.addLayout(mode_layout)

        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        # Single iteration section
        self.single_group = QGroupBox("📝 Single Entry")
        single_layout = QVBoxLayout()

        # Log input
        single_layout.addWidget(QLabel("Log Data:"))
        self.log_input = QTextEdit()
        self.log_input.setPlaceholderText("Paste log data here...")
        self.log_input.setMaximumHeight(120)
        single_layout.addWidget(self.log_input)

        # Processing buttons
        single_btn_layout = QHBoxLayout()
        self.add_iteration_btn = QPushButton("➕ Add Iteration")
        self.add_iteration_btn.clicked.connect(self.add_iteration)
        self.process_all_btn = QPushButton("🔄 Process All")
        self.process_all_btn.clicked.connect(self.process_all_iterations)
        self.process_all_btn.setEnabled(False)

        single_btn_layout.addWidget(self.add_iteration_btn)
        single_btn_layout.addWidget(self.process_all_btn)
        single_layout.addLayout(single_btn_layout)

        self.single_group.setLayout(single_layout)
        layout.addWidget(self.single_group)

        # Batch processing section
        self.batch_group = QGroupBox("📂 Batch Processing")
        batch_layout = QVBoxLayout()

        # File selection
        file_btn_layout = QHBoxLayout()
        self.select_files_btn = QPushButton("🗂️ Select Files")
        self.select_files_btn.clicked.connect(self.select_batch_files)
        self.clear_files_btn = QPushButton("🗑️ Clear")
        self.clear_files_btn.clicked.connect(self.clear_batch_files)

        file_btn_layout.addWidget(self.select_files_btn)
        file_btn_layout.addWidget(self.clear_files_btn)
        batch_layout.addLayout(file_btn_layout)

        # File list
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        batch_layout.addWidget(self.files_list)

        # Process button
        self.process_batch_btn = QPushButton("⚡ Process All Files")
        self.process_batch_btn.clicked.connect(self.process_batch_files)
        self.process_batch_btn.setEnabled(False)
        batch_layout.addWidget(self.process_batch_btn)

        self.batch_group.setLayout(batch_layout)
        self.batch_group.setVisible(False)
        layout.addWidget(self.batch_group)

        # Progress section
        progress_group = QGroupBox("📊 Status")
        progress_layout = QVBoxLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # ENHANCED Export section with PDF and improved TXT
        export_group = QGroupBox("💾 Export Options")
        export_layout = QVBoxLayout()

        # ZIP Export
        self.export_zip_btn = QPushButton("📦 Export All Reports (ZIP)")
        self.export_zip_btn.clicked.connect(self.export_zip_report)
        self.export_zip_btn.setEnabled(False)
        export_layout.addWidget(self.export_zip_btn)

        # Excel export
        self.export_excel_btn = QPushButton("📊 Export Excel")
        self.export_excel_btn.clicked.connect(self.export_excel_with_highlighting)
        self.export_excel_btn.setEnabled(False)
        export_layout.addWidget(self.export_excel_btn)

        # Generate Plot button
        self.generate_plot_btn = QPushButton("📈 Generate Waveform Plot")
        self.generate_plot_btn.clicked.connect(self.generate_waveform_plot)
        self.generate_plot_btn.setEnabled(False)
        export_layout.addWidget(self.generate_plot_btn)

        # Clear button
        self.clear_all_btn = QPushButton("🗑️ Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all)
        export_layout.addWidget(self.clear_all_btn)

        export_group.setLayout(export_layout)
        layout.addWidget(export_group)

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def create_enhanced_right_panel(self):
        """Enhanced right panel with waveform boxes and better visualization"""
        panel = QWidget()
        layout = QVBoxLayout()

        self.tab_widget = QTabWidget()

        # Summary Tab
        self.create_summary_tab()

        # Main Results Tab
        self.create_detailed_results_tab()

        # NEW: Waveform Boxes Tab - Visual grid layout
        self.create_waveform_boxes_tab()

        # Heights/Waveforms Tab
        self.create_heights_waveforms_tab()

        # Batch Results Tab
        self.create_batch_results_tab()

        layout.addWidget(self.tab_widget)
        panel.setLayout(layout)
        return panel

    def create_summary_tab(self):
        """Create summary tab"""
        self.summary_tab = QWidget()
        layout = QVBoxLayout()

        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)

        self.summary_tab.setLayout(layout)
        self.tab_widget.addTab(self.summary_tab, "📊 Summary")

    def create_detailed_results_tab(self):
        """Create detailed results tab - COPY-FRIENDLY TABLE"""
        self.results_tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("📋 Main Results (Copy-friendly for Excel)"))

        # Main results table - optimized for copying to Excel
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)

        self.results_tab.setLayout(layout)
        self.tab_widget.addTab(self.results_tab, "📋 Main Results")

    def create_waveform_boxes_tab(self):
        """Create waveform boxes tab - NEW VISUAL LAYOUT"""
        self.waveform_boxes_tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("📦 Waveform Boxes - Visual Grid Layout"))

        # Scrollable area for the boxes
        scroll_area = QScrollArea()
        scroll_widget = QWidget()

        # Grid layout for iteration boxes
        self.waveform_grid = QGridLayout(scroll_widget)
        self.waveform_grid.setSpacing(10)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)

        self.waveform_boxes_tab.setLayout(layout)
        self.tab_widget.addTab(self.waveform_boxes_tab, "📦 Waveform Boxes")

    def create_heights_waveforms_tab(self):
        """Create heights and waveforms detailed tab"""
        self.heights_tab = QWidget()
        layout = QVBoxLayout()

        layout.addWidget(QLabel("📏 All Heights & Waveforms Details"))

        # Detailed heights table
        self.heights_table = QTableWidget()
        self.heights_table.setAlternatingRowColors(True)
        self.heights_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.heights_table)

        self.heights_tab.setLayout(layout)
        self.tab_widget.addTab(self.heights_tab, "📏 Heights & Waveforms")

    def create_batch_results_tab(self):
        """Create batch results tab"""
        self.batch_tab = QWidget()
        layout = QVBoxLayout()

        self.batch_results_text = QTextEdit()
        self.batch_results_text.setReadOnly(True)
        layout.addWidget(self.batch_results_text)

        self.batch_tab.setLayout(layout)
        self.tab_widget.addTab(self.batch_tab, "📁 Batch Results")

    def create_iteration_waveform_box(self, result):
        """Create a visual box for each iteration's waveform data"""
        box = QFrame()
        box.setFrameStyle(QFrame.StyledPanel)
        box.setStyleSheet(f"""
        QFrame {{
            border: 2px solid {'#0d7377' if not self.dark_mode else '#14a085'};
            border-radius: 8px;
            padding: 10px;
            margin: 5px;
            background-color: {'#ffffff' if not self.dark_mode else '#404040'};
        }}
        QLabel {{
            color: {'#333333' if not self.dark_mode else '#ffffff'};
            font-size: 12px;
        }}
        """)

        layout = QVBoxLayout(box)

        # Header
        header_label = QLabel(f"🔄 ITERATION_{result['iteration']:02d}")
        header_label.setStyleSheet(f"""
            font-weight: bold;
            font-size: 14px;
            color: {'#0d7377' if not self.dark_mode else '#14a085'};
            padding: 5px;
            background-color: {'#f0f8ff' if not self.dark_mode else '#2b2b2b'};
            border-radius: 4px;
        """)
        header_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(header_label)

        # Duration - highlighted
        duration_label = QLabel(f"⏱️ Duration: {result['duration']:.3f} seconds")
        duration_label.setStyleSheet(f"""
            font-weight: bold;
            background-color: yellow;
            color: black;
            padding: 3px;
            border-radius: 3px;
        """)
        layout.addWidget(duration_label)

        # Selected waveform - highlighted
        selected_label = QLabel(f"🎯 Selected: {result['max_height_waveform']}")
        selected_label.setStyleSheet(f"""
            font-weight: bold;
            background-color: yellow;
            color: black;
            padding: 3px;
            border-radius: 3px;
        """)
        layout.addWidget(selected_label)

        # Start/Stop info
        times_label = QLabel(f"🔢 {result['start']} → {result['stop']}")
        times_label.setStyleSheet("font-family: monospace; font-size: 11px;")
        layout.addWidget(times_label)

        # All heights and waveforms
        layout.addWidget(QLabel("📏 All Heights:"))

        for height_info in result['all_heights']:
            is_selected = str(height_info['marker']) == str(result['marker'])
            height_text = f"M{height_info['marker']}: {height_info['height']}px, {height_info['waveform']}"

            height_label = QLabel(height_text)
            if is_selected:
                height_label.setStyleSheet("""
                    background-color: yellow;
                    color: black;
                    font-weight: bold;
                    padding: 2px;
                    border-radius: 2px;
                """)
            else:
                height_label.setStyleSheet("font-size: 11px; padding: 1px;")

            layout.addWidget(height_label)

        # Copy button for this iteration
        copy_btn = QPushButton("📋 Copy Data")
        copy_btn.setMaximumHeight(25)
        copy_btn.clicked.connect(lambda checked, r=result: self.copy_iteration_data(r))
        layout.addWidget(copy_btn)

        return box

    def copy_iteration_data(self, result):
        """Copy iteration data to clipboard in the requested format"""
        # Create a list to store the height and waveform information

        # Iterate through all heights and extract the required information with numbering
        height_waveform_data = []
        for idx, height_info in enumerate(result['all_heights'], 1):
            height = height_info['height']
            waveform = height_info['waveform']
            height_waveform_data.append(f"{idx}. Height - {height}, Waveform - {waveform}")

        # Join all entries with newlines
        data = "\n".join(height_waveform_data)

        QApplication.clipboard().setText(data)
        self.status_label.setText(f"Copied Iteration {result['iteration']} waveform data to clipboard")

    def update_waveform_boxes(self):
        """Update the waveform boxes grid"""
        if not self.results and not self.batch_results:
            return

        # Clear existing boxes
        for i in reversed(range(self.waveform_grid.count())):
            self.waveform_grid.itemAt(i).widget().setParent(None)

        results_to_display = self.results
        if self.processing_mode.currentText() == "Batch Files":
            results_to_display = [item for sublist in [batch['results'] for batch in self.batch_results] for item in sublist]


        # Add new boxes in a 3-column grid
        cols = 3
        for idx, result in enumerate(results_to_display):
            row = idx // cols
            col = idx % cols

            box = self.create_iteration_waveform_box(result)
            self.waveform_grid.addWidget(box, row, col)

        # Add stretch to fill remaining space
        self.waveform_grid.setRowStretch(len(results_to_display) // cols + 1, 1)

    def toggle_dark_mode(self, checked):
        """Toggle between dark and light mode"""
        self.dark_mode = checked
        self.setup_styling()
        # Update waveform boxes with new styling
        if self.results or self.batch_results:
            self.update_waveform_boxes()

    def setup_styling(self):
        """Setup styling with dark mode support"""
        if self.dark_mode:
            # Dark mode styling
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QWidget {
                    background-color: #2b2b2b;
                    color: #ffffff;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #555555;
                    border-radius: 8px;
                    margin: 8px 0px;
                    padding-top: 10px;
                    background-color: #3c3c3c;
                    color: #ffffff;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    color: #ffffff;
                }
                QPushButton {
                    background-color: #0d7377;
                    color: white;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #14a085;
                }
                QPushButton:pressed {
                    background-color: #0a5d61;
                }
                QPushButton:disabled {
                    background-color: #555555;
                    color: #888888;
                }
                QLineEdit, QTextEdit, QComboBox {
                    border: 2px solid #555555;
                    border-radius: 4px;
                    padding: 8px;
                    background-color: #404040;
                    color: #ffffff;
                }
                QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                    border-color: #0d7377;
                }
                QTableWidget {
                    background-color: #404040;
                    alternate-background-color: #4a4a4a;
                    color: #ffffff;
                    gridline-color: #555555;
                    selection-background-color: #0d7377;
                    selection-color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #0d7377;
                    color: white;
                    padding: 8px;
                    border: 1px solid #555555;
                    font-weight: bold;
                }
                QTabWidget::pane {
                    border: 1px solid #555555;
                    background-color: #3c3c3c;
                }
                QTabBar::tab {
                    background: #505050;
                    color: #ffffff;
                    padding: 10px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #0d7377;
                    color: white;
                }
                QListWidget {
                    background-color: #404040;
                    color: #ffffff;
                    border: 2px solid #555555;
                }
                QProgressBar {
                    border: 2px solid #555555;
                    border-radius: 5px;
                    background-color: #404040;
                }
                QProgressBar::chunk {
                    background-color: #0d7377;
                    border-radius: 3px;
                }
                QScrollArea {
                    background-color: #3c3c3c;
                    border: 1px solid #555555;
                }
                QLabel {
                    color: #ffffff;
                }
            """)
        else:
            # Light mode styling
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QWidget {
                    background-color: #f0f0f0;
                    color: #333333;
                }
                QGroupBox {
                    font-weight: bold;
                    border: 2px solid #cccccc;
                    border-radius: 8px;
                    margin: 8px 0px;
                    padding-top: 10px;
                    background-color: #ffffff;
                    color: #333333;
                }
                QGroupBox::title {
                    subcontrol-origin: margin;
                    left: 10px;
                    padding: 0 8px 0 8px;
                    color: #333333;
                }
                QPushButton {
                    background-color: #4a90e2;
                    color: white;
                    border: none;
                    padding: 10px 16px;
                    border-radius: 6px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #357abd;
                }
                QPushButton:pressed {
                    background-color: #2968a3;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                    color: #666666;
                }
                QLineEdit, QTextEdit, QComboBox {
                    border: 2px solid #cccccc;
                    border-radius: 4px;
                    padding: 8px;
                    background-color: #ffffff;
                    color: #333333;
                }
                QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
                    border-color: #4a90e2;
                }
                QTableWidget {
                    background-color: #ffffff;
                    alternate-background-color: #f8f9fa;
                    color: #333333;
                    gridline-color: #e1e8ed;
                    selection-background-color: #4a90e2;
                    selection-color: #ffffff;
                }
                QHeaderView::section {
                    background-color: #4a90e2;
                    color: white;
                    padding: 8px;
                    border: 1px solid #cccccc;
                    font-weight: bold;
                }
                QTabWidget::pane {
                    border: 1px solid #cccccc;
                    background-color: #ffffff;
                    border-radius: 4px;
                }
                QTabBar::tab {
                    background: #e0e0e0;
                    color: #333333;
                    padding: 10px 16px;
                    margin-right: 2px;
                    border-top-left-radius: 4px;
                    border-top-right-radius: 4px;
                }
                QTabBar::tab:selected {
                    background: #4a90e2;
                    color: white;
                }
                QListWidget {
                    background-color: #ffffff;
                    color: #333333;
                    border: 2px solid #cccccc;
                }
                QProgressBar {
                    border: 2px solid #cccccc;
                    border-radius: 5px;
                    background-color: #ffffff;
                }
                QProgressBar::chunk {
                    background-color: #4a90e2;
                    border-radius: 3px;
                }
                QScrollArea {
                    background-color: #ffffff;
                    border: 1px solid #cccccc;
                }
                QLabel {
                    color: #333333;
                }
            """)

    def on_calculation_mode_changed(self):
        """Handle calculation mode change"""
        mode_map = {0: "default", 1: "swipe", 2: "suspend"}
        self.current_mode = mode_map.get(self.calc_mode_combo.currentIndex(), "default")
        self.status_label.setText(f"Mode: {self.calc_mode_combo.currentText()}")

    def on_processing_mode_changed(self, mode):
        """Handle processing mode change"""
        if mode == "Single Entry":
            self.single_group.setVisible(True)
            self.batch_group.setVisible(False)
        else:
            self.single_group.setVisible(False)
            self.batch_group.setVisible(True)

    def add_iteration(self):
        """Add iteration data"""
        log_content = self.log_input.toPlainText().strip()
        if not log_content:
            QMessageBox.warning(self, "Warning", "Please enter log data")
            return

        iteration_header = f"\nITERATION_{self.current_iteration:02d}\n"
        self.all_iterations_data += iteration_header + log_content + "\n"

        self.current_iteration += 1
        self.log_input.clear()
        self.process_all_btn.setEnabled(True)

        self.status_label.setText(f"Added iteration {self.current_iteration-1}. Ready for next iteration.")

    def process_all_iterations(self):
        """Process all iterations"""
        if not self.all_iterations_data:
            QMessageBox.warning(self, "Warning", "No iterations to process")
            return

        test_case = self.test_case_input.text().strip()
        if not test_case:
            QMessageBox.warning(self, "Warning", "Please enter a test case name.")
            return

        if test_case in self.processed_test_cases:
            QMessageBox.warning(self, "Warning", f"Test case '{test_case}' has already been processed.")
            return

        self.progress_bar.setVisible(True)
        self.status_label.setText("Processing iterations...")

        # Create and start log processor thread
        self.log_processor = LogProcessor(self.all_iterations_data, self.current_mode)
        self.log_processor.progress_updated.connect(self.progress_bar.setValue)
        self.log_processor.result_ready.connect(self.on_processing_complete)
        self.log_processor.error_occurred.connect(self.on_processing_error)
        self.log_processor.start()

    def on_processing_complete(self, data):
        """Handle processing completion"""
        if self.processing_mode.currentText() == "Single Entry":
            self.results = data['results']
            self.processed_test_cases.add(self.test_case_input.text().strip())
        else:
            self.batch_results.append({
                'filename': self.current_processing_file,
                'results': data['results']
            })

        self.progress_bar.setVisible(False)
        self.update_all_displays()
        self.enable_export_buttons()
        self.status_label.setText(f"Processed successfully")

    def on_processing_error(self, error):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Processing Error", f"Error during processing: {error}")
        self.status_label.setText("Processing failed")

    def update_all_displays(self):
        """Update all result displays"""
        if not self.results and not self.batch_results:
            return

        # Update summary
        self.update_summary_display()

        # Update main results table
        self.update_results_table()

        # Update waveform boxes - NEW
        self.update_waveform_boxes()

        # Update heights and waveforms table
        self.update_heights_table()

        # Update batch display
        self.update_batch_display()

    def update_summary_display(self):
        """Update summary display"""
        results_to_display = self.results
        if self.processing_mode.currentText() == "Batch Files":
            results_to_display = [item for sublist in [batch['results'] for batch in self.batch_results] for item in sublist]

        if not results_to_display:
            return

        total_iterations = len(results_to_display)
        durations = [r['duration'] for r in results_to_display]
        avg_duration = sum(durations) / total_iterations
        min_duration = min(durations)
        max_duration = max(durations)

        # Create the new format for Quick Copy Summary for Excel
        summary_html = f"""
        <h2>📊 Processing Summary</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
        <tr><td><b>Test Case:</b></td><td>{self.test_case_input.text() or 'Not specified'}</td></tr>
        <tr><td><b>Processing Mode:</b></td><td>{self.calc_mode_combo.currentText()}</td></tr>
        <tr><td><b>Total Iterations:</b></td><td>{total_iterations}</td></tr>
        <tr><td><b>Average Duration:</b></td><td style="background-color: yellow;">{avg_duration:.3f} seconds</td></tr>
        <tr><td><b>Min Duration:</b></td><td>{min_duration:.3f} seconds</td></tr>
        <tr><td><b>Max Duration:</b></td><td>{max_duration:.3f} seconds</td></tr>
        <tr><td><b>Processing Time:</b></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        </table>

        <h3>📋 Iteration with Average:</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; margin-top: 10px;">
        <tr style="background-color: #f0f0f0;">
        <td><b>Test case name</b></td>
"""

        # Add iteration columns
        for i in range(1, total_iterations + 1):
            summary_html += f"<td><b>IT_{i:02d}</b></td>"

        # Add AVG column
        summary_html += "<td><b>AVG</b></td></tr>"

        # Add duration values
        test_case_name = self.test_case_input.text() or 'Not specified'
        summary_html += f"<tr><td><b>{test_case_name}</b></td>"

        # Add duration for each iteration
        for result in results_to_display:
            summary_html += f"<td>{result['duration']:.3f}</td>"

        # Add average duration
        summary_html += f"<td>{avg_duration:.3f}</td></tr>"

        summary_html += "</table>"

        self.summary_text.setHtml(summary_html)

    def update_results_table(self):
        """Update main results table - optimized for copying"""
        results_to_display = self.results
        if self.processing_mode.currentText() == "Batch Files":
            results_to_display = [item for sublist in [batch['results'] for batch in self.batch_results] for item in sublist]

        if not results_to_display:
            return

        self.results_table.setRowCount(len(results_to_display))
        self.results_table.setColumnCount(8)

        headers = ['Iteration', 'Duration (seconds)', 'Start Time', 'Stop Time',
                   'Marker', 'Height', 'Selected Waveform', 'Mode']
        self.results_table.setHorizontalHeaderLabels(headers)

        for i, result in enumerate(results_to_display):
            self.results_table.setItem(i, 0, QTableWidgetItem(str(result['iteration'])))

            # Duration is already in seconds
            duration_item = QTableWidgetItem(f"{result['duration']:.3f}")
            duration_item.setBackground(QBrush(QColor(255, 255, 0, 100)))  # Yellow highlighting
            self.results_table.setItem(i, 1, duration_item)

            self.results_table.setItem(i, 2, QTableWidgetItem(str(result['start'])))
            self.results_table.setItem(i, 3, QTableWidgetItem(str(result['stop'])))
            self.results_table.setItem(i, 4, QTableWidgetItem(str(result['marker'])))
            self.results_table.setItem(i, 5, QTableWidgetItem(str(result['max_height'])))

            # Highlight selected waveform
            waveform_item = QTableWidgetItem(result['max_height_waveform'])
            waveform_item.setBackground(QBrush(QColor(255, 255, 0, 100)))  # Yellow highlighting
            self.results_table.setItem(i, 6, waveform_item)

            self.results_table.setItem(i, 7, QTableWidgetItem(result['mode']))

        self.results_table.resizeColumnsToContents()

    def update_heights_table(self):
        """Update detailed heights and waveforms table"""
        results_to_display = self.results
        if self.processing_mode.currentText() == "Batch Files":
            results_to_display = [item for sublist in [batch['results'] for batch in self.batch_results] for item in sublist]

        if not results_to_display:
            return

        # Count total rows needed
        total_rows = sum(len(result['all_heights']) for result in results_to_display)

        self.heights_table.setRowCount(total_rows)
        self.heights_table.setColumnCount(6)

        headers = ['Iteration', 'Marker', 'Height', 'Waveform', 'Selected', 'End Time']
        self.heights_table.setHorizontalHeaderLabels(headers)

        row = 0
        for result in results_to_display:
            for height_info in result['all_heights']:
                self.heights_table.setItem(row, 0, QTableWidgetItem(str(result['iteration'])))
                self.heights_table.setItem(row, 1, QTableWidgetItem(str(height_info['marker'])))
                self.heights_table.setItem(row, 2, QTableWidgetItem(str(height_info['height'])))
                self.heights_table.setItem(row, 3, QTableWidgetItem(height_info['waveform']))

                # Mark if this is the selected marker for final calculation
                is_selected = str(height_info['marker']) == str(result['marker'])
                selected_item = QTableWidgetItem("✓" if is_selected else "")
                if is_selected:
                    selected_item.setBackground(QBrush(QColor(255, 255, 0, 150)))  # Yellow highlighting
                self.heights_table.setItem(row, 4, selected_item)

                # Show end time if available
                end_time = ""
                if 'all_end_times' in result and str(height_info['marker']) in result['all_end_times']:
                    end_time = str(result['all_end_times'][str(height_info['marker'])]['time'])
                self.heights_table.setItem(row, 5, QTableWidgetItem(end_time))

                row += 1

        self.heights_table.resizeColumnsToContents()

    def export_zip_report(self):
        """Export all reports into a single ZIP file."""
        if not self.results and not self.batch_results:
            QMessageBox.warning(self, "Warning", "No results to export.")
            return

        test_case_name = self.test_case_input.text().strip()
        if not test_case_name:
            QMessageBox.warning(self, "Warning", "Please enter a test case name.")
            return

        default_filename = f"{test_case_name}_reports.zip"
        zip_path, _ = QFileDialog.getSaveFileName(self, "Save ZIP Report", default_filename, "ZIP Files (*.zip)")

        if not zip_path:
            return

        try:
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                # Generate PDF report
                pdf_exporter = PdfExporter()
                pdf_path = f"{test_case_name}_report.pdf"
                results_to_export = self.results if self.results else [item for sublist in [b['results'] for b in self.batch_results] for item in sublist]
                pdf_exporter.generate_pdf_report(results_to_export, pdf_path, self.current_mode)
                zipf.write(pdf_path, os.path.basename(pdf_path))
                os.remove(pdf_path)

                # Generate TXT report
                txt_exporter = TxtExporter()
                txt_path = f"{test_case_name}_report.txt"
                txt_exporter.export_txt_file(results_to_export, txt_path)
                zipf.write(txt_path, os.path.basename(txt_path))
                os.remove(txt_path)

            QMessageBox.information(self, "Success", f"Reports successfully exported to {zip_path}")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to create ZIP file: {e}")
            logging.error(f"Failed to create ZIP file: {e}")

    def export_excel_with_highlighting(self):
        """Export to Excel with yellow highlighting"""
        results_to_export = self.results
        if self.processing_mode.currentText() == "Batch Files":
            results_to_export = [item for sublist in [batch['results'] for batch in self.batch_results] for item in sublist]

        if not results_to_export:
            QMessageBox.warning(self, "Warning", "No results to export")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Excel with Highlighting",
            f"{self.test_case_input.text() or 'kindle_analysis'}_highlighted.xlsx",
            "Excel Files (*.xlsx)"
        )

        if filename:
            try:
                workbook = openpyxl.Workbook()

                # Main Results Sheet
                sheet = workbook.active
                sheet.title = "Main Results"

                # Headers
                headers = ['Iteration', 'Duration (seconds)', 'Start Time', 'Stop Time',
                          'Marker', 'Height', 'Selected Waveform', 'Mode']
                for col, header in enumerate(headers, 1):
                    cell = sheet.cell(row=1, column=col, value=header)
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill(start_color="4A90E2", end_color="4A90E2", fill_type="solid")

                # Data with highlighting
                yellow_fill = PatternFill(start_color="FFFF00", end_color="FFFF00", fill_type="solid")

                # Write data
                row = 2
                for result in results_to_export:
                    sheet.cell(row=row, column=1, value=result['iteration'])

                    # Highlight duration
                    duration_cell = sheet.cell(row=row, column=2, value=result['duration'])
                    duration_cell.fill = yellow_fill

                    sheet.cell(row=row, column=3, value=result['start'])
                    sheet.cell(row=row, column=4, value=result['stop'])
                    sheet.cell(row=row, column=5, value=result['marker'])
                    sheet.cell(row=row, column=6, value=result['max_height'])

                    # Highlight selected waveform
                    waveform_cell = sheet.cell(row=row, column=7, value=result['max_height_waveform'])
                    waveform_cell.fill = yellow_fill

                    sheet.cell(row=row, column=8, value=result['mode'])
                    row += 1

                # Auto-size columns
                for column in sheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if cell.value:
                                length = len(str(cell.value))
                                if length > max_length:
                                    max_length = length
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    sheet.column_dimensions[column_letter].width = adjusted_width

                # Detailed Heights Sheet
                detail_sheet = workbook.create_sheet(title="Heights & Waveforms")

                detail_headers = ['Iteration', 'Marker', 'Height', 'Waveform', 'Selected', 'End Time']
                for col, header in enumerate(detail_headers, 1):
                    cell = detail_sheet.cell(row=1, column=col, value=header)
                    cell.font = Font(bold=True, color="FFFFFF")
                    cell.fill = PatternFill(start_color="4A90E2", end_color="4A90E2", fill_type="solid")

                detail_row = 2
                # Write detailed data
                for result in results_to_export:
                    for height_info in result['all_heights']:
                        detail_sheet.cell(row=detail_row, column=1, value=result['iteration'])
                        detail_sheet.cell(row=detail_row, column=2, value=height_info['marker'])
                        detail_sheet.cell(row=detail_row, column=3, value=height_info['height'])
                        detail_sheet.cell(row=detail_row, column=4, value=height_info['waveform'])

                        # Highlight selected rows
                        is_selected = str(height_info['marker']) == str(result['marker'])
                        selected_cell = detail_sheet.cell(row=detail_row, column=5, value="✓" if is_selected else "")
                        if is_selected:
                            selected_cell.fill = yellow_fill
                            # Highlight entire row for selected marker
                            for col in range(1, 7):
                                detail_sheet.cell(row=detail_row, column=col).fill = yellow_fill

                        # End time
                        end_time = ""
                        if 'all_end_times' in result and str(height_info['marker']) in result['all_end_times']:
                            end_time = result['all_end_times'][str(height_info['marker'])]['time']
                        detail_sheet.cell(row=detail_row, column=6, value=end_time)

                        detail_row += 1

                # Auto-size columns for detail sheet
                for column in detail_sheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if cell.value:
                                length = len(str(cell.value))
                                if length > max_length:
                                    max_length = length
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    detail_sheet.column_dimensions[column_letter].width = adjusted_width

                workbook.save(filename)
                QMessageBox.information(self, "Success", f"Excel file with highlighting saved to:\n{filename}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save Excel file: {str(e)}")

    def select_batch_files(self):
        """Select files for batch processing"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Log Files", "",
            "Log Files (*.log *.txt);;All Files (*)"
        )
        if files:
            self.loaded_files = files
            self.files_list.clear()
            for file in files:
                self.files_list.addItem(os.path.basename(file))
            self.process_batch_btn.setEnabled(True)

    def clear_batch_files(self):
        """Clear selected batch files"""
        self.loaded_files = []
        self.files_list.clear()
        self.process_batch_btn.setEnabled(False)

    def process_batch_files(self):
        """Process batch files"""
        if not self.loaded_files:
            return

        test_case = self.test_case_input.text().strip()
        if not test_case:
            QMessageBox.warning(self, "Warning", "Please enter a test case name.")
            return

        if test_case in self.processed_test_cases:
            QMessageBox.warning(self, "Warning", f"Test case '{test_case}' has already been processed.")
            return

        self.status_label.setText("Processing batch files...")
        self.batch_results = []

        for file_path in self.loaded_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                self.current_processing_file = os.path.basename(file_path)
                # Process content using log processor
                self.log_processor = LogProcessor(content, self.current_mode)
                self.log_processor.result_ready.connect(self.on_processing_complete)
                self.log_processor.start()
                self.log_processor.wait()


            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                QMessageBox.warning(self, "Warning", f"Error processing {file_path}: {str(e)}")

        self.processed_test_cases.add(test_case)
        self.status_label.setText(f"Processed {len(self.loaded_files)} files")

    def update_batch_display(self):
        """Update batch results display"""
        if not self.batch_results:
            return

        batch_html = "<h2>📁 Batch Processing Results</h2>"

        for batch in self.batch_results:
            batch_html += f"<h3>📄 {batch['filename']}</h3>"
            if batch['results']:
                batch_html += "<table border='1' cellpadding='5' cellspacing='0'>"
                batch_html += "<tr><th>Iteration</th><th>Duration</th><th>Start</th><th>Stop</th><th>Height</th><th>Waveform</th></tr>"

                for result in batch['results']:
                    batch_html += f"""
                    <tr>
                    <td>{result['iteration']}</td>
                    <td style='background-color: yellow;'>{result['duration']:.3f}</td>
                    <td>{result['start']}</td>
                    <td>{result['stop']}</td>
                    <td>{result['max_height']}</td>
                    <td style='background-color: yellow;'>{result['max_height_waveform']}</td>
                    </tr>
                    """
                batch_html += "</table><br>"
            else:
                batch_html += "<p>No valid results found.</p>"

        self.batch_results_text.setHtml(batch_html)

    def enable_export_buttons(self):
        """Enable export buttons"""
        self.export_zip_btn.setEnabled(True)
        self.export_excel_btn.setEnabled(True)
        self.generate_plot_btn.setEnabled(True)

    def clear_all(self):
        """Clear all data"""
        self.results = []
        self.batch_results = []
        self.loaded_files = []
        self.all_iterations_data = ""
        self.current_iteration = 1
        self.processed_test_cases.clear()

        self.log_input.clear()
        self.files_list.clear()
        self.summary_text.clear()
        self.results_table.setRowCount(0)
        self.heights_table.setRowCount(0)
        self.batch_results_text.clear()

        # Clear waveform boxes
        for i in reversed(range(self.waveform_grid.count())):
            self.waveform_grid.itemAt(i).widget().setParent(None)

        self.export_zip_btn.setEnabled(False)
        self.export_excel_btn.setEnabled(False)
        self.generate_plot_btn.setEnabled(False)
        self.process_all_btn.setEnabled(False)
        self.process_batch_btn.setEnabled(False)

        self.status_label.setText("Ready")

    def generate_waveform_plot(self):
        """Generate and save the waveform plot"""
        results_to_plot = self.results
        if self.processing_mode.currentText() == "Batch Files":
            results_to_plot = [item for sublist in [batch['results'] for batch in self.batch_results] for item in sublist]

        if not results_to_plot:
            QMessageBox.warning(self, "Warning", "No results to generate a plot.")
            return

        default_filename = f"{self.test_case_input.text() or 'kindle_analysis'}_waveform_grid.png"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Waveform Plot", default_filename, "PNG Files (*.png)"
        )

        if filename:
            try:
                visualizer = WaveformVisualizer()
                success, message = visualizer.create_waveform_grid(results_to_plot, output_path=filename)
                if success:
                    QMessageBox.information(self, "Success", f"Waveform plot saved to:\n{filename}")
                else:
                    QMessageBox.critical(self, "Error", f"Failed to generate plot: {message}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"An error occurred while generating the plot: {str(e)}")