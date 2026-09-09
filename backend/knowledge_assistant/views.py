import re
import logging
import json
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AssistantSession, AssistantMessage
from .serializers import (
    AssistantSessionSerializer,
    AssistantSessionListSerializer,
    AssistantMessageSerializer
)
from .orchestrator import DynamicKnowledgeOrchestrator
from .rag_service import SemanticRAGService
from ekcd.graph_service import UniversalKnowledgeGraphService

logger = logging.getLogger('enterprise')

def make_json_serializable(obj):
    """
    Recursively converts sets, tuples, UUIDs, and custom objects into JSON-serializable primitives.
    """
    if isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, set, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif hasattr(obj, '__dict__'):
        return str(obj)
    elif hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return obj


def generate_conversation_title(query: str) -> str:
    """
    Generates a clean, human-readable ChatGPT-style title from the initial meaningful query.
    Works generically across documents, receipts, sales datasets, and enterprise questions.
    """
    q_clean = query.strip()
    if not q_clean:
        return "New Conversation"

    # Specific topic detection heuristics (Generic)
    q_lower = q_clean.lower()
    if "internship" in q_lower:
        return "Internship Report Analysis"
    elif any(k in q_lower for k in ["sales", "dirty_100_rows", "revenue", "highest sold"]):
        return "Enterprise Sales Analysis"
    elif any(k in q_lower for k in ["receipt", "invoice", "x5100576", "x5100536", "tax invoice", "pharmacy"]):
        return "Receipt Analysis"
    elif "employee" in q_lower or "salary" in q_lower:
        return "Employee & Compensation Directory"
    elif "superstore" in q_lower:
        return "Superstore Profitability Analysis"
    elif "procurement" in q_lower:
        return "Procurement & Spend Analysis"
    elif "fraud" in q_lower or "attrition" in q_lower:
        return "HR Attrition & Fraud Analysis"

    # Generic file name cleaner
    match = re.search(r'([A-Za-z0-9_\-\s]+)\.(pdf|csv|xlsx|docx|jpg|png)', q_clean, re.IGNORECASE)
    if match:
        doc_name = match.group(1).replace('_', ' ').strip()
        doc_name = re.sub(r'\s+', ' ', doc_name)
        if len(doc_name) > 30:
            doc_name = doc_name[:27] + "..."
        return f"{doc_name.title()} Analysis"

    # Fallback to concise capitalized query snippet
    clean_snippet = re.sub(r'[\r\n\t]+', ' ', q_clean)
    clean_snippet = re.sub(r'\s+', ' ', clean_snippet).strip()
    if len(clean_snippet) > 35:
        clean_snippet = clean_snippet[:32] + "..."
    return clean_snippet[0].upper() + clean_snippet[1:]


class ChatQueryEndpoint(APIView):
    """
    POST /api/v1/knowledge-assistant/chat/
    Primary endpoint for Phase 6 Enterprise Knowledge Assistant.
    Executes hybrid RAG + KG query routing, calls local Phi-3.5 Mini LLM, and returns 4-level explanations.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        query = request.data.get('query', '').strip()
        session_id = request.data.get('session_id')

        if not query:
            return Response(
                {"error": "Query string cannot be empty.", "message": "Query string cannot be empty."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Retrieve or create session
            session = None
            if session_id:
                session = AssistantSession.objects.filter(id=session_id, user=request.user).first()
            
            if not session:
                title = generate_conversation_title(query)
                session = AssistantSession.objects.create(user=request.user, title=title)
            elif session.title in ["New Conversation", "Untitled Conversation"] or session.messages.count() <= 1:
                session.title = generate_conversation_title(query)
                session.save()

            # Record User Query Message
            user_msg = AssistantMessage.objects.create(
                session=session,
                role='user',
                content=query
            )

            # Execute Orchestrator Query Pipeline
            orchestrator = DynamicKnowledgeOrchestrator()
            result = orchestrator.execute_query(query, user=request.user)

            # Sanitize JSON payloads
            response_levels = make_json_serializable(result.get("response_levels", {}))
            kg_path = make_json_serializable(result.get("kg_path", []))
            evidence_chunks = make_json_serializable(result.get("evidence_chunks", []))
            knowledge_paths = make_json_serializable(result.get("knowledge_paths", []))
            sources = make_json_serializable(result.get("sources", []))
            claims_mapping = make_json_serializable(result.get("grounded_reasoning_state", {}).get("claims_mapping", []))
            evidence_and_sources = make_json_serializable(result.get("evidence_and_sources", {}))

            # Record Assistant Response Message with 4-Level Explanation
            assistant_msg = AssistantMessage.objects.create(
                session=session,
                role='assistant',
                content=result.get("answer", ""),
                intent_category=result.get("intent_category", "SEMANTIC_UNSTRUCTURED"),
                retrieval_method=result.get("retrieval_method", "HYBRID"),
                response_levels=response_levels,
                kg_path=kg_path,
                evidence_chunks=evidence_chunks,
                knowledge_paths=knowledge_paths,
                sources=sources,
                model_used=result.get("model_used", "Phi-3.5-Mini-3.8B-Q4_K_M"),
                latency_seconds=result.get("latency_seconds", 0.0)
            )

            return Response({
                "session_id": str(session.id),
                "session_title": session.title,
                "query": query,
                "answer": assistant_msg.content,
                "response_levels": response_levels,
                "evidence_and_sources": evidence_and_sources,
                "kg_path": kg_path,
                "claims_mapping": claims_mapping,
                "intent_category": assistant_msg.intent_category,
                "retrieval_method": assistant_msg.retrieval_method,
                "evidence_chunks": assistant_msg.evidence_chunks,
                "knowledge_paths": assistant_msg.knowledge_paths,
                "sources": assistant_msg.sources,
                "model_used": assistant_msg.model_used,
                "latency_seconds": assistant_msg.latency_seconds,
                "created_at": assistant_msg.created_at
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error("ChatQueryEndpoint execution error: %s", str(e), exc_info=True)
            return Response({
                "error": "Assistant processing error",
                "message": f"Assistant Error: {str(e)}",
                "details": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SessionListEndpoint(APIView):
    """
    GET /api/v1/knowledge-assistant/sessions/
    POST /api/v1/knowledge-assistant/sessions/
    Retrieves all conversation sessions or creates a new clean session for the active user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = AssistantSession.objects.filter(user=request.user).order_by('-updated_at')
        serializer = AssistantSessionListSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        title = request.data.get('title', 'New Conversation')
        session = AssistantSession.objects.create(user=request.user, title=title)
        serializer = AssistantSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class SessionDetailEndpoint(APIView):
    """
    GET /api/v1/knowledge-assistant/sessions/<uuid:session_id>/
    DELETE /api/v1/knowledge-assistant/sessions/<uuid:session_id>/
    Retrieves or deletes a specific conversation session.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, session_id):
        session = AssistantSession.objects.filter(id=session_id, user=request.user).first()
        if not session:
            return Response({"error": "Conversation session not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AssistantSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, session_id):
        session = AssistantSession.objects.filter(id=session_id, user=request.user).first()
        if not session:
            return Response({"error": "Conversation session not found."}, status=status.HTTP_404_NOT_FOUND)

        # Deletes session & messages ONLY (leaving documents, FAISS, KnowledgeRecords, and KG untouched)
        session.delete()
        return Response({
            "status": "SUCCESS",
            "message": f"Conversation '{session_id}' deleted successfully.",
            "session_id": str(session_id)
        }, status=status.HTTP_200_OK)


class ChatHistoryEndpoint(APIView):
    """
    GET /api/v1/knowledge-assistant/history/
    Retrieves all conversation sessions with full message lists for the active user.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        sessions = AssistantSession.objects.filter(user=request.user).order_by('-updated_at')
        serializer = AssistantSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ReindexDatasetEndpoint(APIView):
    """
    POST /api/v1/knowledge-assistant/reindex/
    Triggers re-indexing of all 18 enterprise datasets into FAISS and Universal Knowledge Graph.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        rag = SemanticRAGService()
        rag.initialize_embeddings()

        kg = UniversalKnowledgeGraphService()
        kg.initialize_graph(force_rebuild=True)

        return Response({
            "status": "SUCCESS",
            "message": "Universal Enterprise Knowledge Base re-indexed successfully.",
            "vector_chunks": rag.index.ntotal if rag.index else 0,
            "graph_nodes": kg.graph.number_of_nodes() if kg.graph else 0,
            "graph_edges": kg.graph.number_of_edges() if kg.graph else 0
        }, status=status.HTTP_200_OK)

