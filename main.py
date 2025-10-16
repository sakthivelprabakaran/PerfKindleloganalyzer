import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QAction
from PyQt5.QtGui import QFont, QIcon

from ui.main_window import FinalKindleLogAnalyzer
from performance_dashboard.main_window import MainWindow as PerformanceDashboard
from utils.notification_manager import NotificationManager

class ApplicationContainer(QMainWindow):
    """
    The main container that holds and manages all applications (screens).
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kindle Test Engineering Tools")
        self.setGeometry(50, 50, 1600, 1000)

        self.set_app_icon()
        self.dark_mode = False

        # Create the tab widget
        self.tab_widget = QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Create the notification manager
        self.notification_manager = NotificationManager(self)

        # Instantiate the tools
        self.log_analyzer = FinalKindleLogAnalyzer(notification_manager=self.notification_manager)
        self.exec_dashboard = PerformanceDashboard(notification_manager=self.notification_manager)

        # Add tools as tabs
        self.tab_widget.addTab(self.log_analyzer, "Kindle Log Analyzer")
        self.tab_widget.addTab(self.exec_dashboard, "Performance Dashboard")

        # Create the menu bar
        self.create_menu_bar()

        # Load the initial stylesheet
        self.load_stylesheet()

    def create_menu_bar(self):
        """Creates the main menu bar for the application."""
        menu_bar = self.menuBar()
        view_menu = menu_bar.addMenu("View")

        # Dark mode toggle action
        dark_mode_action = QAction("Dark Mode", self, checkable=True)
        dark_mode_action.triggered.connect(self.toggle_dark_mode)
        view_menu.addAction(dark_mode_action)

    def toggle_dark_mode(self, checked):
        """Toggles the application's theme."""
        self.dark_mode = checked
        self.load_stylesheet()

    def load_stylesheet(self):
        """Loads the appropriate stylesheet based on the theme."""
        theme = "dark" if self.dark_mode else "light"
        stylesheet_path = os.path.join("assets", "stylesheets", f"{theme}_mode.qss")
        if os.path.exists(stylesheet_path):
            with open(stylesheet_path, "r") as f:
                self.setStyleSheet(f.read())

    def set_app_icon(self):
        """Sets the application icon based on the operating system."""
        icon_path = ""
        if sys.platform == "darwin":  # macOS
            icon_path = os.path.join("assets", "icons", "Mac.icns")
        elif sys.platform == "win32":  # Windows
            icon_path = os.path.join("assets", "icons", "win.ico")

        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application-wide font
    font = QFont("Arial", 10)
    app.setFont(font)

    container = ApplicationContainer()
    container.show()

    sys.exit(app.exec_())