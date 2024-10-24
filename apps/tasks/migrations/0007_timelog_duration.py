# Generated by Django 5.1.1 on 2024-10-23 09:07

import django.db.models.expressions
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0006_remove_timelog_date_remove_timelog_duration'),
    ]

    operations = [
        migrations.AddField(
            model_name='timelog',
            name='duration',
            field=models.GeneratedField(db_persist=True, expression=django.db.models.expressions.CombinedExpression(models.F('end_time'), '-', models.F('start_time')), null=True, output_field=models.DurationField()),
        ),
    ]