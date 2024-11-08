from django_elasticsearch_dsl import Document
from django_elasticsearch_dsl.registries import registry

from apps.tasks.models import Task, Comment


@registry.register_document
class TaskDocument(Document):
    class Index:
        name = "tasks"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = Task
        fields = [
            "title",
            "description",
        ]


@registry.register_document
class CommentDocument(Document):
    class Index:
        name = "comments"
        settings = {"number_of_shards": 1, "number_of_replicas": 0}

    class Django:
        model = Comment
        fields = [
            "text",
        ]
