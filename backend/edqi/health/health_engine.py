from datetime import datetime
from django.utils import timezone
from edqi.health.health_repository import HealthRepository
from edqi.health.health_report_builder import HealthReportBuilder
from edqi.ml_engine.models import PredictionHistory, TrainedModel
from edqi.explainability.models import ExplainabilityReport, RecommendationHistory
from edqi.models import EnterpriseQualityMetrics

class HealthEngine:
    """
    Computes weighted quality-of-service health matrices for the enterprise platform.
    """
    @classmethod
    def calculate_health(cls) -> dict:
        timestamp_str = datetime.utcnow().isoformat() + "Z"
        
        # 1. Gather stats
        # Avg quality score
        avg_quality = 85.0
        latest_metrics = EnterpriseQualityMetrics.objects.order_by('-id').first()
        if latest_metrics and latest_metrics.average_score is not None:
            avg_quality = float(latest_metrics.average_score)
            
        # Model accuracy
        active_model = TrainedModel.objects.filter(status='ACTIVE').exclude(algorithm='Isolation Forest').first()
        model_accuracy = active_model.accuracy * 100.0 if active_model else 80.0
        
        # Avg confidence
        predictions = PredictionHistory.objects.all()
        total_predictions = len(predictions)
        avg_confidence = 85.0
        
        # Anomaly percentage
        anomalies_count = sum(1 for p in predictions if p.is_anomaly)
        anomaly_ratio = (anomalies_count / max(1, total_predictions)) * 100.0
        
        # Explainability coverage
        total_reports = ExplainabilityReport.objects.count()
        explainability_coverage = (total_reports / max(1, total_predictions)) * 100.0
        
        # Recommendation completion rate
        recs = RecommendationHistory.objects.all()
        total_recs = len(recs)
        applied_recs = sum(1 for r in recs if r.status in ['ACCEPTED', 'IMPLEMENTED'] or r.recommendation_applied)
        rec_completion_rate = (applied_recs / max(1, total_recs)) * 100.0

        # 2. Weighted health math
        health_score = (
            (0.30 * avg_quality) +
            (0.20 * model_accuracy) +
            (0.15 * avg_confidence) +
            (0.15 * rec_completion_rate) +
            (0.10 * (100.0 - anomaly_ratio)) +
            (0.10 * explainability_coverage)
        )

        health_score = min(100.0, max(0.0, health_score))

        # Resolve Grade
        if health_score >= 90.0:
            grade = 'A'
            risk_level = 'LOW'
        elif health_score >= 80.0:
            grade = 'B'
            risk_level = 'LOW'
        elif health_score >= 70.0:
            grade = 'C'
            risk_level = 'MEDIUM'
        else:
            grade = 'D'
            risk_level = 'HIGH'

        # Calculate trend based on history
        history = HealthRepository.load_history()
        trend = "STABLE"
        if history:
            prev = history[-1].get("health_score", 80.0)
            if health_score > prev + 1.0:
                trend = "UPWARD"
            elif health_score < prev - 1.0:
                trend = "DOWNWARD"

        report_data = {
            "report_version": "1.0",
            "timestamp": timestamp_str,
            "health_score": round(health_score, 2),
            "health_grade": grade,
            "risk_level": risk_level,
            "trend": trend,
            "metrics": {
                "overall_quality_score": round(avg_quality, 2),
                "model_accuracy": round(model_accuracy, 2),
                "average_confidence": round(avg_confidence, 2),
                "anomaly_percentage": round(anomaly_ratio, 2),
                "explainability_coverage": round(explainability_coverage, 2),
                "recommendation_completion_rate": round(rec_completion_rate, 2)
            }
        }

        # Record Health metrics inside Central Metrics Repository
        from edqi.metrics.metrics_service import MetricsService
        try:
            MetricsService.record_metric("health", "health_score", health_score)
        except Exception:
            pass

        # Save and build files
        HealthRepository.save_health_report(report_data)
        updated_history = HealthRepository.load_history()
        HealthReportBuilder.build_reports(HealthRepository.get_health_dir(), updated_history)

        return report_data
