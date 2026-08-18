from rest_framework import serializers
from ..models import KnowledgeCandidate, KnowledgeConflict
from .models import ConflictReview, ConflictAuditHistory

class CandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeCandidate
        fields = '__all__'


class ConflictSerializer(serializers.ModelSerializer):
    source_title = serializers.CharField(source='source_document.title', read_only=True)
    target_title = serializers.CharField(source='target_document.title', read_only=True)
    source_text = serializers.CharField(source='knowledge_candidate.source_text', read_only=True)
    target_text = serializers.CharField(source='knowledge_candidate.target_text', read_only=True)
    source_segment_id = serializers.CharField(source='knowledge_candidate.source_segment_id', read_only=True)
    target_segment_id = serializers.CharField(source='knowledge_candidate.target_segment_id', read_only=True)
    strategy_used = serializers.CharField(source='knowledge_candidate.strategy_used', read_only=True)
    source_record = serializers.SerializerMethodField()
    target_record = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeConflict
        fields = [
            'id', 'conflict_id', 'knowledge_candidate', 'source_document', 'target_document',
            'source_title', 'target_title', 'source_text', 'target_text', 'source_segment_id', 'target_segment_id',
            'strategy_used', 'conflict_type', 'severity', 'overall_similarity', 'similarity_metrics',
            'confidence_score', 'embedding_model', 'embedding_metadata', 'classifier_used', 'explanation',
            'evidence', 'processing_trace', 'status', 'metadata', 'detected_at', 'updated_at',
            'source_record', 'target_record'
        ]

    def _sanitize_record(self, record):
        raw = {}
        if record.canonical_data:
            raw.update(record.canonical_data)
        if record.additional_fields:
            raw.update(record.additional_fields)
            
        mapped = {}
        for k, v in raw.items():
            mapped[k.lower().replace(" ", "_")] = v
            
        allowed = {}
        def get_val(keys):
            for k in keys:
                if k in mapped:
                    return mapped[k]
            return None

        allowed["employee_id"] = get_val(["employee_id", "id"])
        allowed["name"] = get_val(["employee_name", "name"])
        allowed["role"] = get_val(["role", "manager", "role_title"])
        allowed["department"] = get_val(["department"])
        allowed["experience_years"] = get_val(["experience_years", "experience"])
        allowed["current_project"] = get_val(["current_project", "project"])
        allowed["work_location"] = get_val(["work_location", "location"])
        allowed["employment_status"] = get_val(["employment_status", "status"])
        allowed["skills"] = get_val(["skills"])
        allowed["joining_date"] = get_val(["joining_date"])
        allowed["email"] = get_val(["email"])
        return allowed

    def get_source_record(self, obj):
        cand = obj.knowledge_candidate
        src_rec_id = cand.metadata.get("source_record_id")
        if src_rec_id:
            try:
                from repository.models import KnowledgeRecord
                rec = KnowledgeRecord.objects.get(id=int(src_rec_id))
                return self._sanitize_record(rec)
            except Exception:
                pass
        return None

    def get_target_record(self, obj):
        cand = obj.knowledge_candidate
        tgt_rec_id = cand.metadata.get("target_record_id")
        if tgt_rec_id:
            try:
                from repository.models import KnowledgeRecord
                rec = KnowledgeRecord.objects.get(id=int(tgt_rec_id))
                return self._sanitize_record(rec)
            except Exception:
                pass
        return None


class ReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='reviewer.username', read_only=True)
    conflict_uuid = serializers.UUIDField(source='conflict.conflict_id', read_only=True)

    class Meta:
        model = ConflictReview
        fields = [
            'id', 'review_id', 'conflict', 'conflict_uuid', 'reviewer', 'reviewer_name',
            'review_status', 'decision', 'resolution', 'comments', 'reviewed_at',
            'created_at', 'updated_at'
        ]


class AuditHistorySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    conflict_uuid = serializers.UUIDField(source='conflict.conflict_id', read_only=True)

    class Meta:
        model = ConflictAuditHistory
        fields = [
            'id', 'conflict', 'conflict_uuid', 'user', 'username', 'action', 'action_type',
            'old_status', 'new_status', 'comments', 'timestamp'
        ]
