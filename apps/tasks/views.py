from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.filters import TaskFilter, TimeLogFilter
from apps.tasks.models import Task, Comment, TimeLog
from apps.tasks.serializers import TaskSerializer, TaskDetailSerializer, TaskListSerializer, \
    TaskUpdateSerializer, TaskCreateSerializer, CommentCreateSerializer, CommentListSerializer, \
    TimeLogListSerializer, TimeLogCreateSerializer, TimeLogStartSerializer, TimeLogStopSerializer, \
    ReportSerializer


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all().order_by('id')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TaskFilter
    search_fields = ['title']

    # pagination_class = PageNumberPagination

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

    @action(detail=True, url_path='comments', url_name='comments')
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

    @action(detail=True, url_path='logs', url_name='logs')
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

        # Calculate the start time based on duration
        duration = timezone.timedelta(minutes=validated_data['duration'])
        start_time = validated_data['end_time'] - duration

        # Create the time log entry
        TimeLog.objects.create(
            task=task,
            start_time=start_time,
            user=validated_data['user'],
            end_time=validated_data['end_time'],
            note=validated_data['note']
        )
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['post'], url_path='logs/start', url_name='logs-start')
    def start_timer(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        task = self.get_object()

        active_timer_exists = TimeLog.objects.filter(task=task, user=validated_data['user'],
                                                     end_time__isnull=True).exists()
        if active_timer_exists:
            return Response({'detail': 'You already have an active timer for this task.'}, status=400)

        TimeLog.objects.create(task=task, start_time=timezone.now(), **validated_data)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=['post'], url_path='logs/stop', url_name='logs-stop')
    def stop_timer(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        task = self.get_object()
        active_timer = get_object_or_404(TimeLog, task=task, user=validated_data['user'], end_time__isnull=True)

        active_timer.end_time = timezone.now()

        note = validated_data.get('note', '')
        if note:
            if active_timer.note:
                active_timer.note += f"\n{note}"
            else:
                active_timer.note = note

        active_timer.save()
        serializer = self.get_serializer(active_timer)
        return Response(serializer.data, status=200)


class ReportViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = TimeLog.objects.all().order_by('id')
    filter_backends = [DjangoFilterBackend]
    filterset_class = TimeLogFilter
    serializer_class = ReportSerializer

    def _get_tasks_with_duration(self, queryset, filterset):
        """
        Aggregate total duration for each task and order them by it
        """
        tasks = (
            queryset
            .values('task__id', 'task__title')
            .annotate(
                total_duration=Sum(
                    ExpressionWrapper(
                        F('duration'),
                        output_field=DurationField()
                    )
                )
            )
            .order_by('-total_duration')
        )

        # Apply top limit if specified in filter
        top = getattr(filterset, 'top', 0)
        if top:
            tasks = tasks[:int(top)]

        return tasks

    def _format_task_data(self, tasks_with_time):
        """
        Format task data for serialization
        """
        return [
            {
                'id': task['task__id'],
                'title': task['task__title'],
                'logged_time': self._duration_to_minutes(task['total_duration'])
            }
            for task in tasks_with_time
        ]

    def _get_total_duration(self, queryset):
        """
        Calculate total duration from queryset
        """
        total = queryset.aggregate(
            total_duration=Sum(
                ExpressionWrapper(
                    F('duration'),
                    output_field=DurationField()
                )
            )
        )['total_duration']
        return self._duration_to_minutes(total)

    @staticmethod
    def _duration_to_minutes(duration):
        """
        Convert duration to minutes
        """
        if not duration:
            return 0
        return duration.total_seconds() // 60

    @method_decorator(cache_page(60))
    def list(self, request):
        # Apply filters
        filterset = self.filterset_class(request.GET, queryset=self.get_queryset(), )
        if not filterset.is_valid():
            return Response(filterset.errors, status=400)

        queryset = filterset.qs

        # Get tasks with their durations
        tasks_with_time = self._get_tasks_with_duration(queryset, filterset)

        # Prepare response data
        tasks = self._format_task_data(tasks_with_time)
        total_logged_time = self._get_total_duration(queryset)

        page = self.paginate_queryset(tasks)
        if page is not None:
            response_data = {
                'total_logged_time': total_logged_time,
                'tasks': page
            }
            return self.get_paginated_response(response_data)

        response_data = {
            'total_logged_time': total_logged_time,
            'tasks': tasks
        }
        return Response(response_data)
