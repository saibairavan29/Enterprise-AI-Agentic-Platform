from rest_framework import permissions

class IsRepositoryAdminOrAnalyst(permissions.BasePermission):
    """
    Role-Based Access Control matrix for the Enterprise Knowledge Repository.
    - Readers: Allowed GET requests (SAFE_METHODS).
    - Analysts and Admins: Allowed complete write, delete, and synchronize operations.
    """
    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated:
            user_role = getattr(request.user, 'role', 'reader').lower()
            if request.method in permissions.SAFE_METHODS:
                return True
            # Analyst or Admin required for write modifications
            return user_role in ['admin', 'analyst']
        return False
