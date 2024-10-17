from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.tasks.models import Task, TimeLog
from apps.tasks.serializers import TimeLogListSerializer
from apps.users.models import User


class TaskCRUDTestCase(APITestCase):
    fixtures = ['users', 'tasks']

    def setUp(self):
        # Authenticate with user John
        self.client.force_authenticate(user=User.objects.get(pk=1))

    def test_create_task(self):
        url = reverse('tasks-list')
        data = {
            "title": "New Task",
            "description": "This is a new task.",
            "executor": 2
        }
        response = self.client.post(url, data, format='json')

        # Assert the task creation is successful
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert that the task was created in the database
        self.assertTrue(Task.objects.filter(title=data["title"]).exists())

    def test_list_tasks(self):
        url = reverse('tasks-list')
        response = self.client.get(url)

        # Assert that the task list request is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that the tasks from the fixture are in the returned list
        self.assertGreaterEqual(len(response.data), 2)

    def test_retrieve_task(self):
        url = reverse('tasks-detail', args=[1])
        response = self.client.get(url)

        # Assert that the task retrieval is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that the retrieved task matches the expected data
        self.assertEqual(response.data['title'], 'Fix Bug #101')

    def test_update_task(self):
        url = reverse('tasks-detail', args=[1])
        data = {
            "executor": 1,
            "is_completed": True
        }
        response = self.client.patch(url, data, format='json')

        # Assert that the task update is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that the task has been updated in the database
        task = Task.objects.get(pk=1)
        self.assertEqual(task.executor, User.objects.get(pk=1))
        self.assertTrue(task.is_completed)

    def test_delete_task(self):
        url = reverse('tasks-detail', args=[1])
        response = self.client.delete(url)

        # Assert that the task deletion is successful
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Assert that the task is no longer in the database
        self.assertFalse(Task.objects.filter(pk=1).exists())


class TaskCommentTestCase(APITestCase):
    fixtures = ['users', 'tasks', 'comments']

    def setUp(self):
        # Authenticate with user John
        self.client.force_authenticate(user=User.objects.get(pk=1))

    def test_add_comment_to_task(self):
        url = reverse('tasks-comments', args=[1])
        data = {
            "text": "This is a comment on task #1"
        }
        response = self.client.post(url, data, format='json')

        # Assert the comment creation is successful
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert that the comment was added to the task
        task = Task.objects.get(pk=1)
        self.assertTrue(task.comments.filter(text=data["text"]).exists())

    def test_list_comments_of_task(self):
        url = reverse('tasks-comments', args=[1])
        response = self.client.get(url)

        # Assert that the comment list request is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that there are comments for the task
        self.assertGreaterEqual(len(response.data), 1)


class TaskTimeLogsTestCase(APITestCase):
    fixtures = ['users', 'tasks', 'time_logs']

    def setUp(self):
        # Authenticate with user John
        self.client.force_authenticate(user=User.objects.get(pk=1))

    def test_list_logs(self):
        # List logs for the task
        url = reverse('tasks-logs', args=[1])
        response = self.client.get(url)

        # Assert that the logs are returned successfully
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert that the response contains the expected logs
        logs = TimeLog.objects.filter(task_id=1)
        serializer = TimeLogListSerializer(logs, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_create_logs(self):
        # Create a log for the task
        url = reverse('tasks-logs', args=[1])
        data = {
            "date": timezone.now().date(),
            "duration": 30,  # duration in minutes
            "note": "Worked on task.",
        }
        response = self.client.post(url, data, format='json')

        # Assert the log creation is successful
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert that the log was created in the database
        self.assertTrue(TimeLog.objects.filter(task_id=1, note=data["note"]).exists())

        # Check the created log entry details
        log = TimeLog.objects.get(task_id=1, note=data["note"])
        self.assertEqual(log.duration, timezone.timedelta(minutes=data["duration"]))

    def test_start_and_stop_task_timer(self):
        # Start the timer
        start_url = reverse('tasks-logs-start', args=[1])
        response = self.client.post(start_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the task now has a start time logged
        task = Task.objects.get(pk=1)
        self.assertTrue(task.time_logs.filter(start_time__isnull=False).exists())

        # Stop the timer
        stop_url = reverse('tasks-logs-stop', args=[1])
        data = {
            "note": "Finished task."
        }
        response = self.client.post(stop_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the task now has a stop time logged
        log = task.time_logs.last()
        self.assertIsNotNone(log.end_time)

    def test_start_timer_twice(self):
        # Start the timer
        start_url = reverse('tasks-logs-start', args=[1])
        response = self.client.post(start_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Attempt to start the timer again
        response = self.client.post(start_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'You already have an active timer for this task.')

    def test_stop_timer_without_starting(self):
        # Attempt to stop the timer without starting it
        stop_url = reverse('tasks-logs-stop', args=[1])
        data = {
            "note": "Finished task."
        }
        response = self.client.post(stop_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['detail'], 'No active timer found for this task.')


class TaskReportTestCase(APITestCase):
    fixtures = ['users', 'tasks', 'comments', 'time_logs']

    def setUp(self):
        # Authenticate with user John
        self.client.force_authenticate(user=User.objects.get(pk=1))

    def test_retrieve_report_without_params(self):
        url = reverse('tasks-reports')
        response = self.client.get(url)

        # Assert the report retrieval is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertIn('total_logged_time', response.data)
        self.assertIn('tasks', response.data)

    def test_retrieve_report_with_top_param(self):
        url = reverse('tasks-reports') + '?top=2'  # Limit to 2 results
        response = self.client.get(url)

        # Assert the report retrieval is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the response data contains at most 2 tasks
        self.assertLessEqual(len(response.data['tasks']), 2)

    def test_retrieve_report_with_interval_param(self):
        url = reverse('tasks-reports') + '?interval=1 week'  # Filter logs for the last week
        response = self.client.get(url)

        # Assert the report retrieval is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_report_with_both_params(self):
        url = reverse('tasks-reports') + '?top=3&interval=1 month'  # Limit to 3 results for the last month
        response = self.client.get(url)

        # Assert the report retrieval is successful
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Assert the response data contains at most 3 tasks
        self.assertLessEqual(len(response.data['tasks']), 3)
