import logging
from django.db import transaction
from edqi.models import EnterpriseDataQualityReport, QualityIssue

logger = logging.getLogger(__name__)

class QualityRepository:
    """
    Data access repository managing database operations for EnterpriseDataQualityReport 
    and QualityIssue models.
    """
    def save_report(self, report: EnterpriseDataQualityReport) -> EnterpriseDataQualityReport:
        """
        Saves or updates a quality report.
        """
        report.save()
        return report

    def save_issues_bulk(self, issues: list) -> list:
        """
        Bulk inserts QualityIssue instances.
        """
        if not issues:
            return []
        with transaction.atomic():
            QualityIssue.objects.bulk_create(issues)
        return issues

    def get_report_by_id(self, report_pk: int) -> EnterpriseDataQualityReport:
        """
        Retrieves a report by its primary key database ID.
        """
        return EnterpriseDataQualityReport.objects.filter(pk=report_pk).first()

    def get_report_by_uuid(self, report_id) -> EnterpriseDataQualityReport:
        """
        Retrieves a report by its UUID string or object.
        """
        return EnterpriseDataQualityReport.objects.filter(report_id=report_id).first()

    def get_latest_report_for_record(self, record_id: int) -> EnterpriseDataQualityReport:
        """
        Retrieves the most recent quality report calculated for a KnowledgeRecord.
        """
        return EnterpriseDataQualityReport.objects.filter(knowledge_record_id=record_id).order_by("-id").first()

    def get_report_by_record_id(self, record_id: int) -> EnterpriseDataQualityReport:
        """
        Retrieves the quality report for a given record.
        """
        # Order by pk/created_at descending to get latest
        return EnterpriseDataQualityReport.objects.filter(knowledge_record_id=record_id).order_by("-id").first()

    def get_issues_for_report(self, report_pk: int) -> list:
        """
        Retrieves all issues associated with a quality report.
        """
        return list(QualityIssue.objects.filter(report_id=report_pk))

    def delete_reports_for_records(self, record_ids: list):
        """
        Removes all reports and related cascading issues for a list of record IDs.
        """
        with transaction.atomic():
            EnterpriseDataQualityReport.objects.filter(knowledge_record_id__in=record_ids).delete()
