def get_file_type_folder(filename: str, mime_type: str = "", parser_type: str = "") -> str:
    """
    Determines the repository destination subfolder (excel, csv, pdf, docx, json, png, txt)
    under Team/enterprise_ingestion_test_pack/ based on file extension, MIME type, or parser type.
    """
    ext = ""
    if filename and '.' in filename:
        ext = filename.rsplit('.', 1)[-1].lower()

    mime = (mime_type or "").lower()
    parser = (parser_type or "").lower()

    if ext in ['xlsx', 'xls'] or 'spreadsheet' in mime or 'excel' in mime or parser in ['excel', 'excelparser']:
        return 'excel'
    elif ext == 'csv' or 'csv' in mime or parser in ['csv', 'csvparser']:
        return 'csv'
    elif ext == 'pdf' or 'pdf' in mime or parser in ['pdf', 'pdfparser']:
        return 'pdf'
    elif ext in ['docx', 'doc'] or 'wordprocessingml' in mime or 'msword' in mime or parser in ['docx', 'docxparser']:
        return 'docx'
    elif ext == 'json' or 'json' in mime or parser in ['json', 'jsonparser']:
        return 'json'
    elif ext in ['png', 'jpg', 'jpeg', 'webp', 'bmp', 'gif'] or mime.startswith('image/') or parser in ['image', 'imageparser']:
        return 'png'
    elif ext in ['txt', 'log', 'md'] or 'text/plain' in mime or parser in ['text', 'textparser']:
        return 'txt'

    return ext if ext else 'txt'
