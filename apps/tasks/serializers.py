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
    owner = serializers.CharField(source='created_by.get_full_name', read_only=True)
    executor = serializers.CharField(source='assigned_to.get_full_name', read_only=True)

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'is_completed', 'owner', 'executor']


class TaskUpdateSerializer(serializers.ModelSerializer):
    assigned_to = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False  # Make this field optional
    )
    is_completed = serializers.BooleanField(
        required=False  # Make this field optional
    )

    class Meta:
        model = Task
        fields = ['id', 'title', 'assigned_to', 'is_completed']
        read_only_fields = ['id', 'title']
