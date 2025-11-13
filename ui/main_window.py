import sys
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QDockWidget,
    QListWidget,
    QStatusBar,
    QLineEdit,
)
from PyQt5.QtCore import Qt

from ui.sidebar import Sidebar
from ui.analyzer_widget import AnalyzerWidget
from ui.terminal_widget import TerminalWidget
from connections.manager import ConnectionManager
from logic.live_log_analyzer import LiveLogAnalyzer
from profiles.profile import Profile
from profiles.profile_manager import ProfileManager
from ui.ssh_connection_dialog import SshConnectionDialog
from ui.serial_connection_dialog import SerialConnectionDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kindle Log Analyzer - SSH/Serial")
        self.setGeometry(100, 100, 1200, 800)

        self.connection_manager = ConnectionManager()
        self.profile_manager = ProfileManager()

        self.setup_ui()
        self.apply_dark_theme()
        self.load_profiles()

    def setup_ui(self):
        # Central tab widget for terminal sessions
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.setCentralWidget(self.tab_widget)

        # Sidebar for connection management
        self.connection_sidebar = QDockWidget("Connections", self)
        self.sidebar = Sidebar()
        self.connection_sidebar.setWidget(self.sidebar)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.connection_sidebar)

        # Bottom panel for log analyzer output
        self.analyzer_panel = QDockWidget("Log Analyzer", self)
        self.analyzer_widget = AnalyzerWidget()
        self.analyzer_panel.setWidget(self.analyzer_widget)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.analyzer_panel)

        # Status bar
        self.setStatusBar(QStatusBar(self))
        self.statusBar().showMessage("Ready")

        # Connect sidebar buttons
        self.sidebar.ssh_button.clicked.connect(self.open_ssh_connection_dialog)
        self.sidebar.serial_button.clicked.connect(self.open_serial_connection_dialog)
        self.sidebar.profile_list.itemDoubleClicked.connect(self.load_profile)

        # Connect analyzer buttons
        self.analyzer_widget.clear_button.clicked.connect(self.analyzer_widget.analyzer_output.clear)

    def open_ssh_connection_dialog(self):
        dialog = SshConnectionDialog(self)
        if dialog.exec_():
            details = dialog.get_details()
            profile = Profile(
                name=details["name"],
                type="ssh",
                host=details["host"],
                port=details["port"],
                username=details["username"],
                password=details["password"] if details["auth_method"] == "Password" else None,
                private_key=details["private_key"] if details["auth_method"] == "Private Key" else None,
                auto_reconnect=details["auto_reconnect"],
            )
            self.profile_manager.add_profile(profile)
            self.load_profiles()
            self.start_connection(profile)

    def open_serial_connection_dialog(self):
        dialog = SerialConnectionDialog(self)
        if dialog.exec_():
            details = dialog.get_details()
            profile = Profile(
                name=details["name"],
                type="serial",
                port=details["port"],
                baudrate=details["baudrate"],
                parity=details["parity"],
                stop_bits=details["stop_bits"],
            )
            self.profile_manager.add_profile(profile)
            self.load_profiles()
            self.start_connection(profile)

    def start_connection(self, profile):
        worker = self.connection_manager.create_connection(profile)
        if worker:
            log_analyzer = LiveLogAnalyzer()
            terminal = self.add_terminal_tab(
                profile.name, self.connection_manager.connections[profile.name], log_analyzer
            )
            worker.data_received.connect(terminal.terminal_output.append)
            worker.data_received.connect(log_analyzer.process_data)
            log_analyzer.result_ready.connect(self.display_analysis_result)
            worker.connection_lost.connect(lambda: self.close_tab(self.tab_widget.indexOf(terminal)))
            worker.start()
            self.statusBar().showMessage(f"Connected to {profile.name}")
        else:
            self.statusBar().showMessage(f"Failed to connect to {profile.name}")

    def add_terminal_tab(self, name, connection, log_analyzer):
        terminal = TerminalWidget(name, connection, log_analyzer)
        terminal.disconnect_button.clicked.connect(lambda: self.close_tab(self.tab_widget.indexOf(terminal)))
        self.tab_widget.addTab(terminal, name)
        return terminal

    def close_tab(self, index):
        terminal = self.tab_widget.widget(index)
        if terminal:
            self.connection_manager.close_connection(terminal.name)
            self.tab_widget.removeTab(index)
            self.statusBar().showMessage(f"Disconnected from {terminal.name}")

    def display_analysis_result(self, result):
        self.analyzer_widget.analyzer_output.append(str(result))

    def load_profiles(self):
        self.sidebar.profile_list.clear()
        for profile in self.profile_manager.get_all_profiles():
            self.sidebar.profile_list.addItem(profile.name)

    def load_profile(self, item):
        profile = self.profile_manager.get_profile(item.text())
        if profile:
            self.start_connection(profile)

    def apply_dark_theme(self):
        self.setStyleSheet(
            """
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTabWidget::pane {
                border-top: 2px solid #C2C7CB;
            }
            QTabBar::tab {
                background: #2b2b2b;
                border: 2px solid #C2C7CB;
                border-bottom-color: #C2C7CB;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 8ex;
                padding: 2px;
                color: white;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #3c3c3c;
            }
            QDockWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QTextEdit {
                background-color: #1e1e1e;
                color: #dcdcdc;
                border: 1px solid #3c3c3c;
            }
            QListWidget {
                background-color: #2b2b2b;
                color: #ffffff;
                border: 1px solid #3c3c3c;
            }
            QStatusBar {
                background-color: #2b2b2b;
                color: #ffffff;
            }
        """
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())
