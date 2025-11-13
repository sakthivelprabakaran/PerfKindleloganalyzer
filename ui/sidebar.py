from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QListWidget, QGroupBox


class Sidebar(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        # Connection buttons
        self.connection_group = QGroupBox("New Connection")
        self.connection_layout = QVBoxLayout()
        self.ssh_button = QPushButton("New SSH Connection")
        self.serial_button = QPushButton("New Serial Connection")
        self.connection_layout.addWidget(self.ssh_button)
        self.connection_layout.addWidget(self.serial_button)
        self.connection_group.setLayout(self.connection_layout)
        self.layout.addWidget(self.connection_group)

        # Saved profiles
        self.profiles_group = QGroupBox("Saved Profiles")
        self.profiles_layout = QVBoxLayout()
        self.profile_list = QListWidget()
        self.profiles_layout.addWidget(self.profile_list)
        self.profiles_group.setLayout(self.profiles_layout)
        self.layout.addWidget(self.profiles_group)

        self.setLayout(self.layout)
