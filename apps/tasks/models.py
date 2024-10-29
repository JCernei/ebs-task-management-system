from django.db import models
from django.db.models import Sum, DurationField, ExpressionWrapper, F

from apps.users.models import User


class Task(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
        ('archived', 'Archived'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='task_owner', null=True, editable=False)
    executor = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='task_executor', null=True)

    @property
    def logged_time(self) -> int:
        total_duration = self.time_logs.aggregate(
            total_duration=Sum(
                ExpressionWrapper(F('duration'), output_field=DurationField())
            )
        )['total_duration']
        return total_duration.total_seconds() // 60 if total_duration else 0

    def __str__(self):
        return self.title


class Comment(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    task = models.ForeignKey('Task', on_delete=models.CASCADE, related_name='comments')
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.user} on {self.task.title}'


class TimeLog(models.Model):
    task = models.ForeignKey(Task, on_delete=models.SET_NULL, null=True , related_name='time_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True , related_name='user_time_logs')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    duration = models.GeneratedField(
        expression=F('end_time') - F('start_time'),
        output_field=DurationField(),
        db_persist=True,
        null=True,
        blank=True,
    )

    def __str__(self):
        return f'{self.user} - {self.task.title} on {self.start_time}'
