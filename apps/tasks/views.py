from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, SimpleTaskSerializer
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


class UserTasksView(ListAPIView):
    serializer_class = SimpleTaskSerializer
    permission_classes = [IsAuthenticated]

    # Filter tasks to only return those assigned to the user in the URL
    def get_queryset(self):
        user_id = self.kwargs['pk']
        return Task.objects.filter(user_id=user_id)


class TaskDetailView(RetrieveAPIView):
    serializer_class = TaskDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = get_object_or_404(Task, id=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj
