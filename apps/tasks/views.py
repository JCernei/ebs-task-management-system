from typing import Optional
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, SimpleTaskSerializer, \
    TaskUpdateSerializer
from .models import Task
from django.contrib.auth.models import User
from drf_spectacular.utils import OpenApiParameter, extend_schema_view, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import ListAPIView, ListCreateAPIView, RetrieveAPIView, UpdateAPIView, get_object_or_404, \
    RetrieveUpdateDestroyAPIView


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
            owner=self.request.user,
            executor=self.request.user
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
        queryset = Task.objects.filter(executor=user)

        completed = self.request.query_params.get('completed', None)
        if completed is not None:
            completed = completed.lower() == 'true'
            queryset = queryset.filter(is_completed=completed)

        return queryset


class TaskDetailUpdateDeleteView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'GET':
            return TaskDetailSerializer
        elif self.request.method in ['PATCH', 'PUT']:
            return TaskUpdateSerializer
        elif self.request.method == 'DELETE':
            return TaskDetailSerializer
        return super().get_serializer_class()

    def get_object(self):
        obj = get_object_or_404(Task, id=self.kwargs['pk'])
        self.check_object_permissions(self.request, obj)
        return obj

    def patch(self, request: Request, pk: int) -> Response:
        task = self.get_object()

        if not request.data:
            return Response({'message': 'No update data provided.'})

        serializer = self.get_serializer(task, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Update the task fields only if provided in the request
        if 'executor' in request.data:
            user_id = request.data['executor']
            assigned_user = get_object_or_404(User, id=user_id)
            task.executor = assigned_user

        if 'is_completed' in request.data:
            task.is_completed = request.data['is_completed']

        task.save()  # Save the updated task

        return Response({'message': 'Task updated successfully', 'task': serializer.data})

    def delete(self, request: Request, pk: int) -> Response:
        task = self.get_object()
        task.delete()
        return Response({'message': 'Task deleted successfully'})

    def get_assigned_user(self, request: Request) -> Optional[User]:
        """Helper function to retrieve the assigned user from the request."""
        user_id = request.data.get('executor')
        if user_id:
            return get_object_or_404(User, id=user_id)
        return None
