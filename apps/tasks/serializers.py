from django.utils import timezone
from rest_framework import serializers

from apps.tasks.models import Task, Comment, TimeLog
from apps.users.models import User
from apps.users.serializers import UserSerializer


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'


class TaskCreateSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    executor = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), default=serializers.CurrentUserDefault(),
                                                  required=False)

    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['is_completed']


class TaskListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title']


class TaskDetailSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    executor = UserSerializer(read_only=True)

    class Meta:
        model = Task
        fields = '__all__'


class TaskUpdateSerializer(serializers.ModelSerializer):
    is_completed = serializers.BooleanField(required=False)
    executor = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False)

    class Meta:
        model = Task
        fields = ['id', 'title', 'executor', 'is_completed']
        read_only_fields = ['id', 'title']


class CommentCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Comment
        fields = ['id', 'text', 'user', 'task']
        read_only_fields = ['user', 'task']

    def to_representation(self, instance):
        return {'id': instance.id}


class CommentListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Comment
        fields = ['id', 'text', 'user', 'created_at']


class TimeLogStartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    start_time = serializers.DateTimeField(default=timezone.now)
    date = serializers.DateField(default=timezone.now().date)
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TimeLog
        fields = ['date', 'start_time', 'note', 'user']
        read_only_fields = ['date', 'start_time']


class TimeLogStopSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    end_time = serializers.DateTimeField(default=timezone.now)
    duration = serializers.DurationField(required=False, allow_null=True)
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TimeLog
        fields = ['end_time', 'duration', 'note', 'user']
        read_only_fields = ['duration', 'end_time']


class TimeLogListSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = TimeLog
        fields = ['id', 'duration', 'note', 'date', 'user']


class TimeLogCreateSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    date = serializers.DateField()
    duration = serializers.IntegerField()
    note = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = TimeLog
        fields = ['id', 'duration', 'note', 'date', 'user', 'task']
        read_only_fields = ['id', 'user', 'task']
