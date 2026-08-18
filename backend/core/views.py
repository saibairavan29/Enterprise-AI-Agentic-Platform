import logging
from django.utils import timezone
from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

logger = logging.getLogger('enterprise')

class HealthCheckView(APIView):
    """
    Health check API endpoint verifying the status of the service,
    running version, system environment parameters, and PostgreSQL database connectivity.
    """
    permission_classes = [permissions.AllowAny]  # Open endpoint for monitor/balancer checks

    def get(self, request):
        db_status = "healthy"
        try:
            # Retrieve cursor to test connection integrity
            connections['default'].cursor()
        except OperationalError as e:
            logger.error(f"Health check failed database connectivity verification: {str(e)}")
            db_status = "unhealthy"

        # Formulate standard JSON response payload aligned with global format
        status_code = status.HTTP_200_OK if db_status == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE
        
        response_payload = {
            "success": db_status == "healthy",
            "status_code": status_code,
            "message": "System status check completed successfully." if db_status == "healthy" else "Database connection failed.",
            "data": {
                "application": "Enterprise AI Decision Intelligence Platform",
                "status": "healthy" if db_status == "healthy" else "degraded",
                "version": "1.0.0",
                "database_connection": db_status,
                "environment": "development" if settings.DEBUG else "production"
            },
            "errors": [],
            "timestamp": timezone.now().isoformat()
        }
        
        return Response(response_payload, status=status_code)
