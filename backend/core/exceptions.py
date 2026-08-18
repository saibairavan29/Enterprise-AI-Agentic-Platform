import logging
from django.conf import settings
from django.utils import timezone
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

# Use our custom root logger configured in settings.py
logger = logging.getLogger('enterprise')

def custom_exception_handler(exc, context):
    """
    Custom exception handler that intercepts DRF errors, standardizes response format
    to match the enterprise API contract:
    {
        "success": false,
        "status_code": 400,
        "message": "Friendly error summary.",
        "data": {},
        "errors": [dict of field errors or list of messages],
        "timestamp": "ISO-TIMESTAMP"
    }
    """
    # Call standard DRF exception handler
    response = exception_handler(exc, context)

    # Logging detail string
    view_name = context['view'].__class__.__name__ if 'view' in context else 'UnknownView'
    method = context['request'].method if 'request' in context else 'UnknownMethod'
    path = context['request'].path if 'request' in context else 'UnknownPath'
    
    logger.error(
        f"API Error - Method: {method} | Path: {path} | View: {view_name} | Exception: {str(exc)}", 
        exc_info=True
    )

    if response is not None:
        # Standard DRF exception returned a response
        err_data = response.data
        message = "An error occurred while validating your request."
        
        # Formulate a friendly error message from detail string if present
        if isinstance(err_data, dict):
            if 'detail' in err_data:
                message = err_data['detail']
                # Clean 'detail' so it doesn't duplicate in errors
                del err_data['detail']
            elif err_data:
                message = "Validation failed for one or more fields."
        elif isinstance(err_data, list):
            if len(err_data) > 0:
                message = str(err_data[0])

        # Format errors container as array/object
        errors = err_data if err_data else []
        if isinstance(errors, dict) and not errors:
            errors = []

        response.data = {
            "success": False,
            "status_code": response.status_code,
            "message": message,
            "data": {},
            "errors": errors,
            "timestamp": timezone.now().isoformat()
        }
    else:
        # Internal server errors (non-DRF exceptions)
        details = str(exc) if settings.DEBUG else "Internal server error occurred."
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        
        response_data = {
            "success": False,
            "status_code": status_code,
            "message": "A critical system error occurred. Please try again later.",
            "data": {},
            "errors": [details] if details else [],
            "timestamp": timezone.now().isoformat()
        }
        response = Response(response_data, status=status_code)

    return response
