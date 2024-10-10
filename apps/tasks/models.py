from django.db import models
from apps.users.models import User


class Task(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_owner', null=True, editable=False)
    executor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='task_executor', null=True)

    def __str__(self):
        return self.title
