import json
from datetime import timedelta

from django.conf import settings
from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.http import HttpResponseBadRequest
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_filters.rest_framework import DjangoFilterBackend
from minio import Minio
from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.tasks.documents import TaskDocument, CommentDocument
from apps.tasks.filters import TaskFilter, TimeLogFilter
from apps.tasks.models import Task, Comment, TimeLog, Attachment
from apps.tasks.serializers import (
    TaskSerializer,
    TaskDetailSerializer,
    TaskListSerializer,
    TaskUpdateSerializer,
    TaskCreateSerializer,
    CommentCreateSerializer,
    CommentListSerializer,
    TimeLogListSerializer,
    TimeLogCreateSerializer,
    TimeLogStartSerializer,
    TimeLogStopSerializer,
    ReportSerializer,
    AttachmentSerializer,
    TaskDocumentSerializer,
    CommentDocumentSerializer,
)


class TaskViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Task.objects.all().order_by("id")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_class = TaskFilter
    search_fields = ["title"]

    def get_serializer_class(self):
        if self.action == "list":
            return TaskListSerializer
        elif self.action == "retrieve":
            return TaskDetailSerializer
        elif self.action == "create":
            return TaskCreateSerializer
        elif self.action == "partial_update":
            return TaskUpdateSerializer
        elif self.action == "list_comment":
            return CommentListSerializer
        elif self.action == "create_comment":
            return CommentCreateSerializer
        elif self.action == "start_timer":
            return TimeLogStartSerializer
        elif self.action == "stop_timer":
            return TimeLogStopSerializer
        elif self.action == "list_logs":
            return TimeLogListSerializer
        elif self.action == "create_logs":
            return TimeLogCreateSerializer
        elif self.action in ["list_attachments", "generate_attachment_url"]:
            return AttachmentSerializer
        return TaskSerializer

    @action(detail=True, url_path="comments", url_name="comments")
    def list_comment(self, request, pk=None):
        task = self.get_object()
        comments = Comment.objects.filter(task=task)
        serializer = self.get_serializer(comments, many=True)
        return Response(serializer.data)

    @list_comment.mapping.post
    def create_comment(self, request, pk=None):
        task = self.get_object()
        serializer = self.get_serializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(task=task)
        return Response(serializer.data, status=201)

    @action(detail=True, url_path="logs", url_name="logs")
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
        duration = timezone.timedelta(minutes=validated_data["duration"])
        start_time = validated_data["end_time"] - duration

        # Create the time log entry
        TimeLog.objects.create(
            task=task,
            start_time=start_time,
            user=validated_data["user"],
            end_time=validated_data["end_time"],
            note=validated_data["note"],
        )
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["post"], url_path="logs/start", url_name="logs-start")
    def start_timer(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        task = self.get_object()

        active_timer_exists = TimeLog.objects.filter(
            task=task, user=validated_data["user"], end_time__isnull=True
        ).exists()
        if active_timer_exists:
            return Response(
                {"detail": "You already have an active timer for this task."},
                status=400,
            )

        TimeLog.objects.create(task=task, start_time=timezone.now(), **validated_data)
        return Response(serializer.data, status=201)

    @action(detail=True, methods=["post"], url_path="logs/stop", url_name="logs-stop")
    def stop_timer(self, request, pk=None):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        task = self.get_object()
        active_timer = get_object_or_404(
            TimeLog, task=task, user=validated_data["user"], end_time__isnull=True
        )

        active_timer.end_time = timezone.now()

        note = validated_data.get("note", "")
        if note:
            if active_timer.note:
                active_timer.note += f"\n{note}"
            else:
                active_timer.note = note

        active_timer.save()
        serializer = self.get_serializer(active_timer)
        return Response(serializer.data, status=200)

    @action(detail=True, url_path="attachments", url_name="attachments")
    def list_attachments(self, request, pk=None):
        task = self.get_object()
        attachments = Attachment.objects.filter(task=task)
        serializer = self.get_serializer(attachments, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="attachments/upload-url", url_name="generate_attachment_url")
    def generate_attachment_url(self, request, pk=None):
        task = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated_data = serializer.validated_data

        attachment = Attachment.objects.create(task=task, user=validated_data["user"], file=None)
        object_name = Attachment.custom_file_name(
            attachment, validated_data["file_name"]
        )

        minio_client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_USE_HTTPS,
        )

        bucket_name = settings.MINIO_MEDIA_FILES_BUCKET

        url = minio_client.presigned_put_object(
            bucket_name=bucket_name,
            object_name=object_name,
            expires=timedelta(seconds=3600),
        )

        if url:
            attachment.file = object_name
            attachment.save()
            return Response({"url": url})
        return Response({"error": "Could not generate pre-signed URL"}, status=500)


class ReportViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    queryset = TimeLog.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_class = TimeLogFilter
    serializer_class = ReportSerializer

    def _get_tasks_with_duration(self, queryset, filterset):
        """
        Aggregate total duration for each task and order them by it
        """
        tasks = (
            queryset.values("task__id", "task__title")
            .annotate(
                total_duration=Sum(
                    ExpressionWrapper(F("duration"), output_field=DurationField())
                )
            )
            .order_by("-total_duration")
        )

        # Apply top limit if specified in filter
        top = getattr(filterset, "top", 0)
        if top:
            tasks = tasks[: int(top)]

        return tasks

    def _format_task_data(self, tasks_with_time):
        """
        Format task data for serialization
        """
        return [
            {
                "id": task["task__id"],
                "title": task["task__title"],
                "logged_time": self._duration_to_minutes(task["total_duration"]),
            }
            for task in tasks_with_time
        ]

    def _get_total_duration(self, queryset):
        """
        Calculate total duration from queryset
        """
        total = queryset.aggregate(
            total_duration=Sum(
                ExpressionWrapper(F("duration"), output_field=DurationField())
            )
        )["total_duration"]
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
        filterset = self.filterset_class(
            request.GET,
            queryset=self.get_queryset(),
        )
        if not filterset.is_valid():
            return Response(filterset.errors, status=400)

        queryset = filterset.qs

        # Get tasks with their durations
        tasks_with_time = self._get_tasks_with_duration(queryset, filterset)

        # Prepare response data
        tasks = self._format_task_data(tasks_with_time)
        total_logged_time = self._get_total_duration(queryset)

        page = self.paginate_queryset(tasks)
        response_data = {"total_logged_time": total_logged_time, "tasks": page}

        return self.get_paginated_response(response_data)


class BaseSearchViewSet(viewsets.GenericViewSet):
    """
    Base viewset for Elasticsearch-based search functionality.
    """

    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    document_class = None  # Should be set by child classes
    search_fields = []

    def list(self, request):
        query = request.query_params.get("search", "")

        # Create an Elasticsearch search object
        search = (
            self.document_class.search()
            .query("multi_match", query=query, fields=self.search_fields)
            .extra(size=10000)
        )

        # Execute search and format results
        response_queryset = search.to_queryset().order_by("id")

        # Paginate the queryset if needed
        page = self.paginate_queryset(response_queryset)

        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class TaskSearchViewSet(BaseSearchViewSet):
    """
    ViewSet for searching tasks using Elasticsearch.
    """

    queryset = Task.objects.all()
    serializer_class = TaskDocumentSerializer
    search_fields = ["title", "description"]
    document_class = TaskDocument


class CommentSearchViewSet(BaseSearchViewSet):
    """
    ViewSet for searching comments using Elasticsearch.
    """

    queryset = Comment.objects.all()
    serializer_class = CommentDocumentSerializer
    search_fields = ["text"]
    document_class = CommentDocument


class WebhookListenerView(viewsets.GenericViewSet):
    permission_classes = []
    serializer_class = None

    def listen(self, request):
        try:
            payload = json.loads(request.body)
            event_type = payload["EventName"]
            file_path = payload["Key"]
            file_name = os.path.basename(file_path)
            task_id = file_path.split("/")[1].split("_")[1]

            if event_type == "s3:ObjectCreated:Put":

                if not file_name:
                    return Response({"detail": "Missing file_name"}, status=400)

                attachment = get_object_or_404(Attachment, file__endswith=file_name, task_id=task_id)
                attachment.status = "Uploaded"
                attachment.save()
                return Response({"detail": "Attachment status updated"}, status=200)

            return Response({"detail": "Unknown event type"}, status=400)

        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid JSON payload")
