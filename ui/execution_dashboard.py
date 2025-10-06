import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QTableWidget, QTabWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer, QTime
from PyQt5.QtGui import QFont

from logic.data_manager import DataManager

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
        """Creates the tab for displaying test case details."""
        details_tab = QWidget()
        layout = QVBoxLayout(details_tab)

        self.test_case_id_label = QLabel("ID: N/A")
        self.test_case_name_label = QLabel("Name: N/A")
        self.n_points_label = QLabel("N-Points: N/A")

        layout.addWidget(self.test_case_id_label)
        layout.addWidget(self.test_case_name_label)

        self.prereq_area = QTextEdit()
        self.prereq_area.setReadOnly(True)
        self.prereq_area.setPlaceholderText("Pre-requisites...")

        self.test_steps_area = QTextEdit()
        self.test_steps_area.setReadOnly(True)
        self.test_steps_area.setPlaceholderText("Test Steps...")

        layout.addWidget(QLabel("Pre-requisites:"))
        layout.addWidget(self.prereq_area)
        layout.addWidget(QLabel("Test Steps:"))
        layout.addWidget(self.test_steps_area)
        layout.addWidget(self.n_points_label)

        return details_tab

    def create_results_tab(self):
        """Creates the tab for displaying results."""
        results_tab = QWidget()
        layout = QVBoxLayout(results_tab)
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(7)
        self.results_table.setHorizontalHeaderLabels([
            "Test Case Name", "Iteration1", "Iteration2", "Iteration3",
            "Iteration4", "Iteration5", "Average"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)
        return results_tab

if __name__ == '__main__':
    # This is for testing purposes only
    app = QApplication(sys.argv)
    # The dashboard now expects to be managed by the main window
    # but we can create a dummy version for testing.
    class TestWindow(QWidget):
        def __init__(self):
            super().__init__()
            layout = QHBoxLayout(self)
            layout.addWidget(ExecutionDashboard())
            self.setWindowTitle("Test Execution Dashboard Panel")
            self.show()

    win = TestWindow()
    sys.exit(app.exec_())