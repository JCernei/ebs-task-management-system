from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.tasks.views import TaskViewSet, ReportViewSet, TaskSearchViewSet, CommentSearchViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'tasks', TaskViewSet, basename='tasks')
urlpatterns = [
    path('search/tasks', TaskSearchViewSet.as_view({'get': 'list'}), name='search-tasks'),
    path('search/comments', CommentSearchViewSet.as_view({'get': 'list'}), name='search-comments'),
    path('tasks/reports', ReportViewSet.as_view({'get': 'list'}), name='tasks-reports'),
    path('', include(router.urls)),
]
