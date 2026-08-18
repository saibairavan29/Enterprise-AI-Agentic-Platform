from .base import BaseExtractor

class CSVExtractor(BaseExtractor):
    """
    Extractor responsible for CSV tabular dimensions:
    row_count and column_count.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        res = {
            "row_count": None,
            "column_count": None
        }

        if not parser_output or parser_output.get("parser_type") != "CSV":
            return res

        structured_data = parser_output.get("structured_data", {})
        records = []
        if isinstance(structured_data, dict):
            records = structured_data.get("records", [])
        elif isinstance(structured_data, list):
            records = structured_data

        if records:
            res["row_count"] = len(records)
            res["column_count"] = len(records[0]) if isinstance(records[0], dict) else 0

        return res
