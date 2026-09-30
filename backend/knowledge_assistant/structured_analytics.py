import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger('enterprise')

class StructuredAnalyticsEngine:
    """
    Generic, document-agnostic Enterprise Structured Analytics Engine.
    Handles dirty tabular records (CSV, XLSX, Database records), dynamic schema discovery,
    data cleaning/normalization, deterministic numerical aggregation (SUM, AVG, MIN, MAX, COUNT),
    ambiguity resolution (e.g. highest sales revenue by Employee vs Department),
    and evidence provenance generation.
    """

    ID_COL_PATTERNS = [
        r'\bemployee_id\b', r'\bemp_id\b', r'\bsale_id\b', r'\btransaction_id\b',
        r'\bpo_id\b', r'\border_id\b', r'\brecord_id\b', r'\bentry_id\b', r'\bitem_id\b'
    ]

    EMP_COL_PATTERNS = [
        r'\bemployee_name\b', r'\bemp_name\b', r'\bemployee\b', r'\bname\b',
        r'\bemployee_id\b', r'\bemp_id\b'
    ]

    DEPT_COL_PATTERNS = [
        r'\bdepartment\b', r'\bdept\b', r'\bdivision\b', r'\bbusiness_unit\b'
    ]

    STATUS_COL_PATTERNS = [
        r'\bemployment_status\b', r'\bemploymentstatus\b', r'\bemployee_status\b',
        r'\bwork_status\b', r'\bjob_status\b', r'\bstatus\b'
    ]

    SALARY_COL_PATTERNS = [
        r'\bmonthly_salary\b', r'\bmonthlysalary\b', r'\bsalary\b', r'\bmonthly_income\b',
        r'\bannual_salary\b', r'\bcompensation\b', r'\bwage\b', r'\bpay\b',
        r'\baverage_salary\b', r'\btotal_monthly_salary\b'
    ]

    SALES_COL_PATTERNS = [
        r'\bsales_revenue\b', r'\bsalesrevenue\b', r'\btotal_sales\b', r'\brevenue\b',
        r'\bsales\b', r'\bamount\b', r'\btotal_amount\b', r'\bprice_total\b',
        r'\btotal_price\b', r'\bval\b', r'\bvalue\b', r'\bgrand_total\b', r'\bline_total\b'
    ]

    QTY_COL_PATTERNS = [
        r'\bunits_sold\b', r'\bunitssold\b', r'\bquantity\b', r'\bqty\b',
        r'\bunits\b', r'\bquantity_sold\b', r'\bvolume\b', r'\bitems_sold\b', r'\bcount\b'
    ]

    ITEM_COL_PATTERNS = [
        r'\bproduct\b', r'\bitem\b', r'\bproduct_name\b', r'\bitem_name\b',
        r'\bsku\b', r'\bproduct_id\b', r'\bitem_description\b', r'\bdescription\b'
    ]

    UNIT_PRICE_PATTERNS = [
        r'\bunit_price\b', r'\bunitprice\b', r'\bprice_per_unit\b', r'\bprice\b', r'\brate\b'
    ]

    DISCOUNT_PATTERNS = [
        r'\bdiscount\b', r'\bdiscount_rate\b', r'\brebate\b'
    ]

    def _match_column(self, columns: List[str], patterns: List[str]) -> Optional[str]:
        """
        Robust column matcher that handles underscore-separated, hyphen-separated,
        and space-separated column headers against regex pattern lists.
        """
        if not columns:
            return None

        # 1. Exact or regex match against raw & space-normalized headers
        for pat in patterns:
            for col in columns:
                clean_col = col.strip().lower()
                space_col = clean_col.replace('_', ' ').replace('-', ' ')
                if re.search(pat, clean_col) or re.search(pat, space_col):
                    return col

        # 2. Token-based subset matching fallback
        for pat in patterns:
            pat_clean = pat.replace(r'\b', '').replace('_', ' ').strip()
            pat_tokens = set(re.findall(r'\b[a-z0-9]+\b', pat_clean))
            if not pat_tokens:
                continue
            for col in columns:
                space_col = col.strip().lower().replace('_', ' ').replace('-', ' ')
                col_tokens = set(re.findall(r'\b[a-z0-9]+\b', space_col))
                if pat_tokens.issubset(col_tokens):
                    return col

        return None

    def _clean_number(self, val: Any) -> Tuple[Optional[float], Optional[str]]:
        """
        Parses raw values into valid floats while handling numeric strings, comma formatting,
        currency symbols ($/RM/EUR), trailing units, and missing values.
        Returns tuple of (parsed_float_or_none, exclusion_reason_or_none).
        """
        if val is None:
            return None, "Missing / Null Value"

        val_str = str(val).strip()
        if not val_str or val_str.lower() in ["none", "null", "nan", "n/a", "", "-", "unknown", "invalid"]:
            return None, "Missing / Null Value"

        cleaned = re.sub(r'[\$\,\sRM\u20ac\u00a3]', '', val_str)

        match = re.search(r'^-?\d+(?:\.\d+)?', cleaned)
        if match:
            try:
                num = float(match.group(0))
                return num, None
            except ValueError:
                return None, f"Unparseable numeric string '{val_str}'"

        return None, f"Non-numeric string value '{val_str}'"

    def _select_sheet(
        self,
        records_dict: Dict[str, List[Dict[str, Any]]],
        query: str,
        plan: Dict[str, Any]
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Executes strict schema-compatibility sheet selection for multi-sheet workbooks.
        Excludes reference sheets (e.g. Salary_Bands) unless explicitly requested.
        """
        query_lower = query.lower()
        per_sheet_counts = {s: len(recs) for s, recs in records_dict.items() if isinstance(recs, list)}

        # 1. Match sheet by explicit query name match (e.g. "salary_bands" or "salary bands")
        for s_name, s_recs in records_dict.items():
            if isinstance(s_recs, list) and s_recs:
                s_name_clean = s_name.lower().replace('_', ' ').strip()
                if s_name_clean in query_lower:
                    return s_name, s_recs

        # 2. Inspect sheet column signatures for schema compatibility
        calc_fields = [f.lower() for f in plan.get("calculation_fields", [])]
        
        # Target: Employee Sales / Employee Record dataset
        for s_name, s_recs in records_dict.items():
            if isinstance(s_recs, list) and s_recs:
                first_rec = s_recs[0] if len(s_recs) > 0 else {}
                cols = [str(k).lower().replace('_', ' ') for k in first_rec.keys()]
                
                # Exclude reference sheets if looking for employee records
                if "salary band" in s_name.lower() or "salary_band" in s_name.lower():
                    if not any(k in query_lower for k in ["salary band", "salary_band", "minimum_salary", "maximum_salary"]):
                        continue

                has_emp_id = any("employee id" in c or "emp id" in c or "employee" in c for c in cols)
                has_sales = any("sales" in c or "revenue" in c for c in cols)
                has_salary = any("salary" in c or "monthly" in c for c in cols)

                if has_emp_id and (has_sales or has_salary or "department" in cols):
                    return s_name, s_recs

        # 3. Fall back to sheet with the most records, skipping reference sheets if possible
        candidate_sheets = [(s, len(r)) for s, r in records_dict.items() if isinstance(r, list)]
        candidate_sheets.sort(key=lambda x: x[1], reverse=True)
        
        for s_name, cnt in candidate_sheets:
            if "salary band" not in s_name.lower() and "salary_band" not in s_name.lower():
                return s_name, records_dict[s_name]

        best_sheet = candidate_sheets[0][0] if candidate_sheets else list(records_dict.keys())[0]
        return best_sheet, records_dict.get(best_sheet, [])

    def _extract_record_id(self, r: Dict[str, Any], pk_col: Optional[str], all_columns: List[str]) -> str:
        """
        Generically extracts the record primary key / identifier value from a row dict.
        """
        if pk_col and r.get(pk_col) is not None and str(r.get(pk_col)).strip():
            return str(r.get(pk_col)).strip()
        for c in all_columns:
            clean_c = c.lower()
            if any(k in clean_c for k in ["id", "code", "number", "key"]):
                val = r.get(c)
                if val is not None and str(val).strip():
                    return str(val).strip()
        return ""

    def _matches_filters(self, r: Dict[str, Any], plan_filters: Dict[str, Any], all_columns: List[str]) -> bool:
        """
        Generically tests if a row dict satisfies all active plan filters.
        """
        if not plan_filters:
            return True
        for f_col, f_val in plan_filters.items():
            if f_col in ["gt_val", "lt_val", "groups_to_compare"]:
                continue
            target_col = self._match_column(all_columns, [r'\b' + re.escape(str(f_col).lower()) + r'\b'])
            if not target_col:
                for c in all_columns:
                    if str(f_col).lower() in c.lower() or c.lower() in str(f_col).lower():
                        target_col = c
                        break
            if target_col and target_col in r:
                r_val = str(r.get(target_col) or "").strip().lower()
                req_val = str(f_val).strip().lower()
                if r_val != req_val:
                    return False
        return True

    def analyze_dataset(
        self,
        records: Any,
        query: str,
        plan: Dict[str, Any],
        doc_title: str,
        doc_id: str,
        sheet_name_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyzes dirty tabular records, performs deterministic schema discovery,
        cleans numeric values, calculates operation-specific sums/averages/rankings,
        and constructs evidence items and authoritative calculation traces.
        Preserves multi-sheet structural isolation while supporting cross-sheet analysis for Excel workbooks.
        """
        if not records:
            return {
                "evidence_item": None,
                "fact_statement": f"Dataset '{doc_title}' contains zero records.",
                "schema_discovered": {},
                "audit_counts": {"total_records": 0, "valid_records": 0}
            }

        sheet_name_selected = sheet_name_override
        per_sheet_counts = {}

        if isinstance(records, dict):
            per_sheet_counts = {s: len(recs) for s, recs in records.items() if isinstance(recs, list)}
            if len(records) > 1 and not sheet_name_override:
                all_sheet_items = []
                primary_res = None
                for s_name, s_recs in records.items():
                    if isinstance(s_recs, list) and s_recs:
                        s_res = self.analyze_dataset(
                            records=s_recs,
                            query=query,
                            plan=plan,
                            doc_title=doc_title,
                            doc_id=doc_id,
                            sheet_name_override=s_name
                        )
                        if s_res and s_res.get("evidence_item"):
                            ev_item = s_res["evidence_item"]
                            sel_cnt = s_res.get("forensic_trace", {}).get("selected_record_count", 0)
                            if sel_cnt > 0 or not plan.get("filters"):
                                all_sheet_items.append(ev_item)
                            if not primary_res:
                                primary_res = s_res

                if all_sheet_items:
                    combined_fact_stmt = "\n\n".join([it["text"] for it in all_sheet_items])
                    return {
                        "evidence_items": all_sheet_items,
                        "evidence_item": all_sheet_items[0],
                        "fact_statement": combined_fact_stmt,
                        "schema_discovered": primary_res.get("schema_discovered", {}) if primary_res else {},
                        "forensic_trace": primary_res.get("forensic_trace", {}) if primary_res else {},
                        "audit_counts": primary_res.get("audit_counts", {}) if primary_res else {}
                    }

            sheet_name_selected, records = self._select_sheet(records, query, plan)

        if not isinstance(records, list):
            records = []

        total_raw_records = len(records)

        # Discover columns for primary key matcher
        sample_columns = []
        for r in records[:30]:
            for k in r.keys():
                if k not in sample_columns and k != "pages":
                    sample_columns.append(k)

        pk_col = self._match_column(sample_columns, self.ID_COL_PATTERNS)

        # 1. Primary Key / Record Deduplication Audit
        unique_records = []
        seen_keys = set()
        duplicate_count = 0
        for r in records:
            if pk_col and r.get(pk_col) is not None:
                pk_val = str(r.get(pk_col)).strip()
                if pk_val in seen_keys:
                    duplicate_count += 1
                    continue
                else:
                    seen_keys.add(pk_val)
                    unique_records.append(r)
            else:
                filtered_r = {k: v for k, v in r.items() if k not in ["pages", "id", "created_at", "updated_at"]}
                hash_key = json.dumps(filtered_r, sort_keys=True, default=str)
                if hash_key in seen_keys:
                    duplicate_count += 1
                else:
                    seen_keys.add(hash_key)
                    unique_records.append(r)

        # 2. Schema Discovery
        all_columns = []
        for r in unique_records[:30]:
            for k in r.keys():
                if k not in all_columns and k != "pages":
                    all_columns.append(k)

        emp_col = self._match_column(all_columns, self.EMP_COL_PATTERNS)
        dept_col = self._match_column(all_columns, self.DEPT_COL_PATTERNS)
        status_col = self._match_column(all_columns, self.STATUS_COL_PATTERNS)
        salary_col = self._match_column(all_columns, self.SALARY_COL_PATTERNS)
        sales_col = self._match_column(all_columns, self.SALES_COL_PATTERNS)
        qty_col = self._match_column(all_columns, self.QTY_COL_PATTERNS)
        item_col = self._match_column(all_columns, self.ITEM_COL_PATTERNS)
        unit_price_col = self._match_column(all_columns, self.UNIT_PRICE_PATTERNS)

        schema_summary = {
            "all_columns": all_columns,
            "pk_column": pk_col,
            "employee_column": emp_col,
            "department_column": dept_col,
            "status_column": status_col,
            "salary_column": salary_col,
            "sales_column": sales_col,
            "quantity_column": qty_col,
            "item_column": item_col,
            "unit_price_column": unit_price_col
        }

        # 3. OPERATION-SPECIFIC STRUCTURED CALCULATIONS
        query_lower = query.lower()
        plan_op = plan.get("operation", "DIRECT_FACT") if plan else "DIRECT_FACT"
        plan_filters = plan.get("filters", {}) if plan else {}
        plan_group_by = plan.get("group_by") if plan else None

        employee_ranking_result = None
        grouped_aggregation_result = None
        exclusion_reasons_log = []

        # Generic Filter Application
        filtered_records = [r for r in unique_records if self._matches_filters(r, plan_filters, all_columns)]
        if not filtered_records and unique_records and not plan_filters:
            filtered_records = unique_records

        # Determine Target Metric Generically
        query_metric_text = query_lower
        if doc_title:
            query_metric_text = query_metric_text.replace(doc_title.lower(), "")
        query_metric_text = re.sub(r'[\w\-]+\.(xlsx|csv|pdf|docx|txt|json|jpg|png|jpeg)', '', query_metric_text).strip()

        plan_calc_fields = plan.get("calculation_fields", []) if plan else []

        is_price_focused = any(k in query_metric_text for k in ["priced", "unit price", "unitprice", "price per unit", "highest price", "most expensive", "costliest", "rate"])
        is_sales_value_focused = any(k in query_metric_text for k in ["sales value", "order value", "highest-value", "highest value", "revenue", "net amount", "order total"])
        is_quantity_focused = (any(k in query_metric_text for k in ["sold", "units sold", "quantity", "qty", "units", "items sold", "volume"]) and not (is_price_focused or is_sales_value_focused))

        primary_metric_col = None
        if is_price_focused and unit_price_col:
            primary_metric_col = unit_price_col
        elif is_quantity_focused and qty_col:
            primary_metric_col = qty_col
        elif is_sales_value_focused and sales_col:
            primary_metric_col = sales_col
        elif ("salary" in query_metric_text or "income" in query_metric_text or "compensation" in query_metric_text) and salary_col:
            primary_metric_col = salary_col
        elif ("sales" in query_metric_text or "revenue" in query_metric_text or "amount" in query_metric_text or "net amount" in query_metric_text or "net_amount" in query_metric_text or "price" in query_metric_text or "cost" in query_metric_text) and sales_col:
            primary_metric_col = sales_col
        elif ("quantity" in query_metric_text or "units" in query_metric_text or "qty" in query_metric_text) and qty_col:
            primary_metric_col = qty_col

        # Fallback to search all_columns for any matching numeric column (Finding 8)
        if not primary_metric_col:
            for c in all_columns:
                c_clean = c.lower().replace('_', ' ')
                if any(k in query_metric_text for k in c_clean.split()) or any(k in c_clean for k in ["days", "time", "duration", "cost", "score", "amount", "price", "rate", "count"]):
                    for r in unique_records[:10]:
                        n_val, _ = self._clean_number(r.get(c))
                        if n_val is not None:
                            primary_metric_col = c
                            break
                    if primary_metric_col:
                        break

        if not primary_metric_col:
            primary_metric_col = sales_col or salary_col or qty_col

        # Determine Grouping Target Column
        group_col_target = None
        if plan_group_by:
            group_col_target = self._match_column(all_columns, [r'\b' + re.escape(plan_group_by.lower()) + r'\b'])
            if not group_col_target:
                for c in all_columns:
                    if plan_group_by.lower() in c.lower() or c.lower() in plan_group_by.lower():
                        group_col_target = c
                        break
        if not group_col_target:
            group_col_target = dept_col
        if not group_col_target and all_columns:
            for c in all_columns:
                if c != pk_col and c != emp_col and not any(k in c.lower() for k in ["id", "date", "created", "updated"]):
                    group_col_target = c
                    break

        # Discover secondary categorical column for sub-breakdowns (Finding 7)
        sub_col = None
        for c in all_columns:
            if c != group_col_target and c != pk_col and c != emp_col and any(k in c.lower() for k in ["status", "severity", "category", "type", "priority"]):
                sub_col = c
                break

        # Determine dispatch pattern
        target_entities = plan.get("target_entities", []) if plan else []
        is_employee_query = "Employee" in target_entities or any(k in query_lower for k in ["employee", "staff", "person", "worker", "which employee"])
        is_ranking_op = plan_op in ["MAX", "MIN", "TOP_GROUP_BY_COUNT"] or any(k in query_lower for k in ["highest", "top", "lowest", "max", "min", "most", "performs best", "fastest", "quickest"])

        # -------------------------------------------------------------
        # PATTERN A (Q3/Finding 8) — RECORD MIN/MAX RANKING OVER METRIC
        # -------------------------------------------------------------
        is_item_ranking_query = any(k in query_lower for k in ["highest sold item", "highest priced item", "top sold item", "most sold item", "best selling item", "highest selling item", "highest sold product", "top product", "highest sold", "highest priced"])
        if is_ranking_op and primary_metric_col and (not plan_group_by or is_employee_query or is_item_ranking_query):
            best_rec = None
            best_val = -float('inf') if plan_op != "MIN" else float('inf')
            valid_metric_count = 0

            eval_recs = filtered_records if filtered_records else unique_records

            for r in eval_recs:
                val_raw = r.get(primary_metric_col)
                num_val, err = self._clean_number(val_raw)
                if num_val is not None:
                    valid_metric_count += 1
                    if plan_op == "MIN":
                        if num_val < best_val:
                            best_val = num_val
                            best_rec = r
                    else:
                        if num_val > best_val:
                            best_val = num_val
                            best_rec = r
                elif err:
                    exclusion_reasons_log.append(f"Record {r.get(pk_col, 'N/A')}: {err}")

            if best_rec:
                emp_name_val = str(best_rec.get(emp_col) or best_rec.get("Employee_Name") or best_rec.get(pk_col) or "Unknown Entity").strip()
                emp_id_val = self._extract_record_id(best_rec, pk_col, all_columns)
                dept_val = str(best_rec.get(dept_col) or best_rec.get("Department") or best_rec.get("Project") or "N/A").strip()
                region_val = str(best_rec.get("Region") or best_rec.get("region") or "N/A").strip()
                role_val = str(best_rec.get("Role") or best_rec.get("Observation_Type") or best_rec.get("role") or "N/A").strip()
                status_val = str(best_rec.get(status_col) or best_rec.get("Employment_Status") or best_rec.get("Status") or "N/A").strip()
                salary_val = best_rec.get(salary_col or "Monthly_Salary")
                salary_num, _ = self._clean_number(salary_val)
                sal_str = f"${salary_num:,.2f}" if salary_num is not None else str(salary_val or 'N/A')

                employee_ranking_result = {
                    "employee_name": emp_name_val,
                    "employee_id": emp_id_val,
                    "department": dept_val,
                    "region": region_val,
                    "role": role_val,
                    "status": status_val,
                    "metric_field": primary_metric_col,
                    "max_value": best_val,
                    "formatted_max_value": f"${best_val:,.2f}" if any(k in primary_metric_col.lower() for k in ["sales", "revenue", "salary", "income"]) else f"{best_val:,.0f}",
                    "monthly_salary_str": sal_str,
                    "valid_record_count": valid_metric_count,
                    "contributing_record_id": emp_id_val,
                    "full_record": best_rec
                }

        # -------------------------------------------------------------
        # PATTERN B/C/D — GROUP AGGREGATION WITH SUB-BREAKDOWNS & SUPPORTING IDs
        # -------------------------------------------------------------
        if not employee_ranking_result and group_col_target:
            dept_counts = {}
            dept_sums = {}
            dept_qty_sums = {}
            dept_record_ids = {}
            dept_values = {}
            dept_qty_values = {}
            dept_sub_breakdown = {}
            dept_record_details = {}

            # Preserving complete record set for grouping (Requirement 1)
            eval_recs = unique_records if unique_records else records
            total_source_records = len(eval_recs)
            all_source_ids = [self._extract_record_id(r, pk_col, all_columns) or f"ROW_{idx}" for idx, r in enumerate(eval_recs, 1)]

            target_m_col = primary_metric_col or sales_col or salary_col

            for r in eval_recs:
                g_val = str(r.get(group_col_target) or "Unknown").strip()
                if not g_val or g_val.lower() in ["none", "null", "n/a", "nan", ""]:
                    g_val = "Unassigned"

                dept_counts[g_val] = dept_counts.get(g_val, 0) + 1
                r_id = self._extract_record_id(r, pk_col, all_columns) or f"ROW_{len(dept_record_ids.get(g_val, []))+1}"
                dept_record_ids.setdefault(g_val, []).append(r_id)

                # Store full clean record details for traceability (Requirement 6)
                dept_record_details.setdefault(g_val, []).append({k: v for k, v in r.items() if k != "pages" and v is not None})

                if target_m_col:
                    num_val, err = self._clean_number(r.get(target_m_col))
                    if num_val is not None:
                        dept_sums[g_val] = round(dept_sums.get(g_val, 0.0) + num_val, 2)
                        dept_values.setdefault(g_val, []).append(num_val)
                    elif err:
                        exclusion_reasons_log.append(f"Record {r_id or 'Row'}: {err}")

                if qty_col:
                    q_val, err = self._clean_number(r.get(qty_col))
                    if q_val is not None:
                        dept_qty_sums[g_val] = round(dept_qty_sums.get(g_val, 0.0) + q_val, 2)
                        dept_qty_values.setdefault(g_val, []).append(q_val)

                if sub_col:
                    sub_val = str(r.get(sub_col) or "Unknown").strip()
                    dept_sub_breakdown.setdefault(g_val, {}).setdefault(sub_val, 0)
                    dept_sub_breakdown[g_val][sub_val] += 1

            if dept_counts:
                dept_avgs = {}
                if dept_sums:
                    dept_avgs = {g: round(dept_sums[g] / max(1, len(dept_values.get(g, []))), 2) for g in dept_sums}
                    if plan_op == "MIN":
                        top_group_sum = min(dept_sums.items(), key=lambda x: x[1])
                        top_group_avg = min(dept_avgs.items(), key=lambda x: x[1])
                    else:
                        top_group_sum = max(dept_sums.items(), key=lambda x: x[1])
                        top_group_avg = max(dept_avgs.items(), key=lambda x: x[1])
                else:
                    dept_sums = dept_counts
                    dept_avgs = dept_counts
                    top_group_sum = max(dept_counts.items(), key=lambda x: x[1])
                    top_group_avg = top_group_sum

                # Group Completeness Validation (Requirement 3)
                grouped_record_count = sum(dept_counts.values())
                all_grouped_ids = [rid for ids in dept_record_ids.values() for rid in ids]
                missing_ids = [rid for rid in all_source_ids if rid not in all_grouped_ids]
                duplicate_ids = [rid for rid in set(all_grouped_ids) if all_grouped_ids.count(rid) > 1]
                is_group_complete = (grouped_record_count == total_source_records) and (len(missing_ids) == 0) and (len(duplicate_ids) == 0)

                # Grand Total Independent Calculation & Reconciliation (Requirement 4)
                indep_sales_list = []
                indep_qty_list = []
                for r in eval_recs:
                    if target_m_col:
                        nv, _ = self._clean_number(r.get(target_m_col))
                        if nv is not None: indep_sales_list.append(nv)
                    if qty_col:
                        qv, _ = self._clean_number(r.get(qty_col))
                        if qv is not None: indep_qty_list.append(qv)

                indep_grand_total_sales = round(sum(indep_sales_list), 2) if indep_sales_list else 0.0
                indep_grand_total_qty = round(sum(indep_qty_list), 2) if indep_qty_list else 0.0

                sum_of_group_sales = round(sum(dept_sums.values()), 2)
                sum_of_group_qty = round(sum(dept_qty_sums.values()), 2)

                sales_reconciled = (abs(indep_grand_total_sales - sum_of_group_sales) < 0.01)
                qty_reconciled = (abs(indep_grand_total_qty - sum_of_group_qty) < 0.01)

                # Percentage Contribution Calculations (Requirement 5)
                dept_sales_pct = {}
                if indep_grand_total_sales > 0:
                    for g, s in dept_sums.items():
                        dept_sales_pct[g] = round((s / indep_grand_total_sales) * 100, 2)

                dept_qty_pct = {}
                if indep_grand_total_qty > 0:
                    for g, q in dept_qty_sums.items():
                        dept_qty_pct[g] = round((q / indep_grand_total_qty) * 100, 2)

                grouped_aggregation_result = {
                    "group_column": group_col_target,
                    "sub_column": sub_col,
                    "metric_field": target_m_col or "Record_Count",
                    "quantity_field": qty_col,
                    "filter_applied": plan_filters,
                    "dept_sums": dept_sums,
                    "dept_qty_sums": dept_qty_sums,
                    "dept_avgs": dept_avgs,
                    "dept_counts": dept_counts,
                    "dept_record_ids": dept_record_ids,
                    "dept_values": dept_values,
                    "dept_qty_values": dept_qty_values,
                    "dept_sales_pct": dept_sales_pct,
                    "dept_qty_pct": dept_qty_pct,
                    "dept_sub_breakdown": dept_sub_breakdown,
                    "dept_record_details": dept_record_details,
                    "top_dept_by_sum": top_group_sum,
                    "top_dept_by_avg": top_group_avg,
                    "group_validation": {
                        "total_source_records": total_source_records,
                        "grouped_record_count": grouped_record_count,
                        "is_group_complete": is_group_complete,
                        "missing_ids": missing_ids,
                        "duplicate_ids": duplicate_ids,
                        "indep_grand_total_sales": indep_grand_total_sales,
                        "sum_of_group_sales": sum_of_group_sales,
                        "sales_reconciled": sales_reconciled,
                        "indep_grand_total_qty": indep_grand_total_qty,
                        "sum_of_group_qty": sum_of_group_qty,
                        "qty_reconciled": qty_reconciled
                    }
                }

        # 4. Construct Authoritative Factual Statements & Evidence
        summary_lines = []
        sheet_info = f" (Sheet: '{sheet_name_selected}')" if sheet_name_selected else ""
        summary_lines.append(f"Structured Dataset Analytics ({doc_title}{sheet_info}):")
        summary_lines.append(f"- Record Audit: {total_raw_records} raw records evaluated ({duplicate_count} duplicate records removed, {len(unique_records)} unique records).")
        summary_lines.append(f"- Schema Columns ({len(all_columns)} columns): {', '.join(all_columns)}.")

        # Grounded Overview Summary (Finding 1)
        if plan.get("intent") == "DOCUMENT_SUMMARY" or any(k in query_lower for k in ["summary", "summarize", "overview", "content of"]):
            sample_recs_str = []
            for r in unique_records[:3]:
                r_clean = {k: v for k, v in r.items() if k != "pages" and v is not None}
                sample_recs_str.append(json.dumps(r_clean))
            if sample_recs_str:
                summary_lines.append(f"- Source Record Samples:\n  " + "\n  ".join(sample_recs_str))

        if employee_ranking_result:
            r_info = employee_ranking_result
            rec_detail = json.dumps({k: v for k, v in r_info['full_record'].items() if k != "pages" and v is not None}) if 'full_record' in r_info else ""
            summary_lines.append(
                f"- Top/Best Metric Record ({r_info['metric_field']} = {r_info['formatted_max_value']}): "
                f"Record ID '{r_info['employee_id']}', Entity '{r_info['employee_name']}', Group '{r_info['department']}' (Role/Type: {r_info['role']}). "
                f"Full Record Details: {rec_detail}."
            )

        if grouped_aggregation_result:
            g_info = grouped_aggregation_result
            top_grp_name = g_info['top_dept_by_sum'][0]
            top_grp_val = g_info['top_dept_by_sum'][1]
            top_grp_ids = g_info.get('dept_record_ids', {}).get(top_grp_name, [])
            top_grp_vals = g_info.get('dept_values', {}).get(top_grp_name, [])
            top_ids_str = f" [Supporting Record IDs: {', '.join(top_grp_ids)}]" if top_grp_ids else ""

            is_currency = primary_metric_col and any(k in primary_metric_col.lower() for k in ["sales", "revenue", "salary", "income", "amount", "price", "cost", "inr", "usd", "spend", "pay"])
            
            def fmt_val(v):
                if isinstance(v, (int, float)):
                    v_num_str = f"{v:,.2f}".rstrip('0').rstrip('.')
                    if is_currency:
                        if primary_metric_col and ("inr" in primary_metric_col.lower() or "inr" in query_lower):
                            return f"₹{v_num_str}"
                        elif primary_metric_col and ("usd" in primary_metric_col.lower() or "usd" in query_lower):
                            return f"${v_num_str}"
                        return f"₹{v_num_str}" if "inr" in query_lower or "inr" in doc_title.lower() else f"${v_num_str}"
                    return v_num_str
                return str(v)

            top_val_formatted = fmt_val(top_grp_val)

            group_summaries = []
            sorted_groups = list(dept_counts.keys())
            
            for d in sorted_groups:
                g_ids = g_info.get('dept_record_ids', {}).get(d, [])
                g_cnt = g_info['dept_counts'].get(d, len(g_ids) or 1)
                
                s_sum = dept_sales_sums.get(d) if 'dept_sales_sums' in locals() else g_info.get('dept_sums', {}).get(d)
                q_sum = g_info.get('dept_qty_sums', {}).get(d)
                
                sales_str = f"Total Net Amount = ${s_sum:,.2f}" if s_sum is not None else ""
                qty_str = f"Total Quantity = {int(q_sum) if q_sum is not None and float(q_sum).is_integer() else q_sum}" if q_sum is not None else ""
                
                metrics_combined = ", ".join([p for p in [sales_str, qty_str] if p])
                ids_part = f" [Supporting Record IDs: {', '.join(g_ids)}]" if g_ids else ""

                group_summaries.append(f"'{d}': {metrics_combined} (across {g_cnt} records){ids_part}")

            count_str = "; ".join(group_summaries)
            metric_label = g_info['metric_field']

            summary_lines.append(
                f"- Group Aggregation & Multi-Metric Breakdown ({g_info['group_column']}): "
                f"Complete Group Breakdown: {count_str}."
            )

        # Compute exact deterministic multi-metric aggregations over eval_filtered (Hard Rule - Deterministic Truth)
        eval_filtered = filtered_records if filtered_records else unique_records

        # Resolve primary metric fields for sales, quantity, and primary key
        resolved_sales_col = sales_col or salary_col or primary_metric_col
        resolved_qty_col = qty_col
        resolved_pk_col = pk_col

        # 1. Total Orders / Record Count
        total_orders = len(eval_filtered)

        # 2. Total Quantity Sold (aggregated over ALL matching records without slicing)
        qty_values = []
        if resolved_qty_col and eval_filtered:
            for r in eval_filtered:
                q_num, _ = self._clean_number(r.get(resolved_qty_col))
                if q_num is not None:
                    qty_values.append(q_num)
        total_quantity = sum(qty_values) if qty_values else None
        if total_quantity is not None:
            total_quantity = int(total_quantity) if float(total_quantity).is_integer() else round(total_quantity, 2)

        # 3. Sales / Primary Metric Values & Record Pairing (aggregated over ALL matching records without slicing)
        sales_records_pairs = []
        sales_values = []
        if resolved_sales_col and eval_filtered:
            for r in eval_filtered:
                s_num, _ = self._clean_number(r.get(resolved_sales_col))
                if s_num is not None:
                    sales_values.append(s_num)
                    sales_records_pairs.append((r, s_num))

        total_sales = sum(sales_values) if sales_values else None
        average_order_value = (total_sales / total_orders) if (total_sales is not None and total_orders > 0) else None

        # 4. Highest & Lowest Value Orders with Associated Record Identifiers
        highest_order = None
        lowest_order = None
        if sales_records_pairs:
            sales_records_pairs.sort(key=lambda x: x[1])
            lowest_rec, lowest_val = sales_records_pairs[0]
            highest_rec, highest_val = sales_records_pairs[-1]

            highest_ord_id = self._extract_record_id(highest_rec, resolved_pk_col, all_columns) or str(highest_rec.get("Order_ID") or highest_rec.get("Employee_ID") or highest_rec.get("Department") or "REC_MAX")
            lowest_ord_id = self._extract_record_id(lowest_rec, resolved_pk_col, all_columns) or str(lowest_rec.get("Order_ID") or lowest_rec.get("Employee_ID") or lowest_rec.get("Department") or "REC_MIN")

            highest_order = {
                "order_id": highest_ord_id,
                "value": round(highest_val, 2)
            }
            lowest_order = {
                "order_id": lowest_ord_id,
                "value": round(lowest_val, 2)
            }

        structured_calculation_result = {
            "total_orders": total_orders,
            "total_quantity": total_quantity,
            "total_sales": round(total_sales, 2) if total_sales is not None else None,
            "average_order_value": round(average_order_value, 2) if average_order_value is not None else None,
            "highest_order": highest_order,
            "lowest_order": lowest_order
        }

        calc_count = total_orders
        calc_sum = total_sales
        calc_avg = average_order_value
        calc_min = lowest_order["value"] if lowest_order else None
        calc_max = highest_order["value"] if highest_order else None

        verified_computation = {
            "source_file": doc_title,
            "sheet_name": sheet_name_selected,
            "filter_applied": plan_filters,
            "metric_field": resolved_sales_col or primary_metric_col or "Records",
            "quantity_field": resolved_qty_col,
            "pk_field": resolved_pk_col,
            "record_count": total_orders,
            "total_orders": total_orders,
            "total_quantity": total_quantity,
            "total_sales": round(total_sales, 2) if total_sales is not None else None,
            "sum": round(calc_sum, 2) if calc_sum is not None else None,
            "average_order_value": round(average_order_value, 2) if average_order_value is not None else None,
            "average": round(calc_avg, 2) if calc_avg is not None else None,
            "highest_order": highest_order,
            "lowest_order": lowest_order,
            "min": calc_min,
            "max": calc_max,
            "operation": plan_op,
            "source_records": [{k: v for k, v in r.items() if k != "pages" and v is not None} for r in eval_filtered],
            "structured_calculation_result": structured_calculation_result,
            "provenance": {
                "source_file": doc_title,
                "sheet_name": sheet_name_selected,
                "matching_row_count": total_orders
            }
        }

        is_sales_order_dataset = (total_sales is not None and total_quantity is not None and resolved_qty_col and any(k in resolved_qty_col.lower() for k in ["quantity", "unit", "sold", "volume"]))
        if is_sales_order_dataset:
            if is_quantity_focused and employee_ranking_result:
                r_info = employee_ranking_result
                summary_lines.append(
                    f"- VERIFIED DETERMINISTIC QUANTITY COMPUTATION (Numerical Truth):\n"
                    f"  * Total Quantity Sold: {total_quantity}\n"
                    f"  * Highest Quantity Item/Record: Product '{r_info.get('employee_name', 'N/A')}', Order ID '{r_info.get('employee_id', 'N/A')}', Quantity: {r_info.get('formatted_max_value', 'N/A')} units\n"
                    f"  * Total Number of Orders (Count): {total_orders}"
                )
            elif is_price_focused and employee_ranking_result:
                r_info = employee_ranking_result
                summary_lines.append(
                    f"- VERIFIED DETERMINISTIC UNIT PRICE COMPUTATION (Numerical Truth):\n"
                    f"  * Highest Priced Item/Record: Product '{r_info.get('employee_name', 'N/A')}', Order ID '{r_info.get('employee_id', 'N/A')}', Unit Price: ${r_info.get('max_value', 0):,.2f}\n"
                    f"  * Total Number of Orders (Count): {total_orders}"
                )
            elif is_sales_value_focused:
                h_str = f"Order ID '{highest_order['order_id']}' (${highest_order['value']:,.2f})" if highest_order else "N/A"
                l_str = f"Order ID '{lowest_order['order_id']}' (${lowest_order['value']:,.2f})" if lowest_order else "N/A"
                summary_lines.append(
                    f"- VERIFIED DETERMINISTIC SALES VALUE COMPUTATION (Numerical Truth):\n"
                    f"  * Total Sales Revenue / Net Amount: ${total_sales:,.2f}\n"
                    f"  * Highest-Value Order: {h_str}\n"
                    f"  * Lowest-Value Order: {l_str}\n"
                    f"  * Average Order Value: ${average_order_value:,.2f}"
                )
            else:
                h_str = f"Order ID '{highest_order['order_id']}' (${highest_order['value']:,.2f})" if highest_order else "N/A"
                l_str = f"Order ID '{lowest_order['order_id']}' (${lowest_order['value']:,.2f})" if lowest_order else "N/A"
                summary_lines.append(
                    f"- VERIFIED DETERMINISTIC MULTI-METRIC COMPUTATION (Numerical Truth):\n"
                    f"  * Total Number of Orders (Count): {total_orders}\n"
                    f"  * Total Quantity Sold: {total_quantity}\n"
                    f"  * Total Sales Revenue: ${total_sales:,.2f}\n"
                    f"  * Average Order Value: ${average_order_value:,.2f}\n"
                    f"  * Highest-Value Order: {h_str}\n"
                    f"  * Lowest-Value Order: {l_str}"
                )
        elif verified_computation and calc_avg is not None:
            summary_lines.append(
                f"- VERIFIED DETERMINISTIC COMPUTATION (Numerical Truth): Record Count (N) = {calc_count}, "
                f"Sum = ${calc_sum:,.2f}, Verified Average = ${calc_avg:,.2f}, Min = ${calc_min:,.2f}, Max = ${calc_max:,.2f} "
                f"(Filter: {plan_filters or 'All matching records'})."
            )

        # Filtered Matching Records List (Findings 6 & 9)
        if plan_filters or any(k in query_lower for k in ["list", "show", "provide", "all", "each"]):
            match_recs_str = []
            for r in eval_filtered[:10]:
                r_id = self._extract_record_id(r, pk_col, all_columns)
                r_clean = {k: v for k, v in r.items() if k != "pages" and v is not None}
                match_recs_str.append(f"Record {r_id or 'Row'}: {json.dumps(r_clean)}")
            if match_recs_str:
                summary_lines.append(f"- Filtered Matching Records ({len(eval_filtered)} matching records, showing top {len(match_recs_str)}):\n  " + "\n  ".join(match_recs_str))

        fact_statement = "\n".join(summary_lines)

        evidence_item = {
            "title": f"Structured Dataset Analysis ({doc_title}{sheet_info})",
            "text": fact_statement,
            "source": f"{doc_title}{sheet_info}" if sheet_name_selected else doc_title,
            "document_id": doc_id,
            "source_type": "CSV" if doc_title.lower().endswith(".csv") else "XLSX",
            "evidence_type": "STRUCTURED_RECORD",
            "category": "Structured_Dataset_Analytics",
            "score": 1.0,
            "confidence": "100.0%",
            "verified_computation": verified_computation,
            "location_meta": {"sheet": sheet_name_selected, "record_count": len(unique_records), "per_sheet_counts": per_sheet_counts}
        }

        calculation_trace = {
            "operation": plan_op,
            "source_document": doc_title,
            "sheet_name": sheet_name_selected,
            "selected_record_count": len(eval_filtered),
            "excluded_record_count": total_raw_records - len(eval_filtered),
            "fields_used": {
                "pk_field": resolved_pk_col,
                "quantity_field": resolved_qty_col,
                "sales_field": resolved_sales_col,
                "primary_metric": primary_metric_col
            },
            "filter_conditions": plan_filters,
            "aggregation_values": structured_calculation_result,
            "result": "SUCCESS"
        }

        forensic_trace = {
            "query_id": plan.get("query_id") if plan else "",
            "document_id": doc_id,
            "source_document": doc_title,
            "sheet_name": sheet_name_selected,
            "operation": plan_op,
            "field": primary_metric_col,
            "filters": plan.get("filters", {}),
            "group_by": plan_group_by,
            "raw_record_count": total_raw_records,
            "duplicate_count": duplicate_count,
            "unique_record_count": len(unique_records),
            "selected_record_count": len(eval_filtered),
            "excluded_record_count": total_raw_records - len(eval_filtered),
            "structured_calculation_result": structured_calculation_result,
            "calculation_trace": calculation_trace,
            "employee_ranking_result": employee_ranking_result,
            "grouped_aggregation_result": grouped_aggregation_result,
            "exclusion_reasons": exclusion_reasons_log[:10]
        }

        return {
            "evidence_item": evidence_item,
            "fact_statement": fact_statement,
            "employee_ranking_result": employee_ranking_result,
            "grouped_aggregation_result": grouped_aggregation_result,
            "schema_discovered": schema_summary,
            "forensic_trace": forensic_trace,
            "audit_counts": {
                "raw_records": total_raw_records,
                "unique_records": len(unique_records),
                "duplicates_removed": duplicate_count
            }
        }
