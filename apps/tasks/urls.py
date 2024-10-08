from django.urls import path
from .views import TaskListCreateView, TaskDetailView, UserTaskListView


urlpatterns = [
    path("tasks", TaskListCreateView.as_view(), name="task_list_create"),
    path('tasks/<int:pk>', TaskDetailView.as_view(), name='task_detail'),
    path('users/<int:pk>/tasks', UserTaskListView.as_view(), name='user_task_list'),
]
