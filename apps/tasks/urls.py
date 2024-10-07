from django.urls import path
# from . import views
from .views import TaskListCreateView, TaskDetailView, UserTasksView

urlpatterns = [
    path("tasks", TaskListCreateView.as_view(), name="task_list_create"),
]