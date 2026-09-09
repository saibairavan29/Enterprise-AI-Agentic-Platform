import math
import re
from .text_transformer import TextTransformer
from .numeric_transformer import NumericTransformer
from .date_transformer import DateTransformer
from .boolean_transformer import BooleanTransformer
from .null_transformer import NullTransformer
from .collection_transformer import CollectionTransformer

class RecordTransformer:
    """
    Orchestrator responsible for recursively walking document dictionaries and lists
    and executing the field-level transformation pipeline on leaf values.
    Optimized for high-throughput memory-safe enterprise dataset ingestion.
    """
    def __init__(self):
        self.null_trans = NullTransformer()
        self.bool_trans = BooleanTransformer()
        self.date_trans = DateTransformer()
        self.num_trans = NumericTransformer()
        self.text_trans = TextTransformer()
        self.coll_trans = CollectionTransformer()
        
        self._path_cache = {}
        self._iso_date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

    def _get_path_info(self, path):
        if path not in self._path_cache:
            lower_path = path.lower()
            is_date = ("date" in lower_path or "timestamp" in lower_path or "time" in lower_path)
            is_num = any(term in lower_path for term in ["salary", "amount", "count", "size", "width", "height", "confidence"])
            self._path_cache[path] = (is_date, is_num)
        return self._path_cache[path]

    def transform_record(self, record, rules):
        """
        Orchestrates transformation on record dictionary without expensive deepcopies.
        Returns (standardized_record, changes_list, skipped_count, failed_count)
        """
        if not record or not isinstance(record, dict):
            return {}, [], 0, 0

        changes_list = []
        metrics = {"skipped": 0, "failed": 0}

        standardized_rec = self._transform_node(record, "", rules, changes_list, metrics)

        return standardized_rec, changes_list, metrics["skipped"], metrics["failed"]

    def _transform_node(self, node, path, rules, changes_list, metrics):
        if isinstance(node, dict):
            new_dict = {}
            for k, v in node.items():
                current_path = f"{path}.{k}" if path else k
                if isinstance(v, (dict, list)):
                    new_dict[k] = self._transform_node(v, current_path, rules, changes_list, metrics)
                else:
                    try:
                        new_dict[k] = self._transform_leaf(v, current_path, rules, changes_list)
                    except Exception:
                        metrics["failed"] += 1
                        new_dict[k] = v
            return new_dict
        elif isinstance(node, list):
            new_list = []
            for idx, item in enumerate(node):
                current_path = f"{path}[{idx}]"
                if isinstance(item, (dict, list)):
                    new_list.append(self._transform_node(item, current_path, rules, changes_list, metrics))
                else:
                    try:
                        new_list.append(self._transform_leaf(item, current_path, rules, changes_list))
                    except Exception:
                        metrics["failed"] += 1
                        new_list.append(item)
            return new_list
        else:
            return self._transform_leaf(node, path, rules, changes_list)

    def _transform_leaf(self, val, field_path, rules, changes_list):
        """
        Runs the pipeline of validators and transformations with fast-path short-circuits.
        """
        # Fast null check
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return None

        # 1. Null transformer check
        val = self.null_trans.transform(val, field_path, rules, changes_list)
        if val is None:
            return None

        # Fast primitive short-circuit for numbers and booleans
        if isinstance(val, bool):
            return val
        if isinstance(val, (int, float)):
            return val

        # 2. Collection check
        val = self.coll_trans.transform(val, field_path, rules, changes_list)
        if isinstance(val, (list, dict)):
            return val

        # 3. Boolean check
        val = self.bool_trans.transform(val, field_path, rules, changes_list)
        if isinstance(val, bool):
            return val

        # 4. Path-based type hints using pre-cached path info
        is_date, is_num = self._get_path_info(field_path)

        if is_date:
            res = self.date_trans.transform(val, field_path, rules, changes_list)
            if res != val:
                return res

        if is_num:
            res = self.num_trans.transform(val, field_path, rules, changes_list)
            if res != val:
                return res

        # 5. Dynamic type detection for generic string values
        if isinstance(val, str):
            # Try date parsing
            date_res = self.date_trans.transform(val, field_path, rules, changes_list)
            if date_res != val and self._iso_date_pattern.match(str(date_res)):
                return date_res

            # Try numeric parsing
            num_res = self.num_trans.transform(val, field_path, rules, changes_list)
            if num_res != val and isinstance(num_res, (int, float)):
                return num_res

            # Text cleaning fall-through
            val = self.text_trans.transform(val, field_path, rules, changes_list)

        return val
