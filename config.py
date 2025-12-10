import os
import sys

# --- Server Configuration ---
# Change SERVER_IP to the actual IP address when deploying (e.g., "192.168.1.50")
SERVER_IP = "127.0.0.1"
SERVER_PORT = 8000
SERVER_URL = f"http://{SERVER_IP}:{SERVER_PORT}"

# --- Application Settings ---
APP_NAME = "Kindle Test Engineering Tools"
APP_VERSION = "1.0.0"
DEFAULT_PASSWORD = "ChangeMe123!"
DARK_MODE_DEFAULT = False

# --- File Paths ---
# Base directory of the application
if getattr(sys, 'frozen', False):
    # If running as compiled executable
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # If running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(BASE_DIR, "assets")
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")

# Platform-specific icon paths
if sys.platform == "darwin":
    APP_ICON_PATH = os.path.join(ICONS_DIR, "Mac.icns")
elif sys.platform == "win32":
    APP_ICON_PATH = os.path.join(ICONS_DIR, "win.ico")
else:
    APP_ICON_PATH = os.path.join(ICONS_DIR, "win.ico")

# --- Network Settings ---
REQUEST_TIMEOUT = 10  # Seconds
POLL_INTERVAL_MS = 2000  # Milliseconds

# --- Database Settings ---
DB_NAME = "live_audit.db"
DB_BACKUP_DIR = "backups"
DB_BACKUP_RETENTION = 30  # Keep last 30 backups

# --- Security Settings ---
SECRET_KEY = "super-secret-key-change-this-in-production"  # In prod, load from env var
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours
