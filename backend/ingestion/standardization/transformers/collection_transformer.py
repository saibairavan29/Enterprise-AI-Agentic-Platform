from .base import BaseTransformer

class CollectionTransformer(BaseTransformer):
    """
    Transformer responsible for collection normalizations:
    Converts sets or tuples into standard, JSON-compatible lists.
    """
    def transform(self, val, field_name, rules, changes_list):
        if val is None:
            return None

        original = val
        if isinstance(val, (set, tuple)):
            standardized = list(val)
            changes_list.append({
                "field": field_name,
                "original": str(original),
                "standardized": str(standardized),
                "rule": "COLLECTION_NORMALIZE"
            })
            return standardized

        return val
PostgresCollectionTransformer = CollectionTransformer
