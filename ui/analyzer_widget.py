from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QFileDialog


class AnalyzerWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QVBoxLayout(self)

        # Analyzer output
        self.analyzer_output = QTextEdit()
        self.analyzer_output.setReadOnly(True)
        self.layout.addWidget(self.analyzer_output)

        # Buttons
        self.button_layout = QHBoxLayout()
        self.clear_button = QPushButton("Clear")
        self.export_button = QPushButton("Export Results")
        self.export_button.clicked.connect(self.export_results)
        self.button_layout.addWidget(self.clear_button)
        self.button_layout.addWidget(self.export_button)
        self.layout.addLayout(self.button_layout)

        self.setLayout(self.layout)

    def export_results(self):
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Results", "analyzer_results.txt", "Text Files (*.txt)"
        )
        if filename:
            with open(filename, "w") as f:
                f.write(self.analyzer_output.toPlainText())
