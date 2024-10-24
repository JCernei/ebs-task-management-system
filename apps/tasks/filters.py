from django.utils import timezone
from django_filters import rest_framework as filters

from apps.tasks.models import Task, TimeLog


class TaskFilter(filters.FilterSet):
    class Meta:
        model = Task
        fields = ['is_completed', 'executor']


class TimeLogFilter(filters.FilterSet):
    user = filters.NumberFilter(field_name='user__id')
    top = filters.NumberFilter(method='filter_top')
    date_from = filters.DateFilter(
        field_name='end_time__date',
        lookup_expr='gte',
        help_text='Filter logs from this date (inclusive, format: YYYY-MM-DD)'
    )
    date_to = filters.DateFilter(
        field_name='end_time__date',
        lookup_expr='lte',
        help_text='Filter logs until this date (inclusive, format: YYYY-MM-DD)'
    )

    class Meta:
        model = TimeLog
        fields = ['user', 'date_from', 'date_to', 'top']

    def filter_top(self, queryset, name, value):
        """Store top value for later use in view"""
        if value and value > 0:
            self.top = value
        return queryset

    def filter_queryset(self, queryset):
        """
        Apply default date filter if no dates specified
        """
        queryset = super().filter_queryset(queryset)

        # If no date filters provided, default to current month
        if not any(key in self.data for key in ['date_from', 'date_to']):
            today = timezone.now().date()
            first_day = today.replace(day=1)
            queryset = queryset.filter(
                end_time__date__gte=first_day,
                end_time__date__lte=today
            )

        return queryset
