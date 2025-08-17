# Generated migration for nutrition tracking models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_add_dietary_goal_fields'),
    ]

    operations = [
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
