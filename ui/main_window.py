import sys
import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTextEdit, QPushButton, QLabel,
                             QTableWidget, QTableWidgetItem, QTabWidget,
                             QSplitter, QGroupBox, QFileDialog, QProgressBar,
                             QLineEdit, QComboBox, QListWidget, QMessageBox,
                             QHeaderView, QAbstractItemView, QCheckBox, QGridLayout,
                             QFrame, QScrollArea, QStackedWidget, QAction)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QFont, QColor, QBrush

from logic.data_manager import DataManager
from logic.log_processor import LogProcessor
from logic.state_manager import StateManager
from ui.launcher_screen import LauncherScreen
from ui.setup_screen import SetupScreen
from ui.execution_dashboard import ExecutionDashboard
from utils.pdf_export import PdfExporter
from utils.txt_export import TxtExporter
from utils.excel_export import ExcelExporter
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill

class FinalKindleLogAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = StateManager()
        self.data_manager = None
        self.active_test_file = None
        self.active_build_details = None
        self.current_sheet = None
        self.current_test_case_index = 0
        self.current_iteration = 0
        self.is_timer_running = False
        self.timer = QTimer(self)
        self.time_elapsed = QTime(0, 0, 0)

        logging.basicConfig(filename='kindle_log_analyzer.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

        self.setup_ui()
        self.connect_signals()
        self.setup_styling()
        self.check_for_previous_session()

    def setup_ui(self):
        self.setWindowTitle("Kindle Log Analyzer & Execution Dashboard")
        self.setGeometry(50, 50, 1600, 1000)

        # Central Stacked Widget
        self.main_stack = QStackedWidget()
        self.setCentralWidget(self.main_stack)

        # Page 0: Launcher Screen
        self.launcher_screen = LauncherScreen()
        self.main_stack.addWidget(self.launcher_screen)

        # Page 1: Setup Screen
        self.setup_screen = SetupScreen()
        self.main_stack.addWidget(self.setup_screen)

        # Page 2: Main Application
        self.main_app_widget = self.create_main_app_widget()
        self.main_stack.addWidget(self.main_app_widget)

        # Menu Bar
        self.create_menu_bar()

        self.show_launcher()

    def create_main_app_widget(self):
        """Creates the main application widget with its splitter layout."""
        main_app_widget = QWidget()
        main_layout = QHBoxLayout(main_app_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_splitter = QSplitter(Qt.Horizontal)

        # Left Panel Stack
        self.left_panel_stack = QStackedWidget()
        log_analyzer_controls = self.create_log_analyzer_controls()
        dashboard_controls = self.create_execution_dashboard_controls()
        self.left_panel_stack.addWidget(log_analyzer_controls)
        self.left_panel_stack.addWidget(dashboard_controls)
        main_splitter.addWidget(self.left_panel_stack)

        # Right Panel
        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 1200])
        main_layout.addWidget(main_splitter)
        return main_app_widget

    def create_menu_bar(self):
        """Creates the main menu bar for the application."""
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")

        return_to_launcher_action = QAction("Return to Launcher", self)
        return_to_launcher_action.triggered.connect(self.show_launcher)
        file_menu.addAction(return_to_launcher_action)

    def show_launcher(self):
        """Switches the view to the launcher screen."""
        self.main_stack.setCurrentIndex(0)
        self.menuBar().hide()

    def show_setup_screen(self):
        """Switches the view to the session setup screen."""
        self.main_stack.setCurrentIndex(1)
        self.menuBar().hide()

    def show_main_app(self, panel_index=0):
        """Switches the view to the main application and shows the correct left panel."""
        self.left_panel_stack.setCurrentIndex(panel_index)
        self.main_stack.setCurrentIndex(2)
        self.menuBar().show()

    def connect_signals(self):
        """Connects signals for all components."""
        # Launcher Screen
        self.launcher_screen.log_analyzer_btn.clicked.connect(lambda: self.show_main_app(0))
        self.launcher_screen.new_session_btn.clicked.connect(self.show_setup_screen)
        self.launcher_screen.recent_sessions_list.itemDoubleClicked.connect(self.load_selected_session)

        # Setup Screen
        self.setup_screen.back_btn.clicked.connect(self.show_launcher)
        self.setup_screen.browse_btn.clicked.connect(self.browse_for_directory)
        self.setup_screen.start_btn.clicked.connect(self.start_new_session)

        # Dashboard Controls
        self.timer.timeout.connect(self.update_timer_display)
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        self.reset_iteration_btn.clicked.connect(self.reset_iteration)
        self.confirm_btn.clicked.connect(self.confirm_iteration)
        self.remember_checkbox.stateChanged.connect(self.save_remember_state)
        self.prev_btn.clicked.connect(self.prev_test_case)
        self.next_btn.clicked.connect(self.next_test_case)
        self.notes_area.textChanged.connect(self.save_note)

        # Main Tab Widget
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def save_current_session(self, filepath, suite, device, week):
        """Saves the path to the currently active test file."""
        try:
            sessions = []
            if os.path.exists("session.json"):
                with open("session.json", "r") as f:
                    sessions = json.load(f)

            # Remove any existing entry for this file to prevent duplicates
            sessions = [s for s in sessions if s.get("filepath") != filepath]

            # Add new session to the top
            sessions.insert(0, {
                "filepath": filepath,
                "suite": suite,
                "device": device,
                "week": week
            })

            # Keep only the last 10 sessions
            with open("session.json", "w") as f:
                json.dump(sessions[:10], f, indent=4)
            logging.info(f"Session saved for file: {filepath}")
        except Exception as e:
            logging.error(f"Error saving session file: {e}")

    def check_for_previous_session(self):
        """Checks for previous sessions and populates the launcher list."""
        self.launcher_screen.recent_sessions_list.clear()
        if not os.path.exists("session.json"): return

        try:
            with open("session.json", "r") as f:
                sessions = json.load(f)
                for session in sessions:
                    if os.path.exists(session.get("filepath", "")):
                        display_text = f"{session['suite']} - {session['device']} - Week {session['week']}"
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, session) # Store all data in the item
                        self.launcher_screen.recent_sessions_list.addItem(item)
            logging.info("Previous sessions loaded.")
        except Exception as e:
            logging.error(f"Could not read session file: {e}")

    def load_selected_session(self, item):
        """Loads the session selected from the recent sessions list."""
        session_data = item.data(Qt.UserRole)
        filepath = session_data["filepath"]
        suite = session_data["suite"]
        self.active_test_file = filepath
        self.active_build_details = "Loaded from session"
        self.setup_dashboard_with_file(filepath, suite)
        self.show_main_app(panel_index=1)

    def setup_dashboard_with_file(self, filepath, suite):
        """Initializes the dashboard with a specific test file."""
        try:
            self.data_manager = DataManager(filepath)
            self.load_sheet_data(suite)
        except Exception as e:
            QMessageBox.critical(self, "Dashboard Error", f"Could not load dashboard: {e}")
            self.show_launcher()

    def browse_for_directory(self):
        """Opens a dialog to select a directory."""
        directory = QFileDialog.getExistingDirectory(self, "Select Working Directory")
        if directory:
            self.setup_screen.dir_input.setText(directory)

    def start_new_session(self):
        """Validates setup inputs and starts a new test session."""
        work_dir = self.setup_screen.dir_input.text().strip()
        device_name = self.setup_screen.device_input.text().strip()
        week_num = self.setup_screen.week_input.value()
        build_details = self.setup_screen.build_input.text().strip()
        suite = self.setup_screen.suite_combo.currentText()

        if not all([work_dir, device_name, build_details]):
            QMessageBox.warning(self, "Input Error", "Please fill in all fields.")
            return

        if not os.path.isdir(work_dir):
            QMessageBox.warning(self, "Input Error", "The selected working directory does not exist.")
            return

        new_filename = f"{suite}_{device_name}_Week_{week_num:02d}.xlsx"
        self.active_test_file = os.path.join(work_dir, new_filename)
        self.active_build_details = build_details

        if not os.path.exists(self.active_test_file):
            try:
                shutil.copy("template_test_cases.xlsx", self.active_test_file)
            except Exception as e:
                QMessageBox.critical(self, "File Error", f"Could not create test file: {e}")
                return

        self.save_current_session(self.active_test_file, suite, device_name, week_num)
        self.check_for_previous_session() # Refresh launcher list
        self.setup_dashboard_with_file(self.active_test_file, suite)
        self.show_main_app(panel_index=1)
        self.tab_widget.setCurrentIndex(self.tab_widget.count() - 1) # Switch to dashboard tab

    def load_sheet_data(self, sheet_name):
        """Loads data from the selected sheet and updates the UI."""
        if self.data_manager is None: return
        self.current_sheet = sheet_name
        self.current_test_case_index = 0
        self.display_test_case()
        self.update_results_table()

    def display_test_case(self):
        """Displays the current test case details."""
        if not self.data_manager or not self.current_sheet: return

        df = self.data_manager.get_sheet_data(self.current_sheet)
        if df is None or self.current_test_case_index >= len(df): return

        self.confirm_btn.setEnabled(True)
        self.reset_iteration_btn.setEnabled(True)

        row = df.iloc[self.current_test_case_index]
        self.execution_dashboard.test_case_id_label.setText(f"<b>ID:</b> {row.get('Test Case ID', '')}")
        self.execution_dashboard.test_case_name_label.setText(f"<b>Name:</b> {row.get('Test Case Name', '')}")
        self.execution_dashboard.prereq_area.setText(str(row.get('Pre-requisites', '')))
        self.execution_dashboard.test_steps_area.setText(str(row.get('Test Steps', '')))
        self.execution_dashboard.n_points_label.setText(f"<b>N-Points:</b> {row.get('N-Points', '')}")

        self.notes_area.setText(str(row.get('Notes', '')))
        remember_val = str(row.get('Remember', 'False')).upper() == 'TRUE'
        self.remember_checkbox.setChecked(remember_val)

        self.current_iteration = 0
        for i in range(1, 6):
            if pd.to_numeric(row.get(f"Iteration{i}"), errors='coerce') > 0:
                self.current_iteration = i

        self.update_iteration_indicators()
        self.reset_iteration()

        if self.current_iteration >= 5:
            self.confirm_btn.setEnabled(False)
            self.reset_iteration_btn.setEnabled(False)

    def toggle_timer(self):
        """Starts or stops the timer."""
        if self.is_timer_running:
            self.is_timer_running = False
            self.timer.stop()
        else:
            self.time_elapsed.start()
            self.is_timer_running = True
            self.timer.start(11)

    def update_timer_display(self):
        """Updates the timer display label in seconds.milliseconds format."""
        if self.is_timer_running:
            self.timer_display.setText(f"{self.time_elapsed.elapsed() / 1000.0:.3f}")

    def reset_iteration(self):
        """Resets the timer for the current iteration without saving."""
        if self.is_timer_running: self.toggle_timer()
        self.timer_display.setText("0.000")

    def confirm_iteration(self):
        """Confirms the current iteration, saves the time, and moves to the next."""
        if self.is_timer_running: self.toggle_timer()

        if self.current_iteration < 5:
            time_val = float(self.timer_display.text())
            if time_val == 0.0: return

            col_name = f"Iteration{self.current_iteration + 1}"
            self.data_manager.update_cell(self.current_sheet, self.current_test_case_index, col_name, f"{time_val:.3f}")
            self.data_manager.update_cell(self.current_sheet, self.current_test_case_index, "Build Details", self.active_build_details)

            self.current_iteration += 1
            self.update_iteration_indicators()
            self.calculate_average()
            self.data_manager.save_data()
            self.update_results_table()
            self.reset_iteration()

            if self.current_iteration == 5:
                self.confirm_btn.setEnabled(False)
                self.reset_iteration_btn.setEnabled(False)
                QTimer.singleShot(1000, self.next_test_case)

    def next_test_case(self):
        """Navigates to the next test case."""
        df = self.data_manager.get_sheet_data(self.current_sheet)
        if df is not None and self.current_test_case_index < len(df) - 1:
            self.current_test_case_index += 1
            self.display_test_case()

    def prev_test_case(self):
        """Navigates to the previous test case."""
        if self.current_test_case_index > 0:
            self.current_test_case_index -= 1
            self.display_test_case()

    def update_iteration_indicators(self):
        """Updates the visual indicators for iterations."""
        for i in range(5):
            is_done = i < self.current_iteration
            color = "#2E8B57" if is_done else "#d3d3d3"
            self.iteration_indicators[i].setStyleSheet(f"background-color: {color}; border-radius: 10px;")

    def calculate_average(self):
        """Calculates and saves the average of the iterations."""
        df = self.data_manager.get_sheet_data(self.current_sheet)
        row = df.iloc[self.current_test_case_index]

        times = [pd.to_numeric(row.get(f"Iteration{i}"), errors='coerce') for i in range(1, 6)]
        valid_times = [t for t in times if pd.notna(t)]

        if valid_times:
            average = sum(valid_times) / len(valid_times)
            self.data_manager.update_cell(self.current_sheet, self.current_test_case_index, "Average", f"{average:.3f}")

    def update_results_table(self):
        """Updates the results table with data from the current sheet."""
        if not self.data_manager or not self.current_sheet: return
        df = self.data_manager.get_sheet_data(self.current_sheet)
        if df is None: return

        table = self.execution_dashboard.results_table
        table.setColumnCount(len(df.columns))
        table.setHorizontalHeaderLabels(df.columns)
        table.setRowCount(len(df))
        for i, row in df.iterrows():
            for j, col in enumerate(df.columns):
                item = QTableWidgetItem(str(row.get(col, '')))
                table.setItem(i, j, item)

    def save_note(self):
        """Saves the note for the current test case."""
        if not self.data_manager or not self.current_sheet: return
        self.data_manager.update_cell(self.current_sheet, self.current_test_case_index, "Notes", self.notes_area.toPlainText())
        self.data_manager.save_data()

    def save_remember_state(self, state):
        """Saves the state of the 'Remember' checkbox."""
        if not self.data_manager or not self.current_sheet: return
        self.data_manager.update_cell(self.current_sheet, self.current_test_case_index, "Remember", str(state == Qt.Checked).upper())
        self.data_manager.save_data()

    def create_log_analyzer_controls(self):
        """Creates the control panel for the Log Analyzer."""
        panel = QGroupBox("📁 Input & Processing")
        layout = QVBoxLayout()
        header_layout = QHBoxLayout()
        title_label = QLabel("Kindle Log Analyzer")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        self.dark_mode_toggle = QCheckBox("Dark Mode")
        self.dark_mode_toggle.toggled.connect(self.toggle_dark_mode)
        header_layout.addWidget(self.dark_mode_toggle)
        layout.addLayout(header_layout)
        settings_group = QGroupBox("🔧 Configuration")
        settings_layout = QVBoxLayout()
        self.test_case_layout = QHBoxLayout()
        self.test_case_layout.addWidget(QLabel("Test Case:"))
        self.test_case_input = QLineEdit()
        self.test_case_input.setPlaceholderText("e.g., Kindle_Performance_Test")
        self.test_case_layout.addWidget(self.test_case_input)
        settings_layout.addLayout(self.test_case_layout)
        calc_mode_layout = QHBoxLayout()
        calc_mode_layout.addWidget(QLabel("Mode:"))
        self.calc_mode_combo = QComboBox()
        self.calc_mode_combo.addItems(["Default (Button Up)", "Swipe (Button Down)", "Suspend (Power Button)"])
        self.calc_mode_combo.currentIndexChanged.connect(self.on_calculation_mode_changed)
        calc_mode_layout.addWidget(self.calc_mode_combo)
        settings_layout.addLayout(calc_mode_layout)
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Processing:"))
        self.processing_mode = QComboBox()
        self.processing_mode.addItems(["Single Entry", "Batch Files"])
        self.processing_mode.currentTextChanged.connect(self.on_processing_mode_changed)
        mode_layout.addWidget(self.processing_mode)
        settings_layout.addLayout(mode_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        self.single_group = QGroupBox("📝 Single Entry")
        single_layout = QVBoxLayout()
        single_layout.addWidget(QLabel("Log Data:"))
        self.log_input = QTextEdit()
        self.log_input.setPlaceholderText("Paste log data here...")
        self.log_input.setMaximumHeight(120)
        single_layout.addWidget(self.log_input)
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
        self.batch_group = QGroupBox("📂 Batch Processing")
        batch_layout = QVBoxLayout()
        file_btn_layout = QHBoxLayout()
        self.select_files_btn = QPushButton("🗂️ Select Files")
        self.select_files_btn.clicked.connect(self.select_batch_files)
        self.clear_files_btn = QPushButton("🗑️ Clear")
        self.clear_files_btn.clicked.connect(self.clear_batch_files)
        file_btn_layout.addWidget(self.select_files_btn)
        file_btn_layout.addWidget(self.clear_files_btn)
        batch_layout.addLayout(file_btn_layout)
        self.files_list = QListWidget()
        self.files_list.setMaximumHeight(100)
        batch_layout.addWidget(self.files_list)
        self.process_batch_btn = QPushButton("⚡ Process All Files")
        self.process_batch_btn.clicked.connect(self.process_batch_files)
        self.process_batch_btn.setEnabled(False)
        batch_layout.addWidget(self.process_batch_btn)
        self.batch_group.setLayout(batch_layout)
        self.batch_group.setVisible(False)
        layout.addWidget(self.batch_group)
        progress_group = QGroupBox("📊 Status")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        self.status_label = QLabel("Ready")
        progress_layout.addWidget(self.status_label)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)
        export_group = QGroupBox("💾 Export Options")
        export_layout = QVBoxLayout()
        self.export_zip_btn = QPushButton("📦 Export All Reports (ZIP)")
        self.export_zip_btn.clicked.connect(self.export_zip_report)
        self.export_zip_btn.setEnabled(False)
        self.export_zip_btn.setVisible(False)
        export_layout.addWidget(self.export_zip_btn)
        self.export_excel_btn = QPushButton("📊 Export Excel")
        self.export_excel_btn.clicked.connect(self.export_excel_with_highlighting)
        self.export_excel_btn.setEnabled(False)
        self.export_excel_btn.setVisible(False)
        export_layout.addWidget(self.export_excel_btn)
        self.single_export_widget = QWidget()
        single_export_layout = QHBoxLayout(self.single_export_widget)
        single_export_layout.setContentsMargins(0,0,0,0)
        self.export_report_btn = QPushButton("Export Report")
        self.export_report_btn.setEnabled(False)
        self.export_report_btn.clicked.connect(self.export_single_report)
        self.pdf_export_checkbox = QCheckBox("PDF")
        self.pdf_export_checkbox.setChecked(True)
        self.txt_export_checkbox = QCheckBox("TXT")
        self.txt_export_checkbox.setChecked(True)
        single_export_layout.addWidget(self.export_report_btn)
        single_export_layout.addWidget(self.pdf_export_checkbox)
        single_export_layout.addWidget(self.txt_export_checkbox)
        export_layout.addWidget(self.single_export_widget)
        self.clear_all_btn = QPushButton("🗑️ Clear All")
        self.clear_all_btn.clicked.connect(self.clear_all)
        export_layout.addWidget(self.clear_all_btn)
        export_group.setLayout(export_layout)
        layout.addWidget(export_group)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def create_execution_dashboard_controls(self):
        """Creates the control panel for the Execution Dashboard."""
        panel = QGroupBox("🚀 Timer Control & Navigation")
        layout = QVBoxLayout()
        self.timer_display = QLabel("0.000")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setFont(QFont("Courier", 48, QFont.Bold))
        self.timer_display.setStyleSheet("color: #2E8B57;")
        layout.addWidget(self.timer_display)
        controls_layout = QHBoxLayout()
        self.start_stop_btn = QPushButton("Start/Stop (Space)")
        self.reset_iteration_btn = QPushButton("Reset Iteration")
        controls_layout.addWidget(self.start_stop_btn)
        controls_layout.addWidget(self.reset_iteration_btn)
        layout.addLayout(controls_layout)
        iteration_group = QGroupBox("Iterations")
        iteration_layout = QVBoxLayout()
        self.iteration_indicators = []
        indicator_layout = QHBoxLayout()
        for _ in range(5):
            indicator = QFrame()
            indicator.setFrameShape(QFrame.StyledPanel)
            indicator.setFixedSize(20, 20)
            indicator.setStyleSheet("background-color: #d3d3d3; border-radius: 10px;")
            self.iteration_indicators.append(indicator)
            indicator_layout.addWidget(indicator)
        iteration_layout.addLayout(indicator_layout)
        self.confirm_btn = QPushButton("Confirm & Next Iteration (Enter)")
        iteration_layout.addWidget(self.confirm_btn)
        iteration_group.setLayout(iteration_layout)
        layout.addWidget(iteration_group)
        self.remember_checkbox = QCheckBox("Remember for follow-up")
        layout.addWidget(self.remember_checkbox)
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("<< Previous (Left)")
        self.next_btn = QPushButton("Next >> (Right)")
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)
        layout.addWidget(QLabel("Notes:"))
        self.notes_area = QTextEdit()
        self.notes_area.setPlaceholderText("Add notes for the current test case...")
        layout.addWidget(self.notes_area)
        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def create_right_panel(self):
        """Enhanced right panel with waveform boxes and better visualization"""
        panel = QWidget()
        layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.create_summary_tab()
        self.create_detailed_results_tab()
        self.create_waveform_boxes_tab()
        self.create_heights_waveforms_tab()
        self.create_batch_results_tab()
        self.create_comparison_tab()
        self.execution_dashboard = ExecutionDashboard()
        self.tab_widget.addTab(self.execution_dashboard, "🚀 Execution Dashboard")
        layout.addWidget(self.tab_widget)
        panel.setLayout(layout)
        return panel

    def on_tab_changed(self, index):
        """Switches the left panel controls based on the selected tab."""
        if self.tab_widget.tabText(index) == "🚀 Execution Dashboard":
            self.left_panel_stack.setCurrentIndex(1)
        else:
            self.left_panel_stack.setCurrentIndex(0)

    def create_summary_tab(self):
        self.summary_tab = QWidget()
        layout = QVBoxLayout(self.summary_tab)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        layout.addWidget(self.summary_text)
        self.tab_widget.addTab(self.summary_tab, "📊 Summary")

    def create_detailed_results_tab(self):
        self.results_tab = QWidget()
        layout = QVBoxLayout(self.results_tab)
        layout.addWidget(QLabel("📋 Main Results (Copy-friendly for Excel)"))
        self.results_table = QTableWidget()
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.results_table)
        self.tab_widget.addTab(self.results_tab, "📋 Main Results")

    def create_waveform_boxes_tab(self):
        self.waveform_boxes_tab = QWidget()
        layout = QVBoxLayout(self.waveform_boxes_tab)
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("📦 Waveform Boxes - Table Layout"))
        top_layout.addStretch()
        self.copy_all_waveforms_btn = QPushButton("📋 Copy All Waveforms")
        self.copy_all_waveforms_btn.clicked.connect(self.copy_all_waveforms_data)
        self.copy_all_waveforms_btn.setMaximumWidth(200)
        top_layout.addWidget(self.copy_all_waveforms_btn)
        layout.addLayout(top_layout)
        self.waveform_table = QTableWidget()
        self.waveform_table.setAlternatingRowColors(True)
        self.waveform_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.waveform_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.waveform_table)
        self.tab_widget.addTab(self.waveform_boxes_tab, "📦 Waveform Boxes")

    def create_heights_waveforms_tab(self):
        self.heights_tab = QWidget()
        layout = QVBoxLayout(self.heights_tab)
        layout.addWidget(QLabel("📏 All Heights & Waveforms Details"))
        self.heights_table = QTableWidget()
        self.heights_table.setAlternatingRowColors(True)
        self.heights_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.heights_table)
        self.tab_widget.addTab(self.heights_tab, "📏 Heights & Waveforms")

    def create_batch_results_tab(self):
        self.batch_tab = QWidget()
        layout = QVBoxLayout(self.batch_tab)
        self.batch_results_text = QTextEdit()
        self.batch_results_text.setReadOnly(True)
        layout.addWidget(self.batch_results_text)
        self.tab_widget.addTab(self.batch_tab, "📁 Batch Results")

    def create_comparison_tab(self):
        self.comparison_tab = QWidget()
        main_layout = QVBoxLayout(self.comparison_tab)
        input_splitter = QSplitter(Qt.Horizontal)
        log_a_group = QGroupBox("Log A (e.g., Previous Version)")
        log_a_layout = QVBoxLayout(log_a_group)
        self.log_a_input = QTextEdit()
        self.log_a_input.setPlaceholderText("Paste log for iteration A here...")
        log_a_layout.addWidget(self.log_a_input)
        input_splitter.addWidget(log_a_group)
        log_b_group = QGroupBox("Log B (e.g., Current Version)")
        log_b_layout = QVBoxLayout(log_b_group)
        self.log_b_input = QTextEdit()
        self.log_b_input.setPlaceholderText("Paste log for iteration B here...")
        log_b_layout.addWidget(self.log_b_input)
        input_splitter.addWidget(log_b_group)
        main_layout.addWidget(input_splitter)
        results_group = QGroupBox("Comparison")
        results_layout = QVBoxLayout(results_group)
        controls_layout = QHBoxLayout()
        self.compare_btn = QPushButton("⚖️ Compare Logs")
        self.compare_btn.clicked.connect(self.compare_logs)
        self.clear_comparison_btn = QPushButton("🗑️ Clear")
        self.clear_comparison_btn.clicked.connect(self.clear_comparison_fields)
        controls_layout.addWidget(self.compare_btn)
        controls_layout.addWidget(self.clear_comparison_btn)
        results_layout.addLayout(controls_layout)
        self.comparison_results_text = QTextEdit()
        self.comparison_results_text.setReadOnly(True)
        results_layout.addWidget(self.comparison_results_text)
        main_layout.addWidget(results_group)
        self.tab_widget.addTab(self.comparison_tab, "⚖️ Comparison")

    def compare_logs(self):
        # ... (rest of the original methods)
        pass

    def setup_styling(self):
        if self.state.dark_mode:
            with open('ui/dark_mode.qss', 'r') as f:
                self.setStyleSheet(f.read())
        else:
            with open('ui/light_mode.qss', 'r') as f:
                self.setStyleSheet(f.read())

    # ... (Keep all other original methods like on_calculation_mode_changed, export_single_report, etc.)
    # Dummy methods for brevity
    def on_calculation_mode_changed(self): pass
    def on_processing_mode_changed(self, mode): pass
    def export_single_report(self): pass
    def add_iteration(self): pass
    def process_all_iterations(self): pass
    def on_single_processing_complete(self, data): pass
    def on_batch_processing_complete(self, data, filename): pass
    def on_processing_error(self, error): pass
    def update_all_displays(self): pass
    def update_summary_display(self, results_to_display=None): pass
    def generate_summary_for_file(self, filename, results): pass
    def update_results_table(self, results_to_display=None): pass
    def populate_results_table(self, results): pass
    def update_heights_table(self, results_to_display=None): pass
    def populate_heights_table(self, results): pass
    def update_batch_display(self): pass
    def export_zip_report(self): pass
    def export_excel_with_highlighting(self): pass
    def select_batch_files(self): pass
    def clear_batch_files(self): pass
    def process_batch_files(self): pass
    def enable_export_buttons(self): pass
    def save_session(self): pass
    def load_session(self): pass
    def clear_all(self): pass
    def clear_comparison_fields(self): pass
    def process_single_log_iteration(self, log_content): pass
    def create_iteration_waveform_box(self, result): pass
    def copy_iteration_data(self, result): pass
    def copy_all_waveforms_data(self): pass
    def copy_file_waveforms_data(self, results): pass
    def _copy_waveform_data_to_clipboard(self, results_to_copy): pass
    def update_waveform_boxes(self, results_to_display=None): pass
    def populate_waveform_boxes_table(self, results): pass
    def toggle_dark_mode(self, checked): pass
    def generate_comparison_html(self, result_a, result_b): pass

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FinalKindleLogAnalyzer()
    window.show()
    sys.exit(app.exec_())