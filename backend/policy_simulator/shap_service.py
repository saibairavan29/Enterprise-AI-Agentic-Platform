import os
os.environ["USE_TF"] = "0"
os.environ["USE_TORCH"] = "1"

import joblib
import shap
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

PIPELINE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config", "random_forest_pipeline.joblib"))

class PolicySimulatorSHAPService:
    """
    Production SHAP Explainability Service for Employee Workforce Policy Impact Simulator.
    Calculates TreeSHAP values using saved Random Forest artifact and maps encoded features
    back to original human-readable workforce variables.
    """

    def __init__(self, pipeline_path: str = PIPELINE_PATH):
        self.pipeline_path = pipeline_path
        self.model = None
        self.column_transformer = None
        self.num_cols = []
        self.cat_cols = []
        self.feature_names_out = []
        self.explainer = None
        self._load_artifact()

    def _load_artifact(self):
        if not os.path.exists(self.pipeline_path):
            raise FileNotFoundError(f"Random Forest pipeline artifact not found at {self.pipeline_path}")
        
        payload = joblib.load(self.pipeline_path)
        self.model = payload["model"]
        self.column_transformer = payload["column_transformer"]
        self.num_cols = payload["num_cols"]
        self.cat_cols = payload["cat_cols"]
        self.feature_names_out = payload["feature_names_out"]
        
        # Initialize TreeExplainer for Class 1 (Attrition = Yes)
        self.explainer = shap.TreeExplainer(self.model)

    def _convert_primitive(self, val):
        if isinstance(val, (np.integer, int)):
            return int(val)
        elif isinstance(val, (np.floating, float)):
            return float(val)
        elif isinstance(val, (np.bool_, bool)):
            return bool(val)
        return str(val) if val is not None else None

    def _resolve_parent_feature(self, feat_name: str) -> str:
        clean = feat_name.replace("cat__", "").replace("num__", "")
        for c in self.cat_cols:
            if clean == c or clean.startswith(c + "_"):
                return c
        for n in self.num_cols:
            if clean == n:
                return n
        return clean

    def predict_and_explain(self, instance_df: pd.DataFrame) -> Dict[str, Any]:
        if instance_df.empty:
            raise ValueError("Input DataFrame is empty.")

        X_trans = self.column_transformer.transform(instance_df)
        proba_yes = float(self.model.predict_proba(X_trans)[0, 1])
        pred_label = "Attrition Risk" if proba_yes >= 0.5 else "Retained (No Attrition)"

        # Compute SHAP values
        shap_values = self.explainer.shap_values(X_trans)
        
        if isinstance(shap_values, list):
            vals = shap_values[1][0]
        elif len(shap_values.shape) == 3:
            vals = shap_values[0, :, 1]
        else:
            vals = shap_values[0]

        # Aggregate SHAP values back to original feature names
        aggregated_shap = {}
        for feat_name, shap_val in zip(self.feature_names_out, vals):
            parent_col = self._resolve_parent_feature(feat_name)
            aggregated_shap[parent_col] = aggregated_shap.get(parent_col, 0.0) + float(shap_val)

        factors = []
        for col, shap_val in aggregated_shap.items():
            raw_val = instance_df[col].iloc[0] if col in instance_df.columns else None
            val = self._convert_primitive(raw_val)
            factors.append({
                "feature": str(col),
                "shap_value": round(float(shap_val), 4),
                "impact": "Increases Attrition Risk" if shap_val > 0 else "Decreases Attrition Risk",
                "value": val
            })

        factors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)

        top_positive = [f for f in factors if f["shap_value"] > 0][:5]
        top_negative = [f for f in factors if f["shap_value"] < 0][:5]

        return {
            "prediction": pred_label,
            "attrition_probability": round(proba_yes, 4),
            "top_positive_factors": top_positive,
            "top_negative_factors": top_negative,
            "all_feature_contributions": factors
        }

    def get_global_feature_importance(self, sample_df: pd.DataFrame, top_n: int = 10) -> List[Dict[str, Any]]:
        X_trans = self.column_transformer.transform(sample_df)
        shap_values = self.explainer.shap_values(X_trans)
        
        if isinstance(shap_values, list):
            vals = shap_values[1]
        elif len(shap_values.shape) == 3:
            vals = shap_values[:, :, 1]
        else:
            vals = shap_values

        mean_abs_shap = np.mean(np.abs(vals), axis=0)

        agg_importance = {}
        for feat_name, imp_val in zip(self.feature_names_out, mean_abs_shap):
            parent_col = self._resolve_parent_feature(feat_name)
            agg_importance[parent_col] = agg_importance.get(parent_col, 0.0) + float(imp_val)

        importance_list = [
            {"feature": str(k), "mean_abs_shap": round(float(v), 4)}
            for k, v in agg_importance.items()
        ]
        importance_list.sort(key=lambda x: x["mean_abs_shap"], reverse=True)
        return importance_list[:top_n]

    def _friendly_feature_label(self, feat: str) -> str:
        mapping = {
            "OverTime": "overtime requirement",
            "JobSatisfaction": "job satisfaction level",
            "WorkLifeBalance": "work-life balance level",
            "StockOptionLevel": "stock option incentive tier",
            "PercentSalaryHike": "salary hike percentage",
            "NumCompaniesWorked": "job mobility history",
            "DistanceFromHome": "commute distance",
            "Age": "career tenure stage",
            "MonthlyIncome": "monthly income level",
            "JobInvolvement": "job involvement level",
            "EnvironmentSatisfaction": "workplace environment satisfaction",
            "YearsAtCompany": "tenure at company",
            "YearsInCurrentRole": "role tenure",
            "YearsWithCurrManager": "managerial tenure",
            "TrainingTimesLastYear": "annual training participation"
        }
        return mapping.get(feat, str(feat).replace("cat__", "").replace("num__", "").replace("_", " ").lower())

    def get_clean_feature_name(self, feat: str) -> str:
        clean_map = {
            "OverTime": "Overtime Requirement",
            "WorkLifeBalance": "Work-Life Balance",
            "JobSatisfaction": "Job Satisfaction",
            "JobInvolvement": "Job Involvement",
            "PercentSalaryHike": "Annual Salary Hike",
            "StockOptionLevel": "Stock Option Level",
            "TrainingTimesLastYear": "Annual Training Programs",
            "TotalWorkingYears": "Total Working Years",
            "YearsAtCompany": "Years at Company",
            "YearsInCurrentRole": "Years in Current Role",
            "YearsWithCurrManager": "Years with Current Manager",
            "YearsSinceLastPromotion": "Years Since Last Promotion",
            "DistanceFromHome": "Distance from Home",
            "NumCompaniesWorked": "Companies Worked",
            "MonthlyIncome": "Monthly Income",
            "Age": "Employee Age",
            "EnvironmentSatisfaction": "Environment Satisfaction",
            "RelationshipSatisfaction": "Relationship Satisfaction",
            "JobLevel": "Job Level",
            "BusinessTravel": "Business Travel",
            "Education": "Education Level",
            "EducationField": "Education Field",
            "Gender": "Gender",
            "MaritalStatus": "Marital Status",
            "DailyRate": "Daily Rate",
            "HourlyRate": "Hourly Rate",
            "MonthlyRate": "Monthly Rate",
            "PerformanceRating": "Performance Rating"
        }
        return clean_map.get(feat, str(feat).replace("cat__", "").replace("num__", ""))

    def explain_employee_records(
        self,
        base_df: pd.DataFrame,
        scen_df: pd.DataFrame,
        base_probas: np.ndarray,
        scen_probas: np.ndarray,
        limit_per_category: Optional[int] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Calculates employee-level TreeSHAP feature explanations for Before, After, Risk Reduced,
        Still High Risk, and Newly High Risk employees across full IBM HR dataset population.
        """
        X_base_trans = self.column_transformer.transform(base_df)
        X_scen_trans = self.column_transformer.transform(scen_df)

        base_shap = self.explainer.shap_values(X_base_trans)
        scen_shap = self.explainer.shap_values(X_scen_trans)

        def extract_vals(shap_res):
            if isinstance(shap_res, list):
                return shap_res[1]
            elif len(shap_res.shape) == 3:
                return shap_res[:, :, 1]
            return shap_res

        base_vals_matrix = extract_vals(base_shap)
        scen_vals_matrix = extract_vals(scen_shap)

        n_samples = len(base_df)

        before_indices = [i for i in range(n_samples) if base_probas[i] >= 0.5]
        after_indices = [i for i in range(n_samples) if scen_probas[i] >= 0.5]
        risk_reduced_indices = [i for i in range(n_samples) if base_probas[i] >= 0.5 and scen_probas[i] < 0.5]
        still_high_indices = [i for i in range(n_samples) if base_probas[i] >= 0.5 and scen_probas[i] >= 0.5]
        newly_high_indices = [i for i in range(n_samples) if base_probas[i] < 0.5 and scen_probas[i] >= 0.5]

        before_indices.sort(key=lambda i: base_probas[i], reverse=True)
        after_indices.sort(key=lambda i: scen_probas[i], reverse=True)
        risk_reduced_indices.sort(key=lambda i: base_probas[i], reverse=True)
        still_high_indices.sort(key=lambda i: scen_probas[i], reverse=True)
        newly_high_indices.sort(key=lambda i: scen_probas[i], reverse=True)

        def slice_list(lst):
            return lst[:limit_per_category] if limit_per_category is not None else lst

        def build_employee_item(i, df_row, proba, shap_row, category):
            agg_shap = {}
            for feat_name, s_val in zip(self.feature_names_out, shap_row):
                parent = self._resolve_parent_feature(feat_name)
                agg_shap[parent] = agg_shap.get(parent, 0.0) + float(s_val)

            factors = []
            for col, s_val in agg_shap.items():
                raw_v = df_row[col] if col in df_row else None
                factors.append({
                    "factor": str(col),
                    "clean_factor": self.get_clean_feature_name(col),
                    "direction": "increases_risk" if s_val > 0 else "decreases_risk",
                    "contribution": round(float(s_val), 4),
                    "value": self._convert_primitive(raw_v)
                })

            factors.sort(key=lambda x: abs(x["contribution"]), reverse=True)
            top_pos = [f for f in factors if f["contribution"] > 0][:3]
            top_neg = [f for f in factors if f["contribution"] < 0][:3]

            emp_num = df_row.get("EmployeeNumber", i + 1)
            dept = df_row.get("Department", "General")
            role = df_row.get("JobRole", "Employee")
            emp_id = int(emp_num) if str(emp_num).isdigit() else i + 1

            if category == "before_policy":
                pos_labels = [self._friendly_feature_label(f["factor"]) for f in top_pos]
                if pos_labels:
                    reason_text = f"{', '.join(pos_labels[:-1]) + (' and ' if len(pos_labels) > 1 else '') + pos_labels[-1]} are the main factors contributing to the higher predicted risk."
                else:
                    reason_text = "Workplace factors and historical tenure contribute to the baseline predicted risk."
            elif category == "after_policy":
                pos_labels = [self._friendly_feature_label(f["factor"]) for f in top_pos]
                if pos_labels:
                    reason_text = f"{', '.join(pos_labels[:-1]) + (' and ' if len(pos_labels) > 1 else '') + pos_labels[-1]} remain the primary factors contributing to predicted risk under this scenario."
                else:
                    reason_text = "Role assignments and workplace variables contribute to the scenario predicted risk."
            elif category == "risk_reduced":
                neg_labels = [self._friendly_feature_label(f["factor"]) for f in top_neg]
                if neg_labels:
                    reason_text = f"The policy reduced the contribution of {neg_labels[0]}, resulting in a lower predicted attrition risk."
                else:
                    reason_text = "The policy scenario reduced key workplace risk contributions, leading to a lower predicted risk."
            elif category == "still_high_risk":
                pos_labels = [self._friendly_feature_label(f["factor"]) for f in top_pos]
                if pos_labels:
                    reason_text = f"{pos_labels[0]} and {pos_labels[1] if len(pos_labels)>1 else 'job factors'} continue to be important factors in the model's prediction."
                else:
                    reason_text = "Workplace role factors continue to contribute to the higher predicted risk."
            elif category == "newly_high_risk":
                reason_text = "The selected policy scenario changed factors that contribute to a higher predicted attrition risk for this employee."
            else:
                reason_text = "Model-attributed factors influence the predicted turnover risk for this employee."

            top_factors_summary = [f["clean_factor"] for f in (top_pos if top_pos else factors[:3])]

            b_p = round(float(base_probas[i]) * 100.0, 1)
            s_p = round(float(scen_probas[i]) * 100.0, 1)
            chg = round(s_p - b_p, 1)

            return {
                "employee_id": emp_id,
                "name": f"IBM HR Employee #{emp_id} ({role})",
                "department": str(dept),
                "designation": str(role),
                "data_source": "IBM HR.csv Observational Benchmark Dataset",
                "baseline_risk_pct": b_p,
                "scenario_risk_pct": s_p,
                "risk_change_pts": chg,
                "risk_probability": round(float(proba), 4),
                "prediction": "Yes" if proba >= 0.5 else "No",
                "category": category,
                "risk_reasons": factors[:5],
                "reason": reason_text,
                "top_factors_summary": top_factors_summary
            }

        return {
            "before_policy": [build_employee_item(i, base_df.iloc[i], base_probas[i], base_vals_matrix[i], "before_policy") for i in slice_list(before_indices)],
            "after_policy": [build_employee_item(i, scen_df.iloc[i], scen_probas[i], scen_vals_matrix[i], "after_policy") for i in slice_list(after_indices)],
            "risk_reduced": [build_employee_item(i, scen_df.iloc[i], scen_probas[i], scen_vals_matrix[i], "risk_reduced") for i in slice_list(risk_reduced_indices)],
            "still_high_risk": [build_employee_item(i, scen_df.iloc[i], scen_probas[i], scen_vals_matrix[i], "still_high_risk") for i in slice_list(still_high_indices)],
            "newly_high_risk": [build_employee_item(i, scen_df.iloc[i], scen_probas[i], scen_vals_matrix[i], "newly_high_risk") for i in slice_list(newly_high_indices)],
        }
