import os
from django.core.exceptions import ValidationError
from common.constants import MAX_UPLOAD_SIZE, SUPPORTED_EXTENSIONS

def validate_file_size(file):
    """
    Validates that the uploaded file size is within configured limits (up to 1GB).
    """
    if file.size > MAX_UPLOAD_SIZE:
        max_mb = MAX_UPLOAD_SIZE / (1024 * 1024)
        if max_mb >= 1024:
            limit_str = f"{max_mb / 1024:.1f}GB"
        else:
            limit_str = f"{max_mb:.0f}MB"
        raise ValidationError(f"File size exceeds the maximum configured limit of {limit_str}.")

def validate_file_extension(file_name):
    """
    Validates the file extension against supported types.
    """
    ext = os.path.splitext(file_name)[1].lower().strip('.')
    if not ext:
         raise ValidationError("File has no extension.")
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValidationError(f"File extension '.{ext}' is not supported. Supported extensions: {', '.join(SUPPORTED_EXTENSIONS)}.")
    return ext

def validate_mime_type(file, extension):
    """
    Validates the file MIME type using signature verification (magic bytes check).
    """
    header = file.read(16)
    file.seek(0)  # Always reset stream pointer
    
    ext = extension.lower().strip('.')
    
    # Signature maps for binary checking
    signatures = {
        'pdf': b'%PDF',
        'png': b'\x89PNG\r\n\x1a\n',
        'jpg': b'\xff\xd8\xff',
        'jpeg': b'\xff\xd8\xff',
        'xlsx': b'PK\x03\x04',
        'xls': b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1',
    }
    
    if ext == 'pdf':
        if not header.startswith(signatures['pdf']):
            raise ValidationError("File signature mismatch. The file is not a valid PDF.")
    elif ext == 'png':
        if not header.startswith(signatures['png']):
            raise ValidationError("File signature mismatch. The file is not a valid PNG image.")
    elif ext in ['jpg', 'jpeg']:
        if not header.startswith(signatures['jpeg'][:2]):
            raise ValidationError("File signature mismatch. The file is not a valid JPEG image.")
    elif ext == 'xlsx':
        if not header.startswith(signatures['xlsx']):
            raise ValidationError("File signature mismatch. The file is not a valid Excel (.xlsx) file.")
    elif ext == 'xls':
        if not header.startswith(signatures['xls']):
            raise ValidationError("File signature mismatch. The file is not a valid Excel (.xls) file.")
    elif ext in ['csv', 'txt', 'json']:
        try:
            # Check decodability for text-based extensions
            header.decode('utf-8')
        except UnicodeDecodeError:
            try:
                header.decode('latin-1')
            except UnicodeDecodeError:
                raise ValidationError(f"File signature mismatch. The file is not a valid text-based file (.{ext}).")
