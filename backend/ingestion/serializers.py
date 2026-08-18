from rest_framework import serializers
from .models import Document

class DocumentSerializer(serializers.ModelSerializer):
    """
    Serializer representing the stored Document entity.
    """
    uploaded_by = serializers.ReadOnlyField(source='uploaded_by.username')

    class Meta:
        model = Document
        fields = (
            'id', 
            'uploaded_by', 
            'file', 
            'file_hash', 
            'original_name', 
            'file_size', 
            'mime_type', 
            'processing_status', 
            'validation_status', 
            'created_at', 
            'updated_at'
        )
        read_only_fields = fields


class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer to receive and validate the raw file upload stream.
    """
    file = serializers.FileField(required=True, help_text="The binary document stream to upload.")
    repository_type = serializers.CharField(required=False, default='team')

    def validate_file(self, value):
        # Additional basic validation can go here if needed
        if not value:
            raise serializers.ValidationError("File is required.")
        return value

    def validate_repository_type(self, value):
        if value not in ['personal', 'team']:
            raise serializers.ValidationError("repository_type must be either 'personal' or 'team'.")
        return value
