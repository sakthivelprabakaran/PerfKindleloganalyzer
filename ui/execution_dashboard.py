import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QSplitter, QGroupBox, QTextEdit, QTableWidget, QTabWidget,
    QTableWidgetItem, QHeaderView, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QFont, QColor

from logic.data_manager import DataManager

class ExecutionDashboard(QWidget):
    """A widget for the Execution Dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)

        try:
            self.data_manager = DataManager()
        except (FileNotFoundError, Exception) as e:
            self.show_error_message(str(e))
            return

        self.current_sheet = None
        self.current_test_case_index = 0
        self.current_iteration = 0
        self.is_timer_running = False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer_display)
        self.time_elapsed = QTime(0, 0)

        self.setup_ui()
        self.connect_signals()
        self.load_initial_data()

    def setup_ui(self):
        """Sets up the UI of the widget."""
        self.setWindowTitle("Execution Dashboard")
        self.setMinimumSize(1400, 900)

        main_layout = QHBoxLayout(self)
        main_splitter = QSplitter(Qt.Horizontal)

        left_panel = self.create_left_panel()
        main_splitter.addWidget(left_panel)

        right_panel = self.create_right_panel()
        main_splitter.addWidget(right_panel)

        main_splitter.setSizes([350, 1050])
        main_layout.addWidget(main_splitter)

    def create_left_panel(self):
        """Creates the left panel with timer controls and navigation."""
        panel = QGroupBox("Timer Control & Navigation")
        layout = QVBoxLayout()

        # Priority selection
        layout.addWidget(QLabel("Priority:"))
        self.priority_combo = QComboBox()
        layout.addWidget(self.priority_combo)

        # Timer display
        self.timer_display = QLabel("00:00.000")
        self.timer_display.setAlignment(Qt.AlignCenter)
        self.timer_display.setFont(QFont("Courier", 48, QFont.Bold))
        self.timer_display.setStyleSheet("color: #2E8B57;")
        layout.addWidget(self.timer_display)

        # Timer controls
        self.start_stop_btn = QPushButton("Start/Stop")
        self.start_stop_btn.setShortcut("Space")
        layout.addWidget(self.start_stop_btn)

        # Iteration management
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

        self.confirm_btn = QPushButton("Confirm & Next Iteration")
        self.confirm_btn.setShortcut("Return")
        iteration_layout.addWidget(self.confirm_btn)
        iteration_group.setLayout(iteration_layout)
        layout.addWidget(iteration_group)

        # Navigation controls
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("<< Previous")
        self.prev_btn.setShortcut("Left")
        self.next_btn = QPushButton("Next >>")
        self.next_btn.setShortcut("Right")
        nav_layout.addWidget(self.prev_btn)
        nav_layout.addWidget(self.next_btn)
        layout.addLayout(nav_layout)

        # Notes section
        layout.addWidget(QLabel("Notes:"))
        self.notes_area = QTextEdit()
        self.notes_area.setPlaceholderText("Add notes for the current test case...")
        layout.addWidget(self.notes_area)

        layout.addStretch()
        panel.setLayout(layout)
        return panel

    def create_right_panel(self):
        """Creates the right panel with test case details and results."""
        panel = QGroupBox("Test Case Details & Results")
        layout = QVBoxLayout()

        self.tab_widget = QTabWidget()

        # Test Case Details Tab
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)

        self.test_case_id_label = QLabel("ID: N/A")
        self.test_case_name_label = QLabel("Name: N/A")
        self.n_points_label = QLabel("N-Points: N/A")

        details_layout.addWidget(self.test_case_id_label)
        details_layout.addWidget(self.test_case_name_label)

        self.prereq_area = QTextEdit()
        self.prereq_area.setReadOnly(True)
        self.prereq_area.setPlaceholderText("Pre-requisites...")

        self.test_steps_area = QTextEdit()
        self.test_steps_area.setReadOnly(True)
        self.test_steps_area.setPlaceholderText("Test Steps...")

        details_layout.addWidget(QLabel("Pre-requisites:"))
        details_layout.addWidget(self.prereq_area)
        details_layout.addWidget(QLabel("Test Steps:"))
        details_layout.addWidget(self.test_steps_area)
        details_layout.addWidget(self.n_points_label)

        self.tab_widget.addTab(details_tab, "Test Case Details")

        # Results Tab
        results_tab = QWidget()
        results_layout = QVBoxLayout(results_tab)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Test Case Name", "Iteration1", "Iteration2", "Iteration3",
            "Iteration4", "Iteration5", "Average"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.results_table)
        self.tab_widget.addTab(results_tab, "Results")

        layout.addWidget(self.tab_widget)
        panel.setLayout(layout)
        return panel

    def connect_signals(self):
        """Connects UI element signals to corresponding slots."""
        self.priority_combo.currentTextChanged.connect(self.load_sheet_data)
        self.start_stop_btn.clicked.connect(self.toggle_timer)
        self.confirm_btn.clicked.connect(self.confirm_iteration)
        self.next_btn.clicked.connect(self.next_test_case)
        self.prev_btn.clicked.connect(self.prev_test_case)
        self.notes_area.textChanged.connect(self.save_note)

    def load_initial_data(self):
        """Loads the initial data into the dashboard."""
        sheet_names = self.data_manager.get_sheet_names()
        if sheet_names:
            self.priority_combo.addItems(sheet_names)
            self.load_sheet_data(sheet_names[0])
        else:
            self.show_error_message("No sheets found in the Excel file.")

    def load_sheet_data(self, sheet_name):
        """Loads data from the selected sheet and updates the UI."""
        self.current_sheet = sheet_name
        self.current_test_case_index = 0
        self.display_test_case()
        self.update_results_table()

    def display_test_case(self):
        """Displays the current test case details."""
        if not self.current_sheet:
            return

        df = self.data_manager.get_sheet_data(self.current_sheet)
        if df is None or self.current_test_case_index >= len(df):
            return

        row = df.iloc[self.current_test_case_index]
        self.test_case_id_label.setText(f"ID: {row.get('Test Case ID', 'N/A')}")
        self.test_case_name_label.setText(f"Name: {row.get('Test Case Name', 'N/A')}")
        self.prereq_area.setText(str(row.get('Pre-requisites', '')))
        self.test_steps_area.setText(str(row.get('Test Steps', '')))
        self.n_points_label.setText(f"N-Points: {row.get('N-Points', 'N/A')}")
        self.notes_area.setText(str(row.get('Notes', '')))

        self.current_iteration = 0
        self.update_iteration_indicators()

    def toggle_timer(self):
        """Starts or stops the timer."""
        if self.is_timer_running:
            self.is_timer_running = False
            self.timer.stop()
        else:
            self.is_timer_running = True
            self.time_elapsed.setHMS(0, 0, 0, 0)
            self.timer.start(1)  # Update every millisecond

    def update_timer_display(self):
        """Updates the timer display label."""
        self.time_elapsed = self.time_elapsed.addMSecs(1)
        self.timer_display.setText(self.time_elapsed.toString("mm:ss.zzz"))

    def confirm_iteration(self):
        """Confirms the current iteration and saves the time."""
        if self.is_timer_running:
            self.toggle_timer()

        if self.current_iteration < 5:
            col_name = f"Iteration{self.current_iteration + 1}"
            time_str = self.timer_display.text()

            self.data_manager.update_cell(
                self.current_sheet, self.current_test_case_index, col_name, time_str
            )
            self.data_manager.save_data()

            self.current_iteration += 1
            self.update_iteration_indicators()
            self.update_results_table()

            if self.current_iteration == 5:
                self.calculate_average()
                self.next_test_case()

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
        for i, indicator in enumerate(self.iteration_indicators):
            if i < self.current_iteration:
                indicator.setStyleSheet("background-color: #2E8B57; border-radius: 10px;")
            else:
                indicator.setStyleSheet("background-color: #d3d3d3; border-radius: 10px;")

    def calculate_average(self):
        """Calculates and saves the average of the iterations."""
        df = self.data_manager.get_sheet_data(self.current_sheet)
        row = df.iloc[self.current_test_case_index]

        total_time = 0
        for i in range(1, 6):
            time_str = row.get(f"Iteration{i}", "00:00.000")
            if time_str and isinstance(time_str, str):
                parts = time_str.split(":")
                minutes = int(parts[0])
                seconds, ms = map(int, parts[1].split('.'))
                total_time += minutes * 60000 + seconds * 1000 + ms

        avg_time_ms = total_time / 5
        avg_time = QTime(0, 0).addMSecs(avg_time_ms)
        avg_str = avg_time.toString("mm:ss.zzz")

        self.data_manager.update_cell(
            self.current_sheet, self.current_test_case_index, "Average", avg_str
        )
        self.data_manager.save_data()
        self.update_results_table()

    def update_results_table(self):
        """Updates the results table with data from the current sheet."""
        df = self.data_manager.get_sheet_data(self.current_sheet)
        if df is None:
            return

        self.results_table.setRowCount(len(df))
        for i, row in df.iterrows():
            self.results_table.setItem(i, 0, QTableWidgetItem(str(row.get("Test Case Name", ""))))
            for j in range(1, 6):
                self.results_table.setItem(i, j, QTableWidgetItem(str(row.get(f"Iteration{j}", ""))))
            self.results_table.setItem(i, 6, QTableWidgetItem(str(row.get("Average", ""))))

    def save_note(self):
        """Saves the note for the current test case."""
        note_text = self.notes_area.toPlainText()
        self.data_manager.update_cell(
            self.current_sheet, self.current_test_case_index, "Notes", note_text
        )
        self.data_manager.save_data()

    def show_error_message(self, message):
        """Displays an error message in the widget."""
        error_label = QLabel(message)
        error_label.setAlignment(Qt.AlignCenter)
        error_label.setStyleSheet("color: red; font-size: 16px;")

        layout = QVBoxLayout(self)
        layout.addWidget(error_label)
        self.setLayout(layout)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    dashboard = ExecutionDashboard()
    dashboard.show()
    sys.exit(app.exec_())