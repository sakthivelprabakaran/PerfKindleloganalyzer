#!/usr/bin/env python3
"""
Simple script to reset the database by deleting the SQLite file.
WARNING: This will delete ALL data!
"""
import os

db_file = "live_audit.db"

if os.path.exists(db_file):
    print(f"🗑️  Deleting {db_file}...")
    os.remove(db_file)
    print("✅ Database deleted. Restart the server to create a fresh database with the new schema.")
else:
    print(f"⚠️  Database file '{db_file}' not found.")
