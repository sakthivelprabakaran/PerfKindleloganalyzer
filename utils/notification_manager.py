from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import QTimer, Qt, QPropertyAnimation, QRect
from PyQt5.QtGui import QFont

class NotificationManager(QLabel):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QLabel {
                color: white;
                background-color: rgba(0, 0, 0, 180);
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        self.hide()

    def show_message(self, message, level="info"):
        self.setText(message)
        if level == "success":
            self.setStyleSheet("QLabel { color: white; background-color: rgba(0, 128, 0, 180); border-radius: 5px; padding: 10px; font-size: 14px; }")
        elif level == "warning":
            self.setStyleSheet("QLabel { color: white; background-color: rgba(255, 165, 0, 180); border-radius: 5px; padding: 10px; font-size: 14px; }")
        else: # info
            self.setStyleSheet("QLabel { color: white; background-color: rgba(0, 0, 0, 180); border-radius: 5px; padding: 10px; font-size: 14px; }")

        self.adjustSize()
        parent_rect = self.parent().geometry()
        self.move(
            parent_rect.x() + (parent_rect.width() - self.width()) // 2,
            parent_rect.y() + parent_rect.height() - self.height() - 20
        )
        self.show()
        QTimer.singleShot(3000, self.hide)