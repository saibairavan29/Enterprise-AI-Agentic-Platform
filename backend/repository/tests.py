import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from repository.models import KnowledgeDocument, KnowledgeRecord, KnowledgeDocumentVersion
from repository.validators.repository_validator import RepositoryValidator
from repository.exceptions import ValidationException
from repository.services.stages.version_diff_stage import VersionDiffStage

User = get_user_model()

class RepositoryLogicTests(TestCase):
    """
    Unit tests for repository synchronization rules, record diff computations,
    and validation constraints.
    """
    def test_record_diff_only_added(self):
        """
        Verify added records detection when no previous version exists.
        """
        diff_stage = VersionDiffStage()
        old_records = []
        new_records = [
            {"employee_id": "EMP1", "email": "a@co.com", "salary": 5000},
            {"employee_id": "EMP2", "email": "b@co.com", "salary": 6000}
        ]
        
        summary = diff_stage._calculate_diff(old_records, new_records)
        self.assertEqual(summary["added_count"], 2)
        self.assertEqual(summary["removed_count"], 0)
        self.assertEqual(summary["modified_count"], 0)
        self.assertEqual(summary["added_sample"][0]["employee_id"], "EMP1")

    def test_record_diff_modified_and_removed(self):
        """
        Verify added, removed, and modified records classification based on unique fields.
        """
        diff_stage = VersionDiffStage()
        old_records = [
            {"employee_id": "EMP1", "email": "a@co.com", "salary": 5000},
            {"employee_id": "EMP2", "email": "b@co.com", "salary": 6000}
        ]
        new_records = [
            {"employee_id": "EMP1", "email": "a@co.com", "salary": 5500}, # Modified
            {"employee_id": "EMP3", "email": "c@co.com", "salary": 7000}  # Added
            # EMP2 Removed
        ]
        
        summary = diff_stage._calculate_diff(old_records, new_records)
        self.assertEqual(summary["added_count"], 1)
        self.assertEqual(summary["removed_count"], 1)
        self.assertEqual(summary["modified_count"], 1)
        self.assertEqual(summary["modified_sample"][0]["key_value"], "EMP1")
        self.assertEqual(summary["modified_sample"][0]["after"]["salary"], 5500)

    def test_record_diff_no_unique_keys_fallback(self):
        """
        Verify tuple hash matching behavior when no standard unique key is present.
        """
        diff_stage = VersionDiffStage()
        old_records = [
            {"role": "staff", "dept": "HR"},
            {"role": "director", "dept": "Sales"}
        ]
        new_records = [
            {"role": "staff", "dept": "HR"},
            {"role": "vp", "dept": "Sales"}
        ]
        
        summary = diff_stage._calculate_diff(old_records, new_records)
        self.assertEqual(summary["added_count"], 1) # VP added
        self.assertEqual(summary["removed_count"], 1) # Director removed
        self.assertEqual(summary["modified_count"], 0) # Fallback doesn't yield modified

    def test_validator_fails_on_empty_doc(self):
        """
        Verify that validator rejects empty document ID payloads.
        """
        with self.assertRaises(ValidationException):
            RepositoryValidator.validate_sync_payload(None, [], {})


class RepositoryAPITests(APITestCase):
    """
    API integration tests validating CRUD routes, role validations,
    and generalized PostgreSQL JSONB query parameters.
    """
    def setUp(self):
        # Create standard users
        self.admin = User.objects.create_user(
            username="admin_user",
            email="admin@co.com",
            password="pwd",
            role="admin"
        )
        self.reader = User.objects.create_user(
            username="reader_user",
            email="reader@co.com",
            password="pwd",
            role="reader"
        )
        
        # Paths
        self.docs_url = reverse('documents-list')
        self.records_url = reverse('records-list')

    def test_reader_cannot_post_sync(self):
        """
        Verify that a reader is blocked from manually triggering synchronizations.
        """
        self.client.force_authenticate(user=self.reader)
        response = self.client.post(self.docs_url, {"document_id": 1, "reason": "sync"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_requests_denied(self):
        """
        Verify that guest requests are rejected.
        """
        response = self.client.get(self.docs_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_personal_repository_access_isolation(self):
        """
        Verify that a personal document uploaded by User A is visible only to User A (and admin),
        and remains hidden (returns 404/403) for User B.
        """
        from ingestion.models import Document
        # Create user B (another reader)
        user_b = User.objects.create_user(
            username="user_b",
            email="user_b@co.com",
            password="pwd",
            role="reader"
        )
        
        # Create ingestion Document for User A
        source_doc_a = Document.objects.create(
            uploaded_by=self.reader,
            file="raw/personal_test.csv",
            file_hash="dummy-sha-personal",
            original_name="personal_test.csv",
            file_size=100,
            mime_type="text/csv",
            metadata={"repository_type": "personal"}
        )
        
        # Create synced KnowledgeDocument for User A
        personal_doc = KnowledgeDocument.objects.create(
            source_document=source_doc_a,
            title="personal_test.csv",
            current_version=1,
            repository_status="ACTIVE",
            metadata={"repository_type": "personal"}
        )
        
        # 1. User A checks: visible
        self.client.force_authenticate(user=self.reader)
        response = self.client.get(self.docs_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify document is in User A's list
        doc_ids = [d["id"] for d in response.data["data"]]
        self.assertIn(str(personal_doc.id), doc_ids)
        
        # User A direct detail retrieve: visible
        detail_url = reverse('documents-detail', kwargs={'pk': personal_doc.id})
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 2. User B checks: NOT visible in list
        self.client.force_authenticate(user=user_b)
        response = self.client.get(self.docs_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        doc_ids_b = [d["id"] for d in response.data["data"]]
        self.assertNotIn(str(personal_doc.id), doc_ids_b)
        
        # User B direct detail retrieve: 404 Not Found
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        
        # User B direct view_file retrieve: 404 Not Found
        view_file_url = detail_url + "view_file/"
        response = self.client.get(view_file_url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_team_repository_access(self):
        """
        Verify that a team document is visible to all authenticated users.
        """
        from ingestion.models import Document
        source_doc_team = Document.objects.create(
            uploaded_by=self.admin,
            file="raw/team_test.csv",
            file_hash="dummy-sha-team",
            original_name="team_test.csv",
            file_size=100,
            mime_type="text/csv",
            metadata={"repository_type": "team"}
        )
        team_doc = KnowledgeDocument.objects.create(
            source_document=source_doc_team,
            title="team_test.csv",
            current_version=1,
            repository_status="ACTIVE",
            metadata={"repository_type": "team"}
        )
        
        # Both self.reader and self.admin can view it
        self.client.force_authenticate(user=self.reader)
        response = self.client.get(self.docs_url)
        doc_ids = [d["id"] for d in response.data["data"]]
        self.assertIn(str(team_doc.id), doc_ids)
