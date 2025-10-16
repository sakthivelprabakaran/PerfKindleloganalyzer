import time
import pandas as pd
from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QLabel, QPushButton,
    QTextEdit, QTableWidget, QTabWidget, QSplitter,
    QTableWidgetItem, QHeaderView, QMessageBox, QFrame
)
from PyQt5.QtGui import QPainter, QFont
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


class DynamicHeightTextEdit(QTextEdit):
    """A QTextEdit that automatically adjusts its height to fit its content."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setReadOnly(True)


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
        self.note_button_timer = QTimer(self)
        self.note_button_timer.setSingleShot(True)
        self.note_button_timer.timeout.connect(lambda: self.add_note_btn.setText("Add Note"))
        self.start_time = 0
        self.recorded_time = 0
        self.current_iteration = 1

        self.current_test_case = None
        self.total_test_cases = 0
        self.total_n_points = 0

        self.init_ui()

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

    def create_left_panel(self):
        """Creates the left panel for timer controls and navigation."""
        panel = QGroupBox("Timer Control & Navigation")
        layout = QVBoxLayout()
        panel.setLayout(layout)

        # Session Info
        session_group = QGroupBox("📊 Session Info")
        session_layout = QVBoxLayout()
        self.session_info_label = QLabel("Session: N/A")
        self.total_n_points_label = QLabel("<b>Total N-Points: 0</b>")
        session_layout.addWidget(self.session_info_label)
        session_layout.addWidget(self.total_n_points_label)
        session_group.setLayout(session_layout)
        layout.addWidget(session_group)

        # Timer
        timer_group = QGroupBox("⏱️ Timer")
        timer_layout = QVBoxLayout()
        self.timer_display = QLabel("00:00.000")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setFont(QFont("Arial", 50, QFont.Bold))
        self.timer_display.setObjectName("timerDisplay")
        timer_layout.addWidget(self.timer_display)
        self.start_stop_btn = QPushButton("Start (Space)")
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        timer_layout.addWidget(self.start_stop_btn)
        timer_group.setLayout(timer_layout)
        layout.addWidget(timer_group)

        # Iteration Management
        iteration_group = QGroupBox("🔄 Iteration Management")
        iteration_layout = QVBoxLayout()
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
        iteration_group.setLayout(iteration_layout)
        layout.addWidget(iteration_group)

        # Navigation Controls
        nav_group = QGroupBox("Navigate")
        nav_layout = QVBoxLayout()
        nav_buttons_layout = QHBoxLayout()
        prev_btn = QPushButton("⬅️ Previous")
        prev_btn.clicked.connect(self.navigate_previous)
        next_btn = QPushButton("Next ➡️")
        next_btn.clicked.connect(self.navigate_next)
        nav_buttons_layout.addWidget(prev_btn)
        nav_buttons_layout.addWidget(next_btn)
        nav_layout.addLayout(nav_buttons_layout)
        self.test_case_progress_label = QLabel("Test Case: 1 / 1")
        self.test_case_progress_label.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(self.test_case_progress_label)
        nav_group.setLayout(nav_layout)
        layout.addWidget(nav_group)

        # Notes Section
        notes_group = QGroupBox("📝 Notes")
        notes_layout = QVBoxLayout()
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Enter notes for the current test case...")
        notes_layout.addWidget(self.notes_input)
        self.add_note_btn = QPushButton("Add Note")
        self.add_note_btn.clicked.connect(self.save_notes)
        notes_layout.addWidget(self.add_note_btn)
        notes_group.setLayout(notes_layout)
        layout.addWidget(notes_group)

        layout.addStretch()

        # Save and Return Button
        save_return_btn = QPushButton("💾 Save & Return to Launcher")
        save_return_btn.clicked.connect(self.save_and_return)
        layout.addWidget(save_return_btn)

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
        self.update_total_n_points() # Calculate initial N-Points
        self.load_test_case_by_index(self.state.get_current_test_case_index())
        self.update_results_tab()

    def load_test_case_by_index(self, index):
        """Loads a specific test case into the UI."""
        active_sheet = self.state.get_active_sheet()
        self.current_test_case = self.data_manager.get_test_case(active_sheet, index)

        if self.current_test_case is not None:
            self.state.update_current_session('current_test_case_index', index)

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

    def navigate_next(self):
        current_index = self.state.get_current_test_case_index()
        if current_index + 1 < self.total_test_cases:
            # Notes are now saved explicitly via the "Add Note" button
            self.load_test_case_by_index(current_index + 1)

    def navigate_previous(self):
        current_index = self.state.get_current_test_case_index()
        if current_index > 0:
            # Notes are now saved explicitly via the "Add Note" button
            self.load_test_case_by_index(current_index - 1)

    def toggle_timer(self):
        if self.timer.isActive():
            self.timer.stop()
            self.recorded_time = time.perf_counter() - self.start_time
            self.start_stop_btn.setText("Start (Space)")
            self.confirm_iteration_btn.setEnabled(True)
        else:
            self.start_time = time.perf_counter()
            self.timer.start(10) # Update display every 10ms
            self.start_stop_btn.setText("Stop (Space)")
            self.confirm_iteration_btn.setEnabled(False)

    def update_timer_display(self):
        elapsed = time.perf_counter() - self.start_time
        minutes, seconds = divmod(elapsed, 60)
        self.timer_display.setText(f"{int(minutes):02d}:{int(seconds):02d}.{int((seconds % 1) * 1000):03d}")

    def confirm_iteration(self):
        """Saves the current time and moves to the next iteration."""
        if self.current_iteration > 5:
            QMessageBox.information(self, "Completed", "All iterations for this test case are complete.")
            return

        # Format the recorded time to 3 decimal places for consistency
        formatted_time = float(f"{self.recorded_time:.3f}")

        updated_test_case = self.data_manager.save_iteration_time(
            self.state.get_active_sheet(),
            self.state.get_current_test_case_index(),
            self.current_iteration,
            formatted_time
        )

        if updated_test_case is not None:
            self.current_test_case = updated_test_case

        # Check if all iterations are now complete to update N-Points
        self.determine_next_iteration() # This will now set current_iteration to 6 if complete
        if self.current_iteration > 5:
            self.update_total_n_points()

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
        for i, indicator in enumerate(self.iteration_indicators):
            # Iterations are 1-based, index is 0-based
            indicator.set_active(i < self.current_iteration - 1)

    def save_notes(self):
        """Saves the notes for the current test case."""
        if self.current_test_case is not None:
            notes = self.notes_input.toPlainText()
            updated_test_case = self.data_manager.save_notes(
                self.state.get_active_sheet(),
                self.state.get_current_test_case_index(),
                notes
            )
            # Refresh the local test case data and provide user feedback
            if updated_test_case is not None:
                self.current_test_case = updated_test_case
                self.add_note_btn.setText("Note Saved!")
                self.note_button_timer.start(2000) # Reset text after 2 seconds

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
                    if column_header == "Test Case Name" or column_header == "Average":
                        table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)

                    self.results_table.setItem(i, j, table_item)
            self.results_table.resizeColumnsToContents()
            self.results_table.blockSignals(False)

    def save_and_return(self):
        """Saves final state and returns to the launcher screen."""
        self.note_button_timer.stop() # Stop the timer to prevent crash
        # self.save_notes() # No longer needed as it's explicit
        self.state.update_current_session('status', 'Completed') # Or some other status
        self.return_to_launcher()

    def manual_result_edit(self, item):
        """Handles manual editing of iteration values in the results table."""
        self.results_table.itemChanged.disconnect(self.manual_result_edit)
        try:
            row_index = item.row()
            column_index = item.column()
            column_header = self.results_table.horizontalHeaderItem(column_index).text()

            if "Iteration" not in column_header:
                return

            new_value_str = item.text()
            try:
                new_value = float(new_value_str)
                iteration_number = int(column_header.replace("Iteration", ""))
                updated_test_case = self.data_manager.save_iteration_time(
                    self.state.get_active_sheet(), row_index, iteration_number, new_value
                )
                if updated_test_case is not None:
                    self.current_test_case = updated_test_case

                self.update_total_n_points() # Recalculate totals after manual edit
            except (ValueError, TypeError):
                print(f"Invalid value: {new_value_str}. Reverting.")
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