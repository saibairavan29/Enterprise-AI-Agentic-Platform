import collections
from edqi.explainability.models import ExplainabilityReport, RecommendationHistory
from edqi.ml_engine.models import PredictionHistory

class ExplainabilityStatisticsBuilder:
    """
    Assembles aggregate KPIs, trends, and distribution metrics for dashboard visualization.
    """
    @classmethod
    def compile_explainability_statistics(cls, cache_hits: int = 0, cache_misses: int = 0) -> dict:
        """
        Calculates metric summaries over explainability and predictions history.
        """
        reports = list(ExplainabilityReport.objects.all())
        total_reports = len(reports)
        
        # 1. Basic metrics
        avg_confidence = 0.0
        prediction_grades_counts = collections.Counter()
        
        if total_reports > 0:
            avg_confidence = sum(r.confidence_score for r in reports) / total_reports
            for r in reports:
                prediction_grades_counts[r.overall_prediction] += 1
                
        # 2. Extract feature magnitudes
        feature_importance_accum = collections.defaultdict(float)
        feature_importance_counts = collections.defaultdict(int)
        
        for r in reports:
            # Add absolute shap values to calculate average feature importance magnitude
            raw_shap = r.raw_shap_values or {}
            for feat, val in raw_shap.items():
                feature_importance_accum[feat] += abs(val)
                feature_importance_counts[feat] += 1

        avg_feature_importance = {}
        for feat in feature_importance_accum:
            count = feature_importance_counts[feat]
            avg_feature_importance[feat] = round(feature_importance_accum[feat] / max(1, count), 4)

        # Sort absolute importances
        sorted_features = sorted(avg_feature_importance.items(), key=lambda x: x[1], reverse=True)
        top_influential_features = [{"feature": f, "avg_magnitude": v} for f, v in sorted_features[:5]]

        # 3. Recommendations totals & category counts
        recs = list(RecommendationHistory.objects.all())
        total_recommendations = len(recs)
        
        rec_categories = collections.Counter()
        rec_priorities = collections.Counter()
        avg_expected_improvement = 0.0
        
        if total_recommendations > 0:
            avg_expected_improvement = sum(rc.expected_improvement for rc in recs) / total_recommendations
            for rc in recs:
                rec_categories[rc.category] += 1
                rec_priorities[rc.priority] += 1

        # 4. Cache hit ratio calculation
        total_lookups = cache_hits + cache_misses
        cache_hit_ratio = 1.0
        if total_lookups > 0:
            cache_hit_ratio = float(cache_hits) / float(total_lookups)

        return {
            "total_explanations": total_reports,
            "average_confidence": round(avg_confidence, 4),
            "prediction_distribution": dict(prediction_grades_counts),
            "top_influential_features": top_influential_features,
            "feature_importance_all": avg_feature_importance,
            "total_recommendations": total_recommendations,
            "average_expected_improvement": round(avg_expected_improvement, 2),
            "recommendation_category_distribution": dict(rec_categories),
            "recommendation_priority_distribution": dict(rec_priorities),
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_ratio": round(cache_hit_ratio, 4)
        }
