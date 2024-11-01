from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from apps.tasks.models import TimeLog
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Sum, F, ExpressionWrapper, DurationField

class Command(BaseCommand):
    help = 'Send weekly time report emails to users'

    def handle(self, *args, **kwargs):
        User = get_user_model()
        users = User.objects.all()

        # Get date range for the past week
        end_date = timezone.now()
        start_date = end_date - timedelta(days=7)

        for user in users:
            # Get user's time logs for the past week
            queryset = TimeLog.objects.filter(
                user=user,
                start_time__lt=end_date,
                end_time__gte=start_date,
            )

            # Aggregate tasks data
            tasks = (
                queryset
                .values('task__id', 'task__title')
                .annotate(
                    total_duration=Sum(
                        ExpressionWrapper(
                            F('duration'),
                            output_field=DurationField()
                        )
                    )
                )
                .order_by('-total_duration')[:20]
            )

            # Calculate total time
            total_duration = queryset.aggregate(
                total_duration=Sum(
                    ExpressionWrapper(
                        F('duration'),
                        output_field=DurationField()
                    )
                )
            )['total_duration']

            # Convert duration to minutes
            formatted_tasks = [
                {
                    'title': task['task__title'],
                    'logged_time': int(task['total_duration'].total_seconds() // 60)
                }
                for task in tasks
            ]

            total_minutes = int(total_duration.total_seconds() // 60) if total_duration else 0

            # Render email template
            html_content = render_to_string('emails/weekly_report.html', {
                'tasks': formatted_tasks,
                'total_logged_time': total_minutes,
            })

            # Send email
            send_mail(
                subject='Your Weekly Time Report',
                message='',  # Empty string for plain text version
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False,
            )

        self.stdout.write(self.style.SUCCESS('Successfully sent weekly reports.'))
