import os
from django.test import TestCase
from django.contrib.auth import get_user_model
from knowledge_assistant.orchestrator import DynamicKnowledgeOrchestrator
from repository.models import KnowledgeDocument, KnowledgeRecord

User = get_user_model()

class ERPOrchestratorIntentTestCase(TestCase):
    """
    Test suite for Expanded Phase 5 Enterprise Knowledge Assistant Orchestration & Intent Detection.
    Verifies query understanding, intent classification, multi-intent routing, failsafes, and deterministic calculations.
    """

    def setUp(self):
        self.orchestrator = DynamicKnowledgeOrchestrator()
        self.user = User.objects.create_user(username='erp_test_user', password='password123')
        
        self.doc = KnowledgeDocument.objects.create(
            title='sample_dirty_hr_dataset.csv',
            metadata={'repository_type': 'team'}
        )
        KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            canonical_data={'employee_id': 'EMP001', 'department': 'IT/IS', 'salary': 85000, 'employment_status': 'Active'},
            additional_fields={'Employee_Name': 'John Doe'}
        )
        KnowledgeRecord.objects.create(
            knowledge_document=self.doc,
            canonical_data={'employee_id': 'EMP002', 'department': 'Sales', 'salary': 60000, 'employment_status': 'Terminated'},
            additional_fields={'Employee_Name': 'Jane Smith'}
        )

    def test_01_factual_retrieval_intent(self):
        intent = self.orchestrator.classify_intent("Find employee EMP001")
        self.assertIn(intent, ["DOCUMENT_FACTUAL_RETRIEVAL", "FACTUAL_RETRIEVAL", "ANALYTICAL_CALCULATION"])

    def test_02_analytical_aggregation_intent(self):
        res = self.orchestrator.execute_query("What is the average salary in IT/IS?", user=self.user)
        self.assertIn(res["intent_category"], ["ANALYTICAL_CALCULATION", "RANKING_ANALYSIS"])
        self.assertTrue(len(res["evidence_chunks"]) > 0)

    def test_03_grouping_intent(self):
        intent = self.orchestrator.classify_intent("Show average salary by department")
        self.assertIn(intent, ["GROUPED_ANALYSIS", "ANALYTICAL_CALCULATION"])

    def test_04_ranking_intent(self):
        intent = self.orchestrator.classify_intent("Which supplier has the highest procurement spend?")
        self.assertIn(intent, ["RANKING_ANALYSIS", "ANALYTICAL_CALCULATION"])

    def test_05_status_percentage_intent(self):
        res = self.orchestrator.execute_query("sample_dirty_hr_dataset.csv, what percentage of employees are active?", user=self.user)
        self.assertIn(res["intent_category"], ["STATUS_ANALYSIS", "ANALYTICAL_CALCULATION"])
        self.assertTrue(any("Employee Status" in ev["title"] for ev in res["evidence_chunks"]))

    def test_06_comparison_intent(self):
        intent = self.orchestrator.classify_intent("Compare Technology and Furniture sales")
        self.assertIn(intent, ["COMPARISON", "COMPARISON_ANALYSIS", "ANALYTICAL_CALCULATION"])

    def test_07_conflict_detection_intent(self):
        intent = self.orchestrator.classify_intent("Find conflicting employee records")
        self.assertEqual(intent, "CONFLICT_DETECTION")

    def test_08_duplicate_detection_intent(self):
        intent = self.orchestrator.classify_intent("Find duplicate employee IDs")
        self.assertEqual(intent, "DUPLICATE_DETECTION")

    def test_09_data_quality_intent(self):
        intent = self.orchestrator.classify_intent("How complete is the employee dataset?")
        self.assertIn(intent, ["DATA_QUALITY", "COMPLETENESS_ANALYSIS", "HYBRID_ANALYSIS"])

    def test_10_fraud_analysis_intent(self):
        intent = self.orchestrator.classify_intent("What percentage of job postings are fraudulent?")
        self.assertEqual(intent, "FRAUD_ANALYSIS")

    def test_11_kg_multi_hop_intent(self):
        intent = self.orchestrator.classify_intent("Who manages Wilson K Adinolfi?")
        self.assertIn(intent, ["KG_MULTI_HOP", "ANALYTICAL_CALCULATION"])

    def test_12_policy_rag_intent(self):
        intent = self.orchestrator.classify_intent("What are the core functions of the NIST cybersecurity framework?")
        self.assertEqual(intent, "POLICY_QUERY")

    def test_13_unsupported_query_failsafe(self):
        res = self.orchestrator.execute_query("What is the Customer Acquisition Cost (CAC) for Superstore?", user=self.user)
        self.assertEqual(res["intent_category"], "UNSUPPORTED_QUERY")
        self.assertTrue(any("Insufficient evidence" in ev["text"] for ev in res["evidence_chunks"]))

    def test_14_security_authorization_intent(self):
        intent = self.orchestrator.classify_intent("Can I access private restricted document?")
        self.assertEqual(intent, "SECURITY_AUTHORIZATION")

    # MANDATORY SECTION 33 ACCEPTANCE TEST SUITE
    def test_15_sec33_test1_text_rich_pdf_scope_lock(self):
        pdf_doc = KnowledgeDocument.objects.create(
            title='Internship Report_YOGESHWARAN K.pdf',
            raw_content='Internship Report for Yogeshwaran K. Summary of work, architecture details, and key accomplishments.',
            metadata={'repository_type': 'team'}
        )
        res = self.orchestrator.execute_query("Internship Report_YOGESHWARAN K.pdf, read this document carefully and explain what it contains", user=self.user)
        self.assertIn(res["intent_category"], ["DOCUMENT_ANALYSIS", "DOCUMENT_SUMMARY"])
        self.assertEqual(len(res["knowledge_paths"]), 0)
        self.assertTrue(all("Internship Report_YOGESHWARAN K.pdf" in ev["source"] for ev in res["evidence_chunks"]))
        self.assertIn("execution_audit_trace", res)

    def test_16_sec33_test2_scanned_pdf_ocr_fallback(self):
        scan_doc = KnowledgeDocument.objects.create(
            title='BHARATHWAJ EXAM FEE.pdf',
            metadata={'repository_type': 'team'}
        )
        res = self.orchestrator.execute_query("BHARATHWAJ EXAM FEE.pdf, tell me the amount paid", user=self.user)
        trace = res.get("execution_audit_trace", {})
        self.assertTrue(trace.get("ocr_attempted", False))
        self.assertGreaterEqual(trace.get("ocr_pages_attempted", 0), 1)
        if trace.get("ocr_success"):
            self.assertGreater(trace.get("ocr_text_length", 0), 0)
            self.assertGreater(trace.get("evidence_count", 0), 0)
        else:
            self.assertIsNotNone(trace.get("ocr_error"))
            self.assertIn("Extraction Failure", res["answer"])
        self.assertNotIn("No direct content available", res["answer"])

    def test_17_sec33_test3_csv_overview(self):
        res = self.orchestrator.execute_query("What does this dataset contain? sample_dirty_hr_dataset.csv", user=self.user)
        self.assertIn(res["intent_category"], ["STRUCTURED_DATA_ANALYSIS", "DOCUMENT_SUMMARY"])

    def test_18_sec33_test4_csv_deterministic_calculation(self):
        res = self.orchestrator.execute_query("sample_dirty_hr_dataset.csv, which department has highest average salary?", user=self.user)
        self.assertIn(res["intent_category"], ["RANKING_ANALYSIS", "ANALYTICAL_CALCULATION"])

    def test_19_sec33_test5_xlsx_trend_analysis(self):
        intent = self.orchestrator.classify_intent("Analyze this spreadsheet and identify important trends in Sample - Superstore.xlsx")
        self.assertIn(intent, ["STRUCTURED_DATA_ANALYSIS", "ANALYTICAL_CALCULATION", "DOCUMENT_SUMMARY"])

    def test_20_sec33_test6_json_structure(self):
        intent = self.orchestrator.classify_intent("What information does this JSON contain?")
        self.assertIn(intent, ["STRUCTURED_DATA_ANALYSIS", "DOCUMENT_SUMMARY"])

    def test_21_sec33_test7_docx_summary(self):
        intent = self.orchestrator.classify_intent("Summarize this docx document")
        self.assertIn(intent, ["DOCUMENT_SUMMARY", "DOCUMENT_ANALYSIS"])

    def test_22_sec33_test8_image_ocr_key_values(self):
        intent = self.orchestrator.classify_intent("Read this receipt image and tell me the important information")
        self.assertIn(intent, ["DOCUMENT_ANALYSIS", "DOCUMENT_FACTUAL_RETRIEVAL"])

    def test_23_sec33_test9_cross_source_comparison(self):
        intent = self.orchestrator.classify_intent("Compare information from File A and File B")
        self.assertIn(intent, ["COMPARISON", "COMPARISON_ANALYSIS"])

    def test_24_sec33_test10_kg_relationship_query(self):
        intent = self.orchestrator.classify_intent("What employees are connected to this project?")
        self.assertIn(intent, ["KG_MULTI_HOP", "CROSS_SOURCE_ANALYSIS"])

    def test_25_sec33_test11_no_kg_document_query(self):
        res = self.orchestrator.execute_query("Summarize Internship Report_YOGESHWARAN K.pdf", user=self.user)
        self.assertEqual(len(res["knowledge_paths"]), 0)

    def test_26_sec33_test12_unsupported_info_failsafe(self):
        res = self.orchestrator.execute_query("What is the stock price forecast for non_existent_company?", user=self.user)
        self.assertTrue(len(res["answer"]) > 0)
