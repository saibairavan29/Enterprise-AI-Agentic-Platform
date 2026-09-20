import logging
from edqi.models import DataQualityDimension

logger = logging.getLogger(__name__)

class QualityScoreCalculator:
    """
    Computes overall data quality score dynamically from applicable dimension scores
    and provides explicit mathematical traceability for auditing.
    """

    CATEGORY_WEIGHTS = {
        "tabular": {
            "completeness": 0.30,
            "validity": 0.25,
            "consistency": 0.20,
            "uniqueness": 0.15,
            "timeliness": 0.10
        },
        "pdf": {
            "extraction_integrity": 0.35,
            "ocr_confidence": 0.25,
            "page_coverage": 0.25,
            "syntax_integrity": 0.15
        },
        "text_doc": {
            "readability": 0.35,
            "text_completeness": 0.35,
            "encoding_validity": 0.15,
            "structure_consistency": 0.15
        },
        "image": {
            "resolution_quality": 0.35,
            "ocr_extractability": 0.35,
            "noise_ratio": 0.15,
            "aspect_ratio_validity": 0.15
        },
        "json": {
            "schema_validity": 0.40,
            "completeness": 0.30,
            "syntax_integrity": 0.15,
            "key_uniqueness": 0.10
        }
    }

    DEFAULT_DIMENSION_WEIGHTS = {
        "completeness": 0.30,
        "validity": 0.25,
        "consistency": 0.20,
        "uniqueness": 0.15,
        "timeliness": 0.10,
        "extraction_integrity": 0.35,
        "ocr_confidence": 0.25,
        "page_coverage": 0.25,
        "syntax_integrity": 0.15,
        "readability": 0.35,
        "text_completeness": 0.35,
        "encoding_validity": 0.15,
        "structure_consistency": 0.15,
        "resolution_quality": 0.35,
        "ocr_extractability": 0.35,
        "noise_ratio": 0.15,
        "aspect_ratio_validity": 0.15,
        "schema_validity": 0.40,
        "key_uniqueness": 0.10
    }

    @classmethod
    def _normalize_key(cls, key: str) -> str:
        return str(key).lower().replace("_score", "").replace(" ", "_").strip()

    @classmethod
    def calculate_score_with_traceability(cls, dimension_scores: dict, file_category: str = None, rules: dict = None) -> dict:
        """
        Calculates final score and returns full mathematical traceability payload.
        Normalizes over active dimension weights if sum of active weights != 1.0.
        """
        if not dimension_scores:
            return {
                "calculation_method": "Normalized Weighted Score",
                "file_category": file_category or "generic",
                "applicable_dimensions": [],
                "total_weight": 1.0,
                "weighted_score_sum": 100.0,
                "final_score": 100.0
            }

        cat_weights = cls.CATEGORY_WEIGHTS.get(file_category, {}) if file_category else {}
        custom_weights = (rules or {}).get("quality_weights", {})

        applicable_dims = []
        total_weight = 0.0
        weighted_sum = 0.0

        for dim_key, score_val in dimension_scores.items():
            if dim_key in ["quality_score", "overall_score"] or not isinstance(score_val, (int, float)):
                continue

            clean_key = cls._normalize_key(dim_key)

            weight = custom_weights.get(dim_key, custom_weights.get(clean_key,
                     cat_weights.get(dim_key, cat_weights.get(clean_key,
                     cls.DEFAULT_DIMENSION_WEIGHTS.get(dim_key, cls.DEFAULT_DIMENSION_WEIGHTS.get(clean_key, 0.20))))))

            score = float(score_val)
            contribution = round(score * weight, 4)

            applicable_dims.append({
                "dimension": dim_key,
                "clean_dimension": clean_key,
                "score": round(score, 2),
                "weight": round(weight, 4),
                "contribution": round(contribution, 2)
            })

            weighted_sum += score * weight
            total_weight += weight

        if total_weight <= 0.0:
            final_score = 100.0
        else:
            final_score = round(weighted_sum / total_weight, 1)

        return {
            "calculation_method": "Normalized Weighted Score",
            "file_category": file_category or "generic",
            "applicable_dimensions": applicable_dims,
            "total_weight": round(total_weight, 4),
            "weighted_score_sum": round(weighted_sum, 2),
            "final_score": final_score
        }

    @classmethod
    def calculate_score(cls, dimension_scores: dict, file_category: str = None, rules: dict = None) -> float:
        """
        Calculates final score float dynamically across whatever dimensions are provided.
        """
        traceability = cls.calculate_score_with_traceability(dimension_scores, file_category, rules)
        return traceability["final_score"]

    @classmethod
    def calculate_repair_impact(cls, current_dimension_scores: dict, affected_dimension: str, dim_delta_single: float, issue_count: int = 1, file_category: str = None, rules: dict = None) -> dict:
        """
        Calculates mathematically precise single-issue and cumulative repair impact.
        Uses the single authoritative calculate_score function for both current and projected states.
        """
        current_overall_score = cls.calculate_score(current_dimension_scores, file_category, rules)

        cat_weights = cls.CATEGORY_WEIGHTS.get(file_category, {}) if file_category else {}
        custom_weights = (rules or {}).get("quality_weights", {})

        affected_clean = cls._normalize_key(affected_dimension)

        # Discover current dimension score
        current_dim_score = 100.0
        dim_key_found = None
        for k, v in current_dimension_scores.items():
            if k in ["quality_score", "overall_score"]:
                continue
            clean_k = cls._normalize_key(k)
            if clean_k == affected_clean:
                current_dim_score = float(v)
                dim_key_found = k
                break

        # Discover dimension weight
        weight = custom_weights.get(affected_clean,
                 cat_weights.get(affected_clean,
                 cls.DEFAULT_DIMENSION_WEIGHTS.get(affected_clean, 0.20)))

        # Single issue repair metrics
        single_dim_imp = round(min(100.0 - current_dim_score, max(0.0, dim_delta_single)), 2)
        single_projected_dim_score = round(min(100.0, current_dim_score + single_dim_imp), 2)

        # Compute projected overall score using authoritative scoring function
        projected_dim_scores = dict(current_dimension_scores)
        if dim_key_found:
            projected_dim_scores[dim_key_found] = single_projected_dim_score
        else:
            projected_dim_scores[affected_clean] = single_projected_dim_score

        single_projected_overall = cls.calculate_score(projected_dim_scores, file_category, rules)
        single_overall_impact = round(max(0.0, single_projected_overall - current_overall_score), 2)

        # Cumulative repair metrics for multiple issues in same dimension
        cum_dim_delta = dim_delta_single * issue_count
        cum_dim_imp = round(min(100.0 - current_dim_score, max(0.0, cum_dim_delta)), 2)
        cum_projected_dim_score = round(min(100.0, current_dim_score + cum_dim_imp), 2)

        cum_projected_dim_scores = dict(current_dimension_scores)
        if dim_key_found:
            cum_projected_dim_scores[dim_key_found] = cum_projected_dim_score
        else:
            cum_projected_dim_scores[affected_clean] = cum_projected_dim_score

        cum_projected_overall = cls.calculate_score(cum_projected_dim_scores, file_category, rules)
        cum_overall_impact = round(max(0.0, cum_projected_overall - current_overall_score), 2)

        raw_weighted_contrib_imp = round(single_dim_imp * weight, 2)
        cum_raw_weighted_contrib_imp = round(cum_dim_imp * weight, 2)

        return {
            "affected_dimension": affected_clean.replace("_", " ").capitalize(),
            "current_dimension_score": round(current_dim_score, 2),
            "projected_dimension_score": single_projected_dim_score,
            "dimension_improvement": single_dim_imp,
            "dimension_weight": round(weight, 4),
            "raw_weighted_contribution_impact": raw_weighted_contrib_imp,
            "normalized_overall_score_impact": single_overall_impact,
            "overall_score_impact": single_overall_impact,
            "current_overall_score": round(current_overall_score, 2),
            "projected_overall_score": single_projected_overall,
            "cumulative_issue_count": issue_count,
            "cumulative_dimension_improvement": cum_dim_imp,
            "cumulative_projected_dimension_score": cum_projected_dim_score,
            "cumulative_raw_weighted_contribution_impact": cum_raw_weighted_contrib_imp,
            "cumulative_overall_score_impact": cum_overall_impact,
            "cumulative_projected_overall_score": cum_projected_overall,
            "quantifiable": True
        }

    @classmethod
    def calculate_cumulative_repair_impact(cls, current_dimension_scores: dict, recommendations: list, file_category: str = None, rules: dict = None) -> dict:
        """
        Calculates combined cumulative impact across ALL proposed repairs without double counting.
        Recalculates all affected dimension scores in memory and computes authoritative final overall score.
        """
        current_overall_score = cls.calculate_score(current_dimension_scores, file_category, rules)
        cat_weights = cls.CATEGORY_WEIGHTS.get(file_category, {}) if file_category else {}
        custom_weights = (rules or {}).get("quality_weights", {})

        dim_groups = {}
        for r in recommendations:
            cat = str(r.get("affected_dimension") or r.get("category") or "Validity").strip()
            if cat not in dim_groups:
                dim_groups[cat] = {
                    "count": 0,
                    "dim_delta_single_sum": 0.0,
                    "affected_dimension": cat
                }
            dim_groups[cat]["count"] += 1
            dim_delta = float(r.get("dimension_improvement", 0.0))
            dim_groups[cat]["dim_delta_single_sum"] += dim_delta

        repaired_dim_scores = dict(current_dimension_scores)
        dimension_breakdown = []

        for cat, group in dim_groups.items():
            affected_clean = cls._normalize_key(cat)

            current_dim_score = 100.0
            dim_key_found = None
            for k, v in current_dimension_scores.items():
                if k in ["quality_score", "overall_score"]:
                    continue
                if cls._normalize_key(k) == affected_clean:
                    current_dim_score = float(v)
                    dim_key_found = k
                    break

            weight = custom_weights.get(affected_clean,
                     cat_weights.get(affected_clean,
                     cls.DEFAULT_DIMENSION_WEIGHTS.get(affected_clean, 0.20)))

            total_dim_imp = round(min(100.0 - current_dim_score, max(0.0, group["dim_delta_single_sum"])), 2)
            projected_dim_score = round(min(100.0, current_dim_score + total_dim_imp), 2)
            weighted_impact = round(total_dim_imp * weight, 2)

            if dim_key_found:
                repaired_dim_scores[dim_key_found] = projected_dim_score
            else:
                repaired_dim_scores[affected_clean] = projected_dim_score

            dimension_breakdown.append({
                "dimension": cat.replace("_", " ").capitalize(),
                "issue_count": group["count"],
                "current_dimension_score": round(current_dim_score, 2),
                "projected_dimension_score": projected_dim_score,
                "dimension_improvement": total_dim_imp,
                "dimension_weight": round(weight, 4),
                "weighted_overall_impact": weighted_impact
            })

        projected_overall_score = cls.calculate_score(repaired_dim_scores, file_category, rules)
        total_overall_impact = round(max(0.0, projected_overall_score - current_overall_score), 2)

        if total_overall_impact == 0.0:
            projected_overall_score = current_overall_score

        return {
            "current_overall_score": round(current_overall_score, 2),
            "projected_overall_score_after_all_repairs": round(projected_overall_score, 2),
            "total_overall_impact": total_overall_impact,
            "dimension_breakdown": dimension_breakdown
        }




