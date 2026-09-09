from rest_framework import serializers
from .models import AssistantSession, AssistantMessage

class AssistantMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssistantMessage
        fields = [
            'id', 'session', 'role', 'content', 'intent_category',
            'retrieval_method', 'response_levels', 'kg_path', 'evidence_chunks',
            'knowledge_paths', 'sources', 'model_used', 'latency_seconds', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AssistantSessionSerializer(serializers.ModelSerializer):
    messages = AssistantMessageSerializer(many=True, read_only=True)

    class Meta:
        model = AssistantSession
        fields = ['id', 'user', 'title', 'messages', 'created_at', 'updated_at']
        read_only_fields = ['id', 'user', 'created_at', 'updated_at']


class AssistantSessionListSerializer(serializers.ModelSerializer):
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = AssistantSession
        fields = ['id', 'title', 'message_count', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_message_count(self, obj):
        return obj.messages.count()

