from edqi.explainability.models import RecommendationHistory

class RecommendationRepository:
    """
    Data access repository managing database operations for RecommendationHistory models.
    """
    def save_recommendation(self, rec: RecommendationHistory) -> RecommendationHistory:
        """
        Saves a recommendation record.
        """
        rec.save()
        return rec

    def get_recommendation_by_id(self, recommendation_id) -> RecommendationHistory:
        """
        Retrieves a recommendation by its UUID.
        """
        return RecommendationHistory.objects.filter(recommendation_id=recommendation_id).first()

    def get_recommendations_by_report(self, report_id) -> list:
        """
        Retrieves all recommendations associated with a specific report.
        """
        return list(RecommendationHistory.objects.filter(report_id=report_id).order_by('-priority_score'))

    def get_recommendations_by_prediction(self, prediction_id) -> list:
        """
        Retrieves recommendations linked directly to a prediction history record.
        """
        return list(RecommendationHistory.objects.filter(report__prediction_id=prediction_id).order_by('-priority_score'))

    def list_recommendations(self) -> list:
        """
        Returns all recommendations.
        """
        return list(RecommendationHistory.objects.all().order_by('-created_at'))
