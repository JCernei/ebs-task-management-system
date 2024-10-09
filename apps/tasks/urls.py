from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TaskViewSet


# Create a router and register our TaskViewSet with it.
router = DefaultRouter(trailing_slash=False)
router.register(r'tasks', TaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
    # path("tasks", TaskListCreateView.as_view(), name="task_list_create"),
    # path('tasks/<int:pk>', TaskDetailUpdateDeleteView.as_view(), name='task_detail_update_delete'),
    # path('users/<int:pk>/tasks', UserTaskListView.as_view(), name='user_task_list'),
]
