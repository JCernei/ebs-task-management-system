from django.urls import path
from .views import TaskListCreateView, TaskDetailUpdateView, UserTaskListView

urlpatterns = [
    path("tasks", TaskListCreateView.as_view(), name="task_list_create"),
    path('tasks/<int:pk>', TaskDetailUpdateView.as_view(), name='task_detail_update'),
    path('users/<int:pk>/tasks', UserTaskListView.as_view(), name='user_task_list'),
]
