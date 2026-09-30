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

        self.so_doc = KnowledgeDocument.objects.create(
            title='Sales_Orders.csv',
            logical_path='Team/enterprise_ingestion_test_pack/csv/Sales_Orders.csv',
            metadata={'repository_type': 'team'}
        )
        so_records = [
            {'Order_ID': 'SO1001', 'Product': 'Industrial Sensor', 'Client': 'Arun Industries', 'Business_Unit': 'AI Engineering', 'Order_Date': '2026-07-01', 'Quantity': 12, 'Unit_Price': 18000, 'Net_Amount': 216000},
            {'Order_ID': 'SO1002', 'Product': 'Control Panel', 'Client': 'Metro Controls', 'Business_Unit': 'Sales', 'Order_Date': '2026-07-03', 'Quantity': 8, 'Unit_Price': 24000, 'Net_Amount': 192000},
            {'Order_ID': 'SO1003', 'Product': 'Drive System', 'Client': 'Harbour Automation', 'Business_Unit': 'Operations', 'Order_Date': '2026-07-08', 'Quantity': 10, 'Unit_Price': 37500, 'Net_Amount': 375000},
            {'Order_ID': 'SO1004', 'Product': 'Industrial Sensor', 'Client': 'Prime Manufacturing', 'Business_Unit': 'Sales', 'Order_Date': '2026-07-12', 'Quantity': 15, 'Unit_Price': 18000, 'Net_Amount': 270000},
            {'Order_ID': 'SO1005', 'Product': 'Control Panel', 'Client': 'Arun Industries', 'Business_Unit': 'AI Engineering', 'Order_Date': '2026-07-18', 'Quantity': 6, 'Unit_Price': 24000, 'Net_Amount': 144000},
            {'Order_ID': 'SO1006', 'Product': 'Drive System', 'Client': 'Metro Controls', 'Business_Unit': 'Operations', 'Order_Date': '2026-07-22', 'Quantity': 5, 'Unit_Price': 37500, 'Net_Amount': 187500},
            {'Order_ID': 'SO1008', 'Product': 'Control Panel', 'Client': 'Prime Manufacturing', 'Business_Unit': 'AI Engineering', 'Order_Date': '2026-08-05', 'Quantity': 11, 'Unit_Price': 24000, 'Net_Amount': 264000},
            {'Order_ID': 'SO1009', 'Product': 'Drive System', 'Client': 'Arun Industries', 'Business_Unit': 'Operations', 'Order_Date': '2026-08-10', 'Quantity': 7, 'Unit_Price': 37500, 'Net_Amount': 262500},
            {'Order_ID': 'SO1010', 'Product': 'Industrial Sensor', 'Client': 'Metro Controls', 'Business_Unit': 'Sales', 'Order_Date': '2026-08-14', 'Quantity': 14, 'Unit_Price': 18000, 'Net_Amount': 252000},
        ]
        for rdata in so_records:
            KnowledgeRecord.objects.create(
                knowledge_document=self.so_doc,
                canonical_data=rdata,
                additional_fields=rdata
            )
        self.lnt_doc = KnowledgeDocument.objects.create(
            title='L&T Life Saving Rules 4 1.pdf',
            logical_path='Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf',
            metadata={'repository_type': 'team'}
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
        self.assertIn(res["intent_category"], ["STATUS_ANALYSIS", "ANALYTICAL_CALCULATION", "STRUCTURED_DATA_ANALYSIS"])
        self.assertTrue(any("Structured Dataset" in ev["title"] or "Employee" in ev["title"] for ev in res["evidence_chunks"]))

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

    def test_27_sales_orders_csv_deterministic_grouping(self):
        so_doc = KnowledgeDocument.objects.create(
            title='Sales_Orders.csv',
            metadata={'repository_type': 'team'}
        )
        records_data = [
            {'Order_ID': 'SO1001', 'Product': 'Industrial Sensor', 'Client': 'Arun Industries', 'Business_Unit': 'AI Engineering', 'Order_Date': '2026-07-01', 'Quantity': 12, 'Unit_Price': 18000, 'Net_Amount': 216000},
            {'Order_ID': 'SO1002', 'Product': 'Control Panel', 'Client': 'Metro Controls', 'Business_Unit': 'Sales', 'Order_Date': '2026-07-03', 'Quantity': 8, 'Unit_Price': 24000, 'Net_Amount': 192000},
            {'Order_ID': 'SO1003', 'Product': 'Drive System', 'Client': 'Harbour Automation', 'Business_Unit': 'Operations', 'Order_Date': '2026-07-08', 'Quantity': 10, 'Unit_Price': 37500, 'Net_Amount': 375000},
            {'Order_ID': 'SO1004', 'Product': 'Industrial Sensor', 'Client': 'Prime Manufacturing', 'Business_Unit': 'Sales', 'Order_Date': '2026-07-12', 'Quantity': 15, 'Unit_Price': 18000, 'Net_Amount': 270000},
            {'Order_ID': 'SO1005', 'Product': 'Control Panel', 'Client': 'Arun Industries', 'Business_Unit': 'AI Engineering', 'Order_Date': '2026-07-18', 'Quantity': 6, 'Unit_Price': 24000, 'Net_Amount': 144000},
            {'Order_ID': 'SO1006', 'Product': 'Drive System', 'Client': 'Metro Controls', 'Business_Unit': 'Operations', 'Order_Date': '2026-07-22', 'Quantity': 5, 'Unit_Price': 37500, 'Net_Amount': 187500},
            {'Order_ID': 'SO1007', 'Product': 'Industrial Sensor', 'Client': 'Harbour Automation', 'Business_Unit': 'Sales', 'Order_Date': '2026-08-02', 'Quantity': 9, 'Unit_Price': 18000, 'Net_Amount': 162000},
            {'Order_ID': 'SO1008', 'Product': 'Control Panel', 'Client': 'Prime Manufacturing', 'Business_Unit': 'AI Engineering', 'Order_Date': '2026-08-05', 'Quantity': 11, 'Unit_Price': 24000, 'Net_Amount': 264000},
            {'Order_ID': 'SO1009', 'Product': 'Drive System', 'Client': 'Arun Industries', 'Business_Unit': 'Operations', 'Order_Date': '2026-08-10', 'Quantity': 7, 'Unit_Price': 37500, 'Net_Amount': 262500},
            {'Order_ID': 'SO1010', 'Product': 'Industrial Sensor', 'Client': 'Metro Controls', 'Business_Unit': 'Sales', 'Order_Date': '2026-08-14', 'Quantity': 14, 'Unit_Price': 18000, 'Net_Amount': 252000},
        ]
        for rdata in records_data:
            KnowledgeRecord.objects.create(
                knowledge_document=so_doc,
                canonical_data=rdata,
                additional_fields=rdata
            )

        res = self.orchestrator.execute_query("Calculate total net amount and quantity by Business_Unit in Sales_Orders.csv", user=self.user)
        self.assertIn(res["intent_category"], ["GROUPED_ANALYSIS", "ANALYTICAL_CALCULATION", "STRUCTURED_DATA_ANALYSIS"])
        
        # Verify evidence chunks contain verified grouping results
        ev_text = " ".join([ev.get("text", "") for ev in res.get("evidence_chunks", [])])
        self.assertIn("624000", ev_text.replace(" ", "").replace(",", ""))
        self.assertIn("876000", ev_text.replace(" ", "").replace(",", ""))
        self.assertIn("825000", ev_text.replace(" ", "").replace(",", ""))
        self.assertIn("2325000", ev_text.replace(" ", "").replace(",", ""))

    def test_28_hybrid_chat_endpoint_authentication(self):
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user)
        response = client.post('/api/v1/knowledge-assistant/chat/', {
            'query': 'What is the total sales revenue in Sales_Orders.csv?'
        }, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('answer', response.data)
        self.assertTrue(bool(response.data.get('retrieval_method')))

    def test_29_non_analytical_grouping_all_10_records(self):
        query = "Using only Team/enterprise_ingestion_test_pack/csv/Sales_Orders.csv, list every Order_ID and its Business_Unit. Do not calculate anything. Group the Order_IDs under AI Engineering, Sales, and Operations."
        res = self.orchestrator.execute_query(query, user=self.user)
        ev_text = " ".join([ev.get("text", "") for ev in res.get("evidence_chunks", [])])
        for expected_id in ["SO1001", "SO1002", "SO1003", "SO1004", "SO1005", "SO1006", "SO1007", "SO1008", "SO1009", "SO1010"]:
            self.assertIn(expected_id, ev_text, f"Expected {expected_id} to be retrieved in evidence chunks before LLM generation.")

    def test_30_full_document_pdf_summary_preserves_all_rules(self):
        pdf_doc = KnowledgeDocument.objects.create(
            title='L&T Life Saving Rules 4 1.pdf',
            logical_path='Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf',
            metadata={'repository_type': 'team'}
        )
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf, give a complete detailed summary including all text extracted from the document, all 11 Life Saving Rules, headings, commitments, and important information from every page, including OCR-extracted content."
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        
        # Verify evidence contains all 17 page chunks
        self.assertEqual(len(res.get("evidence_chunks", [])), 17)
        
        # Verify answer contains all 11 rules without truncation
        self.assertIn("11. Bypassing Safety Controls", answer)
        self.assertIn("Obtain authorisation before overriding or disabling safety controls", answer)
        self.assertIn("Any work shall only proceed if all risks have been considered", answer)
        self.assertIn("Protect yourself against a fall and any object being dropped when working at height", answer)

    def test_31_factual_rule_10_lookup(self):
        pdf_doc = KnowledgeDocument.objects.create(
            title='L&T Life Saving Rules 4 1.pdf',
            logical_path='Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf',
            metadata={'repository_type': 'team'}
        )
        query = "What is Life Saving Rule 10 in Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Working at Height", answer)

    def test_32_ocr_derived_content_included_in_summary(self):
        scan_doc = KnowledgeDocument.objects.create(
            title='BHARATHWAJ EXAM FEE.pdf',
            metadata={'repository_type': 'team'}
        )
        query = "Summarize BHARATHWAJ EXAM FEE.pdf including all OCR extracted content"
        res = self.orchestrator.execute_query(query, user=self.user)
        self.assertIn(res["intent_category"], ["DOCUMENT_SUMMARY", "DOCUMENT_ANALYSIS"])
        self.assertTrue(len(res.get("evidence_chunks", [])) > 0)
        trace = res.get("execution_audit_trace", {})
        self.assertTrue(trace.get("ocr_attempted", False))

    def test_33_concept_importance_dynamic_resolution(self):
        pdf_doc = KnowledgeDocument.objects.create(
            title='L&T Life Saving Rules 4 1.pdf',
            logical_path='Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf',
            metadata={'repository_type': 'team'}
        )
        query_5 = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf, explain Life Saving Rule 5 (Energy Isolation), state exactly what the document requires, identify the page containing the rule, and explain why the document considers this rule important. Base the answer strictly on the document. Do not use outside safety knowledge or invent a rationale."
        res_5 = self.orchestrator.execute_query(query_5, user=self.user)
        ans_5 = res_5.get("answer", "")
        self.assertIn("Energy Isolation", ans_5)
        self.assertNotIn("Working at Height", ans_5)

        query_10 = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf, explain Life Saving Rule 10 (Working at Height), state exactly what the document requires, identify the page containing the rule, and explain why the document considers this rule important. Base the answer strictly on the document. Do not use outside safety knowledge or invent a rationale."
        res_10 = self.orchestrator.execute_query(query_10, user=self.user)
        ans_10 = res_10.get("answer", "")
        self.assertIn("Working at Height", ans_10)
        self.assertNotIn("Energy Isolation", ans_10)

        query_1 = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf, explain Life Saving Rule 1 (Fit For Duty), state exactly what the document requires, identify the page containing the rule, and explain why the document considers this rule important. Base the answer strictly on the document. Do not use outside safety knowledge or invent a rationale."
        res_1 = self.orchestrator.execute_query(query_1, user=self.user)
        ans_1 = res_1.get("answer", "")
        self.assertIn("Fit For Duty", ans_1)
        self.assertNotIn("Energy Isolation", ans_1)
        self.assertNotIn("Working at Height", ans_1)

    def test_34_all_11_rules_query(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What are the 11 Life Saving Rules?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Fit For Duty", answer)
        self.assertIn("Energy Isolation", answer)
        self.assertIn("Working at Height", answer)
        self.assertIn("Bypassing Safety Controls", answer)

    def test_35_my_commitment_query(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What does MY COMMITMENT say?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("MY COMMITMENT", answer)
        self.assertTrue("Page" in answer)

    def test_36_document_purpose_query(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What is this document about?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertTrue(len(answer) > 0)
        self.assertIn("Life Saving Rules", answer)

    def test_37_multi_rule_query_5_10_11(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf Give me Rules 5, 10 and 11."
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Energy Isolation", answer)
        self.assertIn("Page 10", answer)
        self.assertIn("Working at Height", answer)
        self.assertIn("Page 15", answer)
        self.assertIn("Bypassing Safety Controls", answer)
        self.assertIn("Page 16", answer)

    def test_38_single_rule_10_query(self):
        query = "What does Life Saving Rule 10 say?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Working at Height", answer)
        self.assertIn("Page 15", answer)

    def test_39_single_rule_5_query(self):
        query = "What does Life Saving Rule 5 say?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Energy Isolation", answer)
        self.assertIn("Page 10", answer)

    def test_40_non_existent_rule_12_query(self):
        query = "What is Life Saving Rule 12?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertTrue("could not be found" in answer.lower() or "not found" in answer.lower() or "non-existence" in answer.lower())

    def test_41_concept_title_energy_isolation_query(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What does Energy Isolation say?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Energy Isolation", answer)
        self.assertIn("Page 10", answer)

    def test_42_concept_title_working_at_height_query(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What does Working at Height say?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Working at Height", answer)
        self.assertIn("Page 15", answer)

    def test_43_supporting_context_query(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What supports the implementation of the Life Saving Rules?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertTrue("Standards, Procedures" in answer or "supported by" in answer.lower())

    def test_44_document_status_classification_query(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What are the Life Saving Rules considered to be?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("non-negotiable", answer.lower())
        self.assertIn("ehs standards", answer.lower())

    def test_45_multi_rule_tell_me_about_rules_2_7(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf Tell me about Rules 2 and 7."
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Risk Management", answer)
        self.assertIn("Page 7", answer)
        self.assertIn("Hot Work", answer)
        self.assertIn("Page 12", answer)
        # Ensure it does not dump the full 11-rule document summary
        self.assertNotIn("Fit For Duty", answer)
        self.assertNotIn("Energy Isolation", answer)

    def test_46_multi_rule_compare_rules_1_5_10(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf Compare Rules 1, 5 and 10 by their requirements and pages."
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Fit For Duty", answer)
        self.assertIn("Page 6", answer)
        self.assertIn("Energy Isolation", answer)
        self.assertIn("Page 10", answer)
        self.assertIn("Working at Height", answer)
        self.assertIn("Page 15", answer)

    def test_47_filtered_rules_permit_authorisation(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf Which rules mention permit or authorisation?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Work Authorisation", answer)
        self.assertIn("Page 8", answer)
        self.assertIn("Confined Space", answer)
        self.assertIn("Page 11", answer)
        self.assertIn("Bypassing Safety Controls", answer)
        self.assertIn("Page 16", answer)
        self.assertNotIn("Fit For Duty", answer)
        self.assertNotIn("Driving", answer)

    def test_48_cross_section_commitment_non_negotiable(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf What is the relationship between MY COMMITMENT and the non-negotiable status of the Life Saving Rules?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertNotIn("No Knowledge Graph multi-hop relationship exists", answer)
        self.assertIn("MY COMMITMENT", answer)
        self.assertIn("non-negotiable", answer.lower())
        self.assertIn("Page 4", answer)
        self.assertIn("Page 5", answer)

    def test_49_multi_rule_rules_8_9_10(self):
        query = "Team/enterprise_ingestion_test_pack/pdf/L&T Life Saving Rules 4 1.pdf Give me Rules 8, 9 and 10."
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Line of Fire", answer)
        self.assertIn("Page 13", answer)
        self.assertIn("Safe Lifting", answer)
        self.assertIn("Page 14", answer)
        self.assertIn("Working at Height", answer)
        self.assertIn("Page 15", answer)

    def test_50_highest_sold_item(self):
        query = "Team/enterprise_ingestion_test_pack/csv/Sales_Orders.csv , highest sold item?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Industrial Sensor", answer)
        self.assertIn("15", answer)
        self.assertIn("SO1004", answer)

    def test_51_highest_priced_item(self):
        query = "Team/enterprise_ingestion_test_pack/csv/Sales_Orders.csv , highest priced item?"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("Drive System", answer)
        self.assertIn("SO1003", answer)
        self.assertTrue("37,500" in answer or "37500" in answer)

    def test_52_highest_sales_value(self):
        query = "Team/enterprise_ingestion_test_pack/csv/Sales_Orders.csv , highest sales value"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("SO1003", answer)
        self.assertTrue("375,000" in answer or "375000" in answer)

    def test_53_total_quantity_sold(self):
        query = "Team/enterprise_ingestion_test_pack/csv/Sales_Orders.csv , total quantity sold"
        res = self.orchestrator.execute_query(query, user=self.user)
        answer = res.get("answer", "")
        self.assertIn("97", answer)



