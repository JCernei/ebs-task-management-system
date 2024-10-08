from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, SimpleTaskSerializer
from .models import Task
from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiParameter, extend_schema_view, extend_schema
from drf_spectacular.types import OpenApiTypes

@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                'completed',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter tasks by completion status (true or false)',
            ),
        ]
    )
)
class TaskListCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return SimpleTaskSerializer
        return TaskSerializer


    def get_queryset(self):
        queryset = Task.objects.all()
        completed = self.request.query_params.get('completed', None)

        if completed is not None:
            completed = completed.lower() == 'true'
            queryset = queryset.filter(is_completed=completed)

        return queryset

    # Define behavior for POST requests (create task)
    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user,
            assigned_to=self.request.user
        )


@extend_schema_view(
    get=extend_schema(
        parameters=[
            OpenApiParameter(
                'completed',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter tasks by completion status (true or false)',
            ),
        ]
    )
)
class UserTaskListView(ListAPIView):
    serializer_class = SimpleTaskSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user_id = self.kwargs['pk']
        user = get_object_or_404(User, pk=user_id)
        queryset = Task.objects.filter(assigned_to=user)

        completed = self.request.query_params.get('completed', None)
        if completed is not None:
            completed = completed.lower() == 'true'
            queryset = queryset.filter(is_completed=completed)

        return queryset


class TaskDetailView(RetrieveAPIView):
    serializer_class = TaskDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        obj = get_object_or_404(Task, id=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj
