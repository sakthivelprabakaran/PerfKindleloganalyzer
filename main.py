import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ui.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application-wide font - use a cross-platform font
    font = QFont("Arial", 10)
    app.setFont(font)

    try:
        window = MainWindow()
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"An error occurred: {e}")
        sys.exit(1)
