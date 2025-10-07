import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PyQt5.QtGui import QFont

from ui.universal_launcher import UniversalLauncher
from ui.main_window import FinalKindleLogAnalyzer
from performance_dashboard.main_window import MainWindow as PerformanceDashboard

class ApplicationContainer(QMainWindow):
    """
    The main container that holds and manages all applications (screens).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kindle Test Engineering Tools")
        self.setGeometry(50, 50, 1600, 1000)

        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # Instantiate all the applications/screens
        self.universal_launcher = UniversalLauncher(
            self.launch_log_analyzer,
            self.launch_exec_dashboard
        )
        self.log_analyzer = FinalKindleLogAnalyzer(back_to_launcher_callback=self.back_to_launcher)
        self.exec_dashboard = PerformanceDashboard(back_to_launcher_callback=self.back_to_launcher)

        # Add them to the stack
        self.stacked_widget.addWidget(self.universal_launcher)
        self.stacked_widget.addWidget(self.log_analyzer)
        self.stacked_widget.addWidget(self.exec_dashboard)

        # Set the initial screen
        self.stacked_widget.setCurrentWidget(self.universal_launcher)

    def launch_log_analyzer(self):
        """Switches the view to the Kindle Log Analyzer."""
        self.setWindowTitle("Final Kindle Log Analyzer")
        self.stacked_widget.setCurrentWidget(self.log_analyzer)

    def launch_exec_dashboard(self):
        """Switches the view to the Performance Execution Dashboard."""
        self.setWindowTitle("Performance Execution Dashboard")
        self.stacked_widget.setCurrentWidget(self.exec_dashboard)

    def back_to_launcher(self):
        """Switches the view back to the universal launcher."""
        self.setWindowTitle("Kindle Test Engineering Tools")
        self.stacked_widget.setCurrentWidget(self.universal_launcher)

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont("Arial", 10)
    app.setFont(font)

    container = ApplicationContainer()
    container.show()

    sys.exit(app.exec_())