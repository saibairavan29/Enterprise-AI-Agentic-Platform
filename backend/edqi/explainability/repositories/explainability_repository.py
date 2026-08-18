from edqi.explainability.models import ExplainabilityReport

class ExplainabilityRepository:
    """
    Data access repository managing database operations for ExplainabilityReport models.
    """
    def save_report(self, report: ExplainabilityReport) -> ExplainabilityReport:
        """
        Saves or updates an ExplainabilityReport.
        """
        report.save()
        return report

    def get_report_by_id(self, report_id) -> ExplainabilityReport:
        """
        Retrieves a report by its UUID primary key.
        """
        return ExplainabilityReport.objects.filter(report_id=report_id).first()

    def get_report_by_prediction(self, prediction_id) -> ExplainabilityReport:
        """
        Retrieves the report associated with a PredictionHistory record.
        """
        return ExplainabilityReport.objects.filter(prediction_id=prediction_id).first()

    def list_reports(self) -> list:
        """
        Returns a list of all explanation reports.
        """
        return list(ExplainabilityReport.objects.all().order_by('-created_at'))
