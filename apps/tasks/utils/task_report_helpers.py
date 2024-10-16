import re

from django.db.models import Sum, F, ExpressionWrapper, DurationField
from django.utils import timezone


def _parse_interval(interval):
    match = re.match(r'(\d+)\s*(days?|weeks?|months?)', interval.lower())
    if match:
        number = int(match.group(1))
        unit = match.group(2)
        return number, unit
    return None, None


def filter_time_logs_by_time_interval(time_logs, interval):
    now = timezone.now()
    number, unit = _parse_interval(interval)

    if unit == 'day' or unit == 'days':
        return time_logs.filter(date__gte=now - timezone.timedelta(days=number))
    elif unit == 'week' or unit == 'weeks':
        return time_logs.filter(date__gte=now - timezone.timedelta(weeks=number))
    elif unit == 'month' or unit == 'months':
        first_day_of_last_month = now.replace(day=1) - timezone.timedelta(days=1)
        last_day_of_last_month = first_day_of_last_month.replace(day=1)
        return time_logs.filter(date__gte=last_day_of_last_month, date__lte=first_day_of_last_month)

    return time_logs


def apply_top_limit(tasks_with_time, top_param):
    if top_param > 0:
        return sorted(tasks_with_time, key=lambda x: x['total_duration'], reverse=True)[:top_param]
    return tasks_with_time


def calculate_total_logged_time(queryset):
    total_time = queryset.aggregate(
        total_duration=Sum(
            ExpressionWrapper(F('duration'), output_field=DurationField())
        )
    )['total_duration']

    return total_time.total_seconds() // 60 if total_time else 0
