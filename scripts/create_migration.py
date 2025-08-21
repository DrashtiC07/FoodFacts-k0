"""
Django migration script to remove unique_together constraint from PersonalizedTip model
Run this script to generate the migration file
"""

import os
import sys
import django
from django.conf import settings
from django.core.management import execute_from_command_line

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_dir)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodfacts.settings')
django.setup()

# Generate migration
print("Generating migration to remove PersonalizedTip unique constraint...")
execute_from_command_line(['manage.py', 'makemigrations', 'accounts', '--name', 'remove_personalizedtip_unique_constraint'])

print("Migration created successfully!")
print("Next steps:")
print("1. Review the generated migration file in accounts/migrations/")
print("2. Run: python manage.py migrate")
print("3. Test the 'Generate Tips' functionality")
