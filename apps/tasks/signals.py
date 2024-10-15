from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.tasks.models import Task, Comment
from apps.tasks.utils.email_notifications import send_task_assigned_email, send_task_commented_email, \
    send_task_completed_email


@receiver(pre_save, sender=Task)
def capture_old_task_state(sender, instance, **kwargs):
    if instance.pk:
        old_task = Task.objects.get(pk=instance.pk)
        instance._old_executor = old_task.executor
        instance._was_completed = old_task.is_completed


@receiver(post_save, sender=Task)
def send_task_assigned_notification(sender, instance, created, **kwargs):
    if created and instance.executor:
        send_task_assigned_email(instance.executor.email, instance.title)

    if not created and hasattr(instance, '_old_executor'):
        old_executor = instance._old_executor
        if old_executor != instance.executor:
            send_task_assigned_email(instance.executor.email, instance.title)


@receiver(post_save, sender=Comment)
def send_comment_notification(sender, instance, created, **kwargs):
    if created:
        task = instance.task
        commenter_name = instance.user.get_full_name()
        comment_text = instance.text
        send_task_commented_email(task.executor.email, task.title, commenter_name, comment_text)


@receiver(post_save, sender=Task)
def send_task_completed_notification(sender, instance, **kwargs):
    commenters = Comment.objects.filter(task=instance).values_list('user__email', flat=True).distinct()

    if hasattr(instance, '_was_completed') and not instance._was_completed and instance.is_completed:
        send_task_completed_email(list(commenters), instance.title)
