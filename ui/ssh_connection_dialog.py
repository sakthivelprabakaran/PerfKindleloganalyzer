from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QCheckBox,
)


class SshConnectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SSH Connection Details")
        self.layout = QVBoxLayout(self)

        # Name
        self.name_layout = QHBoxLayout()
        self.name_label = QLabel("Name:")
        self.name_input = QLineEdit()
        self.name_layout.addWidget(self.name_label)
        self.name_layout.addWidget(self.name_input)
        self.layout.addLayout(self.name_layout)

        # Host
        self.host_layout = QHBoxLayout()
        self.host_label = QLabel("Host:")
        self.host_input = QLineEdit()
        self.host_layout.addWidget(self.host_label)
        self.host_layout.addWidget(self.host_input)
        self.layout.addLayout(self.host_layout)

        # Port
        self.port_layout = QHBoxLayout()
        self.port_label = QLabel("Port:")
        self.port_input = QLineEdit("22")
        self.port_layout.addWidget(self.port_label)
        self.port_layout.addWidget(self.port_input)
        self.layout.addLayout(self.port_layout)

        # Username
        self.username_layout = QHBoxLayout()
        self.username_label = QLabel("Username:")
        self.username_input = QLineEdit()
        self.username_layout.addWidget(self.username_label)
        self.username_layout.addWidget(self.username_input)
        self.layout.addLayout(self.username_layout)

        # Authentication method
        self.auth_method_layout = QHBoxLayout()
        self.auth_method_label = QLabel("Auth Method:")
        self.auth_method_combo = QComboBox()
        self.auth_method_combo.addItems(["Password", "Private Key"])
        self.auth_method_combo.currentTextChanged.connect(self.update_auth_fields)
        self.auth_method_layout.addWidget(self.auth_method_label)
        self.auth_method_layout.addWidget(self.auth_method_combo)
        self.layout.addLayout(self.auth_method_layout)

        # Password
        self.password_layout = QHBoxLayout()
        self.password_label = QLabel("Password:")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_layout.addWidget(self.password_label)
        self.password_layout.addWidget(self.password_input)
        self.layout.addLayout(self.password_layout)

        # Private key
        self.private_key_layout = QHBoxLayout()
        self.private_key_label = QLabel("Private Key:")
        self.private_key_input = QLineEdit()
        self.private_key_button = QPushButton("Browse...")
        self.private_key_button.clicked.connect(self.browse_private_key)
        self.private_key_layout.addWidget(self.private_key_label)
        self.private_key_layout.addWidget(self.private_key_input)
        self.private_key_layout.addWidget(self.private_key_button)
        self.layout.addLayout(self.private_key_layout)

        # Auto-reconnect
        self.auto_reconnect_checkbox = QCheckBox("Auto-reconnect")
        self.layout.addWidget(self.auto_reconnect_checkbox)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        self.button_layout.addWidget(self.ok_button)
        self.button_layout.addWidget(self.cancel_button)
        self.layout.addLayout(self.button_layout)

        self.update_auth_fields(self.auth_method_combo.currentText())

    def update_auth_fields(self, method):
        if method == "Password":
            self.password_label.setVisible(True)
            self.password_input.setVisible(True)
            self.private_key_label.setVisible(False)
            self.private_key_input.setVisible(False)
            self.private_key_button.setVisible(False)
        else:
            self.password_label.setVisible(False)
            self.password_input.setVisible(False)
            self.private_key_label.setVisible(True)
            self.private_key_input.setVisible(True)
            self.private_key_button.setVisible(True)

    def browse_private_key(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Select Private Key")
        if filename:
            self.private_key_input.setText(filename)

    def get_details(self):
        return {
            "name": self.name_input.text(),
            "host": self.host_input.text(),
            "port": int(self.port_input.text()),
            "username": self.username_input.text(),
            "auth_method": self.auth_method_combo.currentText(),
            "password": self.password_input.text(),
            "private_key": self.private_key_input.text(),
            "auto_reconnect": self.auto_reconnect_checkbox.isChecked(),
        }
