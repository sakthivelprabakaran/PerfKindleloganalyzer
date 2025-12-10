#!/usr/bin/env python3
"""
Test Suite for Centralized Configuration Integration
Verifies that config.py is correctly loaded and used.
"""

import sys
import os
import unittest

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    SERVER_URL, SERVER_PORT, SERVER_IP,
    APP_NAME, DEFAULT_PASSWORD,
    REQUEST_TIMEOUT, POLL_INTERVAL_MS,
    DB_NAME, DB_BACKUP_DIR
)

class TestConfigIntegration(unittest.TestCase):
    
    def test_server_config(self):
        """Test server configuration values."""
        print(f"\nTesting Server Config...")
        self.assertEqual(SERVER_IP, "localhost")
        self.assertEqual(SERVER_PORT, 8000)
        self.assertEqual(SERVER_URL, "http://localhost:8000")
        print(f"✓ Server URL: {SERVER_URL}")

    def test_app_config(self):
        """Test application settings."""
        print(f"\nTesting App Config...")
        self.assertEqual(APP_NAME, "Kindle Test Engineering Tools")
        self.assertEqual(DEFAULT_PASSWORD, "ChangeMe123!")
        print(f"✓ App Name: {APP_NAME}")

    def test_network_config(self):
        """Test network settings."""
        print(f"\nTesting Network Config...")
        self.assertEqual(REQUEST_TIMEOUT, 10)
        self.assertEqual(POLL_INTERVAL_MS, 2000)
        print(f"✓ Timeout: {REQUEST_TIMEOUT}s")

    def test_database_config(self):
        """Test database settings."""
        print(f"\nTesting Database Config...")
        self.assertEqual(DB_NAME, "live_audit.db")
        self.assertEqual(DB_BACKUP_DIR, "backups")
        print(f"✓ DB Name: {DB_NAME}")

    def test_file_paths(self):
        """Test that critical paths exist."""
        print(f"\nTesting File Paths...")
        from config import BASE_DIR, ASSETS_DIR, ICONS_DIR
        
        self.assertTrue(os.path.exists(BASE_DIR), "Base directory should exist")
        self.assertTrue(os.path.exists(ASSETS_DIR), "Assets directory should exist")
        self.assertTrue(os.path.exists(ICONS_DIR), "Icons directory should exist")
        print(f"✓ Base Dir: {BASE_DIR}")

if __name__ == '__main__':
    unittest.main(verbosity=2)
