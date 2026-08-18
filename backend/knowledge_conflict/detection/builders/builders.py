import uuid
from datetime import datetime
from ...models import KnowledgeConflict

class ConflictBuilder:
    """
    Builder class for constructing KnowledgeConflict database model instances
    with standardized properties and audit traces.
    """
    @staticmethod
    def build(candidate, classification: dict, similarity_report: dict, trace: dict) -> KnowledgeConflict:
        """
        Assembles a KnowledgeConflict model instance from pipeline results.
        """
        # Formulate self-descriptive similarity metrics dictionary
        metrics_dict = similarity_report.get("similarity_report", {}).get("similarity_metrics")
        if not metrics_dict:
            metrics_dict = similarity_report.get("similarity_metrics", {})
            
        # Formulate self-descriptive embedding metadata dictionary
        emb_metadata = {
            "model": similarity_report.get("model_used"),
            "dimension": similarity_report.get("dimension"),
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "cached": similarity_report.get("cached", False)
        }
        
        # Calculate overall similarity and evidence score
        overall_sim = similarity_report.get("overall_similarity", 0.0)
        evidence_data = classification.get("evidence", {})
        
        evidence_score = 0.0
        if len(evidence_data.get("contradiction_terms", [])) > 0:
            evidence_score += 0.5
        if evidence_data.get("numeric_difference", 0.0) > 0.0:
            evidence_score += 0.5
        if evidence_data.get("version_difference", 0) > 0:
            evidence_score += 0.3
        evidence_score = min(evidence_score, 1.0)
        
        # Calculate confidence using the formula
        calculated_confidence = 0.7 * overall_sim + 0.3 * evidence_score
        calculated_confidence = round(min(max(calculated_confidence, 0.0), 1.0), 4)

        # Compile processing trace fingerprint
        processing_trace = {
            **trace,
            "candidate_id": str(candidate.candidate_id),
            "embedding_model": similarity_report.get("model_used"),
            "embedding_cached": similarity_report.get("cached", False),
            "similarity_engine": "CosineSimilarity",
            "classifier": classification.get("classifier_used", "GenericClassifier"),
            "rules_version": "1.0",
            "pipeline_version": "3.0",
            "execution_duration": similarity_report.get("execution_time", 0.0),
            "execution_timestamp": datetime.utcnow().isoformat() + "Z",
            "confidence_formula": "0.7 * overall_similarity + 0.3 * evidence_score",
            "evidence_score": evidence_score
        }

        return KnowledgeConflict(
            conflict_id=uuid.uuid4(),
            knowledge_candidate=candidate,
            source_document_id=candidate.source_document_id,
            target_document_id=candidate.target_document_id,
            conflict_type=classification.get("conflict_type", "UNKNOWN"),
            severity=classification.get("severity", "LOW"),
            overall_similarity=overall_sim,
            similarity_metrics=metrics_dict,
            confidence_score=calculated_confidence,
            embedding_model=similarity_report.get("model_used", ""),
            embedding_metadata=emb_metadata,
            classifier_used=classification.get("classifier_used", ""),
            explanation=classification.get("explanation", ""),
            evidence=classification.get("evidence", {}),
            processing_trace=processing_trace,
            status='NEW',
            metadata={}
        )


class StatisticsBuilder:
    """
    Builder class for compiling execution run reports metrics.
    """
    @staticmethod
    def build_report(conflicts_list: list, total_processed: int, cache_stats: dict, elapsed_time: float, 
                     batch_id: str = "N/A", model_version: str = "MiniLM-v1", 
                     rules_version: str = "1.0", pipeline_version: str = "3.0") -> dict:
        """
        Compiles aggregate execution metrics inside a standardized report dictionary.
        """
        duplicates = sum(1 for c in conflicts_list if c.conflict_type == "DUPLICATE")
        conflicts = sum(1 for c in conflicts_list if c.conflict_type == "CONFLICTING")
        outdated = sum(1 for c in conflicts_list if c.conflict_type == "OUTDATED")
        consistent = sum(1 for c in conflicts_list if c.conflict_type == "CONSISTENT")
        unknown = sum(1 for c in conflicts_list if c.conflict_type == "UNKNOWN")
        
        # Calculate averages
        avg_similarity = 0.0
        avg_confidence = 0.0
        
        if conflicts_list:
            avg_similarity = sum(c.overall_similarity for c in conflicts_list) / len(conflicts_list)
            avg_confidence = sum(c.confidence_score for c in conflicts_list) / len(conflicts_list)
            
        # Cache hit ratio
        cache_hits = cache_stats.get("cache_hits", 0)
        cache_misses = cache_stats.get("cache_misses", 0)
        total_requests = cache_hits + cache_misses
        cache_ratio = round((cache_hits / total_requests) * 100, 2) if total_requests > 0 else 0.0

        return {
            "processed_candidates": total_processed,
            "generated_conflicts": len(conflicts_list),
            "duplicates": duplicates,
            "conflicts": conflicts,
            "outdated": outdated,
            "consistent": consistent,
            "unknown": unknown,
            "average_similarity": round(avg_similarity, 4),
            "average_confidence": round(avg_confidence, 4),
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "cache_hit_ratio": cache_ratio,
            "batch_id": batch_id,
            "model_version": model_version,
            "rules_version": rules_version,
            "pipeline_version": pipeline_version,
            "execution_time": round(elapsed_time, 4)
        }

