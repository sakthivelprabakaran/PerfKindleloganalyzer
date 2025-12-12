import time
import pandas as pd
import threading

# Note: All necessary PyQt5 widgets are imported below.
# The code review may have been based on an older version of this file.
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTabWidget, QSplitter,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame, QLineEdit, QComboBox, QCompleter, QScrollArea,
    QStatusBar, QGridLayout, QCheckBox, QListWidget, QListWidgetItem, QInputDialog
)
from PyQt5.QtGui import QPainter, QFont, QColor, QBrush
from PyQt5.QtCore import Qt, QTimer, QTime, QStringListModel, QSize

class CircleIndicator(QWidget):
    """A simple circular widget to indicate progress."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(20, 20)
        self.active = False

    def set_active(self, active):
        self.active = active
        self.update() # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        if self.active:
            painter.setBrush(Qt.green)
        else:
            painter.setBrush(Qt.gray)
        painter.drawEllipse(0, 0, 18, 18)


class DynamicHeightTextEdit(QTextEdit):
    """
    A QTextEdit that automatically adjusts its height to fit its content,
    providing a stable size hint for layout management.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)
        # Use textChanged signal for more reliable updates
        self.textChanged.connect(self.update_geometry)

    def sizeHint(self):
        """Provide a dynamic size hint based on the document's height."""
        doc_height = self.document().size().height()
        margin = self.contentsMargins().top() + self.contentsMargins().bottom()
        return QSize(super().sizeHint().width(), int(doc_height + margin))

    def update_geometry(self):
        """Inform the layout that the size hint has changed."""
        # This will trigger a layout recalculation that respects the new sizeHint
        self.updateGeometry()

    def setText(self, text):
        """Override setText to ensure the geometry is updated after content is set."""
        super().setText(text)
        # The textChanged signal will fire, which calls self.update_geometry


from performance_dashboard.logic.network_manager import NetworkManager

class ExecutionDashboard(QWidget):
    """
    The main dashboard for test case execution, timing, and data entry.
    """
    def __init__(self, state_manager, data_manager, return_to_launcher_callback, switch_session_callback=None, user_context=None):
        super().__init__()
        self.state = state_manager
        self.data_manager = data_manager
        self.return_to_launcher = return_to_launcher_callback
        self.switch_session_callback = switch_session_callback
        self.user_context = user_context

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer_display)
        self.start_time = 0
        self.recorded_time = 0
        self.current_iteration = 1
        self.iteration_times = []
        
        # Network Manager for Live Audit - created lazily
        self.network_manager = None
        self.live_mode = False
        
        # Baseline tracking
        self.baseline_mode = False
        self.baseline_iterations = []
        self.baseline_build = ""
        self.current_test_case = None
        self.total_test_cases = 0
        self.total_n_points = 0

        self.filtered_indices = []  # To store the original indices of filtered test cases
        self.current_filtered_index = 0 # To track position within the filtered list

        self.init_ui()
        
        # Update UI based on the current session
        self.load_test_case_data()
        
        # Initialize Live Mode since checkbox is checked by default
        # This must be done AFTER init_ui so submit_all_btn exists
        self.live_chk.setChecked(True) 
        # self.toggle_live_mode(2) # Triggered automatically by setChecked

    def init_ui(self):
        """Initializes the UI layout and widgets."""
        main_layout = QVBoxLayout(self)

        # Main splitter for the two panels
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter, 1)

        # Left panel
        left_panel = self.create_left_panel()

        # Right panel
        right_panel = self.create_right_panel()

        main_splitter.addWidget(left_panel)
        main_splitter.addWidget(right_panel)
        main_splitter.setSizes([400, 1200])

        # Status Bar
        self.status_bar = QStatusBar()
        main_layout.addWidget(self.status_bar)

    def create_left_panel(self):
        """Creates the left panel for timer controls and navigation, wrapped in a scroll area."""
        # This is the main widget that will contain all the controls.
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # Session Info
        session_group = QGroupBox("📊 Session Info")
        session_layout = QGridLayout(session_group) # Use Grid Layout for compactness
        
        # Session Selector (Quick Switch)
        self.session_selector = QComboBox()
        self.session_selector.currentIndexChanged.connect(self.on_session_changed)
        
        self.device_name_label = QLabel("<b>Device:</b> N/A")
        self.week_label = QLabel("<b>Week:</b> N/A")
        self.build_label = QLabel("<b>Build:</b> N/A")
        
        # Build Input
        build_layout = QHBoxLayout()
        self.current_build_input = QLineEdit()
        self.current_build_input.setPlaceholderText("Set current build...")
        set_build_btn = QPushButton("Set")
        set_build_btn.clicked.connect(self.set_current_build)
        build_layout.addWidget(self.current_build_input)
        build_layout.addWidget(set_build_btn)
        
        self.total_n_points_label = QLabel("<b>Total N-Points: 0</b>")

        # Live Mode Toggle
        live_layout = QHBoxLayout()
        self.live_chk = QCheckBox("Live Audit Mode")
        # self.live_chk.setChecked(True)  # MOVED: Set in __init__ after UI is fully built
        self.live_chk.stateChanged.connect(self.toggle_live_mode)
        self.server_ip_input = QLineEdit("http://127.0.0.1:8000")
        self.server_ip_input.setPlaceholderText("Server URL")
        self.server_ip_input.setEnabled(False)
        
        # Connection status indicator
        self.connection_indicator = QLabel("⚫ Not Connected")
        self.connection_indicator.setStyleSheet("color: gray; font-weight: bold;")
        
        live_layout.addWidget(self.live_chk)
        live_layout.addWidget(self.connection_indicator)
        live_layout.addWidget(self.server_ip_input)

        # Add widgets to grid
        session_layout.addWidget(self.session_selector, 0, 0, 1, 2) # Span 2 columns
        session_layout.addWidget(self.device_name_label, 1, 0)
        session_layout.addWidget(self.week_label, 1, 1)
        session_layout.addWidget(self.build_label, 2, 0)
        session_layout.addLayout(build_layout, 2, 1)
        session_layout.addWidget(self.total_n_points_label, 3, 0, 1, 2)
        session_layout.addLayout(live_layout, 4, 0, 1, 2)
        
        layout.addWidget(session_group)
        
        # Action buttons row
        action_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Save")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self.save_session)
        action_layout.addWidget(save_btn)

        save_return_btn = QPushButton("💾 Save & Return")
        save_return_btn.setFixedHeight(40)
        save_return_btn.clicked.connect(self.save_and_return)
        action_layout.addWidget(save_return_btn)
        
        # Submit All Completed button
        self.submit_all_btn = QPushButton("📤 Submit All")
        self.submit_all_btn.setFixedHeight(40)
        self.submit_all_btn.setToolTip("Submit all completed test cases to auditor")
        self.submit_all_btn.clicked.connect(self.submit_all_completed)
        self.submit_all_btn.setEnabled(False)  # Disabled until Live Mode is on
        action_layout.addWidget(self.submit_all_btn)
        
        action_layout.addStretch() # Pushes buttons to the left
        layout.addLayout(action_layout)

        # Timer
        timer_group = QGroupBox("⏱️ Timer")
        timer_layout = QVBoxLayout(timer_group)
        self.timer_display = QLabel("00:00.000")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setFont(QFont("Arial", 50, QFont.Bold))
        self.timer_display.setObjectName("timerDisplay")
        self.start_stop_btn = QPushButton("Start (Space)")
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        timer_layout.addWidget(self.timer_display)
        timer_layout.addWidget(self.start_stop_btn)
        layout.addWidget(timer_group)
        

        
        # Baseline Activity
        self.baseline_group = QGroupBox("🎯 Baseline Activity")
        baseline_layout = QVBoxLayout(self.baseline_group)
        
        self.baseline_mode_checkbox = QCheckBox("Enable Baseline Mode")
        self.baseline_mode_checkbox.stateChanged.connect(self.toggle_baseline_mode)
        self.baseline_mode_checkbox.setEnabled(False)
        self.baseline_mode_checkbox.setVisible(False) # Hidden by default, auto-triggered
        
        baseline_build_layout = QHBoxLayout()
        baseline_build_layout.addWidget(QLabel("Baseline Build:"))
        self.baseline_build_input = QLineEdit()
        self.baseline_build_input.setPlaceholderText("Enter baseline build...")
        self.baseline_build_input.setEnabled(False)
        baseline_build_layout.addWidget(self.baseline_build_input)
        
        baseline_layout.addWidget(self.baseline_mode_checkbox)
        baseline_layout.addLayout(baseline_build_layout)
        layout.addWidget(self.baseline_group)
        self.baseline_group.setVisible(False) # Hidden by default

        # Iteration Management
        iteration_group = QGroupBox("🔄 Iteration Management")
        iteration_layout = QVBoxLayout(iteration_group)
        self.iteration_indicators_layout = QHBoxLayout()
        
        self.iteration_label = QLabel("Iteration: 1/5")
        self.iteration_label.setAlignment(Qt.AlignCenter)
        iteration_layout.addWidget(self.iteration_label)
        
        self.iteration_indicators = []
        for _ in range(5):
            indicator = CircleIndicator()
            self.iteration_indicators.append(indicator)
            self.iteration_indicators_layout.addWidget(indicator)
        self.confirm_iteration_btn = QPushButton("Confirm & Next Iteration (Enter)")
        self.confirm_iteration_btn.setEnabled(False)
        self.confirm_iteration_btn.clicked.connect(self.confirm_iteration)
        iteration_layout.addLayout(self.iteration_indicators_layout)
        iteration_layout.addWidget(self.confirm_iteration_btn)

        self.retest_btn = QPushButton("Retest")
        self.retest_btn.clicked.connect(self.retest_current_case)
        iteration_layout.addWidget(self.retest_btn)

        # Block Button
        self.block_btn = QPushButton("🚫 Block Test Case")
        self.block_btn.clicked.connect(self.block_test_case)
        self.block_btn.setStyleSheet("background-color: #ffcccc; color: #cc0000;")
        iteration_layout.addWidget(self.block_btn)

        layout.addWidget(iteration_group)

        # Navigation Controls
        nav_group = QGroupBox("Navigate")
        nav_layout = QVBoxLayout(nav_group)
        nav_buttons_layout = QHBoxLayout()
        prev_btn = QPushButton("Previous")
        prev_btn.setMinimumWidth(120)
        prev_btn.clicked.connect(self.navigate_previous)
        next_btn = QPushButton("Next")
        next_btn.setMinimumWidth(120)
        next_btn.clicked.connect(self.navigate_next)
        nav_buttons_layout.addWidget(prev_btn)
        nav_buttons_layout.addWidget(next_btn)
        self.test_case_progress_label = QLabel("Test Case: 1 / 1")
        self.test_case_progress_label.setAlignment(Qt.AlignCenter)
        nav_layout.addLayout(nav_buttons_layout)
        nav_layout.addWidget(self.test_case_progress_label)
        layout.addWidget(nav_group)

        # Advanced Navigation
        adv_nav_group = QGroupBox("🔎 Advanced Navigation")
        adv_nav_layout = QVBoxLayout(adv_nav_group)
        adv_nav_layout.addWidget(QLabel("Filter by Component:"))
        self.area_filter_combo = QComboBox()
        self.area_filter_combo.addItem("All Components")
        adv_nav_layout.addWidget(self.area_filter_combo)
        adv_nav_layout.addWidget(QLabel("Search by Test Case Name/ID:"))
        self.search_combo = QComboBox()
        self.search_combo.setEditable(True)
        self.search_combo.setInsertPolicy(QComboBox.NoInsert)
        self.search_combo.setPlaceholderText("Type to search...")
        adv_nav_layout.addWidget(self.search_combo)
        jump_layout = QHBoxLayout()
        self.jump_to_input = QLineEdit()
        self.jump_to_input.setPlaceholderText("Go to #")
        jump_btn = QPushButton("Jump")
        jump_btn.setObjectName("jump_btn")
        jump_layout.addWidget(self.jump_to_input)
        jump_layout.addWidget(jump_btn)
        adv_nav_layout.addLayout(jump_layout)
        layout.addWidget(adv_nav_group)

        # Notes Section
        notes_group = QGroupBox("📝 Notes")
        notes_layout = QVBoxLayout(notes_group)
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Enter notes for the current test case...")
        notes_layout.addWidget(self.notes_input)
        layout.addWidget(notes_group)

        layout.addStretch()

        # Create and configure the scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content_widget)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        return scroll_area

    def create_right_panel(self):
        """Creates the right panel for test case details and results."""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)

        # Tab 1: Test Case Details
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)

        # Main Info Box
        info_box = QGroupBox("Test Case Information")
        info_layout = QVBoxLayout(info_box)

        # Top line: ID and N-Points
        top_line_layout = QHBoxLayout()
        top_line_layout.addWidget(QLabel("<b>Test Case ID:</b>"))
        self.tc_id_label = QLabel("N/A")
        top_line_layout.addWidget(self.tc_id_label)
        top_line_layout.addStretch()
        top_line_layout.addWidget(QLabel("<b>N-Points:</b>"))
        self.n_points_label = QLabel("0")
        self.n_points_label.setFont(QFont("Arial", 10, QFont.Bold))
        top_line_layout.addWidget(self.n_points_label)
        info_layout.addLayout(top_line_layout)

        info_layout.addWidget(QLabel("<b>Test Case Name:</b>"))
        self.tc_name_label = QLabel("N/A")
        self.tc_name_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_layout.addWidget(self.tc_name_label)

        details_layout.addWidget(info_box)

        # Pre-requisites Box
        prereq_box = QGroupBox("Pre-requisites")
        prereq_layout = QVBoxLayout(prereq_box)
        self.tc_prereq_text = DynamicHeightTextEdit()
        prereq_layout.addWidget(self.tc_prereq_text)
        details_layout.addWidget(prereq_box)

        # Test Steps Box
        steps_box = QGroupBox("Test Steps")
        steps_layout = QVBoxLayout(steps_box)
        self.tc_steps_text = DynamicHeightTextEdit()
        steps_layout.addWidget(self.tc_steps_text)
        details_layout.addWidget(steps_box)

        details_layout.addStretch()

        # Current Iteration Results
        results_group = QGroupBox("Current Iteration Results")
        results_layout = QVBoxLayout(results_group)
        self.current_results_table = QTableWidget()
        self.current_results_table.setRowCount(1)
        self.current_results_table.setColumnCount(6)
        self.current_results_table.setHorizontalHeaderLabels(["IT1", "IT2", "IT3", "IT4", "IT5", "Average"])
        self.current_results_table.setVerticalHeaderLabels(["Time"])
        self.current_results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.current_results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.current_results_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.current_results_table.setMaximumHeight(80)
        results_layout.addWidget(self.current_results_table)
        details_layout.addWidget(results_group)

        self.tabs.addTab(details_tab, "📋 Test Case Details")

        # Tab 2: Results
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)

        self.results_table = QTableWidget()
        self.results_table.setEditTriggers(QTableWidget.DoubleClicked)
        self.results_table.itemChanged.connect(self.manual_result_edit)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.results_table)

        self.tabs.addTab(results_tab, "📈 Results")

        # Tab 3: Notifications (NEW)
        notifications_tab = QWidget()
        notifications_layout = QVBoxLayout(notifications_tab)
        
        self.notification_list = QListWidget()
        self.notification_list.setAlternatingRowColors(True)
        notifications_layout.addWidget(self.notification_list)
        
        # Clear button
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.notification_list.clear)
        notifications_layout.addWidget(clear_btn)
        
        self.tabs.addTab(notifications_tab, "🔔 Notifications")

        return panel

    def load_session_data(self):
        """Loads data for the current session into the dashboard."""
        if not self.state.current_session:
            return

        session_data = self.state.current_session
        session_name = session_data.get('file_name', 'N/A')
        active_sheet = self.state.get_active_sheet()

        # Populate Session Selector
        self.session_selector.blockSignals(True)
        self.session_selector.clear()
        self.state.load_sessions() # Refresh session list
        
        # Filter sessions by current user
        current_username = self.user_context.get('username', '') if self.user_context else ''
        user_sessions = [s for s in self.state.sessions if s.get('username', '') == current_username]
        
        current_index = 0
        for i, session in enumerate(user_sessions):
            display_text = f"{session.get('file_name')} ({session.get('priority')})"
            self.session_selector.addItem(display_text, session.get('file_name'))
            if session.get('file_name') == session_name:
                current_index = i
        
        self.session_selector.setCurrentIndex(current_index)
        self.session_selector.blockSignals(False)

        self.device_name_label.setText(f"<b>Device:</b> {session_data.get('device_name', 'N/A')}")
        self.week_label.setText(f"<b>Week:</b> {session_data.get('week', 'N/A')}")
        self.build_label.setText(f"<b>Build:</b> {session_data.get('build_details', 'N/A')}")

        self.total_test_cases = self.data_manager.get_test_case_count(active_sheet)
        self.update_total_n_points() # Calculate initial N-Points

        # Populate advanced navigation widgets
        self.populate_advanced_nav(active_sheet)

        # Connect signals
        jump_btn = self.findChild(QPushButton, "jump_btn") # Find the button to connect it
        if jump_btn:
            jump_btn.clicked.connect(self.jump_to_test_case)
        self.area_filter_combo.currentIndexChanged.connect(self.filter_by_area)
        self.search_combo.activated.connect(self.search_test_case)

        # Initial load - Resume from last saved index
        last_index = self.state.get_current_test_case_index()
        self.apply_filters(selected_index=last_index)
        self.update_results_tab()
        
        # Check for incomplete test cases
        self.check_incomplete_test_cases(active_sheet)

        # Auto-enable Live Mode if task assignment exists (NEW)
        if 'task_assignment' in session_data and session_data['task_assignment']:
            task = session_data['task_assignment']
            server_url = session_data.get('server_url', 'http://127.0.0.1:8000')
            
            # Set server URL
            self.server_ip_input.setText(server_url)
            
            # Create network manager if not exists
            if not self.network_manager:
                executor_name = session_data.get('username', 'Executor')
                token = self.user_context.get('token') if hasattr(self, 'user_context') and self.user_context else None
                self.network_manager = NetworkManager(executor_name=executor_name, token=token)
                self.network_manager.notification_received.connect(self.show_audit_notification)
            
            # Set executor name
            if session_data.get('username'):
                self.network_manager.executor_name = session_data['username']
            
            # Enable Live Mode
            self.live_chk.setChecked(True)  # This will trigger toggle_live_mode
            
            # Show confirmation message
            QMessageBox.information(
                self,
                "Live Mode Auto-Enabled",
                f"Live Audit Mode has been automatically enabled.\n\n"
                f"Task: {task['project']} {task['suite']}\n"
                f"Auditor: {task['auditor_username']}\n"
                f"Server: {server_url}\n\n"
                f"Your test results will be sent to {task['auditor_username']} in real-time."
            )

    def load_test_case_by_index(self, index):
        """Loads a specific test case into the UI, saving previous notes first."""
        # Auto-save notes from the previous test case before loading the new one.
        if self.current_test_case is not None:
            self.save_notes()

        active_sheet = self.state.get_active_sheet()
        self.current_test_case = self.data_manager.get_test_case(active_sheet, index)

        if self.current_test_case is not None:
            self.state.update_current_session('current_test_case_index', index)
            
            # Check if baseline is required for this test case
            self.baseline_required = str(self.current_test_case.get('Baseline', '')).strip().lower() == 'yes'
            
            # Reset baseline UI state
            self.baseline_group.setVisible(False)
            self.baseline_mode_checkbox.setChecked(False)
            self.baseline_mode_checkbox.setEnabled(False)
            
            # Reset baseline data to prevent leakage to other test cases
            self.baseline_iterations = []
            self.baseline_build = ""

            self.tc_id_label.setText(str(self.current_test_case.get("Test Case ID", "")))
            self.tc_name_label.setText(str(self.current_test_case.get("Test Case Name", "")))
            self.n_points_label.setText(str(self.current_test_case.get("N-Points", 0)))
            self.tc_prereq_text.setText(str(self.current_test_case.get("Pre-requisites", "")))
            self.tc_steps_text.setText(str(self.current_test_case.get("Test Steps", "")))
            self.notes_input.setText(str(self.current_test_case.get("Notes", "")))

            self.test_case_progress_label.setText(f"Test Case: {index + 1} / {self.total_test_cases}")
            self.update_current_results_display()
            self.reset_timer_and_iterations()
        else:
            QMessageBox.information(self, "End of List", "You have reached the end of the test cases for this sheet.")
    
    def toggle_baseline_mode(self, state):
        """Toggles baseline mode on/off."""
        self.baseline_mode = (state == 2)  # Qt.Checked = 2
        self.baseline_build_input.setEnabled(self.baseline_mode)
        
        if self.baseline_mode:
            self.baseline_iterations = []
            self.baseline_build = ""
            self.iteration_label.setText("Baseline Iteration: 1/5")
            self.baseline_group.setVisible(True)
        else:
            self.iteration_label.setText(f"Iteration: {self.current_iteration}/5")
            self.baseline_group.setVisible(False)
            self.iteration_label.setText(f"Iteration: {self.current_iteration}/5")
            self.baseline_group.setVisible(False)

    def load_test_case_data(self):
        """Loads the test case data for the current index."""
        current_index = self.state.get_current_test_case_index()
        self.load_test_case_by_index(current_index)

    def navigate_next(self):
        current_index = self.state.get_current_test_case_index()
        if current_index + 1 < self.total_test_cases:
            # self.save_notes() is called inside load_test_case_by_index
            self.load_test_case_by_index(current_index + 1)

    def navigate_previous(self):
        current_index = self.state.get_current_test_case_index()
        if current_index > 0:
            # self.save_notes() is called inside load_test_case_by_index
            self.load_test_case_by_index(current_index - 1)

    def format_and_display_time(self, elapsed):
        """Formats the elapsed time and updates the display."""
        minutes, seconds = divmod(elapsed, 60)
        self.timer_display.setText(f"{int(minutes):02d}:{int(seconds):02d}.{int((seconds % 1) * 1000):03d}")

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.recorded_time = time.perf_counter() - self.start_time
            self.format_and_display_time(self.recorded_time) # Update display immediately with exact time
            self.start_stop_btn.setText("Start (Space)")
            self.confirm_iteration_btn.setEnabled(True)
            self.timer_display.setStyleSheet("color: black;") # Reset color
        else:
            self.start_time = time.perf_counter()
            self.timer.start(10) # Update display every 10ms
            self.start_stop_btn.setText("Stop (Space)")
            self.confirm_iteration_btn.setEnabled(False)
            self.timer_display.setStyleSheet("color: green;") # Visual feedback

    def update_timer_display(self):
        elapsed = time.perf_counter() - self.start_time
        self.format_and_display_time(elapsed)

    def confirm_iteration(self):
        """Saves the current time and moves to the next iteration."""
        if self.baseline_mode:
            # Baseline mode logic
            if not self.baseline_build:
                self.baseline_build = self.baseline_build_input.text().strip()
                if not self.baseline_build:
                    QMessageBox.warning(self, "Baseline Build Required", "Please enter a Baseline Build name.")
                    return

            self.baseline_iterations.append(float(f"{self.recorded_time:.3f}"))
            current_baseline_iter = len(self.baseline_iterations)

            if current_baseline_iter < 5:
                self.iteration_label.setText(f"Baseline Iteration: {current_baseline_iter + 1}/5")
                self.reset_timer_and_iterations()
            else:
                # All 5 baseline iterations recorded - calculate average
                avg = sum(self.baseline_iterations) / 5
                baseline_data = {
                    'iterations': self.baseline_iterations,
                    'average': f"{avg:.3f}",
                    'build': self.baseline_build
                }
                self.data_manager.save_baseline_results(
                    self.state.get_active_sheet(),
                    self.state.get_current_test_case_index(),
                    baseline_data
                )
                QMessageBox.information(self, "Baseline Complete", "All 5 baseline iterations recorded. You can now proceed with current build iterations.")
                self.baseline_mode_checkbox.setChecked(False)  # Exit baseline mode
                self.reset_timer_and_iterations()
                self.update_results_tab()
                
                # Check if normal iterations are also complete, if so, submit result
                # We need to check if we have 5 normal iterations saved
                # Since we are in baseline mode, self.current_iteration might be reset, so we check the data
                
                # Get current test case data again to be sure
                active_sheet = self.state.get_active_sheet()
                current_index = self.state.get_current_test_case_index()
                tc_data = self.data_manager.get_test_case(active_sheet, current_index)
                
                normal_iterations_count = 0
                if tc_data is not None and not tc_data.empty:
                    for i in range(1, 6):
                        val = tc_data.get(f"Iteration{i}", "")
                        if pd.notna(val) and str(val).strip() != "":
                            normal_iterations_count += 1
                
                if normal_iterations_count == 5 and self.live_mode:
                    # Trigger submission logic (duplicate of logic below, but needed here)
                    tc_id = tc_data.get("Test Case ID", "")
                    tc_name = tc_data.get("Test Case Name", "")
                    
                    # Calculate average of normal iterations
                    iteration_values = []
                    for i in range(1, 6):
                        try:
                            val = float(tc_data.get(f"Iteration{i}", 0))
                            iteration_values.append(val)
                        except:
                            pass
                            
                    if iteration_values:
                        average_value = sum(iteration_values) / len(iteration_values)
                        suite_name = self.state.get_active_sheet()
                        project_name = self.state.current_session.get('project', 'KindleLogAnalyzer') if self.state.current_session else 'KindleLogAnalyzer'
                        notes = self.notes_input.toPlainText().strip()
                        
                        # Use the just-calculated baseline data
                        baseline_str = f"Build: {self.baseline_build}, Iterations: {self.baseline_iterations}, Avg: {avg:.3f}"
                        
                        try:
                            self.network_manager.submit_result(
                                tc_id, tc_name, f"{average_value:.3f}", 
                                suite_name=suite_name, project_name=project_name,
                                notes=notes, baseline=baseline_str
                            )
                        except Exception as e:
                            print(f"Error submitting result from baseline completion: {e}")
            return


        if self.current_iteration > 5:
            # This part remains as a safeguard, but the main notification is moved.
            QMessageBox.information(self, "Completed", "All iterations for this test case are complete.")
            return

        # Format the recorded time to 3 decimal places for consistency
        formatted_time = float(f"{self.recorded_time:.3f}")

        # Get the current build info from the state
        current_build = self.state.current_session.get('current_build', '')

        updated_test_case = self.data_manager.save_iteration_time(
            self.state.get_active_sheet(),
            self.state.get_current_test_case_index(),
            self.current_iteration,
            formatted_time,
            current_build
        )

        if updated_test_case is not None:
            self.current_test_case = updated_test_case

        # Check if all iterations are now complete to update N-Points
        was_final_iteration = (self.current_iteration == 5)

        self.determine_next_iteration() # This will now set current_iteration to 6 if complete

        if was_final_iteration:
            self.update_total_n_points()
            self.update_results_tab() # Ensure table is updated with the completed test case
            self.update_current_results_display()  # Update the Current Iteration Results table

            # Check for Baseline Requirement
            if self.baseline_required:
                QMessageBox.information(self, "Baseline Required", "Baseline execution is required for this test case. Switching to Baseline Mode.")
                self.baseline_group.setVisible(True)
                self.baseline_mode_checkbox.setEnabled(True)
                self.baseline_mode_checkbox.setChecked(True) # Triggers toggle_baseline_mode
                self.reset_timer_and_iterations()
                return

            # Auto-navigate after completion
            self.reset_timer_and_iterations()
            QMessageBox.information(self, "Completed", "All 5 iterations for this test case are complete. Navigating to the next test case.")
            
            # Log productivity (N-points) for ALL completed test cases
            # This happens BEFORE Live Audit submission to ensure it always runs
            if self.current_test_case is not None and self.network_manager:
                try:
                    tc_id = self.current_test_case.get("Test Case ID", "")
                    tc_name = self.current_test_case.get("Test Case Name", "")
                    suite_name = self.state.get_active_sheet()
                    project_name = self.state.current_session.get('project', 'Unknown') if self.state.current_session else 'Unknown'
                    executor_username = self.user_context.get('username', 'unknown') if self.user_context else 'unknown'
                    session_file_name = self.state.current_session.get('file_name', 'unknown') if self.state.current_session else 'unknown'
                    n_points = int(self.current_test_case.get("N-Points", 0))
                    
                    print(f"📊 Logging productivity: {executor_username} - {tc_id} - {n_points} points (Suite: {suite_name})")
                    
                    success, response = self.network_manager.log_productivity(
                        executor_username=executor_username,
                        session_file_name=session_file_name,
                        test_case_id=tc_id,
                        test_case_name=tc_name,
                        project_name=project_name,
                        suite_name=suite_name,
                        n_points=n_points
                    )
                    
                    if success:
                        print(f"✅ Productivity logged: {n_points} points for {tc_id}")
                    else:
                        print(f"❌ Failed to log productivity: {response}")
                except Exception as e:
                    print(f"❌ Error logging productivity: {e}")
            
            # Live Audit Submission - ONLY submit average after all 5 iterations
            if self.live_mode and self.current_test_case is not None:
                tc_id = self.current_test_case.get("Test Case ID", "")
                tc_name = self.current_test_case.get("Test Case Name", "")
                
                # Calculate average of all 5 iterations
                iteration_values = []
                for i in range(1, 6):
                    val = self.current_test_case.get(f"Iteration{i}", None)  # No space!
                    if val is not None and val != "":
                        try:
                            iteration_values.append(float(val))
                        except:
                            pass
                
                if iteration_values:
                    average_value = sum(iteration_values) / len(iteration_values)
                    suite_name = self.state.get_active_sheet()  # Get the current suite (P0, P1, P2, etc.)
                    project_name = self.state.current_session.get('project', 'KindleLogAnalyzer') if self.state.current_session else 'KindleLogAnalyzer'
                    
                    # Get notes and baseline from UI
                    notes = self.notes_input.toPlainText().strip()
                    baseline_data = ""
                    if hasattr(self, 'baseline_iterations') and self.baseline_iterations:
                        baseline_data = f"Build: {self.baseline_build}, Iterations: {self.baseline_iterations}, Avg: {sum(self.baseline_iterations)/len(self.baseline_iterations):.3f}"
                    
                    # Submit result to Live Audit
                    try:
                        self.network_manager.submit_result(
                            tc_id, tc_name, f"{average_value:.3f}", 
                            suite_name=suite_name, project_name=project_name,
                            notes=notes, baseline=baseline_data
                        )
                        print(f"✅ Result submitted successfully for {tc_id}")
                    except Exception as e:
                        print(f"❌ Error submitting result: {e}")
            
            self.navigate_next()
        else:
            self.reset_timer_and_iterations()
            self.update_results_tab()
            self.update_current_results_display()

    def reset_timer_and_iterations(self):
        """Resets the timer and iteration UI elements."""
        if self.timer.isActive():
            self.timer.stop()
        self.recorded_time = 0
        self.start_time = 0
        self.timer_display.setText("00:00.000")
        self.start_stop_btn.setText("Start (Space)")
        self.confirm_iteration_btn.setEnabled(False)
        self.determine_next_iteration() # This finds the next empty slot and updates indicators

    def determine_next_iteration(self):
        """
        Determines the next available iteration slot for the current test case
        and updates the UI indicators.
        """
        self.current_iteration = 6 # Default to completed
        if self.current_test_case is not None:
            for i in range(1, 6):
                iter_value = self.current_test_case.get(f"Iteration{i}", "")
                if pd.isna(iter_value) or str(iter_value).strip() == "":
                    self.current_iteration = i
                    break
        self.update_iteration_indicators()

    def update_iteration_indicators(self):
        """Updates the visual indicators for the current iteration."""
        if not self.baseline_mode:
            display_iter = min(self.current_iteration, 5)
            self.iteration_label.setText(f"Iteration: {display_iter}/5")

        for i, indicator in enumerate(self.iteration_indicators):
            # Iterations are 1-based, index is 0-based
            indicator.set_active(i < self.current_iteration - 1)

    def set_current_build(self):
        """Saves the entered build string to the current session state."""
        build_text = self.current_build_input.text().strip()
        if build_text:
            self.state.update_current_session('current_build', build_text)
            self.current_build_input.setStyleSheet("background-color: lightgreen;")
        else:
            self.current_build_input.setStyleSheet("")

    def save_notes(self):
        """Saves the notes for the current test case."""
        if self.current_test_case is not None:
            notes = self.notes_input.toPlainText()
            current_build = self.state.current_session.get('current_build', '')
            updated_test_case = self.data_manager.save_notes(
                self.state.get_active_sheet(),
                self.state.get_current_test_case_index(),
                notes,
                current_build
            )
            # Refresh the local test case data
            if updated_test_case is not None:
                self.current_test_case = updated_test_case

    def update_results_tab(self):
        """Refreshes the results table for the current sheet."""
        active_sheet = self.state.get_active_sheet()
        results_df = self.data_manager.get_all_results(active_sheet)

        if results_df is not None and not results_df.empty:
            self.results_table.blockSignals(True)
            self.results_table.setRowCount(results_df.shape[0])
            self.results_table.setColumnCount(results_df.shape[1])
            self.results_table.setHorizontalHeaderLabels(results_df.columns)

            for i in range(results_df.shape[0]):
                for j in range(results_df.shape[1]):
                    item_value = results_df.iloc[i, j]
                    # Format floats to 3 decimal places for display
                    if isinstance(item_value, float):
                        item_value = f"{item_value:.3f}"

                    table_item = QTableWidgetItem(str(item_value))

                    # Make 'Test Case Name' and 'Average' columns read-only
                    column_header = results_df.columns[j]
                    if column_header in ["Test Case Name", "Average", "Baseline Results"]:
                        table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                    # Make Notes column editable
                    elif column_header == "Notes":
                        pass # Keep it editable
                    else: # Iteration columns
                        table_item.setFlags(table_item.flags() | Qt.ItemIsEditable)


                    self.results_table.setItem(i, j, table_item)
            self.results_table.resizeColumnsToContents()
            self.results_table.blockSignals(False)

    def save_and_return(self):
        """Saves final state and returns to the launcher screen."""
        self.save_notes() # Save any pending notes before returning
        
        # Cleanup network manager
        if self.network_manager:
            self.network_manager.stop_polling()
        
        active_sheet = self.state.get_active_sheet()
        if self.is_session_complete(active_sheet):
            self.state.update_current_session('status', 'Completed')
        else:
            self.state.update_current_session('status', 'In Progress')
            
        self.return_to_launcher()

    def is_session_complete(self, sheet_name):
        """Checks if all test cases in the sheet are complete."""
        sheet_data = self.data_manager.get_sheet_data(sheet_name)
        if sheet_data.empty:
            return False

        for index, row in sheet_data.iterrows():
            is_complete = pd.notna(row.get('Average', '')) and str(row.get('Average', '')).strip() != ''
            if not is_complete:
                return False
        return True

    def manual_result_edit(self, item):
        """Handles manual editing of iteration values in the results table."""
        self.results_table.itemChanged.disconnect(self.manual_result_edit)
        try:
            row_index = item.row()
            column_index = item.column()
            column_header = self.results_table.horizontalHeaderItem(column_index).text()

            new_value_str = item.text()

            if "Iteration" in column_header:
                try:
                    new_value = float(new_value_str)
                    iteration_number = int(column_header.replace("Iteration", ""))
                    current_build = self.state.current_session.get('current_build', '')
                    updated_test_case = self.data_manager.save_iteration_time(
                        self.state.get_active_sheet(), row_index, iteration_number, new_value, current_build
                    )
                    if updated_test_case is not None:
                        self.current_test_case = updated_test_case

                    self.update_total_n_points() # Recalculate totals after manual edit
                except (ValueError, TypeError):
                    print(f"Invalid value: {new_value_str}. Reverting.")
            elif column_header == "Notes":
                current_build = self.state.current_session.get('current_build', '')
                self.data_manager.save_notes(
                    self.state.get_active_sheet(), row_index, new_value_str, current_build
                )

        finally:
            self.update_results_tab()
            self.update_current_results_display()
            self.results_table.itemChanged.connect(self.manual_result_edit)

    def update_total_n_points(self):
        """Calculates the total N-Points for all completed test cases."""
        active_sheet = self.state.get_active_sheet()
        sheet_data = self.data_manager.get_sheet_data(active_sheet)
        if sheet_data.empty or 'Average' not in sheet_data.columns:
            return

        # A test case is "complete" if its Average is not empty/null.
        completed_tcs = sheet_data[pd.to_numeric(sheet_data['Average'], errors='coerce').notna()]

        # Sum N-Points for completed test cases
        self.total_n_points = pd.to_numeric(completed_tcs['N-Points'], errors='coerce').sum()
        self.total_n_points_label.setText(f"<b>Total N-Points: {self.total_n_points}</b>")

    def update_current_results_display(self):
        """Updates the compact results table on the Test Case Details tab."""
        if self.current_test_case is None:
            return

        # Disconnect signal to prevent edit triggers while populating
        self.current_results_table.blockSignals(True)

        for i in range(1, 6):
            iter_value = self.current_test_case.get(f"Iteration{i}", "")
            if isinstance(iter_value, float):
                iter_value = f"{iter_value:.3f}"
            self.current_results_table.setItem(0, i - 1, QTableWidgetItem(str(iter_value)))

        avg_value = self.current_test_case.get("Average", "")
        if isinstance(avg_value, float):
            avg_value = f"{avg_value:.3f}"

        avg_item = QTableWidgetItem(str(avg_value))
        avg_item.setFont(QFont("Arial", 10, QFont.Bold))
        self.current_results_table.setItem(0, 5, avg_item)

        # Reconnect signal
        self.current_results_table.blockSignals(False)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts."""
        if event.key() == Qt.Key_Space:
            self.toggle_timer()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if self.confirm_iteration_btn.isEnabled():
                self.confirm_iteration()
        elif event.key() == Qt.Key_Left:
            self.navigate_previous()
        elif event.key() == Qt.Key_Right:
            self.navigate_next()
        else:
            super().keyPressEvent(event)

    def toggle_live_mode(self, state):
        """Toggles the live mode on/off."""
        self.live_mode = (state == 2)
        self.server_ip_input.setEnabled(not self.live_mode)  # Disable editing while active
        self.submit_all_btn.setEnabled(self.live_mode)  # Enable submit button when live
        
        if self.live_mode:
            # Create NetworkManager lazily only when needed
            if self.network_manager is None:
                from performance_dashboard.logic.network_manager import NetworkManager
                self.network_manager = NetworkManager(
                    executor_name=self.user_context.get('username', 'UnknownExecutor'),
                    token=self.user_context.get('auth_token')
                )
                self.network_manager.notification_received.connect(self.show_audit_notification)
                self.network_manager.connection_status.connect(self.update_connection_status)
                
                # Start connection explicitly after signals are connected
                self.network_manager.connect()
            
            # WebSocket connects automatically, no need to start polling
            url = self.server_ip_input.text().strip()
            self.network_manager.server_url = url
            self.status_bar.showMessage(f"Live Mode Active: Connected to {url}")
        else:
            if self.network_manager:
                self.network_manager.stop_polling()
            self.connection_indicator.setText("⚫ Not Connected")
            self.connection_indicator.setStyleSheet("color: gray; font-weight: bold;")
            self.status_bar.showMessage("Live Mode Disabled")
    
    def update_connection_status(self, state, message):
        """Updates the connection status indicator based on network manager state."""
        # Map states to visual indicators
        status_map = {
            "connecting": ("🟡 Connecting...", "color: orange; font-weight: bold;"),
            "connected": ("🟢 Connected", "color: green; font-weight: bold;"),
            "disconnected": ("🔴 Disconnected", "color: red; font-weight: bold;"),
            "failed": ("⚠️ Failed", "color: darkred; font-weight: bold;")
        }
        
        if state in status_map:
            text, style = status_map[state]
            self.connection_indicator.setText(text)
            self.connection_indicator.setStyleSheet(style)
            self.status_bar.showMessage(message)
            
            # If connected, fetch missed notifications
            if state == "connected":
                self.check_missed_notifications()

    def check_missed_notifications(self):
        """Fetches and displays any notifications missed while disconnected."""
        if self.network_manager:
            notifications = self.network_manager.fetch_notifications()
            for notif in notifications:
                # Convert server response to notification format
                data = {
                    "id": notif.get("id"),
                    "title": "Audit Alert (Missed)",
                    "message": f"Test Case '{notif.get('test_case_name')}' was REJECTED.\nComment: {notif.get('auditor_comment')}",
                    "timestamp": notif.get("timestamp"),
                    "status": notif.get("status"),
                    "details": notif
                }
                self.show_audit_notification(data)
    
    def submit_all_completed(self):
        """Submits all completed test cases (those with calculated averages) to auditor."""
        if not self.live_mode or not self.network_manager:
            QMessageBox.warning(self, "Error", "Live Mode must be enabled to submit results.")
            return
        
        # Get all test cases from current sheet
        sheet_name = self.state.get_active_sheet()
        sheet_data = self.data_manager.get_sheet_data(sheet_name)
        
        if sheet_data.empty:
            QMessageBox.information(self, "No Data", "No test cases found in current sheet.")
            return
        
        submitted_count = 0
        failed_count = 0
        
        # Find all test cases with calculated averages
        for idx, row in sheet_data.iterrows():
            tc_id = row.get("Test Case ID", "")
            tc_name = row.get("Test Case Name", "")
            average = row.get("Average", "")
            
            # Check if test case has a valid average
            if average and str(average).strip() != "" and average != "N/A":
                try:
                    avg_float = float(average)
                    if avg_float > 0:  # Valid average
                        suite_name = self.state.get_active_sheet()  # Get current suite
                        project_name = self.state.current_session.get('project', 'KindleLogAnalyzer') if self.state.current_session else 'KindleLogAnalyzer'
                        self.network_manager.submit_result(tc_id, tc_name, f"{avg_float:.3f}", suite_name=suite_name, project_name=project_name)
                        submitted_count += 1
                except Exception as e:
                    print(f"Failed to submit {tc_name}: {e}")
                    failed_count += 1
        
        # Show summary
        if submitted_count > 0:
            QMessageBox.information(
                self, 
                "Submission Complete", 
                f"✅ Successfully submitted {submitted_count} test case(s).\n" +
                (f"⚠️ Failed: {failed_count}" if failed_count > 0 else "")
            )
            self.status_bar.showMessage(f"Submitted {submitted_count} completed test cases to auditor")
        else:
            QMessageBox.information(self, "No Data", "No completed test cases found to submit.")

    def show_audit_notification(self, data):
        """Displays an audit notification and adds it to the panel."""
        title = data.get("title", "Audit Alert")
        message = data.get("message", "")
        timestamp = data.get("timestamp", "")
        
        # 1. Show transient popup
        QMessageBox.warning(self, title, message)
        
        # 2. Add to Notification Panel
        item_text = f"[{timestamp}] {message}"
        item = QListWidgetItem(item_text)
        
        # Style based on status
        if data.get("status") == "Rejected":
            item.setForeground(QBrush(QColor("red")))
            item.setBackground(QBrush(QColor("#ffebee"))) # Light red background
            
        self.notification_list.insertItem(0, item) # Add to top
        
        # 3. Switch to notification tab if not already there
        # self.tabs.setCurrentIndex(2) # Optional: Auto-switch? Maybe annoying.
        
        # 4. Highlight tab header to indicate new notification
        self.tabs.tabBar().setTabTextColor(2, QColor("red"))
        
        # 5. Mark as read on server (if it has an ID)
        if "id" in data and self.network_manager:
            # Run in background to avoid blocking UI
            threading.Thread(target=self.network_manager.mark_read, args=(data["id"],), daemon=True).start()

    def on_tab_changed(self, index):
        """Reset tab color when user views notifications."""
        if index == 2: # Notifications tab
            self.tabs.tabBar().setTabTextColor(2, QColor("black"))

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            if hasattr(self, 'network_manager') and self.network_manager:
                self.network_manager.stop_polling()
        except:
            pass

    def closeEvent(self, event):
        """Cleanup when the dashboard is closed."""
        if self.network_manager:
            self.network_manager.stop_polling()
        event.accept()

    def populate_advanced_nav(self, sheet_name, identifiers=None):
        """Populates the filter and search dropdowns with data from the current sheet."""
        # Component Filter (only needs to be populated once)
        if self.area_filter_combo.count() == 1:
            self.area_filter_combo.blockSignals(True)
            components = self.data_manager.get_unique_components(sheet_name)
            self.area_filter_combo.addItems(components)
            self.area_filter_combo.blockSignals(False)

        # Searchable Test Case list (can be updated dynamically)
        self.search_combo.blockSignals(True)
        self.search_combo.clear()

        if identifiers is None:
            identifiers = self.data_manager.get_all_test_case_identifiers(sheet_name)

        self.search_model = QStringListModel(identifiers)
        self.search_completer = QCompleter(self.search_model, self)
        self.search_completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.search_combo.setCompleter(self.search_completer)
        self.search_combo.addItems(identifiers)
        self.search_combo.setCurrentIndex(-1) # Start with no selection
        self.search_combo.blockSignals(False)

    def apply_filters(self, selected_index=0):
        """
        Applies the selected filters to determine the list of visible test cases.
        """
        active_sheet = self.state.get_active_sheet()
        all_test_cases = self.data_manager.get_sheet_data(active_sheet)

        selected_component = self.area_filter_combo.currentText()

        if selected_component == "All Components":
            self.filtered_indices = list(all_test_cases.index)
        else:
            self.filtered_indices = list(all_test_cases[all_test_cases["Component"] == selected_component].index)

        if not self.filtered_indices:
            QMessageBox.warning(self, "No Test Cases", "No test cases match the selected filter.")
            # Handle empty filter result - maybe disable navigation
            self.test_case_progress_label.setText("Test Case: 0 / 0")
            return

        self.current_filtered_index = selected_index

        # Get the identifiers for the filtered data and update the search combo
        filtered_df = all_test_cases.loc[self.filtered_indices]
        filtered_identifiers = self.data_manager.get_all_test_case_identifiers(active_sheet, filtered_df)
        self.populate_advanced_nav(active_sheet, filtered_identifiers)

        self.load_test_case_by_index(self.filtered_indices[self.current_filtered_index])

    def filter_by_area(self):
        """Triggered when the functional area filter is changed."""
        self.apply_filters()

    def search_test_case(self, index):
        """Finds and loads the test case selected from the search dropdown."""
        if index < 0:
            return  # Ignore invalid signals

        identifier = self.search_combo.itemText(index)
        # Handle cases where the identifier might be empty or malformed
        if ':' not in identifier:
            return

        tc_id_str = identifier.split(':')[0].strip()

        active_sheet = self.state.get_active_sheet()
        all_test_cases = self.data_manager.get_sheet_data(active_sheet)

        # Ensure the 'Test Case ID' column is of a consistent type for comparison
        all_test_cases["Test Case ID"] = all_test_cases["Test Case ID"].astype(str)

        # Find the original DataFrame index for the selected Test Case ID
        matching_rows = all_test_cases[all_test_cases["Test Case ID"] == tc_id_str]

        if matching_rows.empty:
            QMessageBox.warning(self, "Not Found", f"Test Case ID '{tc_id_str}' could not be found.")
            return

        original_index = int(matching_rows.index[0])

        # Now, find where this original_index is in our currently filtered list

        if original_index in self.filtered_indices:
            self.current_filtered_index = self.filtered_indices.index(original_index)
            self.load_test_case_by_index(original_index)
        else:
            QMessageBox.information(self, "Filter Active", "The selected test case is not in the current filtered view. Clear the filter to see it.")

    def on_session_changed(self, index):
        """Handles switching to a different session from the dropdown."""
        if index < 0 or not self.switch_session_callback:
            return

        # Get the filename of the selected session
        selected_filename = self.session_selector.itemData(index)
        if not selected_filename:
            return

        # Find the session data
        new_session_data = self.state.get_session_by_filename(selected_filename)
        if not new_session_data:
            return

        # Save current session state before switching
        self.save_notes()
        active_sheet = self.state.get_active_sheet()
        if self.is_session_complete(active_sheet):
            self.state.update_current_session('status', 'Completed')
        else:
            self.state.update_current_session('status', 'In Progress')

        # Switch to the new session
        self.switch_session_callback(new_session_data)

    def check_incomplete_test_cases(self, sheet_name):
        """Checks for test cases that have started but are not complete."""
        sheet_data = self.data_manager.get_sheet_data(sheet_name)
        if sheet_data.empty:
            return

        incomplete_cases = []
        for index, row in sheet_data.iterrows():
            # Check if Iteration1 has data but Average is empty (meaning not all 5 are done)
            has_started = pd.notna(row.get('Iteration1', '')) and str(row.get('Iteration1', '')).strip() != ''
            is_complete = pd.notna(row.get('Average', '')) and str(row.get('Average', '')).strip() != ''
            
            if has_started and not is_complete:
                tc_id = row.get('Test Case ID', f"Row {index+1}")
                incomplete_cases.append(str(tc_id))

        if incomplete_cases:
            msg = "The following test cases are incomplete (started but not finished):\n\n"
            msg += "\n".join(incomplete_cases[:10]) # Show max 10
            if len(incomplete_cases) > 10:
                msg += f"\n...and {len(incomplete_cases) - 10} more."
            msg += "\n\nPlease complete them."
            QMessageBox.warning(self, "Incomplete Test Cases", msg)

    def jump_to_test_case(self):
        """Jumps to a specific test case number (1-based index)."""
        try:
            target_number = int(self.jump_to_input.text())
            if 1 <= target_number <= len(self.filtered_indices):
                self.current_filtered_index = target_number - 1
                self.load_test_case_by_index(self.filtered_indices[self.current_filtered_index])
            else:
                QMessageBox.warning(self, "Invalid Number", f"Please enter a number between 1 and {len(self.filtered_indices)}.")
        except ValueError:
            QMessageBox.warning(self, "Invalid Input", "Please enter a valid number.")
        finally:
            self.jump_to_input.clear()

    def retest_current_case(self):
        """Resets the current test case for retesting."""
        reply = QMessageBox.question(self, 'Retest Confirmation',
                                     "Are you sure you want to retest this case? All current iterations will be cleared.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.reset_timer_and_iterations()
            # Clear data in data manager
            active_sheet = self.state.get_active_sheet()
            current_index = self.state.get_current_test_case_index()
            
            # Clear iterations in dataframe
            df = self.data_manager.get_sheet_data(active_sheet)
            
            # Ensure columns are object type to accept empty strings without warning
            cols_to_clear = [f"Iteration{i}" for i in range(1, 6)] + ["Average"]
            for col in cols_to_clear:
                if col in df.columns and df[col].dtype != 'object':
                    df[col] = df[col].astype('object')

            for i in range(1, 6):
                df.at[current_index, f"Iteration{i}"] = ""
            df.at[current_index, "Average"] = ""
            self.data_manager.workbook[active_sheet] = df
            self.data_manager.save_to_excel_async()
            
            # Refresh current_test_case with cleared data
            self.current_test_case = self.data_manager.get_test_case(active_sheet, current_index)
            
            self.update_results_tab()
            self.update_current_results_display()
            
    def block_test_case(self):
        """Marks the current test case as blocked."""
        if self.current_test_case is None or (hasattr(self.current_test_case, 'empty') and self.current_test_case.empty):
            return
            
        reason, ok = QInputDialog.getText(self, "Block Test Case", "Reason for blocking:")
        if ok and reason:
            # Save reason to notes
            current_notes = self.notes_input.toPlainText()
            new_notes = f"[BLOCKED]: {reason}\n{current_notes}"
            self.notes_input.setText(new_notes)
            self.save_notes()
            
            # Submit as blocked
            if self.live_mode:
                tc_id = self.current_test_case.get("Test Case ID", "")
                tc_name = self.current_test_case.get("Test Case Name", "")
                suite_name = self.state.get_active_sheet()
                project_name = self.state.current_session.get('project', 'KindleLogAnalyzer') if self.state.current_session else 'KindleLogAnalyzer'
                
                self.network_manager.submit_result(
                    tc_id, tc_name, "0", 
                    suite_name=suite_name, project_name=project_name,
                    notes=new_notes, baseline="", status="Blocked"
                )
                
            QMessageBox.warning(self, "Blocked", "Test case marked as blocked.")
            self.navigate_next()

    def save_session(self):
        """Saves the current session to disk in the background."""
        self.save_notes() # Ensure notes are saved to memory first
        
        self.status_bar.showMessage("Saving...")
        self.save_thread = self.data_manager.save_to_excel_async()
        if self.save_thread:
            self.save_thread.finished_signal.connect(self.on_save_finished)
            self.save_thread.start()
        else:
            self.status_bar.showMessage("Nothing to save.", 3000)

    def on_save_finished(self, success, message):
        """Handle save completion."""
        if success:
            self.status_bar.showMessage("Saved", 3000) # Show for 3 seconds
        else:
            self.status_bar.showMessage(f"Error: {message}")
            QMessageBox.warning(self, "Save Error", message)