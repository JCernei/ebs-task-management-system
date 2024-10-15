from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.models import Task, Comment, TimeLog
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, TaskListSerializer, \
    TaskUpdateSerializer, TaskCreateSerializer, CommentCreateSerializer, CommentListSerializer, \
    TimeLogListSerializer, TimeLogCreateSerializer, TimeLogStartSerializer, TimeLogStopSerializer


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
        elif self.action == 'start_timer':
            return TimeLogStartSerializer
        elif self.action == 'stop_timer':
            return TimeLogStopSerializer
        elif self.action == 'list_logs':
            return TimeLogListSerializer
        elif self.action == 'create_logs':
            return TimeLogCreateSerializer
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

    @action(detail=True, url_path='logs', url_name='task_logs')
    def list_logs(self, request, pk=None):
        task = self.get_object()
        logs = TimeLog.objects.filter(task=task)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)

    @list_logs.mapping.post
    def create_logs(self, request, pk=None):
        task = self.get_object()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        # Calculate the end time based on duration
        start_time = timezone.datetime.combine(validated_data['date'], timezone.now().time(),
                                               tzinfo=timezone.get_current_timezone())
        duration = timezone.timedelta(minutes=validated_data['duration'])
        end_time = start_time + duration

        # Create the time log entry
        TimeLog.objects.create(
            task=task,
            user=validated_data['user'],
            start_time=start_time,
            end_time=end_time,
            date=validated_data['date'],
            duration=duration,
            note=validated_data['note']
        )
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['post'], url_path='logs/start', url_name='task_logs')
    def start_timer(self, request, pk=None):
        task = self.get_object()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        active_timer = TimeLog.objects.filter(task=task, user=validated_data['user'], end_time__isnull=True).first()
        if active_timer:
            return Response({'detail': 'You already have an active timer for this task.'},
                            status=400)

        TimeLog.objects.create(task=task, **validated_data)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['post'], url_path='logs/stop', url_name='task_logs')
    def stop_timer(self, request, pk=None):
        task = self.get_object()
        note = request.data.get('note')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        active_timer = TimeLog.objects.filter(task=task, user=validated_data['user'], end_time__isnull=True).first()
        if not active_timer:
            return Response({'detail': 'No active timer found for this task.'}, status=400)

        active_timer.end_time = validated_data['end_time']
        active_timer.duration = validated_data['end_time'] - active_timer.start_time

        if active_timer.note:
            active_timer.note += f"\n{note}"
        else:
            active_timer.note = note

        active_timer.save()
        serializer = self.get_serializer(active_timer)
        return Response(serializer.data)
