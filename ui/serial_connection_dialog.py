from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
)


class SerialConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Serial Connection Details")
        self.layout = QVBoxLayout(self)

        # Name
        self.name_layout = QHBoxLayout()
        self.name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_input)
        self.layout.addLayout(self.name_layout)

        # Port
        self.port_layout = QHBoxLayout()
        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit()
        self.port_layout.addWidget(self.port_label)
        self.port_layout.addWidget(self.port_input)
        self.layout.addLayout(self.port_layout)

        # Baudrate
        self.baudrate_layout = QHBoxLayout()
        self.baudrate_label = QLabel("Baudrate:")
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(["9600", "115200", "57600"])
        self.baudrate_layout.addWidget(self.baudrate_label)
        self.baudrate_layout.addWidget(self.baudrate_combo)
        self.layout.addLayout(self.baudrate_layout)

        # Parity
        self.parity_layout = QHBoxLayout()
        self.parity_label = QLabel("Parity:")
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None", "Even", "Odd"])
        self.parity_layout.addWidget(self.parity_label)
        self.parity_layout.addWidget(self.parity_combo)
        self.layout.addLayout(self.parity_layout)

        # Stop bits
        self.stop_bits_layout = QHBoxLayout()
        self.stop_bits_label = QLabel("Stop Bits:")
        self.stop_bits_combo = QComboBox()
        self.stop_bits_combo.addItems(["1", "1.5", "2"])
        self.stop_bits_layout.addWidget(self.stop_bits_label)
        self.stop_bits_layout.addWidget(self.stop_bits_combo)
        self.layout.addLayout(self.stop_bits_layout)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

    def get_details(self):
        return {
            "name": self.name_input.text(),
            "port": self.port_input.text(),
            "baudrate": int(self.baudrate_combo.currentText()),
            "parity": self.parity_combo.currentText(),
            "stop_bits": self.stop_bits_combo.currentText(),
        }
