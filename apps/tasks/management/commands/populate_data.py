import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker
from apps.tasks.models import Task, TimeLog
from apps.users.models import User

fake = Faker()

class Command(BaseCommand):
    help = 'Populate database with random users, tasks, and time logs'

    def handle(self, *args, **kwargs):
        users = []

        # Create 100 random users
        for _ in range(100):
            user = User(
                email=fake.email(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                is_superuser=fake.boolean(),
                is_staff=fake.boolean(),
            )
            password=fake.password()
            user.set_password(password)
            users.append(user)

        # Bulk create users
        User.objects.bulk_create(users)
        self.stdout.write(self.style.SUCCESS('Successfully added 100 users.'))

        # Refresh list of created users
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR('No users found in the database.'))
            return

        status_choices = dict(Task.STATUS_CHOICES)
        tasks = []
        time_logs = []

        # Create 25,000 random tasks
        for _ in range(25000):
            task = Task(
                title=fake.sentence(),
                description=fake.text(),
                status=random.choice(list(status_choices.keys())),
                owner=random.choice(users),
                executor=random.choice(users),
            )
            tasks.append(task)

        # Bulk create tasks
        Task.objects.bulk_create(tasks)
        self.stdout.write(self.style.SUCCESS('Successfully added 25,000 tasks.'))

        # Fetch created tasks
        created_tasks = Task.objects.all()

        # Create 50,000 random time logs
        for _ in range(50000):
            start_time = fake.date_time_this_year(before_now=True, after_now=False, tzinfo=timezone.now().tzinfo)
            end_time = start_time + timedelta(minutes=random.randint(10, 300))

            time_log = TimeLog(
                task=random.choice(created_tasks),
                user=random.choice(users),
                start_time=start_time,
                end_time=end_time,
                note=fake.sentence(),
            )
            time_logs.append(time_log)

        # Bulk create time logs
        TimeLog.objects.bulk_create(time_logs)
        self.stdout.write(self.style.SUCCESS('Successfully added 50,000 time logs.'))

