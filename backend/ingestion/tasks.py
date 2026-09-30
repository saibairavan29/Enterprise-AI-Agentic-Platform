import logging
import hashlib
from typing import Dict, Any, List
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from celery import shared_task

from common.path_utils import get_file_type_folder
from .models import ProcessedEmail, Document
from .services.email_collector_service import EmailCollectorService
from .services.upload_service import DocumentUploadService
from .orchestration.services.orchestration_service import IngestionOrchestrationService

logger = logging.getLogger('enterprise')
User = get_user_model()

def get_system_ingestion_user():
    """
    Retrieves or creates a dedicated system ingestion operator user for automated pipeline runs.
    """
    user = User.objects.filter(is_superuser=True).first()
    if not user:
        user = User.objects.filter(username='system_ingestion').first()
    if not user:
        user = User.objects.create_user(
            username='system_ingestion',
            email='erpsystementerprises@gmail.com',
            is_staff=True
        )
    return user

@shared_task(name='ingestion.tasks.poll_gmail_inbox_task')
def poll_gmail_inbox_task():
    """
    Celery Beat task: Periodically polls Gmail IMAP for newly received enterprise emails.
    Identifies unprocessed email messages, checks persistent Message-ID deduplication,
    validates authorized senders, and dispatches asynchronous processing tasks to Celery workers.
    """
    logger.info("Celery Beat: Polling Gmail IMAP enterprise mailbox...")
    try:
        collector = EmailCollectorService()
        new_emails = collector.fetch_new_emails()
        dispatched_count = 0
        for email_data in new_emails:
            msg_id = email_data.get('message_id')
            if not msg_id:
                continue

            sender = email_data.get('sender', '')
            if not collector.is_authorized_sender(sender):
                logger.warning(f"Skipping email from unauthorized sender: '{sender}' (Message-ID: {msg_id})")
                continue

            # Persistent idempotency check against ProcessedEmail model
            if ProcessedEmail.objects.filter(message_id=msg_id).exists():
                logger.info(f"Skipping previously processed email message_id: {msg_id}")
                continue

            # Dispatch asynchronous task to Celery Worker
            process_email_message_task.delay(email_data)
            dispatched_count += 1

        logger.info(f"Gmail Beat Poll completed. Dispatched {dispatched_count} new email processing tasks.")
        return dispatched_count
    except Exception as exc:
        logger.error(f"Error during Gmail Beat polling task: {str(exc)}", exc_info=True)
        return 0

@shared_task(name='ingestion.tasks.process_email_message_task')
def process_email_message_task(email_data: Dict[str, Any]):
    """
    Celery Worker task: Asynchronously processes an enterprise email message and its attachments.
    - Authorized Sender Check: Verifies sender against AUTHORIZED_EMAIL_SENDERS setting.
    - Scenario A (Email without attachments): Ingests email body content as an enterprise text document.
    - Scenario B (Email with attachments): Ingests attachments via existing DocumentUploadService and IngestionOrchestrationService.
    - Idempotency & SHA-256 deduplication: Handled by ProcessedEmail message_id and existing Document file_hash deduplication.
    """
    msg_id = email_data.get('message_id')
    sender = email_data.get('sender', 'Unknown Sender')
    recipient = email_data.get('recipient', 'erpsystementerprises@gmail.com')
    subject = email_data.get('subject', 'Enterprise Email Notice')
    received_at_str = email_data.get('received_at')
    body = email_data.get('body', '').strip()
    attachments = email_data.get('attachments', [])

    logger.info(f"Celery Worker: Processing email '{subject}' from {sender} (Message-ID: {msg_id})")

    collector = EmailCollectorService()
    if not collector.is_authorized_sender(sender):
        logger.warning(f"Rejecting email processing for unauthorized sender '{sender}' (Message-ID: {msg_id})")
        processed_record, _ = ProcessedEmail.objects.get_or_create(
            message_id=msg_id,
            defaults={
                'sender': sender,
                'recipient': recipient,
                'subject': subject,
                'body': body,
                'has_attachments': len(attachments) > 0,
                'attachment_count': len(attachments),
                'attachment_names': [att.get('filename') for att in attachments if att.get('filename')],
                'status': 'REJECTED_UNAUTHORIZED',
                'error_message': f"Unauthorized sender: {sender}"
            }
        )
        if processed_record.status != 'REJECTED_UNAUTHORIZED':
            processed_record.status = 'REJECTED_UNAUTHORIZED'
            processed_record.error_message = f"Unauthorized sender: {sender}"
            processed_record.save()
        return {"status": "REJECTED_UNAUTHORIZED", "message_id": msg_id, "reason": f"Unauthorized sender: {sender}"}

    # 1. Idempotency Check
    existing_proc = ProcessedEmail.objects.filter(message_id=msg_id).first()
    if existing_proc and existing_proc.status == 'SUCCESS':
        logger.info(f"Email {msg_id} already successfully processed. Idempotent skip.")
        return {"status": "SKIPPED", "message_id": msg_id}

    system_user = get_system_ingestion_user()

    # Create or update ProcessedEmail DB record
    processed_record, created = ProcessedEmail.objects.get_or_create(
        message_id=msg_id,
        defaults={
            'sender': sender,
            'recipient': recipient,
            'subject': subject,
            'body': body,
            'has_attachments': len(attachments) > 0,
            'attachment_count': len(attachments),
            'attachment_names': [att.get('filename') for att in attachments if att.get('filename')],
            'status': 'PROCESSING'
        }
    )

    created_documents = []

    try:
        upload_service = DocumentUploadService()
        orchestrator = IngestionOrchestrationService()

        # Scenario B — Process Email Attachments
        if attachments:
            for att in attachments:
                att_filename = att.get('filename', 'attachment.dat')
                att_bytes = att.get('payload', b'')
                if not att_bytes:
                    continue

                file_obj = ContentFile(att_bytes, name=att_filename)

                # Check SHA-256 deduplication against existing Document records
                sha256 = hashlib.sha256(att_bytes).hexdigest()
                already_exists = Document.objects.filter(file_hash=sha256).first()
                if already_exists:
                    logger.info(f"Duplicate attachment detected (SHA-256: {sha256[:8]}). Linking existing Document {already_exists.id}.")
                    processed_record.documents.add(already_exists)
                    created_documents.append(already_exists)
                    continue

                # Upload attachment using existing DocumentUploadService
                doc = upload_service.execute(file_obj, system_user)

                # Attach Gmail provenance metadata with exact enterprise repository pathing
                folder_name = get_file_type_folder(att_filename, att.get('content_type', ''))
                target_log_path = f"Team/enterprise_ingestion_test_pack/{folder_name}/{att_filename}"
                rel_path = f"enterprise_ingestion_test_pack/{folder_name}/{att_filename}"

                doc.metadata = {
                    "source": "gmail_imap",
                    "gmail_source": "gmail_imap",
                    "collector_mailbox": "erpsystementerprises@gmail.com",
                    "authorized_sender": sender,
                    "email_subject": subject,
                    "message_id": msg_id,
                    "attachment_filename": att_filename,
                    "repository_type": "team",
                    "target_logical_path": target_log_path,
                    "relative_path": rel_path
                }
                doc.processing_status = 'PROCESSING'
                doc.save()

                # Ingest through existing Enterprise Ingestion Pipeline
                orchestrator.process_document(doc.id, system_user)
                processed_record.documents.add(doc)
                created_documents.append(doc)

        # Scenario A — Process Email Body as Enterprise Information Document (if no attachments OR if body contains meaningful text)
        if not attachments or (body and len(body) > 15):
            clean_subject_slug = "".join([c if c.isalnum() else "_" for c in subject]).strip("_")[:30] or "email_notification"
            body_filename = f"Email_{clean_subject_slug}_{msg_id[:8]}.txt"
            body_bytes = f"Sender: {sender}\nRecipient: {recipient}\nSubject: {subject}\nMessage-ID: {msg_id}\n\n{body}".encode('utf-8')

            sha256 = hashlib.sha256(body_bytes).hexdigest()
            already_exists = Document.objects.filter(file_hash=sha256).first()
            if already_exists:
                logger.info(f"Duplicate email body detected (SHA-256: {sha256[:8]}). Linking existing Document {already_exists.id}.")
                processed_record.documents.add(already_exists)
            else:
                file_obj = ContentFile(body_bytes, name=body_filename)
                doc = upload_service.execute(file_obj, system_user)
                folder_name = "txt"
                target_log_path = f"Team/enterprise_ingestion_test_pack/{folder_name}/{body_filename}"
                rel_path = f"enterprise_ingestion_test_pack/{folder_name}/{body_filename}"

                doc.metadata = {
                    "source": "gmail_imap",
                    "gmail_source": "gmail_imap",
                    "collector_mailbox": "erpsystementerprises@gmail.com",
                    "authorized_sender": sender,
                    "email_subject": subject,
                    "message_id": msg_id,
                    "ingestion_type": "email_body_text",
                    "repository_type": "team",
                    "target_logical_path": target_log_path,
                    "relative_path": rel_path
                }
                doc.processing_status = 'PROCESSING'
                doc.save()

                # Ingest through existing Enterprise Ingestion Pipeline
                orchestrator.process_document(doc.id, system_user)
                processed_record.documents.add(doc)
                created_documents.append(doc)

        processed_record.status = 'SUCCESS'
        processed_record.save()

        logger.info(f"Celery Worker: Successfully processed email '{subject}' (Message-ID: {msg_id}). Ingested {len(created_documents)} documents.")
        return {
            "status": "SUCCESS",
            "message_id": msg_id,
            "documents_count": len(created_documents)
        }
    except Exception as exc:
        logger.error(f"Error processing email message {msg_id}: {str(exc)}", exc_info=True)
        processed_record.status = 'FAILED'
        processed_record.error_message = str(exc)
        processed_record.save()
        return {
            "status": "FAILED",
            "message_id": msg_id,
            "error": str(exc)
        }
