from django.db import transaction

class TransactionManager:
    """
    Manager responsible for wrapping database queries under transaction.atomic contexts.
    """
    def execute_atomic(self, func, *args, **kwargs):
        """Runs the provided function inside an atomic database transaction."""
        with transaction.atomic():
            return func(*args, **kwargs)
PostgresTransactionManager = TransactionManager
