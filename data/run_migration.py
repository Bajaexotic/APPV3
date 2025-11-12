#!/usr/bin/env python3
"""
Database migration runner - adds missing efficiency column.

Run this script to update your database schema:
    python data/run_migration.py
"""

from pathlib import Path
from data.db_engine import engine
from sqlalchemy import text

def run_migration():
    """Run the efficiency column migration."""
    migration_file = Path(__file__).parent / "migrations" / "add_efficiency_column.sql"

    print(f"[MIGRATION] Reading migration from: {migration_file}")

    if not migration_file.exists():
        print(f"[MIGRATION] ERROR: Migration file not found: {migration_file}")
        return False

    sql = migration_file.read_text()
    print(f"[MIGRATION] Executing SQL migration...")

    try:
        with engine.connect() as conn:
            # Execute the migration
            conn.execute(text(sql))
            conn.commit()
            print(f"[MIGRATION] ✓ Successfully added 'efficiency' column to traderecord table")
            return True
    except Exception as e:
        print(f"[MIGRATION] ERROR: {e}")
        # If column already exists, that's OK
        if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
            print(f"[MIGRATION] Column already exists, migration skipped")
            return True
        return False

if __name__ == "__main__":
    print("\n" + "="*80)
    print("DATABASE MIGRATION: Add efficiency column")
    print("="*80 + "\n")

    success = run_migration()

    if success:
        print("\n✓ Migration completed successfully!")
        print("You can now start the app.\n")
    else:
        print("\n✗ Migration failed!")
        print("Please check the error above and try again.\n")
