import os
import django
import json
import logging
from datetime import datetime

# Initialize Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "enterprise_platform.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.test import APIClient
from rest_framework import status

from ingestion.models import Document, ProcessingHistory
from ingestion.orchestration.services.orchestration_service import IngestionOrchestrationService

# Setup logger
logger = logging.getLogger('enterprise')

User = get_user_model()
TEST_FILES_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Testing", "TestFiles"))

def setup_test_user():
    username = "integration_tester"
    email = "tester@enterprise.com"
    password = "SecurePassword123"
    user, created = User.objects.get_or_create(username=username, defaults={"email": email})
    if created:
        user.set_password(password)
        user.save()
    else:
        # Reset password to ensure JWT login is deterministic
        user.set_password(password)
        user.save()
    return user, username, password

def run_tests():
    print("=" * 60)
    print("STARTING INTEGRATION TESTING SUITE FOR PHASE 1")
    print("=" * 60)
    
    # 1. Setup User & Client
    user, username, password = setup_test_user()
    client = APIClient()
    
    # Reset database records for idempotent runs
    Document.objects.all().delete()
    
    report = {
        "system_info": {
            "timestamp": datetime.now().isoformat(),
            "environment": "development",
            "db_type": "SQLite3 (Fallback Mode)"
        },
        "api_verification": {},
        "pipeline_results": [],
        "summary": {
            "total_files": 10,
            "passed": 0,
            "failed": 0
        }
    }
    
    # ------------------------------------------------------------
    # PART 4 — Verify APIs (Health, Register, Login, Refresh)
    # ------------------------------------------------------------
    print("\n[PART 4] Verification of REST APIs...")
    
    # Health API
    health_resp = client.get('/api/v1/health/')
    print(f"Health Check API: {health_resp.status_code}")
    report["api_verification"]["health_check"] = {
        "status_code": health_resp.status_code,
        "response": health_resp.data
    }
    
    # Register API (Test error status - duplicate user)
    reg_resp = client.post('/api/v1/auth/register/', {
        "username": username,
        "email": "tester_new@enterprise.com",
        "password": "NewSecurePassword123"
    })
    print(f"Register API (Duplicate User): {reg_resp.status_code}")
    report["api_verification"]["register_duplicate"] = {
        "status_code": reg_resp.status_code,
        "success": reg_resp.data.get("success", False)
    }

    # JWT Login
    login_resp = client.post('/api/v1/auth/login/', {
        "username": username,
        "password": password
    })
    print(f"Login API: {login_resp.status_code}")
    if login_resp.status_code != status.HTTP_200_OK:
        print("Login failed! Aborting tests.")
        return
        
    access_token = login_resp.data.get("data", {}).get("access")
    refresh_token = login_resp.data.get("data", {}).get("refresh")
    
    report["api_verification"]["login"] = {
        "status_code": login_resp.status_code,
        "has_access_token": access_token is not None,
        "has_refresh_token": refresh_token is not None
    }
    
    # JWT Refresh
    refresh_resp = client.post('/api/v1/auth/login/refresh/', {
        "refresh": refresh_token
    })
    print(f"Refresh token API: {refresh_resp.status_code}")
    new_access_token = refresh_resp.data.get("data", {}).get("access")
    report["api_verification"]["token_refresh"] = {
        "status_code": refresh_resp.status_code,
        "has_new_access_token": new_access_token is not None
    }
    
    # Authenticate Client for subsequent calls
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
    
    # Profile API (Auth check)
    profile_resp = client.get('/api/v1/auth/profile/')
    print(f"Auth Profile API check: {profile_resp.status_code}")
    report["api_verification"]["profile_auth_check"] = {
        "status_code": profile_resp.status_code,
        "username": profile_resp.data.get("username")
    }

    # ------------------------------------------------------------
    # PART 5 — Run Integration Testing on Files
    # ------------------------------------------------------------
    print("\n[PART 5] Executing Pipeline Integration Testing on Files...")
    
    files_to_test = [
        # (filename, expect_upload_success, expect_pipeline_success, fail_reason_check)
        ("employee_data.xlsx", True, True, None),
        ("employee_data.csv", True, True, None),
        ("employee_data.json", True, True, None),
        ("employee_report.pdf", True, True, None),
        ("employee_card.png", True, True, None),
        ("scanned_invoice.pdf", True, True, None),
        ("corrupted.pdf", True, False, "MetadataValidationException"),  # parsing or validation error
        ("empty.txt", False, False, "File size must be greater than zero"),
        ("duplicate_test.pdf", False, False, "has already been uploaded"),  # duplicate SHA-256
        ("wrong_extension.pdf", False, False, "File signature mismatch")  # EXE disguised as PDF
    ]
    
    for filename, upload_ok, pipeline_ok, expected_err in files_to_test:
        file_path = os.path.join(TEST_FILES_DIR, filename)
        print(f"\nProcessing test asset file: {filename}")
        
        file_result = {
            "filename": filename,
            "upload_success": False,
            "pipeline_success": False,
            "parser_type": None,
            "stages_executed": [],
            "error": None
        }
        
        if not os.path.exists(file_path):
            print(f"Error: File not found at {file_path}")
            file_result["error"] = "File not found"
            report["pipeline_results"].append(file_result)
            report["summary"]["failed"] += 1
            continue
            
        # Open and upload file
        with open(file_path, "rb") as fp:
            file_data = SimpleUploadedFile(filename, fp.read())
            
        upload_resp = client.post('/api/v1/ingestion/upload/', {"file": file_data}, format='multipart')
        print(f"  Upload Response Status: {upload_resp.status_code}")
        
        if upload_resp.status_code == status.HTTP_201_CREATED:
            file_result["upload_success"] = True
            doc_id = upload_resp.data["data"]["document_id"]
            print(f"  Uploaded Document ID: {doc_id}")
            
            # Trigger pipeline orchestration
            try:
                orchestrator = IngestionOrchestrationService()
                orchestrator_res = orchestrator.process_document(doc_id, user)
                
                # Fetch Document state from database
                doc = Document.objects.get(id=doc_id)
                file_result["pipeline_success"] = orchestrator_res["success"]
                file_result["parser_type"] = doc.parser_type
                file_result["processing_status"] = doc.processing_status
                
                # Fetch executed stages
                histories = ProcessingHistory.objects.filter(document=doc)
                file_result["stages_executed"] = [
                    {
                        "stage": h.stage_name,
                        "status": h.stage_status,
                        "duration": h.execution_duration,
                        "errors": h.error_count
                    }
                    for h in histories
                ]
                
                if orchestrator_res["success"]:
                    print(f"  Pipeline Processing status: SUCCESS ({doc.processing_status})")
                    if pipeline_ok:
                        report["summary"]["passed"] += 1
                    else:
                        print(f"  [WARNING] Expected pipeline failure, but succeeded!")
                        report["summary"]["failed"] += 1
                else:
                    print(f"  Pipeline Processing status: FAILED. Errors: {orchestrator_res.get('errors')}")
                    file_result["error"] = orchestrator_res.get("errors")
                    if not pipeline_ok:
                        report["summary"]["passed"] += 1
                    else:
                        report["summary"]["failed"] += 1
                        
            except Exception as e:
                print(f"  Pipeline Orchestration crashed: {str(e)}")
                file_result["error"] = str(e)
                report["summary"]["failed"] += 1
                
        else:
            # Upload failed
            file_result["upload_success"] = False
            err_msg = str(upload_resp.data.get("message", "")) or str(upload_resp.data.get("errors", ""))
            file_result["error"] = err_msg
            print(f"  Upload failed (Expected: {not upload_ok}). Message: {err_msg}")
            
            # Verify if it failed for the expected reason
            if not upload_ok and expected_err and any(x in err_msg.lower() for x in expected_err.lower().split()):
                print("  Success: Upload failed as expected with matching validation constraints.")
                report["summary"]["passed"] += 1
            elif not upload_ok:
                print("  Success: Upload failed as expected.")
                report["summary"]["passed"] += 1
            else:
                print("  [ERROR] Upload failed unexpectedly!")
                report["summary"]["failed"] += 1
                
        report["pipeline_results"].append(file_result)

    # ------------------------------------------------------------
    # Save Report
    # ------------------------------------------------------------
    report_output_dir = os.path.join(TEST_FILES_DIR, "..")
    os.makedirs(report_output_dir, exist_ok=True)
    report_json_path = os.path.join(report_output_dir, "phase1_test_run_data.json")
    with open(report_json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
        
    print("\n" + "=" * 60)
    print(f"INTEGRATION TESTING COMPLETE. Passed: {report['summary']['passed']}, Failed: {report['summary']['failed']}")
    print(f"Report run details saved to: {report_json_path}")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
