# Generated by Django 5.1.1 on 2024-10-28 12:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0008_remove_task_is_completed_task_status_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(choices=[('open', 'Open'), ('in_progress', 'In Progress'), ('completed', 'Completed'), ('canceled', 'Canceled'), ('archived', 'Archived')], db_index=True, default='open', max_length=20),
        ),
    ]