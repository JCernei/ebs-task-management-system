from django.utils import timezone
from rest_framework import serializers

from apps.tasks.models import Task, Comment, TimeLog, Attachment
from apps.users.models import User
from apps.users.serializers import UserSerializer


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


class TaskCreateSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    executor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        default=serializers.CurrentUserDefault(),
        required=False,
    )

    class Meta:
        model = Task
        fields = "__all__"
        read_only_fields = ["status"]


class TaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "logged_time"]


class TaskDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    executor = UserSerializer(read_only=True)
    logged_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = Task
        fields = "__all__"


class TaskUpdateSerializer(serializers.ModelSerializer):
    status = serializers.ChoiceField(choices=Task.STATUS_CHOICES, required=False)
    executor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False
    )

    class Meta:
        model = Task
        fields = ["id", "title", "executor", "status"]
        read_only_fields = ["id", "title"]


class CommentCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Comment
        fields = ["id", "text", "user", "task"]
        read_only_fields = ["user", "task"]

    def to_representation(self, instance):
        return {"id": instance.id}


class CommentListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "text", "user", "created_at"]


class TimeLogStartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TimeLog
        fields = ["start_time", "note", "user"]
        read_only_fields = ["start_time"]


class TimeLogStopSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TimeLog
        fields = ["end_time", "note", "user"]
        read_only_fields = ["end_time"]


class TimeLogListSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeLog
        fields = "__all__"


class TimeLogCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    end_time = serializers.DateTimeField(required=False, default=timezone.now)
    duration = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TimeLog
        fields = ["duration", "note", "end_time", "user"]


class ReportTaskListSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    logged_time = serializers.IntegerField()


class ReportSerializer(serializers.Serializer):
    total_logged_time = serializers.IntegerField()
    tasks = ReportTaskListSerializer(many=True)


class AttachmentSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Attachment
        fields = ["id", "name", "status", "user", "file"]
        read_only_fields = ["status", "user", "file", "id"]


class TaskDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = "__all__"


class CommentDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"
