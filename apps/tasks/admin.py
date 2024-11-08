from django.contrib import admin

from apps.tasks.models import Task, Comment


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 1


class TaskAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "executor", "status", "comment_count")
    list_filter = ("status", "executor")
    search_fields = ("title",)
    inlines = [CommentInline]

    def comment_count(self, obj):
        return Comment.objects.filter(task=obj).count()

    comment_count.short_description = "Comments"


admin.site.register(Task, TaskAdmin)
