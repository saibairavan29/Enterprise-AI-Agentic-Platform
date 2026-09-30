import os
import re
import imaplib
import email
import email.utils
import logging
from email.header import decode_header
from typing import Dict, Any, List, Optional
from django.conf import settings

logger = logging.getLogger('enterprise')

class EmailCollectorService:
    """
    Service responsible for communicating with Gmail IMAP server, fetching newly received
    enterprise emails from the ERP collector mailbox (erpsystementerprises@gmail.com),
    extracting metadata, email body, and attachments without modifying existing parsers.
    """
    def __init__(self, host: Optional[str] = None, port: Optional[int] = None, username: Optional[str] = None, password: Optional[str] = None):
        self.host = host or getattr(settings, 'EMAIL_HOST', 'imap.gmail.com')
        self.port = port or getattr(settings, 'EMAIL_PORT', 993)
        self.username = username or getattr(settings, 'EMAIL_USERNAME', 'erpsystementerprises@gmail.com')
        self.password = password or getattr(settings, 'EMAIL_APP_PASSWORD', '')

    @staticmethod
    def normalize_email_address(sender_str: str) -> str:
        """
        Normalizes email address by trimming whitespace, stripping display names,
        and converting to lowercase for safe comparison.
        e.g., '  Sai B <SaiB4618@Gmail.com> ' -> 'saib4618@gmail.com'
        """
        if not sender_str:
            return ""
        name, addr = email.utils.parseaddr(sender_str)
        clean_addr = addr if addr else sender_str
        return clean_addr.strip().lower()

    def is_authorized_sender(self, sender_str: str) -> bool:
        """
        Checks if the normalized sender email is included in the AUTHORIZED_EMAIL_SENDERS setting.
        """
        clean_sender = self.normalize_email_address(sender_str)
        auth_list = getattr(settings, 'AUTHORIZED_EMAIL_SENDERS', [])
        auth_set = {self.normalize_email_address(s) for s in auth_list if s}
        return clean_sender in auth_set

    def _decode_header_str(self, header_val: Optional[str]) -> str:
        if not header_val:
            return ""
        decoded_fragments = []
        try:
            for frag, encoding in decode_header(header_val):
                if isinstance(frag, bytes):
                    decoded_fragments.append(frag.decode(encoding or 'utf-8', errors='ignore'))
                else:
                    decoded_fragments.append(str(frag))
            return "".join(decoded_fragments).strip()
        except Exception:
            return str(header_val).strip()

    def parse_raw_email(self, raw_bytes: bytes, fallback_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Parses raw email RFC822 bytes into a standardized dictionary structure:
        - message_id
        - sender
        - recipient
        - subject
        - received_at
        - body
        - attachments: list of {filename, content_type, payload}
        """
        msg = email.message_from_bytes(raw_bytes)
        
        msg_id = msg.get('Message-ID') or msg.get('Message-Id')
        if msg_id:
            msg_id = self._decode_header_str(msg_id).strip('<>')
        else:
            msg_id = fallback_id or f"MSG_{hash(raw_bytes)}"
            
        sender = self._decode_header_str(msg.get('From', 'Unknown Sender'))
        recipient = self._decode_header_str(msg.get('To', self.username))
        subject = self._decode_header_str(msg.get('Subject', 'Enterprise Email'))
        date_str = self._decode_header_str(msg.get('Date', ''))

        body_text = ""
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get('Content-Disposition', ''))
                filename = part.get_filename()

                if filename or 'attachment' in content_disposition.lower():
                    clean_filename = self._decode_header_str(filename) if filename else "attachment.dat"
                    payload = part.get_payload(decode=True)
                    if payload:
                        attachments.append({
                            "filename": clean_filename,
                            "content_type": content_type,
                            "payload": payload
                        })
                elif content_type == 'text/plain' and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                elif content_type == 'text/html' and not body_text:
                    payload = part.get_payload(decode=True)
                    if payload:
                        raw_html = payload.decode(part.get_content_charset() or 'utf-8', errors='ignore')
                        clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
                        body_text = re.sub(r'\s+', ' ', clean_text).strip()
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode(msg.get_content_charset() or 'utf-8', errors='ignore')

        return {
            "message_id": msg_id,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "received_at": date_str,
            "body": body_text.strip(),
            "attachments": attachments
        }

    def fetch_new_emails(self, search_criterion: str = 'UNSEEN') -> List[Dict[str, Any]]:
        """
        Connects to Gmail IMAP, authenticates safely using Gmail App Password,
        fetches unread/new emails, and extracts message payload dictionaries.
        """
        if not self.password or not self.password.strip():
            logger.warning("EMAIL_APP_PASSWORD is not set in environment. Skipping live Gmail IMAP fetch.")
            return []

        parsed_emails = []
        mail = None
        try:
            logger.info(f"Connecting to Gmail IMAP server at {self.host}:{self.port} for mailbox {self.username}...")
            mail = imaplib.IMAP4_SSL(self.host, self.port)
            mail.login(self.username, self.password)
            mail.select('INBOX')

            status, search_data = mail.search(None, search_criterion)
            if status != 'OK' or not search_data or not search_data[0]:
                logger.info("No new emails detected in Gmail INBOX.")
                return []

            email_ids = search_data[0].split()
            logger.info(f"Detected {len(email_ids)} unread enterprise email(s) in Gmail INBOX.")

            for e_id in email_ids:
                try:
                    res_status, msg_data = mail.fetch(e_id, '(RFC822)')
                    if res_status == 'OK' and msg_data and msg_data[0]:
                        raw_email_bytes = msg_data[0][1]
                        parsed = self.parse_raw_email(raw_email_bytes, fallback_id=f"UID_{e_id.decode()}")
                        parsed_emails.append(parsed)
                except Exception as fetch_err:
                    logger.error(f"Error fetching email UID {e_id}: {fetch_err}", exc_info=True)

            return parsed_emails
        except Exception as imap_err:
            logger.error(f"Gmail IMAP Connection/Authentication Warning: {imap_err}")
            return []
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except Exception:
                    pass
