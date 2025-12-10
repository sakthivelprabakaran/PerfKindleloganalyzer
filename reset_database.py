#!/usr/bin/env python
"""
Database Reset Script
Clears all test data while preserving database structure and default admin.
"""
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "live_audit_server/live_audit.db"
BACKUP_DIR = "live_audit_server/backups"

def reset_database():
    """Delete the database file to start fresh."""
    print("=" * 60)
    print("DATABASE RESET TOOL")
    print("=" * 60)
    print("\nThis will DELETE all data including:")
    print("  - All users (except default admin)")
    print("  - All projects")
    print("  - All task assignments")
    print("  - All test results")
    print("  - All BRD uploads")
    print("\n⚠️  WARNING: This action cannot be undone!")
    print("\nThe default admin account will be recreated:")
    print("  Username: admin")
    print("  Password: (from config.py DEFAULT_PASSWORD)")
    
    response = input("\nAre you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        print("\n❌ Reset cancelled.")
        return
    
    # Check if database exists
    if not os.path.exists(DB_PATH):
        print(f"\n✓ No database found at {DB_PATH}")
        print("  A fresh database will be created when you start the server.")
        return
    
    # Delete the database
    try:
        os.remove(DB_PATH)
        print(f"\n✅ Database deleted: {DB_PATH}")
        print("\n✓ Reset complete!")
        print("\nNext steps:")
        print("1. Start the server: python live_audit_server/server.py")
        print("2. The server will create a fresh database with default admin")
        print("3. Login with username 'admin' and password from config.py")
        
    except Exception as e:
        print(f"\n❌ Error deleting database: {e}")
        return

if __name__ == "__main__":
    reset_database()
