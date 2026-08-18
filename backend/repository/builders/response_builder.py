from rest_framework.response import Response
from django.utils import timezone

class ResponseBuilder:
    """
    Standardizes successful and failed REST API responses 
    to match the Enterprise Application envelope.
    """
    @staticmethod
    def success(data=None, message="Operation successful.", status_code=200):
        return Response({
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data or {},
            "errors": [],
            "timestamp": timezone.now().isoformat()
        }, status=status_code)

    @staticmethod
    def error(errors=None, message="An error occurred.", status_code=400):
        return Response({
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": {},
            "errors": errors or [],
            "timestamp": timezone.now().isoformat()
        }, status=status_code)
