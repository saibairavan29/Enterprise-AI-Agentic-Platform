import logging
from edqi.models import EnterpriseQualityMetrics

logger = logging.getLogger(__name__)

class MetricsRepository:
    """
    Data access repository managing database operations for EnterpriseQualityMetrics models.
    """
    def save_metrics(self, metrics: EnterpriseQualityMetrics) -> EnterpriseQualityMetrics:
        """
        Saves or updates a metrics record.
        """
        metrics.save()
        return metrics

    def get_latest_metrics_for_document(self, document_id: int) -> EnterpriseQualityMetrics:
        """
        Retrieves the latest quality metrics calculated for a KnowledgeDocument.
        """
        return EnterpriseQualityMetrics.objects.filter(knowledge_document_id=document_id).order_by("-id").first()

    def get_metrics_by_batch_id(self, batch_id: str) -> EnterpriseQualityMetrics:
        """
        Retrieves metrics by their unique batch ID string.
        """
        return EnterpriseQualityMetrics.objects.filter(batch_id=batch_id).first()

    def delete_metrics_for_document(self, document_id: int):
        """
        Removes all metrics records associated with a KnowledgeDocument ID.
        """
        EnterpriseQualityMetrics.objects.filter(knowledge_document_id=document_id).delete()
