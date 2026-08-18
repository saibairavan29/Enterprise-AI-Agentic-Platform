# Supported Extensions and MIME Types
SUPPORTED_EXTENSIONS = {
    'pdf', 
    'xlsx', 
    'xls', 
    'csv', 
    'png', 
    'jpg', 
    'jpeg', 
    'txt', 
    'json'
}

SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
    'application/vnd.ms-excel',                                         # .xls
    'text/csv',
    'image/png',
    'image/jpeg',
    'text/plain',
    'application/json'
}

# Upload Constraints
MAX_UPLOAD_SIZE = 25 * 1024 * 1024   # 25 MB in bytes
MAX_PDF_PAGES = 100
MAX_EXCEL_ROWS = 50000
MAX_CSV_ROWS = 100000

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
