import sys
import requests
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QLineEdit, QPushButton, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon
from config import SERVER_URL, REQUEST_TIMEOUT, APP_NAME

class LoginWindow(QWidget):
    """
    Login window for user authentication.
    Validates credentials against server before app access.
    """
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success  # Callback with (username, role, full_name)
        self.server_url = SERVER_URL
        self.init_ui()
    
    def init_ui(self):
        """Initialize the login UI."""
        self.setWindowTitle(f"{APP_NAME} - Login")
        self.setGeometry(100, 100, 500, 350)
        self.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
            }
            QLabel#titleLabel {
                font-size: 24px;
                font-weight: bold;
                color: #2c3e50;
                padding: 20px;
            }
            QLabel#subtitleLabel {
                font-size: 14px;
                color: #7f8c8d;
                padding-bottom: 10px;
            }
            QLineEdit {
                padding: 12px;
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                font-size: 14px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
            QPushButton {
                padding: 12px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
            QLabel#errorLabel {
                color: #e74c3c;
                font-size: 12px;
                padding: 5px;
            }
            QFrame#loginFrame {
                background-color: white;
                border-radius: 10px;
                padding: 30px;
            }
        """)
        
        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        
        # Login frame (white box)
        login_frame = QFrame()
        login_frame.setObjectName("loginFrame")
        login_frame.setMaximumWidth(400)
        frame_layout = QVBoxLayout(login_frame)
        
        # Title
        title_label = QLabel("🔐 Login")
        title_label.setObjectName("titleLabel")
        title_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Enter your credentials to continue")
        subtitle_label.setObjectName("subtitleLabel")
        subtitle_label.setAlignment(Qt.AlignCenter)
        frame_layout.addWidget(subtitle_label)
        
        # Spacing
        frame_layout.addSpacing(20)
        
        # Username field
        username_label = QLabel("Username:")
        username_label.setFont(QFont("Arial", 11, QFont.Bold))
        username_label.setStyleSheet("color: #2c3e50;")  # Dark color for visibility
        frame_layout.addWidget(username_label)
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter your username")
        self.username_input.setStyleSheet("""
            QLineEdit {
                color: #2c3e50;
            }
            QLineEdit::placeholder {
                color: #7f8c8d;
            }
        """)
        self.username_input.returnPressed.connect(self.focus_password)  # Enter moves to password
        frame_layout.addWidget(self.username_input)
        
        frame_layout.addSpacing(15)
        
        # Password field
        password_label = QLabel("Password:")
        password_label.setFont(QFont("Arial", 11, QFont.Bold))
        password_label.setStyleSheet("color: #2c3e50;")  # Dark color for visibility
        frame_layout.addWidget(password_label)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setEchoMode(QLineEdit.Password)  # Mask password
        self.password_input.setStyleSheet("""
            QLineEdit {
                color: #2c3e50;
            }
            QLineEdit::placeholder {
                color: #7f8c8d;
            }
        """)
        self.password_input.returnPressed.connect(self.login)  # Enter triggers login
        frame_layout.addWidget(self.password_input)
        
        frame_layout.addSpacing(10)
        
        # Error message label
        self.error_label = QLabel("")
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        frame_layout.addWidget(self.error_label)
        
        frame_layout.addSpacing(10)
        
        # Login button
        self.login_btn = QPushButton("Login")
        self.login_btn.clicked.connect(self.login)
        self.login_btn.setCursor(Qt.PointingHandCursor)
        frame_layout.addWidget(self.login_btn)
        
        # Add login frame to main layout
        main_layout.addWidget(login_frame)
        
        # Footer
        footer_label = QLabel("Please contact your administrator if you need password help.")
        footer_label.setStyleSheet("color: #95a5a6; font-size: 11px; padding: 10px;")
        footer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(footer_label)
        
        self.setLayout(main_layout)
        
        # Set focus to username field
        self.username_input.setFocus()
    
    def focus_password(self):
        """Move focus to password field."""
        self.password_input.setFocus()
    
    def login(self):
        """Authenticate user with server."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        # Validate input
        if not username:
            self.show_error("Please enter your username")
            return
        
        if not password:
            self.show_error("Please enter your password")
            return
        
        # Clear previous error
        self.error_label.setText("")
        
        # Disable button while processing
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logging in...")
        
        try:
            # Send login request to server
            response = requests.post(
                f"{self.server_url}/login",
                json={"username": username, "password": password},
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code == 200:
                data = response.json()
                # Extract token and user info
                access_token = data.get("access_token")
                username = data.get("username")
                role = data.get("role")
                full_name = data.get("full_name")
                
                if access_token and username and role and full_name:
                    QMessageBox.information(self, "Success", f"Welcome back, {full_name}!")
                    self.on_login_success(username, role, full_name, access_token)
                    self.close()
                else:
                    self.show_error(data.get("message", "Login failed: Incomplete server response."))
            else:
                error_msg = response.json().get("detail", "Login failed")
                QMessageBox.warning(self, "Login Failed", error_msg)
                self.show_error(error_msg) # Also update the internal error label
        
        except requests.exceptions.ConnectionError:
            self.show_error("Cannot connect to server. Please ensure server is running.")
        except requests.exceptions.Timeout:
            self.show_error("Connection timeout. Please try again.")
        except Exception as e:
            self.show_error(f"Error: {str(e)}")
        
        finally:
            # Re-enable button
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Login")
    
    def show_error(self, message):
        """Display error message."""
        self.error_label.setText(f"⚠ {message}")
