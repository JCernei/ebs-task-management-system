import json
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from minio.error import S3Error
from rest_framework import status
from rest_framework.test import APITestCase
from urllib3 import HTTPResponse

from apps.tasks.models import Task, TimeLog, Comment, Attachment
from apps.tasks.tasks import (
    send_weekly_report,
    clean_pending_uploads,
    process_attachment,
)
from apps.users.models import User


class TaskViewSetTests(APITestCase):
    fixtures = ["users", "tasks", "comments", "time_logs"]

    def setUp(self):
        # Login as Jane Smith (executor)
        self.user = User.objects.get(pk=2)
        self.client.force_authenticate(user=self.user)

        # Get existing task from fixtures
        self.task = Task.objects.get(pk=1)  # Fix Bug #101

        # Define common URLs
        self.task_list_url = reverse("tasks-list")
        self.task_detail_url = reverse("tasks-detail", kwargs={"pk": self.task.pk})

    def test_list_tasks(self):
        """Test retrieving a list of tasks"""
        response = self.client.get(self.task_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["results"]), 2
        )  # Should return both tasks from fixtures

    def test_retrieve_task(self):
        """Test retrieving a single task"""
        response = self.client.get(self.task_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["title"], "Fix Bug #101")
        self.assertEqual(response.data["executor"]["email"], "jane.smith@example.com")

    def test_create_task(self):
        """Test creating a new task"""
        data = {
            "title": "New Test Task",
            "description": "Testing task creation",
            "owner": 1,
            "executor": 2,
        }
        response = self.client.post(self.task_list_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Task.objects.count(), 3)
        new_task = Task.objects.latest("id")
        self.assertEqual(new_task.title, "New Test Task")

    def test_update_task(self):
        """Test updating a task"""
        data = {
            "title": "Updated Bug Fix",
            "description": "Updated the critical bug in the production environment.",
            "status": "in_progress",
        }
        response = self.client.put(self.task_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "Updated Bug Fix")
        self.assertEqual(
            self.task.description,
            "Updated the critical bug in the production environment.",
        )
        self.assertEqual(self.task.status, "in_progress")

    def test_patch_task(self):
        """Test partially updating a task"""
        data = {"executor": 1, "status": "completed"}
        response = self.client.patch(self.task_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.executor.id, 1)
        self.assertEqual(self.task.status, "completed")

    def test_list_comments(self):
        """Test listing comments for a task"""
        url = reverse("tasks-comments", kwargs={"pk": self.task.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["text"], "This needs to be resolved ASAP.")

    def test_create_comment(self):
        """Test creating a comment for a task"""
        url = reverse("tasks-comments", kwargs={"pk": self.task.pk})
        data = {"text": "Working on the fix now"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Comment.objects.count(), 3)
        new_comment = Comment.objects.latest("id")
        self.assertEqual(new_comment.text, "Working on the fix now")
        self.assertEqual(new_comment.user, self.user)

    def test_list_time_logs(self):
        """Test listing time logs for a task"""
        url = reverse("tasks-logs", kwargs={"pk": self.task.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["duration"], "2:00:00")

    def test_create_manual_time_log(self):
        """Test creating a time log manually"""
        url = reverse("tasks-logs", kwargs={"pk": self.task.pk})
        end_time = timezone.now()
        data = {
            "user": self.user.id,
            "duration": 60,
            "end_time": end_time.isoformat(),
            "note": "Additional work on the bug",
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(TimeLog.objects.count(), 3)

    def test_start_timer(self):
        """Test starting a timer for a task"""
        url = reverse("tasks-logs-start", kwargs={"pk": self.task.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        latest_log = TimeLog.objects.latest("id")
        self.assertIsNone(latest_log.end_time)

    def test_stop_timer_without_note(self):
        """Test stopping a timer without providing a note"""
        # Create an active timer
        active_timer = TimeLog.objects.create(
            task=self.task, user=self.user, start_time=timezone.now()
        )

        url = reverse("tasks-logs-stop", kwargs={"pk": self.task.pk})

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        active_timer.refresh_from_db()
        self.assertEqual(active_timer.note, None)

    def test_stop_timer_append_note(self):
        """Test stopping a timer and appending to existing note"""
        # First create an active timer
        active_timer = TimeLog.objects.create(
            task=self.task,
            user=self.user,
            start_time=timezone.now(),
            note="started working on the bug",
        )
        data = {"note": "Taking a pause"}
        url = reverse("tasks-logs-stop", kwargs={"pk": self.task.pk})

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        active_timer.refresh_from_db()
        self.assertIsNotNone(active_timer.end_time)
        self.assertEqual(
            active_timer.note, "started working on the bug\nTaking a pause"
        )

    def test_stop_timer_with_note(self):
        """Test stopping a timer for a task"""
        # First create an active timer
        active_timer = TimeLog.objects.create(
            task=self.task,
            user=self.user,
            start_time=timezone.now(),
        )
        data = {"note": "Fixed the issue"}
        url = reverse("tasks-logs-stop", kwargs={"pk": self.task.pk})
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        active_timer.refresh_from_db()
        self.assertIsNotNone(active_timer.end_time)
        self.assertEqual(active_timer.note, "Fixed the issue")

    def test_cannot_start_multiple_timers(self):
        """Test that a user cannot start multiple timers"""
        # Create an active timer
        TimeLog.objects.create(
            task=self.task, user=self.user, start_time=timezone.now()
        )

        url = reverse("tasks-logs-start", kwargs={"pk": self.task.pk})
        data = {"user": self.user.id}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"], "You already have an active timer for this task."
        )

    def test_cannot_stop_timer_without_active_timer(self):
        """Test stopping a timer when no active timer exists"""
        url = reverse("tasks-logs-stop", kwargs={"pk": self.task.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "Not found.")


class ReportViewSetTests(APITestCase):
    fixtures = ["users", "tasks", "time_logs"]

    def setUp(self):
        self.user = User.objects.get(pk=2)  # Jane Smith
        self.client.force_authenticate(user=self.user)
        self.url = reverse("tasks-reports")

    def test_get_report(self):
        """Test getting time report"""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"]["total_logged_time"], 240)

        tasks = response.data["results"]["tasks"]
        self.assertEqual(len(tasks), 2)

        # Both tasks should have 120 minutes (2 hours) logged
        self.assertEqual(tasks[0]["logged_time"], 120)
        self.assertEqual(tasks[1]["logged_time"], 120)

    def test_get_report_with_date_filter(self):
        """Test getting report with date filter"""
        # Filter for Nov 7 only (should only get Task 1's time log)
        response = self.client.get(
            f"{self.url}?date_from=2024-11-07&date_to=2024-11-07"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["results"]["total_logged_time"], 120)  # 2 hours
        self.assertEqual(len(response.data["results"]["tasks"]), 1)
        self.assertEqual(response.data["results"]["tasks"][0]["id"], 1)

    def test_get_report_with_top_filter(self):
        """Test getting report with top filter"""
        # Add another time log to make one task have more time
        task = Task.objects.get(pk=1)
        TimeLog.objects.create(
            task=task,
            user=self.user,
            start_time="2024-10-18T08:00:00Z",
            end_time="2024-10-18T09:00:00Z",
        )

        response = self.client.get(f"{self.url}?top=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]["tasks"]), 1)
        self.assertEqual(
            response.data["results"]["tasks"][0]["id"], 1
        )  # Should be Task 1 with most time

    def test_filter_top_negative(self):
        """Test filter_top with negative value"""
        response = self.client.get(f"{self.url}?top=-1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_report_with_user_filter(self):
        """Test getting report for specific task"""
        response = self.client.get(f"{self.url}?user=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]["tasks"]), 1)
        self.assertEqual(response.data["results"]["tasks"][0]["id"], 2)
        self.assertEqual(response.data["results"]["total_logged_time"], 120)

    def test_get_report_with_null_total_duration(self):
        """Test total duration when all entries have NULL duration"""
        # Clear existing time logs
        TimeLog.objects.all().delete()
        task_null = Task.objects.create(title="Test Task")
        # Create new time log with NULL duration
        TimeLog.objects.create(
            task=task_null,
            user=self.user,
            start_time="2024-10-18T08:00:00Z",
            duration=None,
        )

        response = self.client.get(f"{self.url}?user=2")

        self.assertEqual(response.status_code, 200)
        # Total duration should be 0 when all durations are NULL
        self.assertEqual(response.data["results"]["total_logged_time"], 0)

    def test_report_with_multiple_invalid_filters(self):
        """Test report generation with multiple invalid filter parameters"""
        response = self.client.get(
            f"{self.url}?date_from=invalid&date_to=also-invalid&top=not-a-number"
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("date_from", response.data)
        self.assertIn("date_to", response.data)
        self.assertIn("top", response.data)


class TestTaskModelStr(APITestCase):
    fixtures = ["users", "tasks", "time_logs", "comments"]

    def setUp(self):
        self.user = User.objects.get(pk=2)
        self.client.force_authenticate(user=self.user)
        self.task = Task.objects.filter(pk=1).first()

    def test_task_str(self):
        """Test the string representation of Task model"""
        self.assertEqual(str(self.task), "Fix Bug #101")

    def test_comment_str(self):
        """Test the string representation of Comment model"""
        comment = Comment.objects.create(
            user=self.user, task=self.task, text="Test comment"
        )
        expected_str = f"Comment by {self.user} on {self.task.title}"
        self.assertEqual(str(comment), expected_str)

    def test_timelog_str(self):
        """Test the string representation of TimeLog model"""
        start_time = timezone.now()
        timelog = TimeLog.objects.create(
            task=self.task, user=self.user, start_time=start_time
        )
        expected_str = f"{self.user} - {self.task.title} on {start_time}"
        self.assertEqual(str(timelog), expected_str)

    def test_attachment_str(self):
        """Test the string representation of Attachment model"""
        attachment = Attachment.objects.create(task=self.task)
        expected_str = f"Attachment for {self.task.title}"
        self.assertEqual(str(attachment), expected_str)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
class TaskSignalTests(APITestCase):
    fixtures = ["users", "tasks", "comments"]

    def setUp(self):
        self.user1 = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)
        self.task1 = Task.objects.get(pk=1)
        self.task2 = Task.objects.get(pk=2)

    def test_send_task_assigned_notification(self):
        self.task1.executor = self.user1  # Reassign executor
        self.task1.save()

        # Check if an email is sent to the new executor
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user1.email, mail.outbox[0].to)
        self.assertIn(self.task1.title, mail.outbox[0].body)

    def test_send_comment_notification(self):
        Comment.objects.create(
            task=self.task1, user=self.user2, text="Another comment."
        )

        # Check if an email is sent to the executor of the task
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user2.email, mail.outbox[0].to)
        self.assertIn(self.task1.title, mail.outbox[0].subject)

    def test_send_task_completed_notification_with_commenters(self):
        Comment.objects.create(
            task=self.task1, user=self.user2, text="Another comment."
        )
        self.task1.status = "completed"
        self.task1.save()

        # Check if an email is sent to distinct commenters
        self.assertEqual(len(mail.outbox), 2)
        self.assertIn(self.user2.email, mail.outbox[0].to)
        self.assertIn(self.user1.email, mail.outbox[1].to)
        self.assertIn(self.task1.title, mail.outbox[0].subject)

    def test_send_task_completed_notification_no_commenters(self):
        Comment.objects.filter(
            task=self.task1
        ).delete()  # Ensure no comments on the task
        self.task1.status = "completed"
        self.task1.save()

        # No email should be sent as there are no commenters
        self.assertEqual(len(mail.outbox), 0)


class SendWeeklyReportTests(APITestCase):
    fixtures = ["users", "tasks"]

    def setUp(self):
        # Ensure emails are cleared before each test
        mail.outbox = []

        # Create time logs within the past week for both users
        self.user1 = User.objects.get(pk=1)
        self.user2 = User.objects.get(pk=2)
        self.task1 = Task.objects.get(pk=1)
        self.task2 = Task.objects.get(pk=2)

    def test_send_weekly_report(self):
        # Create time logs that are not older than one week
        now = timezone.now()
        TimeLog.objects.create(
            task=self.task1,
            user=self.user2,
            start_time=now - timedelta(days=3, hours=2),
            end_time=now - timedelta(days=3),
            note="Worked on fixing the bug.",
            duration=timedelta(hours=2),
        )
        TimeLog.objects.create(
            task=self.task2,
            user=self.user1,
            start_time=now - timedelta(days=5, hours=2),
            end_time=now - timedelta(days=5),
            note="Implemented API design.",
            duration=timedelta(hours=2),
        )
        # Run the task
        send_weekly_report()

        # Check that an email was sent to each user
        expected_emails_count = (
            User.objects.filter(
                user_time_logs__start_time__gte=timezone.now() - timedelta(days=7)
            )
            .distinct()
            .count()
        )
        self.assertEqual(len(mail.outbox), expected_emails_count)

        # Check the email content
        for user in User.objects.all():
            self.assertIn(user.email, [msg.to[0] for msg in mail.outbox])
            self.assertIn(
                "Your Weekly Time Report", [msg.subject for msg in mail.outbox]
            )

    def test_send_weekly_report_no_time_logs_last_week(self):
        # Create time logs that are older than one week
        now = timezone.now()
        TimeLog.objects.create(
            task=self.task1,
            user=self.user2,
            start_time=now - timedelta(days=10, hours=2),
            end_time=now - timedelta(days=10),
            note="Worked on fixing the bug (older).",
            duration=timedelta(hours=2),
        )
        TimeLog.objects.create(
            task=self.task2,
            user=self.user1,
            start_time=now - timedelta(days=14, hours=2),
            end_time=now - timedelta(days=14),
            note="Implemented API design (older).",
            duration=timedelta(hours=2),
        )

        # Run the task
        send_weekly_report()

        # No emails should be sent since there are no logs within the past week
        self.assertEqual(len(mail.outbox), 0)


class TaskAttachmentsTests(APITestCase):
    fixtures = ["users", "tasks"]

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.task = Task.objects.get(pk=1)
        self.client.force_authenticate(user=self.user)

    def test_list_attachments(self):
        """Test listing attachments for a task"""
        Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/1_example_file.txt",
            status="Uploaded",
        )
        url = reverse("tasks-attachments", kwargs={"pk": self.task.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_patch_attachment(self):
        """Test updating an attachment's name"""
        attachment = Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/1_example_file.txt",
            status="Pending Upload",
            name="example_file.txt",
        )
        url = reverse(
            "tasks-attachments-update",
            kwargs={"pk": self.task.pk, "attachment_id": attachment.pk},
        )
        data = {"name": "another_file_name.txt"}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        attachment.refresh_from_db()
        self.assertEqual(attachment.name, "another_file_name.txt")

    def test_generate_upload_url(self):
        """Test generating an upload URL for a task's attachment."""
        url = reverse("tasks-generate-attachment-url", kwargs={"pk": self.task.pk})
        data = {"file_name": "example_file.txt"}

        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("url", response.data)

        # Ensure the attachment is created with a Pending status
        attachment = Attachment.objects.get(task=self.task)
        self.assertEqual(attachment.status, "Pending Upload")
        self.assertIsNotNone(attachment.file)

    def test_webhook_listener_updates_attachment_status(self):
        """Test webhook listener for updating attachment status on S3 event."""
        attachment = Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/2_example_file.txt",
            status="Pending Upload",
        )
        payload = {
            "EventName": "s3:ObjectCreated:Put",
            "Key": "media/task_1/2_example_file.txt",
            "Records": [
                {
                    "s3": {
                        "object": {
                            "key": "task_1/2_example_file.txt",
                            "size": 1024,
                        }
                    }
                }
            ],
        }

        url = reverse("webhook-listener")
        response = self.client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify that the attachment status was updated
        attachment.refresh_from_db()
        self.assertEqual(attachment.status, "Uploaded")

    def test_webhook_listener_unknown_event(self):
        """Test webhook listener for dealing with unknown S3 event."""
        Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/3_example_file.txt",
            status="Uploaded",
        )
        payload = {
            "EventName": "s3:ObjectCreated:Delete",
            "Key": "media/task_1/3_example_file.txt",
            "Records": [
                {
                    "s3": {
                        "object": {
                            "key": "task_1/3_example_file.txt",
                            "size": 1024,
                        }
                    }
                }
            ],
        }

        url = reverse("webhook-listener")
        response = self.client.post(
            url, data=json.dumps(payload), content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data, {"detail": "Unknown event type"})

    def test_delete_task_cascade_attachments(self):
        """Test deleting a task cascades to its attachments."""
        Attachment.objects.create(
            task=self.task, user=self.user, file="example_file.txt"
        )
        self.assertEqual(Attachment.objects.count(), 1)

        url = reverse("tasks-detail", kwargs={"pk": self.task.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Attachment.objects.count(), 0)

    def test_attachment_report(self):
        """Test generating a report of uploaded attachments."""
        Attachment.objects.create(
            task_id=1,
            user=self.user,
            file="media/task_1/file1.txt",
            status="Uploaded",
            size=2048,
            created_at=timezone.now(),
        )
        Attachment.objects.create(
            task_id=1,
            user=self.user,
            file="media/task_1/file2.txt",
            status="Uploaded",
            size=1024,
            created_at=timezone.now(),
        )
        url = reverse("attachments-reports")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)  # One day of data
        self.assertEqual(
            response.data["results"][0]["total_volume_kb"], 3
        )  # 2048 + 1024 bytes
        self.assertEqual(response.data["results"][0]["total_files"], 2)

    def test_attachment_report_empty(self):
        """Test generating a report with no uploaded attachments."""
        url = reverse("attachments-reports")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 0)


class TaskSearchTests(APITestCase):
    fixtures = ["users", "tasks", "comments"]

    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.task = Task.objects.get(pk=1)
        self.client.force_authenticate(user=self.user)

    def test_search_existing_tasks(self):
        """Test searching for existing tasks"""
        url = reverse("search-tasks")
        response = self.client.get(url, {"search": "API"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(
            response.data["results"][0]["title"], "Design API for Comments"
        )

    def test_search_newly_created_task(self):
        """Test searching for newly created tasks"""
        Task.objects.create(
            title="New Task",
            description="New task description",
            owner=self.user,
            executor=self.user,
        )
        url = reverse("search-tasks")
        response = self.client.get(url, {"search": "New Task"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["title"], "New Task")

    def test_search_existing_comments(self):
        """Test searching for existing comments"""
        url = reverse("search-comments")
        response = self.client.get(url, {"search": "API"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["text"], "API design looks good.")

    def test_search_newly_created_comment(self):
        """Test searching for newly created comments"""
        Comment.objects.create(task=self.task, text="New Comment", user=self.user)
        url = reverse("search-comments")
        response = self.client.get(url, {"search": "New Comment"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["text"], "New Comment")


class CleanPendingUploadsTaskTests(APITestCase):
    fixtures = ["users", "tasks"]

    def setUp(self):
        self.task = Task.objects.get(pk=1)
        self.user = User.objects.get(pk=1)

    @patch("apps.tasks.tasks.default_storage.client.stat_object")
    @patch("apps.tasks.tasks.default_storage.client.remove_object")
    def test_process_existing_attachment(self, mock_remove, mock_stat):
        """Test processing an existing attachment with a valid size."""
        attachment = Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/valid_file.txt",
            status="Pending Upload",
        )
        mock_stat.return_value.size = 2048  # Mock the object size

        was_deleted, was_updated = process_attachment(attachment)
        attachment.refresh_from_db()
        self.assertFalse(was_deleted)
        self.assertTrue(was_updated)
        self.assertEqual(attachment.status, "Uploaded")
        mock_remove.assert_not_called()
        mock_stat.assert_called_once()

    @patch("apps.tasks.tasks.default_storage.client.stat_object")
    def test_process_missing_attachment(self, mock_stat):
        """Test processing a missing attachment (object not found)."""
        attachment = Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/missing_file.txt",
            status="Pending Upload",
        )
        mock_stat.side_effect = S3Error(
            code="NoSuchKey",
            message="The specified key does not exist.",
            resource="media/task_1/missing_file.txt",
            request_id="dummy-request-id",
            host_id="dummy-host-id",
            response=HTTPResponse(),
        )

        was_deleted, was_updated = process_attachment(attachment)
        self.assertTrue(was_deleted)
        self.assertFalse(was_updated)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())

    @patch("apps.tasks.tasks.default_storage.client.stat_object")
    @patch("apps.tasks.tasks.default_storage.client.remove_object")
    def test_process_zero_size_attachment(self, mock_remove, mock_stat):
        """Test processing an attachment with a size of zero."""
        attachment = Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/zero_size_file.txt",
            status="Pending Upload",
        )
        mock_stat.return_value.size = 0  # Mock size 0

        was_deleted, was_updated = process_attachment(attachment)
        self.assertTrue(was_deleted)
        self.assertFalse(was_updated)
        self.assertFalse(Attachment.objects.filter(pk=attachment.pk).exists())
        mock_remove.assert_called_once()

    @patch("apps.tasks.tasks.process_attachment")
    def test_clean_pending_uploads(self, mock_process):
        """Test cleaning pending uploads older than threshold time."""
        Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/old_file.txt",
            status="Pending Upload",
            created_at=timezone.now() - timedelta(days=2),
            size=2048,
        )

        Attachment.objects.create(
            task=self.task,
            user=self.user,
            file="media/task_1/recent_file.txt",
            status="Pending Upload",
            created_at=timezone.now() - timedelta(days=2),
            size=1024,
        )

        mock_process.side_effect = [
            (True, False),
            (False, True),
        ]
        result = clean_pending_uploads()

        self.assertEqual(result, "Pending: 2, Deleted: 1, Updated: 1")
