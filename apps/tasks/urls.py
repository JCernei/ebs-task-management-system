from django.urls import path
# from . import views
from .views import TaskListCreateView, TaskDetailView, UserTasksView

urlpatterns = [
    path("tasks", TaskListCreateView.as_view(), name="task_list_create"),
    path('tasks/<int:pk>', TaskDetailView.as_view(), name='task_detail'),
    path('users/<int:pk>/tasks', UserTasksView.as_view(), name='user_tasks'),
]