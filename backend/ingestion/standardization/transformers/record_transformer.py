import copy
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
    Uses immutable deep copies to avoid side-effects.
    """
    def __init__(self):
        self.null_trans = NullTransformer()
        self.bool_trans = BooleanTransformer()
        self.date_trans = DateTransformer()
        self.num_trans = NumericTransformer()
        self.text_trans = TextTransformer()
        self.coll_trans = CollectionTransformer()

    def transform_record(self, record, rules):
        """
        Orchestrates transformation on a deepcopy of the record dictionary.
        Returns (standardized_record, changes_list, skipped_count, failed_count)
        """
        if not record:
            return {}, [], 0, 0

        # Deepcopy to guarantee immutable processing
        standardized_rec = copy.deepcopy(record)
        changes_list = []
        
        # Statistics trackers
        metrics = {"skipped": 0, "failed": 0}

        # Recursively walk the record tree
        self._traverse_and_transform(standardized_rec, "", rules, changes_list, metrics)

        return standardized_rec, changes_list, metrics["skipped"], metrics["failed"]

    def _traverse_and_transform(self, node, path, rules, changes_list, metrics):
        """
        Recursively walks dict and list structures.
        """
        if isinstance(node, dict):
            for k, v in list(node.items()):
                current_path = f"{path}.{k}" if path else k
                
                # If nested collection, recurse
                if isinstance(v, (dict, list)):
                    self._traverse_and_transform(v, current_path, rules, changes_list, metrics)
                else:
                    try:
                        node[k] = self._transform_leaf(v, current_path, rules, changes_list)
                    except Exception:
                        metrics["failed"] += 1
                        node[k] = v
        elif isinstance(node, list):
            for idx, item in enumerate(node):
                current_path = f"{path}[{idx}]"
                
                if isinstance(item, (dict, list)):
                    self._traverse_and_transform(item, current_path, rules, changes_list, metrics)
                else:
                    try:
                        node[idx] = self._transform_leaf(item, current_path, rules, changes_list)
                    except Exception:
                        metrics["failed"] += 1
                        node[idx] = item

    def _transform_leaf(self, val, field_path, rules, changes_list):
        """
        Runs the pipeline of validators and transformations.
        """
        # 1. Null check first
        val = self.null_trans.transform(val, field_path, rules, changes_list)
        if val is None:
            return None

        # 2. Collection check (converts sets/tuples to lists)
        val = self.coll_trans.transform(val, field_path, rules, changes_list)
        if isinstance(val, (list, dict)):
            return val

        # 3. Boolean check
        val = self.bool_trans.transform(val, field_path, rules, changes_list)
        if isinstance(val, bool):
            return val

        lower_path = field_path.lower()

        # 4. Path-based type hints
        if "date" in lower_path or "timestamp" in lower_path or "time" in lower_path:
            res = self.date_trans.transform(val, field_path, rules, changes_list)
            if res != val:
                return res

        if any(term in lower_path for term in ["salary", "amount", "count", "size", "width", "height", "confidence"]):
            res = self.num_trans.transform(val, field_path, rules, changes_list)
            if res != val:
                return res

        # 5. Dynamic type detection for generic values
        if isinstance(val, str):
            # Try date parsing
            date_res = self.date_trans.transform(val, field_path, rules, changes_list)
            if date_res != val and re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_res)):
                return date_res

            # Try numeric parsing
            num_res = self.num_trans.transform(val, field_path, rules, changes_list)
            if num_res != val and isinstance(num_res, (int, float)):
                return num_res

            # Text cleaning fall-through
            val = self.text_trans.transform(val, field_path, rules, changes_list)

        return val
