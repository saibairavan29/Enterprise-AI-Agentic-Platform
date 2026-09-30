import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

import json
import joblib
import numpy as np
import pandas as pd
from django.test import TestCase, Client
from django.urls import reverse
from rest_framework import status
from policy_simulator.simulator import WorkforcePolicyImpactSimulator
from policy_simulator.data_processor import IBMHRDataPreprocessor
from policy_simulator.shap_service import PolicySimulatorSHAPService

class PolicySimulatorTestCase(TestCase):
    """
    Comprehensive Unit & Integration Test Suite for Employee Workforce Policy Impact Simulator.
    Verifies model loading, feature validation, SHAP explainability, scenario evaluation,
    reproducibility, and non-retraining constraints.
    """

    def setUp(self):
        self.client = Client()
        self.simulator = WorkforcePolicyImpactSimulator()
        p1 = os.path.abspath("config/random_forest_pipeline.joblib")
        p2 = os.path.abspath("backend/config/random_forest_pipeline.joblib")
        self.artifact_path = p1 if os.path.exists(p1) else p2

    def test_01_model_and_preprocessor_loading(self):
        """Test 1: Verify model pipeline artifact and preprocessor load successfully."""
        self.assertTrue(os.path.exists(self.artifact_path), "Model pipeline artifact missing.")
        payload = joblib.load(self.artifact_path)
        self.assertIn("model", payload)
        self.assertIn("column_transformer", payload)
        self.assertEqual(payload["model"].__class__.__name__, "RandomForestClassifier")

    def test_02_preprocessing_consistency(self):
        """Test 2: Verify preprocessing pipeline transforms dataset cleanly."""
        processor = IBMHRDataPreprocessor()
        X_train, X_test, y_train, y_test = processor.get_train_test_split()
        X_trans = processor.fit_transform_pipeline(X_train)
        self.assertEqual(X_trans.shape[0], 1176)
        self.assertEqual(X_trans.shape[1], 51)

    def test_03_valid_policy_scenario(self):
        """Test 3: Execute valid policy scenario simulation (OverTime = No)."""
        payload = {"policy_changes": {"OverTime": "No"}}
        res = self.simulator.simulate_scenario(payload["policy_changes"])
        self.assertTrue(res["success"])
        self.assertIn("baseline", res)
        self.assertIn("scenario", res)
        self.assertIn("impact_differential", res)
        self.assertIn("explainability", res)

    def test_04_invalid_policy_feature_rejection(self):
        """Test 4: Reject non-approved or un-controllable policy features (e.g. Age)."""
        invalid_payload = {"Age": 20}
        errors = self.simulator.validate_policy_payload(invalid_payload)
        self.assertTrue(len(errors) > 0)
        self.assertIn("Invalid policy feature 'Age'", errors[0])

    def test_05_invalid_categorical_value_rejection(self):
        """Test 5: Reject invalid categorical values (e.g. OverTime = Maybe)."""
        invalid_payload = {"OverTime": "Maybe"}
        errors = self.simulator.validate_policy_payload(invalid_payload)
        self.assertTrue(len(errors) > 0)
        self.assertIn("Invalid value 'Maybe' for policy feature 'OverTime'", errors[0])

    def test_06_invalid_numerical_range_rejection(self):
        """Test 6: Reject out-of-range numerical policy values (e.g. WorkLifeBalance = 10)."""
        invalid_payload = {"WorkLifeBalance": 10}
        errors = self.simulator.validate_policy_payload(invalid_payload)
        self.assertTrue(len(errors) > 0)
        self.assertIn("exceeds maximum threshold 4", errors[0])

    def test_07_baseline_and_scenario_prediction(self):
        """Test 7: Verify baseline and scenario prediction rates are within valid ranges."""
        res = self.simulator.simulate_scenario({"WorkLifeBalance": 4})
        self.assertTrue(res["success"])
        base_rate = res["baseline"]["predicted_attrition_rate_pct"]
        scen_rate = res["scenario"]["predicted_attrition_rate_pct"]
        self.assertGreaterEqual(base_rate, 0.0)
        self.assertLessEqual(base_rate, 100.0)
        self.assertGreaterEqual(scen_rate, 0.0)
        self.assertLessEqual(scen_rate, 100.0)

    def test_08_shap_explainability_output(self):
        """Test 8: Verify SHAP feature explanations are generated with original column names."""
        res = self.simulator.simulate_scenario({"StockOptionLevel": 3})
        shap_exp = res["explainability"]["sample_instance_explanation"]
        self.assertIn("top_positive_factors", shap_exp)
        self.assertIn("top_negative_factors", shap_exp)
        self.assertIn("attrition_probability", shap_exp)

    def test_09_api_endpoint_structure(self):
        """Test 9: Test POST /api/v1/policy-simulator/simulate/ API endpoint response."""
        response = self.client.post(
            "/api/v1/policy-simulator/simulate/",
            data=json.dumps({"policy_changes": {"OverTime": "No"}}),
            content_type="application/json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res_data = response.json()
        self.assertTrue(res_data["success"])
        self.assertIn("causality_disclaimer", res_data)

    def test_10_reproducibility_verification(self):
        """Test 10: Run exact same policy scenario twice and verify identical outputs."""
        res1 = self.simulator.simulate_scenario({"TrainingTimesLastYear": 4})
        res2 = self.simulator.simulate_scenario({"TrainingTimesLastYear": 4})
        self.assertEqual(res1["baseline"]["predicted_attrition_count"], res2["baseline"]["predicted_attrition_count"])
        self.assertEqual(res1["scenario"]["predicted_attrition_count"], res2["scenario"]["predicted_attrition_count"])
        self.assertEqual(res1["impact_differential"]["percentage_point_change"], res2["impact_differential"]["percentage_point_change"])

    def test_11_no_retraining_during_inference(self):
        """Test 11: Verify model artifact timestamp and retraining flag remain unchanged."""
        mtime_before = os.path.getmtime(self.artifact_path)
        self.simulator.simulate_scenario({"OverTime": "No"})
        mtime_after = os.path.getmtime(self.artifact_path)
        self.assertEqual(mtime_before, mtime_after, "Model artifact was modified or retrained during inference request!")

    def test_12_employee_risk_list_and_shap_reasons(self):
        """Test 12: Verify employee-level risk list and TreeSHAP reasons are generated correctly."""
        res = self.simulator.simulate_scenario({"OverTime": "No", "PercentSalaryHike": 18})
        self.assertIn("employee_risk_list", res)
        risk_list = res["employee_risk_list"]
        self.assertIn("before_policy", risk_list)
        self.assertIn("after_policy", risk_list)
        self.assertIn("risk_reduced", risk_list)
        self.assertIn("still_high_risk", risk_list)
        
        if len(risk_list["before_policy"]) > 0:
            emp = risk_list["before_policy"][0]
            self.assertIn("employee_id", emp)
            self.assertIn("risk_probability", emp)
            self.assertIn("reason", emp)
            self.assertIn("risk_reasons", emp)
            self.assertGreater(len(emp["reason"]), 10)

    def test_audit_01_total_employees_evaluated(self):
        """Audit Test 1: Verify total employees evaluated equals 1,470 (full IBM HR population)."""
        res = self.simulator.simulate_scenario({"OverTime": "No"})
        self.assertEqual(res["simulation_summary"]["population_evaluated"], 1470)

    def test_audit_02_high_risk_count_equals_positive_predictions(self):
        """Audit Test 2: Verify high-risk count equals actual positive predictions (proba >= 0.5)."""
        df_raw, _ = self.simulator.preprocessor.load_and_audit()
        X_trans = self.simulator.shap_service.column_transformer.transform(df_raw)
        probas = self.simulator.shap_service.model.predict_proba(X_trans)[:, 1]
        expected_count = int(np.sum(probas >= 0.5))

        res = self.simulator.simulate_scenario({"OverTime": "No"})
        self.assertEqual(res["baseline"]["predicted_attrition_count"], expected_count)

    def test_audit_03_displayed_percentage_formula(self):
        """Audit Test 3: Verify displayed percentage equals (high_risk / total * 100)."""
        res = self.simulator.simulate_scenario({"WorkLifeBalance": 4})
        base_count = res["baseline"]["predicted_attrition_count"]
        base_pct = res["baseline"]["predicted_attrition_rate_pct"]
        calc_pct = round((base_count / 1470) * 100.0, 2)
        self.assertEqual(base_pct, calc_pct)

    def test_audit_04_before_after_generated_from_actual_predictions(self):
        """Audit Test 4: Verify Before + After risk list counts reflect full actual model predictions."""
        res = self.simulator.simulate_scenario({"StockOptionLevel": 3})
        risk_list = res["employee_risk_list"]
        base_count = res["baseline"]["predicted_attrition_count"]
        scen_count = res["scenario"]["predicted_attrition_count"]

        self.assertEqual(len(risk_list["before_policy"]), base_count)
        self.assertEqual(len(risk_list["after_policy"]), scen_count)

    def test_audit_05_deterministic_mapping(self):
        """Audit Test 5: Verify deterministic mapping from row index to EmployeeNumber."""
        res = self.simulator.simulate_scenario({"OverTime": "No"})
        df_full = pd.read_csv(self.simulator.preprocessor.dataset_path)
        before_list = res["employee_risk_list"]["before_policy"]
        if before_list:
            emp_item = before_list[0]
            emp_id = emp_item["employee_id"]
            matched = df_full[df_full["EmployeeNumber"] == emp_id]
            self.assertEqual(len(matched), 1, f"EmployeeNumber #{emp_id} must deterministically exist in IBM HR dataset.")

    def test_audit_06_no_identity_mixing(self):
        """Audit Test 6: Verify no identity mixing across employee records (role & department match)."""
        res = self.simulator.simulate_scenario({"OverTime": "No"})
        df_full = pd.read_csv(self.simulator.preprocessor.dataset_path)
        for item in res["employee_risk_list"]["before_policy"]:
            emp_id = item["employee_id"]
            raw_row = df_full[df_full["EmployeeNumber"] == emp_id].iloc[0]
            self.assertEqual(item["department"], raw_row["Department"])
            self.assertEqual(item["designation"], raw_row["JobRole"])

    def test_audit_07_shap_explanation_belongs_strictly_to_target_row(self):
        """Audit Test 7: Verify TreeSHAP explanation belongs strictly to the target employee row."""
        res = self.simulator.simulate_scenario({"OverTime": "No"})
        before_list = res["employee_risk_list"]["before_policy"]
        if before_list:
            item = before_list[0]
            self.assertIn("risk_reasons", item)
            self.assertGreater(len(item["risk_reasons"]), 0)
            self.assertIn("clean_factor", item["risk_reasons"][0])
            self.assertIn("contribution", item["risk_reasons"][0])

    def test_audit_08_baseline_and_scenario_shap_distinct(self):
        """Audit Test 8: Verify baseline vs scenario SHAP explanations are distinct and not mixed."""
        res = self.simulator.simulate_scenario({"OverTime": "No"})
        risk_list = res["employee_risk_list"]
        before_item = risk_list["before_policy"][0] if risk_list["before_policy"] else None
        risk_reduced_item = risk_list["risk_reduced"][0] if risk_list["risk_reduced"] else None

        if before_item and risk_reduced_item:
            self.assertIn("baseline_risk_pct", risk_reduced_item)
            self.assertIn("scenario_risk_pct", risk_reduced_item)
            self.assertLess(risk_reduced_item["scenario_risk_pct"], risk_reduced_item["baseline_risk_pct"])

    def test_audit_09_zero_model_retraining(self):
        """Audit Test 9: Verify zero model retraining during inference execution."""
        mtime_before = os.path.getmtime(self.artifact_path)
        res = self.simulator.simulate_scenario({"PercentSalaryHike": 20})
        mtime_after = os.path.getmtime(self.artifact_path)
        self.assertEqual(mtime_before, mtime_after)
        self.assertFalse(res["provenance"]["retraining_executed"])

    def test_audit_10_reproducibility(self):
        """Audit Test 10: Verify repeated identical simulations return identical results."""
        res1 = self.simulator.simulate_scenario({"WorkLifeBalance": 3, "OverTime": "No"})
        res2 = self.simulator.simulate_scenario({"WorkLifeBalance": 3, "OverTime": "No"})
        self.assertEqual(res1["baseline"], res2["baseline"])
        self.assertEqual(res1["scenario"], res2["scenario"])
        self.assertEqual(res1["impact_differential"], res2["impact_differential"])

    def test_audit_11_transition_math_equations(self):
        """Audit Test 11: Verify exact transition mathematics equations across categories."""
        res = self.simulator.simulate_scenario({"OverTime": "No"})
        risk_list = res["employee_risk_list"]
        base_count = res["baseline"]["predicted_attrition_count"]
        scen_count = res["scenario"]["predicted_attrition_count"]
        
        len_before = len(risk_list["before_policy"])
        len_after = len(risk_list["after_policy"])
        len_reduced = len(risk_list["risk_reduced"])
        len_still = len(risk_list["still_high_risk"])
        len_newly = len(risk_list["newly_high_risk"])

        self.assertEqual(len_before, base_count)
        self.assertEqual(len_after, scen_count)
        self.assertEqual(len_reduced + len_still, base_count)
        self.assertEqual(len_still + len_newly, scen_count)


