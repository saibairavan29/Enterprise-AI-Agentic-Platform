# Supported Extensions and MIME Types
SUPPORTED_EXTENSIONS = {
    'pdf', 
    'xlsx', 
    'xls', 
    'csv', 
    'png', 
    'jpg', 
    'jpeg', 
    'webp',
    'gif',
    'bmp',
    'txt', 
    'json',
    'docx',
    'doc',
    'zip',
    'mp4',
    'mp3'
}

SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/vnd.ms-excel',                                         # .xls
    'text/csv',
    'image/png',
    'image/jpeg',
    'image/webp',
    'image/gif',
    'image/bmp',
    'text/plain',
    'application/json',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', # .docx
    'application/msword',                                                      # .doc
    'application/zip',
    'video/mp4',
    'audio/mpeg'
}

# Upload Constraints
MAX_UPLOAD_SIZE = 5 * 1024 * 1024 * 1024   # 5 GB in bytes (configured maximum upload capacity)
MAX_PDF_PAGES = 10000
MAX_EXCEL_ROWS = 1000000
MAX_CSV_ROWS = 5000000
PREVIEW_MAX_RECORDS = 5000  # Capped preview records stored in structured_data for memory-safe UI rendering
PREVIEW_MAX_TEXT_BYTES = 200 * 1024  # Capped text preview (200 KB) for memory-safe content representation

# Defaults
OCR_LANGUAGE = 'eng'
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S%z'
DEFAULT_ENCODING = 'utf-8'

# Process and Ingestion Status State Choices
PROCESS_STATUS = (
    ('UPLOADED', 'Uploaded'),
    ('VALIDATED', 'Validated'),
    ('PARSING', 'Parsing'),
    ('OCR_RUNNING', 'OCR Running'),
    ('STANDARDIZED', 'Standardized'),
    ('FAILED', 'Failed')
)

# Data Quality Validation State Choices (EDQI)
VALIDATION_STATUS = (
    ('pending', 'Pending Validation'),
    ('clean', 'Clean'),
    ('duplicate', 'Duplicate'),
    ('incomplete', 'Incomplete'),
    ('invalid', 'Invalid'),
    ('suspicious', 'Suspicious')
)
