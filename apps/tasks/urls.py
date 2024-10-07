from django.urls import path

from . import views
from .views import TaskListView

urlpatterns = [
    path("", TaskListView.as_view(), name="task_list"),
]