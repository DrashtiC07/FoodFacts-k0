# Generated migration for enhanced dietary tracking
from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='dietarygoal',
            name='sugar_target',
            field=models.IntegerField(default=50, help_text='Daily sugar target in grams'),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='sodium_target',
            field=models.IntegerField(default=2300, help_text='Daily sodium target in mg'),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='fiber_target',
            field=models.IntegerField(default=25, help_text='Daily fiber target in grams'),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='saturated_fat_target',
            field=models.IntegerField(default=20, help_text='Daily saturated fat target in grams'),
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
            name='fiber_consumed',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='saturated_fat_consumed',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='dietarygoal',
            name='last_reset_date',
            field=models.DateField(default=django.utils.timezone.now),
        ),
    ]
