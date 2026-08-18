import uuid
import time
import logging
from datetime import datetime
from django.db import transaction

from ..rules.rules_loader import RulesLoader
from ..validators.validator import CandidateValidator
from ..extractors.document_extractor import DocumentExtractor
from ..extractors.record_extractor import RecordExtractor
from ..preprocessors.normalizer import TextNormalizer
from ..preprocessors.segmenter import RegexSegmenter
from ..registry.strategy_registry import StrategyRegistry
from ..utils.deduplicator import CandidateDeduplicator
from ..builders.candidate_builder import CandidateBuilder
from ..repositories.candidate_repository import CandidateRepository

from repository.repositories.document_repository import DocumentRepository
from repository.repositories.record_repository import RecordRepository
from repository.models import KnowledgeRecord

logger = logging.getLogger('enterprise')

class CandidateOrchestrationService:
    """
    Orchestration service coordinating text extraction, segmentation,
    dynamic pairing strategies, deduplication, and persistence of comparison candidates.
    """
    def __init__(self):
        self.doc_repo = DocumentRepository()
        self.rec_repo = RecordRepository()
        self.candidate_repo = CandidateRepository()
        self.doc_extractor = DocumentExtractor()
        self.rec_extractor = RecordExtractor()
        self.normalizer = TextNormalizer()
        self.segmenter = RegexSegmenter()
        
        # Force strategies registration dynamically
        try:
            import knowledge_conflict.candidates.strategies
        except ImportError:
            pass

    def generate_candidates(self) -> dict:
        """
        Main execution workflow returning a CandidateGenerationReport.
        Coordinates processing rules within an atomic transaction.
        """
        start_time = time.time()
        batch_id = f"{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4()}"
        
        # 1. Load and validate candidate rules configuration
        config = RulesLoader.load_rules()
        CandidateValidator.validate_rules_config(config)
        
        # 2. Fetch registry documents and records
        docs = list(self.doc_repo.list_active())
        records = list(KnowledgeRecord.objects.all())
        CandidateValidator.validate_generation_inputs(docs, records)
        
        logger.info(f"[Batch: {batch_id}] Beginning candidate generation for {len(docs)} documents and {len(records)} records.")
        
        # 3. Extract and normalize segment components
        all_segments = []
        
        # Process document objects
        for doc in docs:
            raw_segments = self.doc_extractor.extract(doc)
            for raw_seg in raw_segments:
                norm_text = self.normalizer.normalize(raw_seg["text"])
                # Segment raw text semantically into sentences/paragraphs
                sub_segments = self.segmenter.segment(norm_text.original, source_id=str(doc.id))
                for sub in sub_segments:
                    norm_sub = self.normalizer.normalize(sub["text"])
                    all_segments.append({
                        "segment_id": sub["segment_id"],
                        "text": norm_sub.original,           # Preserved original text
                        "normalized": norm_sub.normalized,   # Lowercase copy for matching
                        "type": sub["type"],
                        "page": sub.get("page"),
                        "section": sub.get("section"),
                        "metadata": {
                            **raw_seg["metadata"],
                            "type": sub["type"]
                        }
                    })
                    
        # Process record objects
        for record in records:
            raw_segments = self.rec_extractor.extract(record)
            for raw_seg in raw_segments:
                norm_text = self.normalizer.normalize(raw_seg["text"])
                all_segments.append({
                    "segment_id": raw_seg["segment_id"],
                    "text": norm_text.original,
                    "normalized": norm_text.normalized,
                    "type": "record",
                    "page": None,
                    "section": raw_seg.get("section"),
                    "metadata": raw_seg["metadata"]
                })
                
        # 4. Resolve active strategies from registry
        active_strategies = StrategyRegistry.get_active_strategies(config)
        raw_candidates = []
        
        # Execute each registered pairing logic strategy
        for strategy in active_strategies:
            strat_name = strategy.__class__.__name__
            logger.debug(f"Executing pairing strategy: {strat_name}")
            try:
                strategy_pairs = strategy.generate_pairs(docs, records, all_segments)
                raw_candidates.extend(strategy_pairs)
            except Exception as e:
                logger.error(f"Strategy {strat_name} failed during execution: {str(e)}", exc_info=True)
                
        # 5. Run CandidateDeduplicator using fingerprints
        deduplicated, duplicates_removed = CandidateDeduplicator.deduplicate(raw_candidates)
        
        # Limit comparison counts if configured
        max_limit = config.get("max_comparisons", 10000)
        if len(deduplicated) > max_limit:
            logger.warning(f"Generated candidates count ({len(deduplicated)}) exceeds max_limit ({max_limit}). Truncating list.")
            deduplicated = deduplicated[:max_limit]
            
        # 6. Build and persist candidates inside transaction boundaries
        candidates_to_save = []
        for cand_data in deduplicated:
            # Validate payload fields
            CandidateValidator.validate_candidate_fields(cand_data)
            
            # Construct model instance
            candidate_obj = CandidateBuilder.build(cand_data, batch_id)
            candidates_to_save.append(candidate_obj)
            
        # Bulk save records via repository pattern
        if candidates_to_save:
            with transaction.atomic():
                self.candidate_repo.bulk_create(candidates_to_save)
                
        elapsed_duration = time.time() - start_time
        logger.info(f"[Batch: {batch_id}] Successfully generated and persisted {len(candidates_to_save)} comparison candidates in {elapsed_duration:.3f}s.")
        
        # Return Candidate Generation execution stats report
        return {
            "batch_id": batch_id,
            "documents_processed": len(docs),
            "records_processed": len(records),
            "segments_generated": len(all_segments),
            "raw_pairs_generated": len(raw_candidates),
            "candidates_persisted": len(candidates_to_save),
            "duplicates_removed": duplicates_removed,
            "execution_time": round(elapsed_duration, 4)
        }
