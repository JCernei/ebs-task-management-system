from django.db import models
from django.contrib.auth.models import User


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks', null=True, editable=False)
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_tasks', null=True)

    def __str__(self):
        return self.title
