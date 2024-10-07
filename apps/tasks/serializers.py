from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'
        read_only_fields = ['is_completed', 'user']

class SimpleTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ['id', 'title']  # Only include id and title


class TaskDetailSerializer(serializers.ModelSerializer):
    owner = serializers.CharField(source='user.get_full_name', read_only=True)  # Show full name of the owner

    class Meta:
        model = Task
        fields = ['id', 'title', 'description', 'is_completed', 'owner']
