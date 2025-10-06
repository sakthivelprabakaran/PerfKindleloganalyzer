import sys
from PyQt5.QtWidgets import QApplication
from performance_dashboard.main_window import MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # Set a default font if desired
    # from PyQt5.QtGui import QFont
    # font = QFont("Arial", 10)
    # app.setFont(font)

    main_win = MainWindow()
    main_win.show()

    sys.exit(app.exec_())