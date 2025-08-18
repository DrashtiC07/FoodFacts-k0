# Generated migration for PersonalizedTip model
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonalizedTip',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tip_type', models.CharField(choices=[('critical', 'Critical Alert'), ('warning', 'Warning'), ('success', 'Success'), ('info', 'Information')], default='info', max_length=20)),
                ('priority', models.IntegerField(choices=[(1, 'Critical'), (2, 'High'), (3, 'Medium'), (4, 'Low')], default=3)),
                ('icon', models.CharField(default='info-circle', max_length=50)),
                ('color', models.CharField(default='info', max_length=20)),
                ('title', models.CharField(max_length=100)),
                ('message', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('last_nutrition_snapshot', models.JSONField(blank=True, default=dict)),
                ('is_active', models.BooleanField(default=True)),
                ('trigger_condition', models.CharField(blank=True, max_length=100)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='personalized_tips', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['priority', '-created_at'],
            },
        ),
        migrations.AddConstraint(
            model_name='personalizedtip',
            constraint=models.UniqueConstraint(fields=('user', 'trigger_condition'), name='unique_user_trigger_condition'),
        ),
    ]
