import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ui.main_window import FinalKindleLogAnalyzer

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set application-wide font - use a cross-platform font
    font = QFont("Arial", 10)
    app.setFont(font)

    window = FinalKindleLogAnalyzer()
    window.show()

    sys.exit(app.exec_())