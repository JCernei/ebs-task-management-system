from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail


@shared_task
def send_task_assigned_email(user_email, task_title):
    subject = '[EBS-Task-Management] New task assigned'
    message = f'You have been assigned a task: {task_title}'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])


@shared_task
def send_task_commented_email(user_email, task_title, commenter_name, comment_text):
    subject = f'[EBS-Task-Management] New comment on task: {task_title}'
    message = f'Comment Preview:\n{commenter_name}: {comment_text}'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user_email])


@shared_task
def send_task_completed_email(commenters_emails, task_title):
    subject = f'[EBS-Task-Management] Task Completed: {task_title}'
    message = f'The task "{task_title}" has been marked as completed.'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, commenters_emails, )
