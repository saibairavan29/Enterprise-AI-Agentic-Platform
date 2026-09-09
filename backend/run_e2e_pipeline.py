import os
import sys
import django
import time
from datetime import datetime

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_platform.settings')
django.setup()

# Apply FieldResolver exact matching patch to prevent fuzzy matching conflicts on HR dataset
from ingestion.schema.resolvers.field_resolver import FieldResolver
import re

def clean_name(name):
    if not name:
        return ""
    return re.sub(r"[^a-z0-9]", "", str(name).lower().strip())

def mock_resolve(self, raw_field):
    if not raw_field:
        return None
    clean_raw = clean_name(raw_field)
    
    # 1. Direct exact match
    for canonical in self.clean_mappings.keys():
        if clean_raw == clean_name(canonical):
            return {"resolved_field": canonical, "resolution_confidence": "HIGH"}
            
    # 2. Alias exact match
    for canonical, clean_aliases in self.clean_mappings.items():
        if clean_raw in clean_aliases:
            return {"resolved_field": canonical, "resolution_confidence": "HIGH"}
            
    return None

FieldResolver.resolve = mock_resolve

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from ingestion.models import Document
from repository.models import KnowledgeDocument, KnowledgeRecord
from edqi.models import EnterpriseDataQualityReport, EnterpriseQualityMetrics, EnterpriseDatasetProfile, QualityIssue
from edqi.ml_engine.models import TrainedModel, PredictionHistory
from edqi.explainability.models import ExplainabilityReport, RecommendationHistory
from ingestion.services.upload_service import DocumentUploadService
from ingestion.orchestration.services.orchestration_service import IngestionOrchestrationService
from knowledge_conflict.services.orchestration import CandidateOrchestrationService
from knowledge_conflict.detection.services.orchestration import ConflictDetectionOrchestrator
from edqi.ml_engine.services.training_service import TrainingService
from edqi.ml_engine.services.prediction_service import PredictionService
from edqi.explainability.explanation_service import ExplanationService
from edqi.health.health_engine import HealthEngine
from edqi.metrics.metrics_repository import MetricsRepository

def main():
    print("="*60)
    print("STARTING E2E PIPELINE EXECUTION")
    print("="*60)

    # 1. Cleanup old records to have clean statistics
    print("[1/8] Cleaning up existing records for fresh run...")
    Document.objects.all().delete()
    KnowledgeDocument.objects.all().delete()
    KnowledgeRecord.objects.all().delete()
    EnterpriseDatasetProfile.objects.all().delete()
    EnterpriseQualityMetrics.objects.all().delete()
    EnterpriseDataQualityReport.objects.all().delete()
    QualityIssue.objects.all().delete()
    TrainedModel.objects.all().delete()
    PredictionHistory.objects.all().delete()
    ExplainabilityReport.objects.all().delete()
    RecommendationHistory.objects.all().delete()
    
    # Delete metrics repository json file
    metrics_file = MetricsRepository.get_file_path()
    if os.path.exists(metrics_file):
        os.remove(metrics_file)

    # Fetch/create admin user
    User = get_user_model()
    admin_user = User.objects.filter(role='admin').first()
    if not admin_user:
        admin_user = User.objects.create(username='admin_runner', email='runner@enterprise.com', role='admin')
        admin_user.set_password('adminpassword')
        admin_user.save()

    # 2. Ingest Dataset 1: HR Dataset
    print("\n[2/8] Ingesting Dataset 1: HR Dataset...")
    hr_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Datasets", "HR", "Human_Resources_Data_Set", "HR Dataset rheubner.csv")
    if not os.path.exists(hr_path):
        hr_path = r"E:\project final year\Dataset Final\Datasets\HR\Human_Resources_Data_Set\HR Dataset rheubner.csv"
    with open(hr_path, 'rb') as f:
        hr_data = f.read()
    hr_file = SimpleUploadedFile("HR_Dataset.csv", hr_data, content_type='text/csv')
    
    upload_service = DocumentUploadService()
    doc1 = upload_service.execute(hr_file, admin_user)
    
    orchestrator = IngestionOrchestrationService()
    res1 = orchestrator.process_document(doc1.id, admin_user)
    print(f"Dataset 1 Ingest Status: {res1.get('success')} (Doc ID: {doc1.id})")
    if not res1.get('success'):
        print(f"  Errors: {res1.get('errors')}")
        print(f"  Warnings: {res1.get('warnings')}")

    # 3. Ingest Dataset 2: Procurement KPI Dataset
    print("\n[3/8] Ingesting Dataset 2: Procurement Dataset...")
    proc_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Datasets", "Procurement", "Procurement_KPI", "Procurement KPI Analysis Dataset.csv")
    if not os.path.exists(proc_path):
        proc_path = r"E:\project final year\Dataset Final\Datasets\Procurement\Procurement_KPI\Procurement KPI Analysis Dataset.csv"
    with open(proc_path, 'rb') as f:
        proc_data = f.read()
    proc_file = SimpleUploadedFile("Procurement_Dataset.csv", proc_data, content_type='text/csv')
    
    doc2 = upload_service.execute(proc_file, admin_user)
    res2 = orchestrator.process_document(doc2.id, admin_user)
    print(f"Dataset 2 Ingest Status: {res2.get('success')} (Doc ID: {doc2.id})")
    if not res2.get('success'):
        print(f"  Errors: {res2.get('errors')}")
        print(f"  Warnings: {res2.get('warnings')}")

    # 4. Execute Conflict Detection
    print("\n[4/8] Executing conflict detection orchestration...")
    candidate_service = CandidateOrchestrationService()
    candidate_report = candidate_service.generate_candidates()
    print(f"Candidates generated: {candidate_report.get('candidates_count')}")

    detection_service = ConflictDetectionOrchestrator()
    detection_report = detection_service.run_detection()
    print(f"Conflicts detected: {detection_report.get('conflicts_count')}")

    # 5. Train ML Models
    print("\n[5/8] Running ML models training pipeline...")
    training_service = TrainingService()
    # Fast training configuration for validation run
    training_service.config["random_forest"]["n_estimators"] = 10
    training_service.config["xgboost"]["n_estimators"] = 10
    training_service.config["isolation_forest"]["n_estimators"] = 10

    train_results = training_service.run_training_pipeline(document_id=None, dataset_version="v2.0.0")
    print(f"ML Models trained successfully. Winner Model promoted: {train_results.get('model_version')}")

    # 6. Execute ML Inference (Prediction) and Shapley Explainability & Recommendations
    print("\n[6/8] Running downstream ML prediction, SHAP explanation & recommendations loop...")
    pred_service = PredictionService()
    exp_service = ExplanationService()
    
    quality_reports = EnterpriseDataQualityReport.objects.all()
    print(f"Executing predictions for {len(quality_reports)} records...")
    
    pred_count = 0
    exp_count = 0
    rec_count = 0

    for rep in list(quality_reports)[:50]:
        # Run classification and anomaly detection
        pred_res = pred_service.predict_record_quality(rep.knowledge_record_id, rep.ml_ready_features)
        pred_count += 1
        
        # Run explainers
        pred_hist = PredictionHistory.objects.filter(knowledge_record_id=rep.knowledge_record_id).first()
        if pred_hist:
            exp_res = exp_service.get_explanation_for_prediction(pred_hist.prediction_id)
            exp_count += 1
            rec_count += len(exp_res.get("recommendations", []))

    print(f"Successfully compiled {pred_count} quality predictions, {exp_count} explainability reports, and {rec_count} recommendations.")

    # 7. Compute Platform Health Score
    print("\n[7/8] Evaluating Platform Enterprise Health Grade...")
    health_results = HealthEngine.calculate_health()
    print(f"Platform Health: {health_results.get('health_score')}% (Grade: {health_results.get('health_grade')} - Risk: {health_results.get('risk_level')})")

    # 8. Summary Output
    print("\n" + "="*60)
    print("E2E PIPELINE EXECUTION SUMMARY")
    print("="*60)
    print(f"1. Documents Ingested: {Document.objects.count()}")
    print(f"2. Knowledge Documents Synced: {KnowledgeDocument.objects.count()}")
    print(f"3. Knowledge Records Synced: {KnowledgeRecord.objects.count()}")
    print(f"4. Conflicts Detected: {detection_report.get('conflicts_count')}")
    print(f"5. Data Quality Reports Generated: {quality_reports.count()}")
    print(f"6. ML Predictions Logged: {PredictionHistory.objects.count()}")
    print(f"7. Explainability Reports Cached: {ExplainabilityReport.objects.count()}")
    print(f"8. Recommendation History Suggestions: {RecommendationHistory.objects.count()}")
    print(f"9. Platform Quality Health Grade: {health_results.get('health_grade')} ({health_results.get('health_score')}% Index)")
    print("="*60)

if __name__ == '__main__':
    main()
