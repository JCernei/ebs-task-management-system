from django.contrib import admin
from .models import Task

class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'description', 'user', 'is_completed')

admin.site.register(Task, TaskAdmin)