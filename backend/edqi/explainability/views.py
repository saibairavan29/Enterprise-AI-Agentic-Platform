import time
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import HttpResponse

from edqi.explainability.logging.explainability_logger import ExplainabilityLogger
from edqi.explainability.explanation_service import ExplanationService
from edqi.explainability.repositories.explainability_repository import ExplainabilityRepository
from edqi.explainability.repositories.recommendation_repository import RecommendationRepository
from edqi.explainability.builders.statistics_builder import ExplainabilityStatisticsBuilder
from edqi.explainability.report_builder import ExplainabilityReportBuilder
from edqi.ml_engine.services.evaluation_service import EvaluationService
from edqi.explainability.models import ExplainabilityReport, RecommendationHistory

# Instantiate shared explanation service coordinator
service = ExplanationService()
report_repo = ExplainabilityRepository()
rec_repo = RecommendationRepository()
eval_service = EvaluationService()

class GenerateExplanationView(APIView):
    """
    POST /api/v1/edqi/explain/
    Generates explanation SHAP report and recommendations fix list for a prediction record.
    """
    def post(self, request):
        start = time.time()
        pred_id = request.data.get("prediction_id")
        if not pred_id:
            return Response({"error": "prediction_id is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            report_dict = service.get_explanation_for_prediction(pred_id)
            duration = (time.time() - start) * 1000.0
            ExplainabilityLogger.api_request("POST", "/api/v1/edqi/explain/", duration)
            return Response(report_dict, status=status.HTTP_200_OK)
        except Exception as e:
            ExplainabilityLogger.exception("Failed to generate explanation API run", e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ExplanationHistoryView(APIView):
    """
    GET /api/v1/edqi/explanations/
    Lists explainability reports history logs.
    """
    def get(self, request):
        start = time.time()
        reports = report_repo.list_reports()
        data = []
        for r in reports:
            data.append({
                "report_id": str(r.report_id),
                "prediction_id": str(r.prediction_id),
                "overall_prediction": r.overall_prediction,
                "confidence_score": r.confidence_score,
                "model_version": r.model_version,
                "explainer_name": r.explainer_name,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        duration = (time.time() - start) * 1000.0
        ExplainabilityLogger.api_request("GET", "/api/v1/edqi/explanations/", duration)
        return Response(data, status=status.HTTP_200_OK)


class ExplanationDetailView(APIView):
    """
    GET /api/v1/edqi/explanations/<id>/
    Fetches explanation report details, supporting optional query formatting (JSON/MD/CSV).
    """
    def get(self, request, pk):
        start = time.time()
        report = report_repo.get_report_by_id(pk)
        if not report:
            # Fall back to lookup by prediction UUID if primary key UUID wasn't found
            report = report_repo.get_report_by_prediction(pk)
            
        if not report:
            return Response({"error": "Explanation Report not found"}, status=status.HTTP_404_NOT_FOUND)

        # Build dictionary details
        prediction = report.prediction
        input_features = {}
        if prediction and prediction.execution_trace:
            input_features = prediction.execution_trace.get("input_features", {})

        report_dict = {
            "report_id": str(report.report_id),
            "prediction_id": str(report.prediction_id),
            "overall_prediction": report.overall_prediction,
            "confidence_score": report.confidence_score,
            "base_value": report.base_value,
            "predicted_probability": report.predicted_probability,
            "top_positive_features": report.top_positive_features,
            "top_negative_features": report.top_negative_features,
            "raw_shap_values": report.raw_shap_values,
            "normalized_shap_values": report.normalized_shap_values,
            "recommendations": report.recommendations,
            "summary": report.summary,
            "explainer_name": report.explainer_name,
            "explainer_version": report.explainer_version,
            "model_version": report.model_version,
            "dataset_version": report.dataset_version,
            "feature_version": report.feature_version,
            "processing_trace": report.processing_trace,
            "input_features": {
                "completeness_score": input_features.get("completeness_score"),
                "validity_score": input_features.get("validity_score"),
                "consistency_score": input_features.get("consistency_score"),
                "uniqueness_score": input_features.get("uniqueness_score"),
                "timeliness_score": input_features.get("timeliness_score"),
                "quality_score": input_features.get("quality_score"),
                "missing_fields": input_features.get("missing_fields"),
                "invalid_fields": input_features.get("invalid_fields"),
                "duplicate_fields": input_features.get("duplicate_fields"),
                "record_age": input_features.get("record_age"),
            },
            "created_at": report.created_at.isoformat() if report.created_at else None
        }

        # Check export format parameter
        export_format = request.query_params.get("format", "json").lower().strip()
        
        duration = (time.time() - start) * 1000.0
        ExplainabilityLogger.api_request("GET", f"/api/v1/edqi/explanations/{pk}/", duration)

        if export_format == "md":
            md_content = ExplainabilityReportBuilder.generate_markdown_report(report_dict)
            return HttpResponse(md_content, content_type="text/markdown")
        elif export_format == "csv":
            csv_content = ExplainabilityReportBuilder.generate_csv_report(report_dict)
            response = HttpResponse(csv_content, content_type="text/csv")
            response['Content-Disposition'] = f'attachment; filename="explainability_report_{pk}.csv"'
            return response
        else:
            return Response(report_dict, status=status.HTTP_200_OK)


class RecommendationHistoryView(APIView):
    """
    GET /api/v1/edqi/recommendations/
    Lists all generated actions suggestions fixes.
    """
    def get(self, request):
        start = time.time()
        recs = rec_repo.list_recommendations()
        data = []
        for r in recs:
            data.append({
                "recommendation_id": str(r.recommendation_id),
                "report_id": str(r.report_id),
                "prediction_id": str(r.report.prediction_id) if r.report else "",
                "recommendation_type": r.recommendation_type,
                "category": r.category,
                "priority": r.priority,
                "priority_score": r.priority_score,
                "recommendation": r.recommendation,
                "expected_improvement": r.expected_improvement,
                "recommendation_confidence": r.recommendation_confidence,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        duration = (time.time() - start) * 1000.0
        ExplainabilityLogger.api_request("GET", "/api/v1/edqi/recommendations/", duration)
        return Response(data, status=status.HTTP_200_OK)


class RecommendationPredictionDetailView(APIView):
    """
    GET /api/v1/edqi/recommendations/<prediction_id>/
    Lists action items suggestions linked directly to a prediction ID.
    """
    def get(self, request, prediction_id):
        start = time.time()
        recs = rec_repo.get_recommendations_by_prediction(prediction_id)
        
        # If no report was generated yet, trigger one automatically to make UX seamless
        if not recs:
            try:
                service.get_explanation_for_prediction(prediction_id)
                recs = rec_repo.get_recommendations_by_prediction(prediction_id)
            except Exception:
                pass

        data = []
        for r in recs:
            data.append({
                "recommendation_id": str(r.recommendation_id),
                "report_id": str(r.report_id),
                "recommendation_type": r.recommendation_type,
                "category": r.category,
                "priority": r.priority,
                "priority_score": r.priority_score,
                "recommendation": r.recommendation,
                "expected_improvement": r.expected_improvement,
                "recommendation_confidence": r.recommendation_confidence,
                "status": r.status,
                "created_at": r.created_at.isoformat() if r.created_at else None
            })
        duration = (time.time() - start) * 1000.0
        ExplainabilityLogger.api_request("GET", f"/api/v1/edqi/recommendations/{prediction_id}/", duration)
        return Response(data, status=status.HTTP_200_OK)


class ExplainabilityStatisticsView(APIView):
    """
    GET /api/v1/edqi/explainability/statistics/
    Compiles dashboard aggregate KPIs.
    """
    def get(self, request):
        start = time.time()
        hits = service.cache.hits
        misses = service.cache.misses
        
        stats = ExplainabilityStatisticsBuilder.compile_explainability_statistics(hits, misses)
        duration = (time.time() - start) * 1000.0
        ExplainabilityLogger.api_request("GET", "/api/v1/edqi/explainability/statistics/", duration)
        return Response(stats, status=status.HTTP_200_OK)


class ExplainabilityModelsView(APIView):
    """
    GET /explainability/models
    Returns parameters and evaluation scores of currently active classifiers/anomaly models.
    """
    def get(self, request):
        start = time.time()
        classifier_details = eval_service.get_active_model_details()
        anomaly_details = eval_service.get_active_anomaly_details()
        
        data = {
            "active_classifier": classifier_details,
            "active_anomaly_detector": anomaly_details
        }
        duration = (time.time() - start) * 1000.0
        ExplainabilityLogger.api_request("GET", "/explainability/models", duration)
        return Response(data, status=status.HTTP_200_OK)


class ExplainabilityCacheStatsView(APIView):
    """
    GET /explainability/cache/statistics
    Returns explainability cache lookups indices.
    """
    def get(self, request):
        start = time.time()
        hits = service.cache.hits
        misses = service.cache.misses
        total = hits + misses
        ratio = float(hits) / float(total) if total > 0 else 1.0
        
        data = {
            "cache_hits": hits,
            "cache_misses": misses,
            "total_lookups": total,
            "cache_hit_ratio": round(ratio, 4)
        }
        duration = (time.time() - start) * 1000.0
        ExplainabilityLogger.api_request("GET", "/explainability/cache/statistics", duration)
        return Response(data, status=status.HTTP_200_OK)
