import logging
import collections

logger = logging.getLogger(__name__)

class DataProfiler:
    """
    Profiles database record sets, compiling column details, statistics,
    and formats data metrics.
    """
    def profile_records(self, records: list) -> tuple:
        """
        Profiles a list of record dicts (canonical data representations).
        Returns a tuple: (document_statistics, field_profiles)
        """
        if not records:
            return {}, {}

        total_records = len(records)
        all_fields = set()
        for r in records:
            if isinstance(r, dict):
                all_fields.update(r.keys())
        total_fields = len(all_fields)

        # Initialize profiler tracking variables
        field_types = collections.defaultdict(list)
        field_nulls = collections.defaultdict(int)
        field_lengths = collections.defaultdict(list)
        field_values = collections.defaultdict(list)
        
        # Track unique hashes for duplicate percentage
        seen_records = set()
        duplicate_count = 0

        for r in records:
            if not isinstance(r, dict):
                continue
            
            # Uniqueness check of the raw record text
            frozen_rep = frozenset(r.items())
            if frozen_rep in seen_records:
                duplicate_count += 1
            else:
                seen_records.add(frozen_rep)

            for f in all_fields:
                val = r.get(f)
                if val is None or val == "" or str(val).strip().lower() == "null":
                    field_nulls[f] += 1
                else:
                    field_values[f].append(val)
                    # Deduce data type representation
                    val_str = str(val).strip()
                    field_lengths[f].append(len(val_str))
                    
                    try:
                        float(val_str)
                        if "." in val_str:
                            field_types[f].append("Float")
                        else:
                            field_types[f].append("Integer")
                    except ValueError:
                        # Check boolean representation
                        if val_str.lower() in ["true", "false"]:
                            field_types[f].append("Boolean")
                        else:
                            field_types[f].append("String")

        # Compile document level statistics
        total_vals = total_records * total_fields
        total_nulls = sum(field_nulls.values())
        null_percentage = (total_nulls / total_vals * 100.0) if total_vals > 0 else 0.0
        duplicate_percentage = (duplicate_count / total_records * 100.0) if total_records > 0 else 0.0

        document_statistics = {
            "total_records": total_records,
            "total_fields": total_fields,
            "null_percentage": round(null_percentage, 2),
            "duplicate_percentage": round(duplicate_percentage, 2)
        }

        # Compile field-level profiles
        field_profiles = {}
        for f in all_fields:
            null_count = field_nulls[f]
            null_pct = (null_count / total_records * 100.0) if total_records > 0 else 0.0
            
            vals = field_values[f]
            unique_vals = set(vals)
            unique_pct = (len(unique_vals) / total_records * 100.0) if total_records > 0 else 0.0

            # Deduce dominant datatype
            types_list = field_types[f]
            if types_list:
                datatype = collections.Counter(types_list).most_common(1)[0][0]
            else:
                datatype = "Null/Empty"

            # Min/Max length
            lens = field_lengths[f]
            min_len = min(lens) if lens else 0
            max_len = max(lens) if lens else 0
            avg_len = (sum(lens) / len(lens)) if lens else 0.0

            # Min/Max ranges for numerical values
            min_val = None
            max_val = None
            if datatype in ["Integer", "Float"] and vals:
                try:
                    num_vals = [float(v) for v in vals]
                    min_val = min(num_vals)
                    max_val = max(num_vals)
                except Exception:
                    pass

            # Top values frequency
            top_vals = [str(x) for x in vals[:10]] # limit tracking
            top_freq = collections.Counter(top_vals).most_common(5)
            top_values_formatted = {k: v for k, v in top_freq}

            field_profiles[f] = {
                "datatype": datatype,
                "null_percentage": round(null_pct, 2),
                "unique_percentage": round(unique_pct, 2),
                "min_length": min_len,
                "max_length": max_len,
                "average_length": round(avg_len, 2),
                "min_value": min_val,
                "max_value": max_val,
                "top_values": top_values_formatted
            }

        return document_statistics, field_profiles
