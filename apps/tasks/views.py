from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.models import Task, Comment, TimeLog
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, TaskListSerializer, \
    TaskUpdateSerializer, TaskCreateSerializer, CommentCreateSerializer, CommentListSerializer, \
    TimeLogListSerializer, TimeLogCreateSerializer, TimeLogStartSerializer, TimeLogStopSerializer, \
    TaskReportSerializer
from apps.tasks.utils.task_report_helpers import filter_time_logs_by_time_interval, apply_top_limit, \
    calculate_total_logged_time


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
        elif self.action == 'retrieve_report':
            return TaskReportSerializer
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

    @extend_schema(
        parameters=[
            OpenApiParameter(name='top', description='Limit the number of results returned', required=False,
                             type=OpenApiTypes.INT),
            OpenApiParameter(name='interval', description='Time interval (e.g., 1 day, 2 weeks, 3 months)',
                             required=False,
                             type=OpenApiTypes.STR),
        ],
    )
    @action(detail=False, methods=['get'], url_path='reports', url_name='task_reports')
    def retrieve_report(self, request):
        user = request.user
        time_logs = TimeLog.objects.filter(user=user)

        top_param = int(request.query_params.get('top', 0))
        interval = request.query_params.get('interval', '1 month')

        # Filter time logs based on the time interval
        time_logs = filter_time_logs_by_time_interval(time_logs, interval)

        # Aggregate total duration for each task
        tasks_with_time = time_logs.values('task__id', 'task__title').annotate(
            total_duration=Sum(
                ExpressionWrapper(F('duration'), output_field=DurationField())
            )
        )

        # Apply the top limit
        tasks_with_time = apply_top_limit(tasks_with_time, top_param)

        # Use the serializer to format the task data
        tasks = [
            TaskListSerializer({
                'id': task['task__id'],
                'title': task['task__title'],
                'logged_time': task['total_duration'].total_seconds() // 60 if task['total_duration'] else 0
            }).data for task in tasks_with_time
        ]

        # Calculate the total logged time for the user
        total_minutes = calculate_total_logged_time(time_logs)

        response_data = {
            'total_logged_time': total_minutes,
            'tasks': tasks
        }

        serializer = self.get_serializer(data=response_data)
        serializer.is_valid(raise_exception=True)

        return Response(serializer.data)
