from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from apps.tasks.serializers import TaskSerializer, SimpleTaskSerializer
from .models import Task


class TaskListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return SimpleTaskSerializer
        return TaskSerializer

    # Define queryset for GET requests (list tasks)
    def get_queryset(self):
        return Task.objects.all()

    # Define behavior for POST requests (create task)
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)  # Assign the task to the current user
