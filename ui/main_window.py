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
from logic.state_manager import StateManager
from utils.pdf_export import PdfExporter
from utils.txt_export import TxtExporter
from utils.excel_export import ExcelExporter
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill


class FinalKindleLogAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = StateManager()

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
        self.test_case_layout = QHBoxLayout()
        self.test_case_layout.addWidget(QLabel("Test Case:"))
        self.test_case_input = QLineEdit()
        self.test_case_input.setPlaceholderText("e.g., Kindle_Performance_Test")
        self.test_case_layout.addWidget(self.test_case_input)
        settings_layout.addLayout(self.test_case_layout)

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
        self.export_zip_btn.setVisible(False)
        export_layout.addWidget(self.export_zip_btn)

        # PDF export
        self.export_pdf_btn = QPushButton("📄 Export PDF")
        self.export_pdf_btn.clicked.connect(self.export_pdf_report)
        self.export_pdf_btn.setEnabled(False)
        export_layout.addWidget(self.export_pdf_btn)

        # TXT export
        self.export_txt_btn = QPushButton("📄 Export TXT")
        self.export_txt_btn.clicked.connect(self.export_txt_report)
        self.export_txt_btn.setEnabled(False)
        export_layout.addWidget(self.export_txt_btn)

        # Excel export
        self.export_excel_btn = QPushButton("📊 Export Excel")
        self.export_excel_btn.clicked.connect(self.export_excel_with_highlighting)
        self.export_excel_btn.setEnabled(False)
        export_layout.addWidget(self.export_excel_btn)

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
        """Create waveform boxes tab - NEW TABLE LAYOUT"""
        self.waveform_boxes_tab = QWidget()
        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("📦 Waveform Boxes - Table Layout"))
        top_layout.addStretch()

        self.copy_all_waveforms_btn = QPushButton("📋 Copy All Waveforms")
        self.copy_all_waveforms_btn.clicked.connect(self.copy_all_waveforms_data)
        self.copy_all_waveforms_btn.setMaximumWidth(200)
        top_layout.addWidget(self.copy_all_waveforms_btn)
        layout.addLayout(top_layout)

        # Main results table - optimized for copying to Excel
        self.waveform_table = QTableWidget()
        self.waveform_table.setAlternatingRowColors(True)
        self.waveform_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.waveform_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.waveform_table)

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
            border: 2px solid {'#0d7377' if not self.state.dark_mode else '#14a085'};
            border-radius: 8px;
            padding: 10px;
            margin: 5px;
            background-color: {'#ffffff' if not self.state.dark_mode else '#404040'};
        }}
        QLabel {{
            color: {'#333333' if not self.state.dark_mode else '#ffffff'};
            font-size: 12px;
        }}
        """)

        layout = QVBoxLayout(box)

        # Header
        header_label = QLabel(f"🔄 ITERATION_{result['iteration']:02d}")
        header_label.setStyleSheet(f"""
            font-weight: bold;
            font-size: 14px;
            color: {'#0d7377' if not self.state.dark_mode else '#14a085'};
            padding: 5px;
            background-color: {'#f0f8ff' if not self.state.dark_mode else '#2b2b2b'};
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

    def copy_all_waveforms_data(self):
        """Copy all waveform data from all iterations for single entry mode."""
        self._copy_waveform_data_to_clipboard(self.state.results)

    def copy_file_waveforms_data(self, results):
        """Copy waveform data for all iterations of a specific file."""
        self._copy_waveform_data_to_clipboard(results)

    def _copy_waveform_data_to_clipboard(self, results_to_copy):
        """Helper function to format and copy waveform data."""
        if not results_to_copy:
            self.status_label.setText("No waveform data to copy.")
            return

        all_waveforms_text = []
        for result in sorted(results_to_copy, key=lambda x: x['iteration']):
            iteration_header = f"ITERATION_{result['iteration']:02d}"
            all_waveforms_text.append(iteration_header)

            height_waveform_data = []
            for idx, height_info in enumerate(result['all_heights'], 1):
                height = height_info['height']
                waveform = height_info['waveform']
                height_waveform_data.append(f"{idx}. Height - {height}, Waveform - {waveform}")

            all_waveforms_text.append("\n".join(height_waveform_data))

        final_text = "\n\n".join(all_waveforms_text)
        QApplication.clipboard().setText(final_text)
        self.status_label.setText("Copied waveform data to clipboard.")

    def update_waveform_boxes(self, results_to_display=None):
        """Update the waveform boxes table"""
        self.waveform_table.setRowCount(0)
        if self.processing_mode.currentText() == "Batch Files":
            self.waveform_table.setColumnCount(1)
            for filename, results in self.state.batch_results.items():
                row_position = self.waveform_table.rowCount()
                self.waveform_table.insertRow(row_position)

                header_widget = QWidget()
                header_layout = QHBoxLayout(header_widget)
                header_layout.setContentsMargins(0, 0, 0, 0)

                filename_label = QLabel(f"📄 {filename}")
                filename_label.setFont(QFont("Arial", 10, QFont.Bold))

                copy_all_btn = QPushButton("📋 Copy All")
                copy_all_btn.setMaximumWidth(150)
                copy_all_btn.clicked.connect(lambda checked, r=results: self.copy_file_waveforms_data(r))

                header_layout.addWidget(filename_label)
                header_layout.addStretch()
                header_layout.addWidget(copy_all_btn)

                self.waveform_table.setCellWidget(row_position, 0, header_widget)
                self.waveform_table.setSpan(row_position, 0, 1, 3)

                self.populate_waveform_boxes_table(results)
        else:
            if results_to_display is None:
                results_to_display = self.state.results
            self.populate_waveform_boxes_table(results_to_display)

    def populate_waveform_boxes_table(self, results):
        """Populate the waveform boxes table with results"""
        self.waveform_table.setColumnCount(3)
        self.waveform_table.setHorizontalHeaderLabels(["Iteration", "Waveform Data", "Copy"])

        if not results:
            return

        for result in results:
            row_position = self.waveform_table.rowCount()
            self.waveform_table.insertRow(row_position)

            self.waveform_table.setItem(row_position, 0, QTableWidgetItem(str(result['iteration'])))

            waveform_data = []
            for idx, height_info in enumerate(result['all_heights'], 1):
                height = height_info['height']
                waveform = height_info['waveform']
                waveform_data.append(f"{idx}. Height - {height}, Waveform - {waveform}")

            self.waveform_table.setItem(row_position, 1, QTableWidgetItem("\n".join(waveform_data)))

            copy_btn = QPushButton("📋 Copy")
            copy_btn.setMaximumWidth(100)
            copy_btn.clicked.connect(lambda checked, r=result: self.copy_iteration_data(r))
            self.waveform_table.setCellWidget(row_position, 2, copy_btn)

        self.waveform_table.resizeColumnsToContents()
        self.waveform_table.resizeRowsToContents()

    def toggle_dark_mode(self, checked):
        """Toggle between dark and light mode"""
        self.state.dark_mode = checked
        self.setup_styling()
        # Update waveform boxes with new styling
        if self.state.results or self.state.batch_results:
            self.update_waveform_boxes()

    def setup_styling(self):
        """Setup styling with dark mode support"""
        if self.state.dark_mode:
            with open('ui/dark_mode.qss', 'r') as f:
                self.setStyleSheet(f.read())
        else:
            with open('ui/light_mode.qss', 'r') as f:
                self.setStyleSheet(f.read())

    def on_calculation_mode_changed(self):
        """Handle calculation mode change"""
        mode_map = {0: "default", 1: "swipe", 2: "suspend"}
        self.state.current_mode = mode_map.get(self.calc_mode_combo.currentIndex(), "default")
        self.status_label.setText(f"Mode: {self.calc_mode_combo.currentText()}")

    def on_processing_mode_changed(self, mode):
        """Handle processing mode change"""
        if mode == "Single Entry":
            self.single_group.setVisible(True)
            self.batch_group.setVisible(False)
            self.export_zip_btn.setVisible(False)
            self.export_excel_btn.setVisible(False)
            self.export_pdf_btn.setVisible(True)
            self.export_txt_btn.setVisible(True)
            self.test_case_input.setVisible(True)
            self.test_case_layout.itemAt(0).widget().setVisible(True)
            self.copy_all_waveforms_btn.setVisible(True)
        else:
            self.single_group.setVisible(False)
            self.batch_group.setVisible(True)
            self.export_zip_btn.setVisible(True)
            self.export_excel_btn.setVisible(True)
            self.export_pdf_btn.setVisible(False)
            self.export_txt_btn.setVisible(False)
            self.test_case_input.setVisible(False)
            self.test_case_layout.itemAt(0).widget().setVisible(False)
            self.copy_all_waveforms_btn.setVisible(False)

    def export_pdf_report(self):
        """Export a single PDF report."""
        if not self.state.results:
            QMessageBox.warning(self, "Warning", "No results to export.")
            return

        test_case_name = self.test_case_input.text().strip()
        if not test_case_name:
            QMessageBox.warning(self, "Warning", "Please enter a test case name.")
            return

        default_filename = f"{test_case_name}_report.pdf"
        pdf_path, _ = QFileDialog.getSaveFileName(self, "Save PDF Report", default_filename, "PDF Files (*.pdf)")

        if not pdf_path:
            return

        pdf_exporter = PdfExporter()
        success, message = pdf_exporter.export_pdf_report(self.state.results, pdf_path, self.state.current_mode)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
            logging.error(message)

    def export_txt_report(self):
        """Export a single TXT report."""
        if not self.state.results:
            QMessageBox.warning(self, "Warning", "No results to export.")
            return

        test_case_name = self.test_case_input.text().strip()
        if not test_case_name:
            QMessageBox.warning(self, "Warning", "Please enter a test case name.")
            return

        default_filename = f"{test_case_name}_report.txt"
        txt_path, _ = QFileDialog.getSaveFileName(self, "Save TXT Report", default_filename, "TXT Files (*.txt)")

        if not txt_path:
            return

        txt_exporter = TxtExporter()
        success, message = txt_exporter.export_txt_report(self.state.results, txt_path)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
            logging.error(message)

    def add_iteration(self):
        """Add iteration data"""
        log_content = self.log_input.toPlainText().strip()
        if not log_content:
            QMessageBox.warning(self, "Warning", "Please enter log data")
            return

        iteration_header = f"\nITERATION_{self.state.current_iteration:02d}\n"
        self.state.all_iterations_data += iteration_header + log_content + "\n"

        self.state.current_iteration += 1
        self.log_input.clear()
        self.process_all_btn.setEnabled(True)

        self.status_label.setText(f"Added iteration {self.state.current_iteration-1}. Ready for next iteration.")

    def process_all_iterations(self):
        """Process all iterations"""
        if not self.state.all_iterations_data:
            QMessageBox.warning(self, "Warning", "No iterations to process")
            return

        self.progress_bar.setVisible(True)
        self.status_label.setText("Processing iterations...")

        # Create and start log processor thread
        self.log_processor = LogProcessor(self.state.all_iterations_data, self.state.current_mode)
        self.log_processor.progress_updated.connect(self.progress_bar.setValue)
        self.log_processor.result_ready.connect(self.on_single_processing_complete)
        self.log_processor.error_occurred.connect(self.on_processing_error)
        self.log_processor.start()

    def on_single_processing_complete(self, data):
        """Handle single processing completion"""
        self.state.results = data['results']
        self.state.processed_test_cases.add(self.test_case_input.text().strip())
        self.progress_bar.setVisible(False)
        self.update_all_displays()
        self.enable_export_buttons()
        self.status_label.setText(f"Processed successfully")

    def on_batch_processing_complete(self, data, filename):
        """Handle batch processing completion for a single file."""
        self.state.batch_results[filename] = data['results']
        # Check if all files have been processed
        if len(self.state.batch_results) == len(self.state.loaded_files):
            self.progress_bar.setVisible(False)
            self.update_all_displays()
            self.enable_export_buttons()
            self.status_label.setText(f"Processed {len(self.state.loaded_files)} files")

    def on_processing_error(self, error):
        """Handle processing error"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Processing Error", f"Error during processing: {error}")
        self.status_label.setText("Processing failed")

    def update_all_displays(self):
        """Update all result displays"""
        if not self.state.results and not self.state.batch_results:
            return

        if self.processing_mode.currentText() == "Batch Files":
            self.update_summary_display()
            self.update_batch_display()
            results_to_display = [item for sublist in self.state.batch_results.values() for item in sublist]
            self.update_results_table(results_to_display)
            self.update_heights_table(results_to_display)
            self.update_waveform_boxes()
        else:
            self.update_summary_display(self.state.results)
            self.update_results_table(self.state.results)
            self.update_waveform_boxes(self.state.results)
            self.update_heights_table(self.state.results)
            self.batch_results_text.clear()


    def update_summary_display(self, results_to_display=None):
        """Update summary display"""
        if self.processing_mode.currentText() == "Batch Files":
            self.summary_text.clear()
            for filename, results in self.state.batch_results.items():
                self.generate_summary_for_file(filename, results)
            return

        if results_to_display is None:
            results_to_display = self.state.results

        if not results_to_display:
            self.summary_text.clear()
            return

        self.generate_summary_for_file(self.test_case_input.text() or "Single Entry", results_to_display)

    def generate_summary_for_file(self, filename, results):
        if not results:
            return

        total_iterations = len(results)
        durations = [r['duration'] for r in results]
        avg_duration = sum(durations) / total_iterations
        min_duration = min(durations)
        max_duration = max(durations)

        summary_html = f"""
        <h2>📊 Processing Summary for {filename}</h2>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
        <tr><td><b>Test Case:</b></td><td>{filename}</td></tr>
        <tr><td><b>Processing Mode:</b></td><td>{self.calc_mode_combo.currentText()}</td></tr>
        <tr><td><b>Total Iterations:</b></td><td>{total_iterations}</td></tr>
        <tr><td><b>Average Duration:</b></td><td style="background-color: yellow;">{avg_duration:.3f} seconds</td></tr>
        <tr><td><b>Min Duration:</b></td><td>{min_duration:.3f} seconds</td></tr>
        <tr><td><b>Max Duration:</b></td><td>{max_duration:.3f} seconds</td></tr>
        <tr><td><b>Processing Time:</b></td><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
        </table>

        <h3>📋 Iteration with Average for {filename}:</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; margin-top: 10px;">
        <tr style="background-color: #f0f0f0;">
        <td><b>Test case name</b></td>
"""
        for i in range(1, total_iterations + 1):
            summary_html += f"<td><b>IT_{i:02d}</b></td>"
        summary_html += "<td><b>AVG</b></td></tr>"
        summary_html += f"<tr><td><b>{filename}</b></td>"
        for result in results:
            summary_html += f"<td>{result['duration']:.3f}</td>"
        summary_html += f"<td>{avg_duration:.3f}</td></tr>"
        summary_html += "</table><br><hr><br>"

        self.summary_text.append(summary_html)

    def update_results_table(self, results_to_display=None):
        """Update main results table - optimized for copying"""
        self.results_table.setRowCount(0)
        if self.processing_mode.currentText() == "Batch Files":
            self.results_table.setColumnCount(1)
            for filename, results in self.state.batch_results.items():
                row_position = self.results_table.rowCount()
                self.results_table.insertRow(row_position)
                header_item = QTableWidgetItem(f"📄 {filename}")
                header_item.setBackground(QColor("#e0e0e0"))
                header_item.setFont(QFont("Arial", 10, QFont.Bold))
                self.results_table.setItem(row_position, 0, header_item)
                self.results_table.setSpan(row_position, 0, 1, 8)
                self.populate_results_table(results)
        else:
            if results_to_display is None:
                results_to_display = self.state.results
            self.populate_results_table(results_to_display)

    def populate_results_table(self, results):
        self.results_table.setColumnCount(8)
        headers = ['Iteration', 'Duration (seconds)', 'Start Time', 'Stop Time',
                   'Marker', 'Height', 'Selected Waveform', 'Mode']
        self.results_table.setHorizontalHeaderLabels(headers)

        for result in results:
            row_position = self.results_table.rowCount()
            self.results_table.insertRow(row_position)
            self.results_table.setItem(row_position, 0, QTableWidgetItem(str(result['iteration'])))
            duration_item = QTableWidgetItem(f"{result['duration']:.3f}")
            duration_item.setBackground(QBrush(QColor(255, 255, 0, 100)))
            self.results_table.setItem(row_position, 1, duration_item)
            self.results_table.setItem(row_position, 2, QTableWidgetItem(str(result['start'])))
            self.results_table.setItem(row_position, 3, QTableWidgetItem(str(result['stop'])))
            self.results_table.setItem(row_position, 4, QTableWidgetItem(str(result['marker'])))
            self.results_table.setItem(row_position, 5, QTableWidgetItem(str(result['max_height'])))
            waveform_item = QTableWidgetItem(result['max_height_waveform'])
            waveform_item.setBackground(QBrush(QColor(255, 255, 0, 100)))
            self.results_table.setItem(row_position, 6, waveform_item)
            self.results_table.setItem(row_position, 7, QTableWidgetItem(result['mode']))
        self.results_table.resizeColumnsToContents()

    def update_heights_table(self, results_to_display=None):
        """Update detailed heights and waveforms table"""
        self.heights_table.setRowCount(0)
        if self.processing_mode.currentText() == "Batch Files":
            self.heights_table.setColumnCount(1)
            for filename, results in self.state.batch_results.items():
                row_position = self.heights_table.rowCount()
                self.heights_table.insertRow(row_position)
                header_item = QTableWidgetItem(f"📄 {filename}")
                header_item.setBackground(QColor("#e0e0e0"))
                header_item.setFont(QFont("Arial", 10, QFont.Bold))
                self.heights_table.setItem(row_position, 0, header_item)
                self.heights_table.setSpan(row_position, 0, 1, 6)
                self.populate_heights_table(results)
        else:
            if results_to_display is None:
                results_to_display = self.state.results
            self.populate_heights_table(results_to_display)

    def populate_heights_table(self, results):
        self.heights_table.setColumnCount(6)
        headers = ['Iteration', 'Marker', 'Height', 'Waveform', 'Selected', 'End Time']
        self.heights_table.setHorizontalHeaderLabels(headers)
        for result in results:
            for height_info in result['all_heights']:
                row_position = self.heights_table.rowCount()
                self.heights_table.insertRow(row_position)
                self.heights_table.setItem(row_position, 0, QTableWidgetItem(str(result['iteration'])))
                self.heights_table.setItem(row_position, 1, QTableWidgetItem(str(height_info['marker'])))
                self.heights_table.setItem(row_position, 2, QTableWidgetItem(str(height_info['height'])))
                self.heights_table.setItem(row_position, 3, QTableWidgetItem(height_info['waveform']))
                is_selected = str(height_info['marker']) == str(result['marker'])
                selected_item = QTableWidgetItem("✓" if is_selected else "")
                if is_selected:
                    selected_item.setBackground(QBrush(QColor(255, 255, 0, 150)))
                self.heights_table.setItem(row_position, 4, selected_item)
                end_time = ""
                if 'all_end_times' in result and str(height_info['marker']) in result['all_end_times']:
                    end_time = str(result['all_end_times'][str(height_info['marker'])]['time'])
                self.heights_table.setItem(row_position, 5, QTableWidgetItem(end_time))
        self.heights_table.resizeColumnsToContents()

    def update_batch_display(self):
        """Update batch results display"""
        if not self.state.batch_results:
            return

        batch_html = "<h2>📁 Batch Processing Results</h2>"

        for filename, results in self.state.batch_results.items():
            batch_html += f"<h3>📄 {filename}</h3>"
            if results:
                batch_html += "<table border='1' cellpadding='5' cellspacing='0'>"
                batch_html += "<tr><th>Iteration</th><th>Duration</th><th>Start</th><th>Stop</th><th>Height</th><th>Waveform</th></tr>"

                for result in results:
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

    def export_zip_report(self):
        """Export all reports into a single ZIP file."""
        if not self.state.batch_results:
            QMessageBox.warning(self, "Warning", "No results to export.")
            return

        default_filename = "kindle_batch_reports.zip"
        zip_path, _ = QFileDialog.getSaveFileName(self, "Save ZIP Report", default_filename, "ZIP Files (*.zip)")

        if not zip_path:
            return

        pdf_exporter = PdfExporter()
        success, message = pdf_exporter.export_zip_report(self.state.batch_results, zip_path, self.state.current_mode)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
            logging.error(message)

    def export_excel_with_highlighting(self):
        """Export to Excel with the new format."""
        if self.processing_mode.currentText() != "Batch Files" or not self.state.batch_results:
            QMessageBox.warning(self, "Warning", "Excel export is only available for batch processing.")
            return

        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Batch Results to Excel",
            "kindle_batch_analysis.xlsx",
            "Excel Files (*.xlsx)"
        )

        if not filename:
            return

        excel_exporter = ExcelExporter()
        success, message = excel_exporter.export_excel_with_highlighting(self.state.batch_results, filename)
        if success:
            QMessageBox.information(self, "Success", message)
        else:
            QMessageBox.critical(self, "Error", message)
            logging.error(message)

    def select_batch_files(self):
        """Select files for batch processing"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Log Files", "",
            "Log Files (*.log *.txt);;All Files (*)"
        )
        if files:
            self.state.loaded_files = files
            self.files_list.clear()
            for file in files:
                self.files_list.addItem(os.path.basename(file))
            self.process_batch_btn.setEnabled(True)

    def clear_batch_files(self):
        """Clear selected batch files"""
        self.state.loaded_files = []
        self.files_list.clear()
        self.process_batch_btn.setEnabled(False)

    def process_batch_files(self):
        """Process batch files"""
        if not self.state.loaded_files:
            return

        self.status_label.setText("Processing batch files...")
        self.state.batch_results.clear()
        self.state.threads = []

        for file_path in self.state.loaded_files:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                filename = os.path.basename(file_path)
                self.state.current_processing_file = filename
                # Process content using log processor
                log_processor = LogProcessor(content, self.state.current_mode)
                log_processor.result_ready.connect(lambda data, fn=filename: self.on_batch_processing_complete(data, fn))
                self.state.threads.append(log_processor)
                log_processor.start()

            except Exception as e:
                logging.error(f"Error processing {file_path}: {str(e)}")
                QMessageBox.warning(self, "Warning", f"Error processing {file_path}: {str(e)}")

    def enable_export_buttons(self):
        """Enable export buttons"""
        self.export_zip_btn.setEnabled(True)
        self.export_excel_btn.setEnabled(True)
        self.export_pdf_btn.setEnabled(True)
        self.export_txt_btn.setEnabled(True)

    def clear_all(self):
        """Clear all data"""
        self.state.clear_all()

        self.log_input.clear()
        self.files_list.clear()
        self.summary_text.clear()
        self.results_table.setRowCount(0)
        self.heights_table.setRowCount(0)
        self.batch_results_text.clear()
        self.waveform_table.setRowCount(0)

        self.export_zip_btn.setEnabled(False)
        self.export_excel_btn.setEnabled(False)
        self.export_pdf_btn.setEnabled(False)
        self.export_txt_btn.setEnabled(False)
        self.process_all_btn.setEnabled(False)
        self.process_batch_btn.setEnabled(False)

        self.status_label.setText("Ready")