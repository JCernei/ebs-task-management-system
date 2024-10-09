from rest_framework import serializers
from .models import Task
from django.contrib.auth.models import User


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'is_completed']
        read_only_fields = ['id', 'is_completed']


class SimpleTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title']


class TaskDetailSerializer(serializers.ModelSerializer):
    owner_name = serializers.CharField(source='owner.get_full_name', read_only=True)
    executor_name = serializers.CharField(source='executor.get_full_name', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'is_completed', 'owner_name', 'executor_name']


class TaskUpdateSerializer(serializers.ModelSerializer):
    executor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False
    )
    is_completed = serializers.BooleanField(
        required=False
    )

    class Meta:
        model = Task
        fields = ['id', 'title', 'executor', 'is_completed']
        read_only_fields = ['id', 'title']
