# Fix for existing tables migration conflict
from django.db import migrations, models, connection
import django.db.models.deletion
from django.conf import settings

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=%s;
        """, [table_name])
        return cursor.fetchone() is not None

def create_table_if_not_exists(apps, schema_editor):
    """Create tables only if they don't exist"""
    # Check if tables exist and create them if they don't
    if not check_table_exists('accounts_weeklynutritionlog'):
        # Table doesn't exist, let Django create it normally
        pass
    else:
        # Table exists, skip creation
        print("Table accounts_weeklynutritionlog already exists, skipping creation")

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_merge_20250817_1158'),
    ]

    operations = [
        # Remove duplicate operations and handle existing tables
        migrations.RunPython(create_table_if_not_exists, migrations.RunPython.noop),
    ]
