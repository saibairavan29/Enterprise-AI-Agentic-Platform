import os
import openpyxl
import logging
import hashlib
from typing import Dict, Any, List, Tuple

logger = logging.getLogger('enterprise')

class HighThroughputExcelIngestionService:
    """
    High-Throughput Transactional Excel Stream Ingestion & Multi-Version Record Diff Service.
    Supports high-speed openpyxl read-only streaming for Superstore.xlsx and Online Retail.xlsx
    with version diff synchronization (detecting updated quantities, prices, additions, and deletions).
    """

    def stream_ingest_excel(self, file_path: str, max_rows: int = 10000) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Streams large transactional Excel files (Superstore.xlsx / Online Retail.xlsx) in read-only mode.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Excel file not found at {file_path}")

        records = []
        stats = {
            "file_name": os.path.basename(file_path),
            "total_rows_scanned": 0,
            "total_records_ingested": 0,
            "columns": []
        }

        try:
            # Read-only stream mode for high throughput
            wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
            sheet = wb.active

            rows_iter = sheet.iter_rows(values_only=True)
            header_row = next(rows_iter, None)
            if not header_row:
                return [], stats

            headers = [str(cell).strip() if cell is not None else f"col_{i}" for i, cell in enumerate(header_row)]
            stats["columns"] = headers

            row_count = 0
            for row in rows_iter:
                row_count += 1
                if row_count > max_rows:
                    break

                row_dict = {}
                for h, val in zip(headers, row):
                    if val is not None:
                        row_dict[h] = str(val).strip()
                
                if row_dict:
                    records.append(row_dict)

            stats["total_rows_scanned"] = row_count
            stats["total_records_ingested"] = len(records)
            wb.close()

            logger.info(f"Stream ingested {len(records)} rows from {os.path.basename(file_path)}.")
            return records, stats

        except Exception as e:
            logger.error(f"Error streaming Excel file {file_path}: {e}", exc_info=True)
            raise e

    def compute_record_diff(self, version1_records: List[Dict[str, Any]], version2_records: List[Dict[str, Any]], key_field: str = "Order ID") -> Dict[str, Any]:
        """
        Computes multi-version record diff synchronization between Version 1 and Version 2 dataset snapshots.
        """
        v1_map = {}
        for r in version1_records:
            k = r.get(key_field) or r.get("InvoiceNo") or r.get("Order_ID") or r.get("id")
            if k:
                v1_map[str(k)] = r

        v2_map = {}
        for r in version2_records:
            k = r.get(key_field) or r.get("InvoiceNo") or r.get("Order_ID") or r.get("id")
            if k:
                v2_map[str(k)] = r

        added_keys = set(v2_map.keys()) - set(v1_map.keys())
        deleted_keys = set(v1_map.keys()) - set(v2_map.keys())
        common_keys = set(v1_map.keys()).intersection(set(v2_map.keys()))

        modified_records = []
        unchanged_count = 0

        for k in common_keys:
            r1 = v1_map[k]
            r2 = v2_map[k]
            diffs = {}
            for col in set(r1.keys()).union(set(r2.keys())):
                val1 = r1.get(col)
                val2 = r2.get(col)
                if val1 != val2:
                    diffs[col] = {"old_val": val1, "new_val": val2}
            
            if diffs:
                modified_records.append({
                    "record_key": k,
                    "diffs": diffs
                })
            else:
                unchanged_count += 1

        return {
            "total_v1_records": len(version1_records),
            "total_v2_records": len(version2_records),
            "added_records_count": len(added_keys),
            "deleted_records_count": len(deleted_keys),
            "modified_records_count": len(modified_records),
            "unchanged_records_count": unchanged_count,
            "modified_details": modified_records[:10],
            "added_keys_sample": list(added_keys)[:5],
            "deleted_keys_sample": list(deleted_keys)[:5]
        }
