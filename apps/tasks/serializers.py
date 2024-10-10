from rest_framework import serializers

from apps.users.models import User
from apps.users.serializers import UserSerializer
from apps.tasks.models import Task


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
