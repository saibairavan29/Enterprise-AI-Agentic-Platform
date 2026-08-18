import json
import csv
import io
from datetime import datetime

class ExplainabilityReportBuilder:
    """
    Constructs and exports explainability reports as JSON, Markdown, and CSV payloads.
    """
    @classmethod
    def generate_json_report(cls, report_data: dict) -> str:
        """
        Serializes report details into a structured JSON string.
        """
        return json.dumps(report_data, indent=4)

    @classmethod
    def generate_markdown_report(cls, report_data: dict) -> str:
        """
        Formated markdown summary detailing classifications, SHAP values, and recommendations.
        """
        pos_features = report_data.get("top_positive_features", [])
        neg_features = report_data.get("top_negative_features", [])
        recs = report_data.get("recommendations", [])
        trace = report_data.get("processing_trace", {})

        pos_table = "\n".join(f"| {p['feature']} | +{p['value']} | {p['percentage']}% |" for p in pos_features)
        neg_table = "\n".join(f"| {n['feature']} | {n['value']} | {n['percentage']}% |" for n in neg_features)
        recs_table = "\n".join(f"| {r['category']} | {r['priority']} | {r['recommendation']} | +{r['expected_improvement']}% |" for r in recs)

        md = f"""# EDQI Quality Attribution Explanation Report

Generated At: {datetime.utcnow().isoformat()}Z
Model Version: `{report_data.get("model_version", "1.0.0")}`

---

## Core Inference Metrics
- **Predicted Quality Grade:** `{report_data.get("overall_prediction")}`
- **Prediction Confidence:** `{round(report_data.get("confidence_score", 0.0) * 100, 2)}%`
- **Explainer Method:** `{report_data.get("explainer_name")}`
- **Fallback Triggered:** `{trace.get("fallback_used", False)}`

---

## Human Readable Narrative Summary

{report_data.get("summary")}

---

## Positive Attributions (Supported Grade)

| Feature Name | Attribution Weight | Normalized Percentage |
| :--- | :--- | :--- |
{pos_table if pos_table else "| None | - | - |"}

---

## Negative Attributions (Lowered Grade)

| Feature Name | Attribution Weight | Normalized Percentage |
| :--- | :--- | :--- |
{neg_table if neg_table else "| None | - | - |"}

---

## Recommended Quality Fixes

| Dimension | Priority | Action Item | Expected Grade Improvement |
| :--- | :--- | :--- | :--- |
{recs_table if recs_table else "| None | - | All data dimensions optimal | - |"}
"""
        return md.strip()

    @classmethod
    def generate_csv_report(cls, report_data: dict) -> str:
        """
        Builds a tabular CSV report containing feature weights and recommendation logs.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 1. Section 1: Header information
        writer.writerow(["EDQI QUALITY EXPLANATION EXPORT"])
        writer.writerow(["Report ID", report_data.get("report_id", "")])
        writer.writerow(["Predicted Grade", report_data.get("overall_prediction", "")])
        writer.writerow(["Confidence Score", report_data.get("confidence_score", "")])
        writer.writerow([])
        
        # 2. Section 2: Feature Attributions
        writer.writerow(["FEATURE ATTRIBUTIONS"])
        writer.writerow(["Feature Name", "Attribution Weight", "Normalized Impact (%)", "Type"])
        
        for p in report_data.get("top_positive_features", []):
            writer.writerow([p["feature"], p["value"], p["percentage"], "POSITIVE"])
        for n in report_data.get("top_negative_features", []):
            writer.writerow([n["feature"], n["value"], n["percentage"], "NEGATIVE"])
        writer.writerow([])
        
        # 3. Section 3: Recommendations
        writer.writerow(["ACTIONABLE RECOMMENDATIONS"])
        writer.writerow(["Category", "Priority", "Priority Score", "Expected Improvement (%)", "Action Suggested"])
        for r in report_data.get("recommendations", []):
            writer.writerow([
                r.get("category", ""),
                r.get("priority", ""),
                r.get("priority_score", 0.0),
                r.get("expected_improvement", 0.0),
                r.get("recommendation", "")
            ])
            
        return output.getvalue()
