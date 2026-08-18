import time
import logging
from datetime import datetime
from django.db import transaction

from ..rules.rules_loader import RulesLoader
from ..validators.conflict_validator import ConflictValidator
from ..embeddings.embedding_registry import EmbeddingModelRegistry
from ..similarity.similarity_engine import SimilarityEngine
from ..evidence.evidence_extractor import EvidenceExtractor
from ..classifiers.classifiers import ClassifierRegistry
from ..repositories.conflict_repository import ConflictRepository
from ..builders.builders import ConflictBuilder, StatisticsBuilder
from ...repositories.candidate_repository import CandidateRepository
from ..cache.embedding_cache import EmbeddingCache

logger = logging.getLogger('enterprise')

class DetectionService:
    """
    Core service coordinating embedding resolution, similarity engine matching,
    evidence extraction, and classifier registry decisions for a single candidate.
    """
    def __init__(self, config: dict, similarity_engine: SimilarityEngine):
        self.config = config
        self.similarity_engine = similarity_engine
        self.evidence_extractor = EvidenceExtractor(config)
        self.classifiers = ClassifierRegistry.get_active_classifiers(config)

    def process_candidate(self, candidate) -> tuple:
        """
        Executes comparison stages on a candidate pair.
        Returns a tuple: (classification_result_dict, similarity_report_dict)
        """
        # 1. Compute multi-metric similarities
        sim_report = self.similarity_engine.compare_texts(candidate.source_text, candidate.target_text)
        
        # 2. Extract structural and semantic evidence
        evidence = self.evidence_extractor.extract_evidence(candidate, sim_report)
        
        # 3. Classify pair through priority classifiers
        match = None
        for classifier in self.classifiers:
            res = classifier.classify(candidate, sim_report, evidence)
            if res is not None:
                # Add metadata parameters
                res["classifier_used"] = classifier.__class__.__name__
                match = res
                break
                
        # Fallback to UNKNOWN if no classifier registered a match
        if match is None:
            match = {
                "conflict_type": "UNKNOWN",
                "severity": "LOW",
                "confidence": 0.5,
                "explanation": "No matching classification rules met.",
                "evidence": evidence,
                "classifier_used": "None"
            }
            
        return match, sim_report


class ConflictDetectionOrchestrator:
    """
    Orchestrates the E2E conflict detection execution block over stored candidates list.
    """
    def __init__(self):
        self.candidate_repo = CandidateRepository()
        self.conflict_repo = ConflictRepository()
        self.cache = EmbeddingCache()

    def run_detection(self) -> dict:
        """
        Pulls candidates with 'GENERATED' status, processes them, saves conflicts,
        and returns consolidated batch statistics reports.
        """
        start_time = time.time()
        
        # 1. Load configuration rules
        config = RulesLoader.load_rules()
        ConflictValidator.validate_rules_config(config)
        
        # 2. Fetch candidates from database
        candidates = list(self.candidate_repo.get_all())
        # Filter for candidates that need processing
        pending_candidates = [c for c in candidates if c.status in ['GENERATED', 'QUEUED']]
        
        if not pending_candidates:
            logger.info("No pending candidates found. Skipping conflict detection run.")
            return StatisticsBuilder.build_report([], 0, self.cache.stats, 0.0)
            
        # Update pending candidates status to PROCESSING
        with transaction.atomic():
            for c in pending_candidates:
                c.status = 'PROCESSING'
                c.save(update_fields=['status'])
                
        # 3. Initialize embedding model and similarity engine
        model_name = config.get("embedding_model", "MiniLMEmbedding")
        emb_model = EmbeddingModelRegistry.get_model(model_name, config)
        sim_engine = SimilarityEngine(emb_model)
        detection_service = DetectionService(config, sim_engine)
        
        conflicts_to_save = []
        processed_count = 0
        
        # 4. Process each candidate
        for candidate in pending_candidates:
            processed_count += 1
            trace = {
                "candidate_id": str(candidate.candidate_id),
                "started_at": datetime.utcnow().isoformat() + "Z"
            }
            
            try:
                classification, sim_report = detection_service.process_candidate(candidate)
                
                # If similarity metrics show any non-trivial relationship, build conflict model
                # (E.g. only save if not UNKNOWN, or save everything to maintain full auditable registry)
                conflict_obj = ConflictBuilder.build(candidate, classification, sim_report, trace)
                ConflictValidator.validate_conflict_fields(conflict_obj.__dict__)
                conflicts_to_save.append(conflict_obj)
                
                candidate.status = 'PROCESSED'
            except Exception as e:
                logger.error(f"Failed to process candidate {candidate.candidate_id}: {str(e)}", exc_info=True)
                candidate.status = 'FAILED'
                
        # 5. Bulk persist KnowledgeConflicts and update Candidates status in a single transaction
        if conflicts_to_save or pending_candidates:
            with transaction.atomic():
                self.conflict_repo.bulk_create(conflicts_to_save)
                for c in pending_candidates:
                    c.save(update_fields=['status'])
                    
        elapsed_time = time.time() - start_time
        
        # Resolve batch parameters
        batch_id = pending_candidates[0].batch_id if pending_candidates else "N/A"
        model_version = config.get("embedding_model", "MiniLMEmbedding")

        # 6. Generate report statistics
        report = StatisticsBuilder.build_report(
            conflicts_list=conflicts_to_save,
            total_processed=processed_count,
            cache_stats=self.cache.stats,
            elapsed_time=elapsed_time,
            batch_id=batch_id,
            model_version=model_version,
            rules_version="1.0",
            pipeline_version="3.0"
        )
        
        logger.info(f"Conflict detection completed. Found {report['conflicts']} conflicts, {report['duplicates']} duplicates, {report['outdated']} outdated records.")
        return report

