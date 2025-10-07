import sys
import os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QIcon
from ui.main_window import FinalKindleLogAnalyzer

def set_app_icon(app):
    """Sets the application icon based on the operating system."""
    icon_path = ""
    if sys.platform == "darwin":  # macOS
        icon_path = os.path.join("assets", "icons", "Mac.icns")
    elif sys.platform == "win32":  # Windows
        icon_path = os.path.join("assets", "icons", "win.ico")

    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

if __name__ == '__main__':
    app = QApplication(sys.argv)

    set_app_icon(app)

    # Set application-wide font - use a cross-platform font
    font = QFont("Arial", 10)
    app.setFont(font)

    window = FinalKindleLogAnalyzer()
    window.show()

    sys.exit(app.exec_())