from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from core.views import HealthCheckView

# Configuration for Swagger API Documentations
schema_view = get_schema_view(
    openapi.Info(
        title="Enterprise AI Decision Intelligence Platform API",
        default_version='v1',
        description="Comprehensive developer documentation for downstream AI ingestion, validation, and analytics endpoints.",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="admin@enterprise.ai"),
        license=openapi.License(name="Proprietary License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Application Routes (Version 1)
    path('api/v1/auth/', include('authentication.urls')),
    path('api/v1/ingestion/', include('ingestion.urls')),
    path('api/v1/repository/', include('repository.urls')),
    path('api/v1/conflicts/', include('knowledge_conflict.urls')),
    path('api/v1/health/', HealthCheckView.as_view(), name='health_check'),
    path('api/v1/', include('edqi.explainability.urls')),

    
    # Swagger Documentation Routes
    path('api/v1/swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api/v1/redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]
