from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, SimpleTaskSerializer, \
    TaskAssigneeUpdateSerializer
from .models import Task
from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiParameter, extend_schema_view, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, UpdateAPIView, get_object_or_404, \
    RetrieveUpdateAPIView


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


class TaskDetailUpdateView(RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TaskDetailSerializer
        elif self.request.method in ['PATCH', 'PUT']:
            return TaskAssigneeUpdateSerializer
        return super().get_serializer_class()

    def get_object(self):
        obj = get_object_or_404(Task, id=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def patch(self, request: Request, pk: int) -> Response:
        task = get_object_or_404(Task, id=pk)

        user_id = request.data.get('assigned_to')
        assigned_user = get_object_or_404(User, id=user_id)

        task.assigned_to = assigned_user
        task.save()

        serializer = self.get_serializer(task)

        return Response({'message': 'Task assigned successfully', 'task': serializer.data})
