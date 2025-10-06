import time
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTabWidget, QSplitter, QLCDNumber,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame
)
from PyQt5.QtGui import QPainter
from PyQt5.QtCore import Qt, QTimer, QTime

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


class ExecutionDashboard(QWidget):
    """
    The main dashboard for test case execution, timing, and data entry.
    """
    def __init__(self, state_manager, data_manager, return_to_launcher_callback):
        super().__init__()
        self.state = state_manager
        self.data_manager = data_manager
        self.return_to_launcher = return_to_launcher_callback

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer_display)
        self.elapsed_time = QTime(0, 0, 0, 0)

        self.current_test_case = None
        self.total_test_cases = 0

        self.init_ui()

    def init_ui(self):
        """Initializes the UI layout and widgets."""
        main_layout = QVBoxLayout(self)

        # Top bar for session info and save button
        top_bar_layout = QHBoxLayout()
        self.session_info_label = QLabel("Session: N/A")
        top_bar_layout.addWidget(self.session_info_label)
        top_bar_layout.addStretch()
        save_return_btn = QPushButton("Save & Return to Launcher")
        save_return_btn.clicked.connect(self.save_and_return)
        top_bar_layout.addWidget(save_return_btn)
        main_layout.addLayout(top_bar_layout)

        # Main splitter for the two panels
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter, 1)

        # Left Panel: Timer Control & Navigation
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # Right Panel: Test Case Details & Results
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([400, 800]) # Initial size ratio

    def create_left_panel(self):
        """Creates the left panel for timer controls and navigation."""
        panel = QGroupBox("Timer Control & Navigation")
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Priority Selection (Sheet Selection)
        # This will be driven by the session, so for now it's a label
        self.priority_label = QLabel("Priority Sheet: P0")
        layout.addWidget(self.priority_label)

        # Timer Display
        self.timer_display = QLCDNumber()
        self.timer_display.setSegmentStyle(QLCDNumber.Flat)
        self.timer_display.setDigitCount(12)
        self.timer_display.display("00:00.000")
        layout.addWidget(self.timer_display)

        # Timer Controls
        timer_controls_layout = QHBoxLayout()
        self.start_stop_btn = QPushButton("Start (Space)")
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        timer_controls_layout.addWidget(self.start_stop_btn)
        layout.addLayout(timer_controls_layout)

        # Iteration Management
        iteration_group = QGroupBox("Iteration Management")
        iteration_layout = QVBoxLayout()
        iteration_group.setLayout(iteration_layout)

        self.iteration_indicators_layout = QHBoxLayout()
        self.iteration_indicators = []
        for _ in range(5):
            indicator = CircleIndicator()
            self.iteration_indicators.append(indicator)
            self.iteration_indicators_layout.addWidget(indicator)
        iteration_layout.addLayout(self.iteration_indicators_layout)

        self.confirm_iteration_btn = QPushButton("Confirm & Next Iteration (Enter)")
        self.confirm_iteration_btn.setEnabled(False)
        self.confirm_iteration_btn.clicked.connect(self.confirm_iteration)
        iteration_layout.addWidget(self.confirm_iteration_btn)
        layout.addWidget(iteration_group)

        # Navigation Controls
        nav_layout = QHBoxLayout()
        prev_btn = QPushButton("Previous (Left Arrow)")
        prev_btn.clicked.connect(self.navigate_previous)
        next_btn = QPushButton("Next (Right Arrow)")
        next_btn.clicked.connect(self.navigate_next)
        nav_layout.addWidget(prev_btn)
        nav_layout.addWidget(next_btn)
        layout.addLayout(nav_layout)

        self.test_case_progress_label = QLabel("Test Case: 1 / 1")
        layout.addWidget(self.test_case_progress_label)

        # Notes Section
        layout.addWidget(QLabel("Notes:"))
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Enter notes for the current test case...")
        self.notes_input.focusOutEvent = self.auto_save_notes # Monkey-patch focusOutEvent
        layout.addWidget(self.notes_input)

        return panel

    def create_right_panel(self):
        """Creates the right panel for test case details and results."""
        panel = QWidget()
        layout = QVBoxLayout()
        panel.setLayout(layout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Tab 1: Test Case Details
        details_tab = QWidget()
        details_layout = QVBoxLayout()
        details_tab.setLayout(details_layout)

        details_layout.addWidget(QLabel("<b>Test Case ID:</b>"))
        self.tc_id_label = QLabel("N/A")
        details_layout.addWidget(self.tc_id_label)

        details_layout.addWidget(QLabel("<b>Test Case Name:</b>"))
        self.tc_name_label = QLabel("N/A")
        details_layout.addWidget(self.tc_name_label)

        details_layout.addWidget(QLabel("<b>Pre-requisites:</b>"))
        self.tc_prereq_text = QTextEdit()
        self.tc_prereq_text.setReadOnly(True)
        details_layout.addWidget(self.tc_prereq_text)

        details_layout.addWidget(QLabel("<b>Test Steps:</b>"))
        self.tc_steps_text = QTextEdit()
        self.tc_steps_text.setReadOnly(True)
        details_layout.addWidget(self.tc_steps_text)

        self.tabs.addTab(details_tab, "Test Case Details")

        # Tab 2: Results
        results_tab = QWidget()
        results_layout = QVBoxLayout()
        results_tab.setLayout(results_layout)

        self.results_table = QTableWidget()
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.results_table)

        self.tabs.addTab(results_tab, "Results")

        return panel

    def load_session_data(self):
        """Loads data for the current session into the dashboard."""
        if not self.state.current_session:
            return

        session_name = self.state.current_session.get('file_name', 'N/A')
        self.session_info_label.setText(f"<b>Session:</b> {session_name}")

        active_sheet = self.state.get_active_sheet()
        self.priority_label.setText(f"<b>Priority Sheet:</b> {active_sheet}")

        self.total_test_cases = self.data_manager.get_test_case_count(active_sheet)
        self.load_test_case_by_index(self.state.get_current_test_case_index())
        self.update_results_tab()

    def load_test_case_by_index(self, index):
        """Loads a specific test case into the UI."""
        active_sheet = self.state.get_active_sheet()
        self.current_test_case = self.data_manager.get_test_case(active_sheet, index)

        if self.current_test_case is not None:
            self.state.update_current_session('current_test_case_index', index)

            self.tc_id_label.setText(str(self.current_test_case.get("Test Case ID", "N/A")))
            self.tc_name_label.setText(str(self.current_test_case.get("Test Case Name", "N/A")))
            self.tc_prereq_text.setText(str(self.current_test_case.get("Pre-requisites", "")))
            self.tc_steps_text.setText(str(self.current_test_case.get("Test Steps", "")))
            self.notes_input.setText(str(self.current_test_case.get("Notes", "")))

            self.test_case_progress_label.setText(f"Test Case: {index + 1} / {self.total_test_cases}")
            # Reset the iteration count for the new test case
            self.state.update_current_session('current_iteration', 1)
            self.reset_timer_and_iterations()
        else:
            QMessageBox.information(self, "End of List", "You have reached the end of the test cases for this sheet.")

    def navigate_next(self):
        current_index = self.state.get_current_test_case_index()
        if current_index + 1 < self.total_test_cases:
            self.auto_save_notes(None) # Save notes before navigating
            self.load_test_case_by_index(current_index + 1)

    def navigate_previous(self):
        current_index = self.state.get_current_test_case_index()
        if current_index > 0:
            self.auto_save_notes(None) # Save notes before navigating
            self.load_test_case_by_index(current_index - 1)

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.start_stop_btn.setText("Start (Space)")
            self.confirm_iteration_btn.setEnabled(True)
        else:
            self.elapsed_time.setHMS(0, 0, 0, 0)
            self.timer.start(10) # Update every 10ms for better precision
            self.start_stop_btn.setText("Stop (Space)")
            self.confirm_iteration_btn.setEnabled(False)

    def update_timer_display(self):
        self.elapsed_time = self.elapsed_time.addMSecs(10)
        self.timer_display.display(self.elapsed_time.toString("mm:ss.zzz"))

    def confirm_iteration(self):
        """Saves the current time and moves to the next iteration."""
        current_iteration = self.state.get_current_iteration()
        # Format to seconds with 3 decimal places
        time_val = self.elapsed_time.msecsSinceStartOfDay() / 1000.0

        self.data_manager.save_iteration_time(
            self.state.get_active_sheet(),
            self.state.get_current_test_case_index(),
            current_iteration,
            time_val
        )

        if current_iteration < 5:
            self.state.update_current_session('current_iteration', current_iteration + 1)
        else:
            # Last iteration, maybe auto-navigate? For now, just reset.
            self.state.update_current_session('current_iteration', 1)

        self.reset_timer_and_iterations()
        self.update_results_tab()

    def reset_timer_and_iterations(self):
        """Resets the timer and iteration UI elements."""
        if self.timer.isActive():
            self.timer.stop()
        self.elapsed_time.setHMS(0, 0, 0, 0)
        self.timer_display.display("00:00.000")
        self.start_stop_btn.setText("Start (Space)")
        self.confirm_iteration_btn.setEnabled(False)
        self.update_iteration_indicators()

    def update_iteration_indicators(self):
        """Updates the visual indicators for the current iteration."""
        current_iter = self.state.get_current_iteration()
        for i, indicator in enumerate(self.iteration_indicators):
            # Iterations are 1-based, index is 0-based
            indicator.set_active(i < current_iter - 1)

    def auto_save_notes(self, event):
        """Saves the notes when the text area loses focus."""
        if self.current_test_case is not None:
            notes = self.notes_input.toPlainText()
            self.data_manager.save_notes(
                self.state.get_active_sheet(),
                self.state.get_current_test_case_index(),
                notes
            )
        if event:
            super(QTextEdit, self.notes_input).focusOutEvent(event)

    def update_results_tab(self):
        """Refreshes the results table for the current sheet."""
        active_sheet = self.state.get_active_sheet()
        results_df = self.data_manager.get_all_results(active_sheet)

        if results_df is not None and not results_df.empty:
            self.results_table.setRowCount(results_df.shape[0])
            self.results_table.setColumnCount(results_df.shape[1])
            self.results_table.setHorizontalHeaderLabels(results_df.columns)

            for i in range(results_df.shape[0]):
                for j in range(results_df.shape[1]):
                    item = results_df.iloc[i, j]
                    # Format floats to 3 decimal places for display
                    if isinstance(item, float):
                        item = f"{item:.3f}"
                    self.results_table.setItem(i, j, QTableWidgetItem(str(item)))
            self.results_table.resizeColumnsToContents()

    def save_and_return(self):
        """Saves final state and returns to the launcher screen."""
        self.auto_save_notes(None) # Ensure last notes are saved
        self.state.update_current_session('status', 'Completed') # Or some other status
        self.return_to_launcher()

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