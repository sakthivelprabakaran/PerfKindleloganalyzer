from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, QHBoxLayout, QFileDialog


class TerminalWidget(QWidget):
    def __init__(self, name, connection, log_analyzer):
        super().__init__()
        self.name = name
        self.connection = connection
        self.log_analyzer = log_analyzer
        self.layout = QVBoxLayout(self)

        # Terminal output
        self.terminal_output = QTextEdit()
        self.terminal_output.setReadOnly(True)
        self.layout.addWidget(self.terminal_output)

        # Command input
        self.command_input = QLineEdit()
        self.command_input.returnPressed.connect(self.send_command)
        self.layout.addWidget(self.command_input)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.start_button = QPushButton("Start Logging")
        self.start_button.clicked.connect(self.log_analyzer.start)
        self.stop_button = QPushButton("Stop Logging")
        self.stop_button.clicked.connect(self.log_analyzer.stop)
        self.export_button = QPushButton("Export Log")
        self.export_button.clicked.connect(self.export_log)
        self.disconnect_button = QPushButton("Disconnect")
        self.button_layout.addWidget(self.start_button)
        self.button_layout.addWidget(self.stop_button)
        self.button_layout.addWidget(self.export_button)
        self.button_layout.addWidget(self.disconnect_button)
        self.layout.addLayout(self.button_layout)

        self.setLayout(self.layout)

    def send_command(self):
        command = self.command_input.text()
        if command:
            self.connection.write(command.encode("utf-8") + b"\n")
            self.command_input.clear()

    def disconnect(self):
        self.connection.disconnect()

    def export_log(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Log", f"{self.name}.log", "Log Files (*.log)")
        if filename:
            with open(filename, "w") as f:
                f.write(self.terminal_output.toPlainText())
