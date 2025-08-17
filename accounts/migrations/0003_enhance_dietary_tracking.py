# Generated migration for enhanced dietary tracking

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dietarygoal',
            name='sugar_target',
            field=models.IntegerField(default=50),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='sodium_target',
            field=models.IntegerField(default=2300),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='sugar_consumed',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='sodium_consumed',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='last_reset_date',
            field=models.DateField(auto_now_add=True),
        ),
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
                ('calories_achievement', models.FloatField(default=0)),
                ('protein_achievement', models.FloatField(default=0)),
                ('fat_achievement', models.FloatField(default=0)),
                ('carbs_achievement', models.FloatField(default=0)),
                ('sugar_achievement', models.FloatField(default=0)),
                ('sodium_achievement', models.FloatField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='weekly_logs', to='accounts.customuser')),
            ],
            options={
                'ordering': ['-week_start_date'],
            },
        ),
        migrations.AlterUniqueTogether(
            name='weeklynutritionlog',
            unique_together={('user', 'week_start_date')},
        ),
    ]
