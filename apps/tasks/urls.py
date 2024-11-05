from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.tasks.views import TaskViewSet, ReportViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'tasks', TaskViewSet, basename='tasks')
urlpatterns = [
    path('tasks/reports', ReportViewSet.as_view({'get': 'list'}), name='tasks-reports'),
    path('', include(router.urls)),
]
