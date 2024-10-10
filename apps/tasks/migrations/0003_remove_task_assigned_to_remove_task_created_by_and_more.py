# Generated by Django 5.1.1 on 2024-10-09 07:31

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0002_remove_task_user_task_assigned_to_task_created_by'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveField(
            model_name='task',
            name='assigned_to',
        ),
        migrations.RemoveField(
            model_name='task',
            name='created_by',
        ),
        migrations.AddField(
            model_name='task',
            name='executor',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='task_executor', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='task',
            name='owner',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='task_owner', to=settings.AUTH_USER_MODEL),
        ),
    ]
