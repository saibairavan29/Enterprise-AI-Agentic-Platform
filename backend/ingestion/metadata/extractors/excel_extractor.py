from .base import BaseExtractor

class ExcelExtractor(BaseExtractor):
    """
    Extractor responsible for Excel dimensions:
    worksheet_count, sheet_names, row_count, and column_count.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        res = {
            "worksheet_count": 0,
            "sheet_names": [],
            "row_count": None,
            "column_count": None
        }

        if not parser_output or parser_output.get("parser_type") != "EXCEL":
            return res

        parser_meta = parser_output.get("metadata", {})
        structured_data = parser_output.get("structured_data", {})

        res["sheet_names"] = parser_meta.get("sheets", list(structured_data.keys()))
        res["worksheet_count"] = int(parser_meta.get("sheet_count", len(res["sheet_names"])))

        if structured_data:
            total_rows = 0
            max_cols = 0
            for sheet, records in structured_data.items():
                if isinstance(records, list):
                    total_rows += len(records)
                    if records:
                        max_cols = max(max_cols, len(records[0]))
            
            res["row_count"] = total_rows
            res["column_count"] = max_cols if total_rows > 0 else None

        return res
