from rest_framework import serializers
from repository.models import (
    KnowledgeDocument,
    KnowledgeDocumentVersion,
    KnowledgeRecord,
    KnowledgeRelationship,
    RepositoryAuditEntry,
    RepositoryFolder
)

class RepositoryFolderSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    subfolder_count = serializers.SerializerMethodField()
    document_count = serializers.SerializerMethodField()

    class Meta:
        model = RepositoryFolder
        fields = '__all__'

    def get_subfolder_count(self, obj):
        return obj.subfolders.filter(is_deleted=False).count()

    def get_document_count(self, obj):
        return obj.documents.exclude(repository_status='DELETED').count()


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


class DynamicRecordSerializer(serializers.ModelSerializer):
    employee_details = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeRecord
        fields = ('id', 'knowledge_document', 'entity_type', 'canonical_data', 'additional_fields', 'employee_details', 'created_at', 'updated_at')

    def get_employee_details(self, obj):
        data = {}
        if obj.canonical_data:
            data.update(obj.canonical_data)
        if obj.additional_fields:
            data.update(obj.additional_fields)
        return data


# Backward-compatible alias
SanitizedEmployeeRecordSerializer = DynamicRecordSerializer


