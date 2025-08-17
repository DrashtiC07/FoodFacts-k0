# Enhanced dietary tracking migration - handles existing tables
from django.db import migrations, models, connection
import django.db.models.deletion
from django.conf import settings
import django.utils.timezone

def check_table_exists(table_name):
    """Check if a table exists in the database"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name=?;
        """, [table_name])
        return cursor.fetchone() is not None

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    with connection.cursor() as cursor:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        return column_name in columns

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        # Add fields to DietaryGoal only if they don't exist
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN sugar_target INTEGER DEFAULT 50;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN sugar_target;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='sugar_target',
                    field=models.IntegerField(default=50, help_text='Daily sugar target in grams'),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN sodium_target INTEGER DEFAULT 2300;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN sodium_target;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='sodium_target',
                    field=models.IntegerField(default=2300, help_text='Daily sodium target in mg'),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN fiber_target INTEGER DEFAULT 25;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN fiber_target;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='fiber_target',
                    field=models.IntegerField(default=25, help_text='Daily fiber target in grams'),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN saturated_fat_target INTEGER DEFAULT 20;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN saturated_fat_target;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='saturated_fat_target',
                    field=models.IntegerField(default=20, help_text='Daily saturated fat target in grams'),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN sugar_consumed INTEGER DEFAULT 0;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN sugar_consumed;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='sugar_consumed',
                    field=models.IntegerField(default=0),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN sodium_consumed INTEGER DEFAULT 0;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN sodium_consumed;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='sodium_consumed',
                    field=models.IntegerField(default=0),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN fiber_consumed INTEGER DEFAULT 0;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN fiber_consumed;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='fiber_consumed',
                    field=models.IntegerField(default=0),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN saturated_fat_consumed INTEGER DEFAULT 0;
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN saturated_fat_consumed;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='saturated_fat_consumed',
                    field=models.IntegerField(default=0),
                ),
            ]
        ),
        migrations.RunSQL(
            """
            ALTER TABLE accounts_dietarygoal ADD COLUMN last_reset_date DATE DEFAULT (date('now'));
            """,
            reverse_sql="ALTER TABLE accounts_dietarygoal DROP COLUMN last_reset_date;",
            state_operations=[
                migrations.AddField(
                    model_name='dietarygoal',
                    name='last_reset_date',
                    field=models.DateField(default=django.utils.timezone.now),
                ),
            ]
        ),
        
        # Create new models only if tables don't exist
        migrations.CreateModel(
            name='WeeklyNutritionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('week_start_date', models.DateField()),
                ('avg_calories', models.FloatField(default=0)),
                ('avg_protein', models.FloatField(default=0)),
                ('avg_fat', models.FloatField(default=0)),
                ('avg_carbs', models.FloatField(default=0)),
                ('avg_sugar', models.FloatField(default=0)),
                ('avg_sodium', models.FloatField(default=0)),
                ('avg_fiber', models.FloatField(default=0)),
                ('avg_saturated_fat', models.FloatField(default=0)),
                ('total_scans', models.IntegerField(default=0)),
                ('days_tracked', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_logs', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-week_start_date'],
            },
        ),
        migrations.CreateModel(
            name='DailyNutritionSnapshot',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('calories', models.IntegerField(default=0)),
                ('protein', models.IntegerField(default=0)),
                ('fat', models.IntegerField(default=0)),
                ('carbs', models.IntegerField(default=0)),
                ('sugar', models.IntegerField(default=0)),
                ('sodium', models.IntegerField(default=0)),
                ('fiber', models.IntegerField(default=0)),
                ('saturated_fat', models.IntegerField(default=0)),
                ('calories_target', models.IntegerField(default=2000)),
                ('protein_target', models.IntegerField(default=50)),
                ('fat_target', models.IntegerField(default=70)),
                ('carbs_target', models.IntegerField(default=300)),
                ('sugar_target', models.IntegerField(default=50)),
                ('sodium_target', models.IntegerField(default=2300)),
                ('fiber_target', models.IntegerField(default=25)),
                ('saturated_fat_target', models.IntegerField(default=20)),
                ('scans_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_snapshots', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-date'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='weeklynutritionlog',
            unique_together={('user', 'week_start_date')},
        ),
        migrations.AlterUniqueTogether(
            name='dailynutritionsnapshot',
            unique_together={('user', 'date')},
        ),
    ]
