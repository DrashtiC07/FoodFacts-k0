#!/usr/bin/env python
"""
Script to reset migration conflicts and fix database state
Run this script to resolve the migration conflicts
"""

import os
import sys
import django
from django.conf import settings
from django.core.management import execute_from_command_line
from django.db import connection

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodfacts.settings')
django.setup()

def reset_migration_state():
    """Reset the migration state to fix conflicts"""
    
    print("Fixing migration conflicts...")
    
    # Mark problematic migrations as applied without running them
    with connection.cursor() as cursor:
        try:
            # Check if the migration table exists
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='django_migrations';
            """)
            
            if cursor.fetchone():
                # Mark the conflicting migrations as applied
                cursor.execute("""
                    INSERT OR IGNORE INTO django_migrations (app, name, applied) 
                    VALUES ('accounts', '0003_add_dietary_goal_fields', datetime('now'));
                """)
                
                cursor.execute("""
                    INSERT OR IGNORE INTO django_migrations (app, name, applied) 
                    VALUES ('accounts', '0004_create_nutrition_tracking_models', datetime('now'));
                """)
                
                cursor.execute("""
                    INSERT OR IGNORE INTO django_migrations (app, name, applied) 
                    VALUES ('accounts', '0005_merge_20250817_1158', datetime('now'));
                """)
                
                print("✓ Migration state updated successfully")
            else:
                print("Django migrations table not found")
                
        except Exception as e:
            print(f"Error updating migration state: {e}")

def check_tables():
    """Check which tables exist"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name LIKE 'accounts_%';
        """)
        tables = cursor.fetchall()
        print("Existing accounts tables:")
        for table in tables:
            print(f"  - {table[0]}")

if __name__ == '__main__':
    print("=== Migration Conflict Resolver ===")
    check_tables()
    reset_migration_state()
    print("\nNow run: python manage.py migrate")
    print("This should complete without errors.")
