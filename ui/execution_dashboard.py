import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QTableWidget, QTabWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QGroupBox
)
from PyQt5.QtCore import Qt

class ExecutionDashboard(QWidget):
    """The right-hand panel of the Execution Dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        """Sets up the UI of the widget."""
        layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        # Test Case Details Tab
        details_tab = self.create_details_tab()
        self.tab_widget.addTab(details_tab, "Test Case Details")

        # Results Tab
        results_tab = self.create_results_tab()
        self.tab_widget.addTab(results_tab, "Results")

        layout.addWidget(self.tab_widget)

    def create_details_tab(self):
        """Creates the tab for displaying test case details with a dynamic layout."""
        details_tab = QWidget()
        main_layout = QVBoxLayout(details_tab)

        # Use a scroll area to handle potentially long content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        main_layout.addWidget(scroll_area)

        content_widget = QWidget()
        scroll_area.setWidget(content_widget)
        layout = QVBoxLayout(content_widget)

        # --- Test Case Info ---
        info_group = QGroupBox("Test Case Information")
        info_layout = QVBoxLayout(info_group)
        self.test_case_id_label = QLabel("<b>ID:</b> N/A")
        self.test_case_name_label = QLabel("<b>Name:</b> N/A")
        self.n_points_label = QLabel("<b>N-Points:</b> N/A")
        info_layout.addWidget(self.test_case_id_label)
        info_layout.addWidget(self.test_case_name_label)
        info_layout.addWidget(self.n_points_label)
        layout.addWidget(info_group)

        # --- Pre-requisites ---
        prereq_group = QGroupBox("Pre-requisites")
        prereq_layout = QVBoxLayout(prereq_group)
        self.prereq_area = QLabel("N/A")
        self.prereq_area.setWordWrap(True)
        self.prereq_area.setTextInteractionFlags(Qt.TextSelectableByMouse)
        prereq_layout.addWidget(self.prereq_area)
        layout.addWidget(prereq_group)

        # --- Test Steps ---
        steps_group = QGroupBox("Test Steps")
        steps_layout = QVBoxLayout(steps_group)
        self.test_steps_area = QLabel("N/A")
        self.test_steps_area.setWordWrap(True)
        self.test_steps_area.setTextInteractionFlags(Qt.TextSelectableByMouse)
        steps_layout.addWidget(self.test_steps_area)
        layout.addWidget(steps_group)

        layout.addStretch()  # Push everything to the top

        return details_tab

    def create_results_tab(self):
        """Creates the tab for displaying results."""
        results_tab = QWidget()
        layout = QVBoxLayout(results_tab)
        self.results_table = QTableWidget()
        # Columns will be set dynamically when data is loaded
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)
        return results_tab

if __name__ == '__main__':
    # This is for testing purposes only
    app = QApplication(sys.argv)
    class TestWindow(QWidget):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Test Execution Dashboard Panel")
            layout = QVBoxLayout(self)
            dashboard = ExecutionDashboard()
            # Example of setting long text to demonstrate dynamic layout
            dashboard.test_case_id_label.setText("<b>ID:</b> P0-TC1")
            dashboard.test_case_name_label.setText("<b>Name:</b> This is a very long test case name to see how the UI handles it wrapping around.")
            dashboard.prereq_area.setText("This is a very long pre-requisite that should wrap multiple lines. " * 5)
            dashboard.test_steps_area.setText("1. Do the first thing.\n2. Do the second thing which is also very long and should wrap properly.\n" * 3)
            layout.addWidget(dashboard)
            self.resize(800, 600)
            self.show()
    win = TestWindow()
    sys.exit(app.exec_())