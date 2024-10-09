from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, TaskListSerializer, \
    TaskUpdateSerializer, TaskCreateSerializer
from .models import Task
from drf_spectacular.utils import OpenApiParameter, extend_schema
from drf_spectacular.types import OpenApiTypes
from rest_framework.generics import get_object_or_404
from apps.users.models import User


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all()

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        elif self.action == 'create':
            return TaskCreateSerializer
        elif self.action == 'partial_update':
            return TaskUpdateSerializer
        return TaskSerializer


    def perform_update(self, serializer):
        if 'executor' in self.request.data:
            user_id = self.request.data.get('executor')
            assigned_user = get_object_or_404(User, id=user_id)
            serializer.save(executor=assigned_user)
        if 'is_completed' in self.request.data:
            serializer.save(is_completed=self.request.data.get('is_completed'))

    @extend_schema(
        parameters=[
            OpenApiParameter('completed', type=OpenApiTypes.BOOL, location=OpenApiParameter.QUERY,
                             description='Filter tasks by completion status')
        ]
    )
    def list(self, request, *args, **kwargs):
        queryset = self.queryset
        completed = request.query_params.get('completed')
        if completed is not None:
            queryset = queryset.filter(is_completed=completed.lower() == 'true')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)