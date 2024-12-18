from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.storage import default_storage
from django.core.mail import send_mail
from django.db.models import F, Sum, DurationField, ExpressionWrapper
from django.template.loader import render_to_string
from django.utils import timezone
from minio.error import S3Error

from apps.tasks.models import TimeLog, Attachment


@shared_task
def send_task_assigned_email(user_email, task_title):
    subject = "[EBS-Task-Management] New task assigned"
    message = f"You have been assigned a task: {task_title}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])


@shared_task
def send_task_commented_email(user_email, task_title, commenter_name, comment_text):
    subject = f"[EBS-Task-Management] New comment on task: {task_title}"
    message = f"Comment Preview:\n{commenter_name}: {comment_text}"
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])


@shared_task
def send_task_completed_email(commenters_emails, task_title):
    subject = f"[EBS-Task-Management] Task Completed: {task_title}"
    message = f'The task "{task_title}" has been marked as completed.'
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        commenters_emails,
    )


@shared_task
def send_weekly_report():
    User = get_user_model()
    users = User.objects.all()

    # Get date range for the past week
    end_date = timezone.now()
    start_date = end_date - timedelta(days=7)

    for user in users:
        # Get user's time logs for the past week
        queryset = TimeLog.objects.filter(
            user=user,
            start_time__lt=end_date,  # Start time must be before the end date
            end_time__gte=start_date,  # End time must be after the start date
        )

        # Check if there are any time logs for the user
        if not queryset.exists():
            continue

        # Aggregate tasks data
        tasks = (
            queryset.values("task__id", "task__title")
            .annotate(
                total_duration=Sum(
                    ExpressionWrapper(F("duration"), output_field=DurationField())
                )
            )
            .order_by("-total_duration")[:20]
        )

        # Calculate total time
        total_duration = queryset.aggregate(
            total_duration=Sum(
                ExpressionWrapper(F("duration"), output_field=DurationField())
            )
        )["total_duration"]

        # Convert duration to minutes
        formatted_tasks = [
            {
                "title": task["task__title"],
                "logged_time": int(task["total_duration"].total_seconds() // 60),
            }
            for task in tasks
        ]

        total_minutes = (
            int(total_duration.total_seconds() // 60) if total_duration else 0
        )

        # Render email template
        html_content = render_to_string(
            "emails/weekly_report.html",
            {
                "tasks": formatted_tasks,
                "total_logged_time": total_minutes,
            },
        )

        # Send email
        send_mail(
            subject="Your Weekly Time Report",
            message="",  # Empty string for plain text version
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )


def process_attachment(attachment):
    minio_client = default_storage.client
    bucket_name = settings.MINIO_MEDIA_FILES_BUCKET

    object_name = attachment.file.name
    try:
        object_stats = minio_client.stat_object(bucket_name, object_name)
    except S3Error:
        attachment.delete()
        return True, False

    if object_stats.size > 0:
        attachment.status = "Uploaded"
        attachment.save(update_fields=["status"])
        return False, True

    minio_client.remove_object(bucket_name, object_name)
    attachment.delete()
    return True, False


@shared_task
def clean_pending_uploads():
    upper_threshold_time = timezone.now() - timedelta(days=1)
    lower_threshold_time = timezone.now() - timedelta(days=3)

    pending_attachments = Attachment.objects.filter(
        status="Pending Upload",
        created_at__lt=upper_threshold_time,
        created_at__gte=lower_threshold_time,
    )

    deleted_count = 0
    updated_count = 0
    for attachment in pending_attachments:
        was_deleted, was_updated = process_attachment(attachment=attachment)
        if was_deleted:
            deleted_count += 1
        if was_updated:
            updated_count += 1

    return f"Pending: {len(pending_attachments)}, Deleted: {deleted_count}, Updated: {updated_count}"
