import os
import io
import hashlib
from django.test import TestCase
from django.contrib.auth import get_user_model
from ingestion.models import Document, ProcessedEmail
from repository.models import KnowledgeDocument
from ingestion.services.email_collector_service import EmailCollectorService
from ingestion.tasks import poll_gmail_inbox_task, process_email_message_task

User = get_user_model()

class EnterpriseEmailIngestionTestCase(TestCase):
    """
    Comprehensive test suite verifying Real-Time Enterprise Email Ingestion:
    - Test 1: Email Without Attachment (Scenario A)
    - Test 2: PDF Attachment (Scenario B)
    - Test 3: Excel / CSV Attachment (Scenario B)
    - Test 4: Image Attachment (Scenario B)
    - Test 5: Duplicate Attachment SHA-256 Protection
    - Test 6: Repeated Email Polling & Idempotency
    """

    def setUp(self):
        self.collector = EmailCollectorService()
        self.user = User.objects.create_superuser(
            username='test_admin',
            email='erpsystementerprises@gmail.com',
            password='password123'
        )

    def test_01_email_without_attachment_scenario_a(self):
        """
        Test 1 — Email Without Attachment:
        Authorized sender -> ERP Gmail -> meeting schedule / notification -> email body extracted -> existing pipeline invoked.
        """
        raw_email = (
            b"From: bharathwaj271192@gmail.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: Enterprise Q4 Operations Meeting Schedule\r\n"
            b"Message-ID: <TEST_MSG_001_NO_ATT@mail.gmail.com>\r\n"
            b"Date: Sat, 26 Sep 2026 10:00:00 +0000\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
            b"The Q4 Operations Review meeting is scheduled for Monday at 10:00 AM in Conference Room B.\r\n"
            b"Agenda: Procurement budget review, HR attrition metrics, and AI Engineering status.\r\n"
        )

        parsed_email = self.collector.parse_raw_email(raw_email)
        self.assertEqual(parsed_email["message_id"], "TEST_MSG_001_NO_ATT@mail.gmail.com")
        self.assertEqual(parsed_email["sender"], "bharathwaj271192@gmail.com")
        self.assertEqual(parsed_email["recipient"], "erpsystementerprises@gmail.com")
        self.assertEqual(parsed_email["subject"], "Enterprise Q4 Operations Meeting Schedule")
        self.assertIn("Q4 Operations Review meeting is scheduled", parsed_email["body"])
        self.assertEqual(len(parsed_email["attachments"]), 0)

        # Process through Celery task pipeline
        res = process_email_message_task(parsed_email)
        self.assertEqual(res["status"], "SUCCESS")

        # Verify DB records created
        proc_email = ProcessedEmail.objects.get(message_id="TEST_MSG_001_NO_ATT@mail.gmail.com")
        self.assertEqual(proc_email.status, "SUCCESS")
        self.assertFalse(proc_email.has_attachments)
        self.assertEqual(proc_email.documents.count(), 1)

        doc = proc_email.documents.first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.metadata.get("gmail_source"), "gmail_imap")
        self.assertEqual(doc.metadata.get("authorized_sender"), "bharathwaj271192@gmail.com")

    def test_02_pdf_attachment_scenario_b(self):
        """
        Test 2 — PDF Attachment:
        Authorized sender -> ERP Gmail -> PDF attachment -> MIME detection -> existing PDF parser -> pipeline ingested.
        """
        pdf_content = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\n"
            b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
        )
        
        raw_email = (
            b"From: bharathwaj271192@gmail.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: Monthly Operations PDF Report\r\n"
            b"Message-ID: <TEST_MSG_002_PDF@mail.gmail.com>\r\n"
            b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
            b"--BOUNDARY\r\n"
            b"Content-Type: text/plain\r\n\r\n"
            b"Please find attached the monthly report.\r\n\r\n"
            b"--BOUNDARY\r\n"
            b"Content-Type: application/pdf\r\n"
            b"Content-Disposition: attachment; filename=\"meeting_report.pdf\"\r\n\r\n" +
            pdf_content + b"\r\n--BOUNDARY--\r\n"
        )

        parsed_email = self.collector.parse_raw_email(raw_email)
        self.assertEqual(len(parsed_email["attachments"]), 1)
        self.assertEqual(parsed_email["attachments"][0]["filename"], "meeting_report.pdf")

        res = process_email_message_task(parsed_email)
        self.assertEqual(res["status"], "SUCCESS")

        proc_email = ProcessedEmail.objects.get(message_id="TEST_MSG_002_PDF@mail.gmail.com")
        self.assertTrue(proc_email.has_attachments)

        doc = Document.objects.filter(original_name="meeting_report.pdf").first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.mime_type, "application/pdf")
        self.assertEqual(doc.parser_type, "PDF")

    def test_03_excel_csv_attachment(self):
        """
        Test 3 — Excel / CSV Attachment:
        Email with CSV attachment -> MIME detection -> existing CSV parser -> pipeline ingested.
        """
        csv_content = b"Order_ID,Product,Quantity,Net_Amount\nSO1001,Control Panel,10,250000\nSO1002,Sensor,5,90000\n"
        
        raw_email = (
            b"From: bharathwaj271192@gmail.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: Sales Orders Dataset Upload\r\n"
            b"Message-ID: <TEST_MSG_003_CSV@mail.gmail.com>\r\n"
            b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
            b"--BOUNDARY\r\n"
            b"Content-Type: text/plain\r\n\r\n"
            b"Sales orders file attached.\r\n\r\n"
            b"--BOUNDARY\r\n"
            b"Content-Type: text/csv\r\n"
            b"Content-Disposition: attachment; filename=\"sales_orders.csv\"\r\n\r\n" +
            csv_content + b"\r\n--BOUNDARY--\r\n"
        )

        parsed_email = self.collector.parse_raw_email(raw_email)
        res = process_email_message_task(parsed_email)
        self.assertEqual(res["status"], "SUCCESS")

        doc = Document.objects.filter(original_name="sales_orders.csv").first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.mime_type, "text/csv")
        self.assertEqual(doc.parser_type, "CSV")

    def test_04_image_attachment(self):
        """
        Test 4 — Image Attachment:
        Email with PNG image attachment -> MIME detection -> existing Image/OCR parser -> pipeline ingested.
        """
        # Minimal valid 1x1 PNG image bytes
        png_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82"
        
        raw_email = (
            b"From: bharathwaj271192@gmail.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: Receipt Image Attachment\r\n"
            b"Message-ID: <TEST_MSG_004_IMG@mail.gmail.com>\r\n"
            b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
            b"--BOUNDARY\r\n"
            b"Content-Type: image/png\r\n"
            b"Content-Disposition: attachment; filename=\"receipt_scan.png\"\r\n\r\n" +
            png_content + b"\r\n--BOUNDARY--\r\n"
        )

        parsed_email = self.collector.parse_raw_email(raw_email)
        res = process_email_message_task(parsed_email)
        self.assertEqual(res["status"], "SUCCESS")

        doc = Document.objects.filter(original_name="receipt_scan.png").first()
        self.assertIsNotNone(doc)
        self.assertEqual(doc.mime_type, "image/png")
        self.assertEqual(doc.parser_type, "IMAGE")

    def test_05_duplicate_attachment_protection(self):
        """
        Test 5 — Duplicate Attachment Protection:
        Same attachment sent in a 2nd email -> message tracked, SHA-256 deduplication detects identical file, no duplicate document created.
        """
        att_content = b"IDENTICAL_ATTACHMENT_DATA_FOR_SHA256_DEDUPLICATION_TEST"
        att_hash = hashlib.sha256(att_content).hexdigest()

        raw_email_1 = (
            b"From: bharathwaj271192@gmail.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: First Email with File\r\n"
            b"Message-ID: <TEST_MSG_005_DUP1@mail.gmail.com>\r\n"
            b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
            b"--BOUNDARY\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Disposition: attachment; filename=\"shared_data.txt\"\r\n\r\n" +
            att_content + b"\r\n--BOUNDARY--\r\n"
        )

        raw_email_2 = (
            b"From: bharathwaj271192@gmail.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: Second Email with Identical File\r\n"
            b"Message-ID: <TEST_MSG_005_DUP2@mail.gmail.com>\r\n"
            b"Content-Type: multipart/mixed; boundary=\"BOUNDARY\"\r\n\r\n"
            b"--BOUNDARY\r\n"
            b"Content-Type: text/plain\r\n"
            b"Content-Disposition: attachment; filename=\"shared_data.txt\"\r\n\r\n" +
            att_content + b"\r\n--BOUNDARY--\r\n"
        )

        # Ingest Email 1
        parsed_1 = self.collector.parse_raw_email(raw_email_1)
        res_1 = process_email_message_task(parsed_1)
        self.assertEqual(res_1["status"], "SUCCESS")

        doc_count_1 = Document.objects.filter(file_hash=att_hash).count()
        self.assertEqual(doc_count_1, 1)

        # Ingest Email 2 with duplicate attachment
        parsed_2 = self.collector.parse_raw_email(raw_email_2)
        res_2 = process_email_message_task(parsed_2)
        self.assertEqual(res_2["status"], "SUCCESS")

        # Verify second email was tracked in ProcessedEmail, but NO second Document was created for the identical attachment hash
        self.assertTrue(ProcessedEmail.objects.filter(message_id="TEST_MSG_005_DUP2@mail.gmail.com").exists())
        doc_count_2 = Document.objects.filter(file_hash=att_hash).count()
        self.assertEqual(doc_count_2, 1)

    def test_06_repeated_email_polling_idempotency(self):
        """
        Test 6 — Repeated Email Polling & Idempotency:
        Celery Beat polls multiple times -> previously processed emails are skipped -> idempotency strictly preserved.
        """
        raw_email = (
            b"From: bharathwaj271192@gmail.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: Enterprise Policy Update Notification\r\n"
            b"Message-ID: <TEST_MSG_006_IDEMPOTENT@mail.gmail.com>\r\n"
            b"Content-Type: text/plain\r\n\r\n"
            b"This is an enterprise policy notification.\r\n"
        )

        parsed_email = self.collector.parse_raw_email(raw_email)

        # 1st Run
        res_1 = process_email_message_task(parsed_email)
        self.assertEqual(res_1["status"], "SUCCESS")
        self.assertEqual(ProcessedEmail.objects.filter(message_id="TEST_MSG_006_IDEMPOTENT@mail.gmail.com").count(), 1)

        # 2nd Run (Simulating repeated Celery Beat polling / retry)
        res_2 = process_email_message_task(parsed_email)
        self.assertEqual(res_2["status"], "SKIPPED")
        self.assertEqual(ProcessedEmail.objects.filter(message_id="TEST_MSG_006_IDEMPOTENT@mail.gmail.com").count(), 1)

    def test_07_all_authorized_senders_and_unauthorized_rejection(self):
        """
        Test 7 — Authorized & Unauthorized Senders Verification:
        Verifies that all 5 authorized senders are accepted (case-insensitively, whitespace-trimmed, and formatted with display names)
        and that unauthorized senders are safely rejected.
        """
        authorized_senders = [
            'bharathwaj271192@gmail.com',
            'saib4618@gmail.com',
            'yogeshdean27@gmail.com',
            'dakshana1865@gmail.com',
            'hemanthkumar0825@gmail.com'
        ]

        # 1. Test all 5 authorized senders with normalization
        for idx, sender_email in enumerate(authorized_senders, 1):
            formatted_sender = f"  User {idx} <{sender_email.upper()}> "
            self.assertTrue(self.collector.is_authorized_sender(formatted_sender), f"Failed authorization check for: {formatted_sender}")

            raw_email = (
                f"From: {formatted_sender}\r\n"
                f"To: erpsystementerprises@gmail.com\r\n"
                f"Subject: Authorized Test Email {idx}\r\n"
                f"Message-ID: <TEST_MSG_AUTH_{idx}@mail.gmail.com>\r\n"
                f"Content-Type: text/plain\r\n\r\n"
                f"Authorized body text from {sender_email}\r\n"
            ).encode('utf-8')

            parsed = self.collector.parse_raw_email(raw_email)
            res = process_email_message_task(parsed)
            self.assertEqual(res["status"], "SUCCESS", f"Failed ingestion for authorized sender {sender_email}")
            proc = ProcessedEmail.objects.get(message_id=f"TEST_MSG_AUTH_{idx}@mail.gmail.com")
            self.assertEqual(proc.status, "SUCCESS")

        # 2. Test Unauthorized Sender Rejection
        unauthorized_sender = "unauthorized_spammer@external.com"
        self.assertFalse(self.collector.is_authorized_sender(unauthorized_sender))

        raw_unauth_email = (
            b"From: unauthorized_spammer@external.com\r\n"
            b"To: erpsystementerprises@gmail.com\r\n"
            b"Subject: Phishing / Unauthorized Notice\r\n"
            b"Message-ID: <TEST_MSG_UNAUTH_001@mail.gmail.com>\r\n"
            b"Content-Type: text/plain\r\n\r\n"
            b"Unauthorized email body.\r\n"
        )
        parsed_unauth = self.collector.parse_raw_email(raw_unauth_email)
        res_unauth = process_email_message_task(parsed_unauth)
        self.assertEqual(res_unauth["status"], "REJECTED_UNAUTHORIZED")

        proc_unauth = ProcessedEmail.objects.get(message_id="TEST_MSG_UNAUTH_001@mail.gmail.com")
        self.assertEqual(proc_unauth.status, "REJECTED_UNAUTHORIZED")
        self.assertIn("Unauthorized sender", proc_unauth.error_message)

    def test_08_verify_repository_destination_paths(self):
        """
        Test 8 — Repository Destination Folder Verification:
        Verifies that files ingested through Gmail ingestion are synchronized to the exact Team repository paths:
        - Excel -> Team/enterprise_ingestion_test_pack/excel/<filename>
        - CSV -> Team/enterprise_ingestion_test_pack/csv/<filename>
        - PDF -> Team/enterprise_ingestion_test_pack/pdf/<filename>
        - DOCX -> Team/enterprise_ingestion_test_pack/docx/<filename>
        - JSON -> Team/enterprise_ingestion_test_pack/json/<filename>
        - PNG -> Team/enterprise_ingestion_test_pack/png/<filename>
        - TXT -> Team/enterprise_ingestion_test_pack/txt/<filename>
        """
        pdf_bytes = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000052 00000 n\n0000000101 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n"
        csv_bytes = b"Order_ID,Product,Quantity\nSO9001,Widget,10\n"
        import io
        from PIL import Image
        buf = io.BytesIO()
        Image.new('RGB', (20, 20), color='blue').save(buf, format='PNG')
        png_bytes = buf.getvalue()
        from pathlib import Path
        excel_path = Path(r"C:\Users\yogeshwaran\Downloads\training_development_dataset_50_programs.xlsx")
        excel_bytes = excel_path.read_bytes()
        json_bytes = b'{"status": "ok", "items": [1, 2, 3]}'

        test_payload = {
            'message_id': 'TEST_MSG_008_PATH_CHECK@mail.gmail.com',
            'sender': 'saib4618@gmail.com',
            'recipient': 'erpsystementerprises@gmail.com',
            'subject': 'Path Verification Multi File Test',
            'body': 'Verifying logical path for all file types.',
            'attachments': [
                {'filename': 'training_development_dataset_50_programs_p8.xlsx', 'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'payload': excel_bytes},
                {'filename': 'test_report_p8.pdf', 'content_type': 'application/pdf', 'payload': pdf_bytes},
                {'filename': 'test_sales_p8.csv', 'content_type': 'text/csv', 'payload': csv_bytes},
                {'filename': 'test_invoice_p8.png', 'content_type': 'image/png', 'payload': png_bytes},
                {'filename': 'test_config_p8.json', 'content_type': 'application/json', 'payload': json_bytes}
            ]
        }

        res = process_email_message_task(test_payload)
        self.assertEqual(res["status"], "SUCCESS")

        # Verify KnowledgeDocument logical paths in database
        pdf_kdoc = KnowledgeDocument.objects.filter(title="test_report_p8.pdf").first()
        self.assertIsNotNone(pdf_kdoc)
        self.assertEqual(pdf_kdoc.logical_path, "Team/enterprise_ingestion_test_pack/pdf/test_report_p8.pdf")

        csv_kdoc = KnowledgeDocument.objects.filter(title="test_sales_p8.csv").first()
        self.assertIsNotNone(csv_kdoc)
        self.assertEqual(csv_kdoc.logical_path, "Team/enterprise_ingestion_test_pack/csv/test_sales_p8.csv")

        png_kdoc = KnowledgeDocument.objects.filter(title="test_invoice_p8.png").first()
        self.assertIsNotNone(png_kdoc)
        self.assertEqual(png_kdoc.logical_path, "Team/enterprise_ingestion_test_pack/png/test_invoice_p8.png")

        json_kdoc = KnowledgeDocument.objects.filter(title="test_config_p8.json").first()
        self.assertIsNotNone(json_kdoc)
        self.assertEqual(json_kdoc.logical_path, "Team/enterprise_ingestion_test_pack/json/test_config_p8.json")

        excel_kdoc = KnowledgeDocument.objects.filter(title="training_development_dataset_50_programs_p8.xlsx").first()
        self.assertIsNotNone(excel_kdoc)
        self.assertEqual(excel_kdoc.logical_path, "Team/enterprise_ingestion_test_pack/excel/training_development_dataset_50_programs_p8.xlsx")
