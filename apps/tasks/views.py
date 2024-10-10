from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.models import Task, Comment
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, TaskListSerializer, \
    TaskUpdateSerializer, TaskCreateSerializer, CommentCreateSerializer, CommentListSerializer


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['is_completed', 'executor']
    search_fields = ['title']

    def get_serializer_class(self):
        if self.action == 'list':
            return TaskListSerializer
        elif self.action == 'retrieve':
            return TaskDetailSerializer
        elif self.action == 'create':
            return TaskCreateSerializer
        elif self.action == 'partial_update':
            return TaskUpdateSerializer
        elif self.action == 'list_comment':
            return CommentListSerializer
        elif self.action == 'create_comment':
            return CommentCreateSerializer
        return TaskSerializer

    @action(detail=True, url_path='comments', url_name='task_comments')
    def list_comment(self, request, pk=None):
        task = self.get_object()
        comments = Comment.objects.filter(task=task)
        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)

    @list_comment.mapping.post
    def create_comment(self, request, pk=None):
        task = self.get_object()
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data
        serializer.save(task=task, **validated_data)
        return Response(serializer.data, status=201)
