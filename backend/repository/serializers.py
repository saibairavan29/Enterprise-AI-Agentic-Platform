from rest_framework import serializers
from repository.models import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeRecord,
    KnowledgeRelationship,
    RepositoryAuditEntry
)

class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeDocument
        fields = '__all__'


class KnowledgeDocumentVersionSerializer(serializers.ModelSerializer):
    updated_by_username = serializers.CharField(source='updated_by.username', read_only=True)

    class Meta:
        model = KnowledgeDocumentVersion
        fields = '__all__'


class KnowledgeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = KnowledgeRecord
        fields = '__all__'


class KnowledgeRelationshipSerializer(serializers.ModelSerializer):
    source_title = serializers.CharField(source='source_document.title', read_only=True)
    target_title = serializers.CharField(source='target_document.title', read_only=True)

    class Meta:
        model = KnowledgeRelationship
        fields = '__all__'


class RepositoryAuditEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = RepositoryAuditEntry
        fields = '__all__'


class SanitizedEmployeeRecordSerializer(serializers.ModelSerializer):
    employee_details = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeRecord
        fields = ('id', 'knowledge_document', 'employee_details', 'created_at')

    def get_employee_details(self, obj):
        data = obj.canonical_data or {}
        safe_keys = {
            "employee_id", "name", "role", "department", 
            "experience_years", "current_project", 
            "work_location", "employment_status", 
            "skills", "joining_date", "email"
        }
        # Strips out 'salary', bank_info, etc. at serialization layer
        return {k: v for k, v in data.items() if k in safe_keys}

