from repository.repositories.record_repository import RecordRepository
from common.json_utils import sanitize_json_obj

class VersionDiffStage:
    """
    Stage 4: Compare old records and new records to classify added, modified, 
    and removed records and logs a change summary dictionary.
    """
    def __init__(self):
        self.record_repo = RecordRepository()

    def execute(self, context):
        existing_doc = context.get('existing_doc')
        new_records = context.get('records', [])
        
        change_summary = {
            "added_count": len(new_records),
            "removed_count": 0,
            "modified_count": 0,
            "added_sample": new_records[:5],
            "removed_sample": [],
            "modified_sample": []
        }
        
        if existing_doc:
            # List existing records canonical data
            old_records_qs = self.record_repo.list_by_document(existing_doc.id)
            old_records = [r.canonical_data for r in old_records_qs]
            
            # Run comparison engine
            change_summary = sanitize_json_obj(self._calculate_diff(old_records, new_records))
            
            # Update the snapshot created in Stage 3
            snapshot = context.get('version_snapshot')
            if snapshot:
                snapshot.change_summary = change_summary
                snapshot.save()

        context['change_summary'] = change_summary
        return context

    def _calculate_diff(self, old_records, new_records):
        # Try search for matching unique primary keys in records
        common_keys = ['employee_id', 'email', 'id', 'name', 'doj']
        key_to_compare = None
        
        if old_records and new_records:
            for candidate_key in common_keys:
                if all(candidate_key in r for r in old_records) and all(candidate_key in r for r in new_records):
                    key_to_compare = candidate_key
                    break

        added = []
        removed = []
        modified = []

        if key_to_compare:
            old_map = {str(r.get(key_to_compare)): r for r in old_records}
            new_map = {str(r.get(key_to_compare)): r for r in new_records}

            for k, v in new_map.items():
                if k not in old_map:
                    added.append(v)
                elif old_map[k] != v:
                    modified.append({
                        "key_field": key_to_compare,
                        "key_value": k,
                        "before": old_map[k],
                        "after": v
                    })

            for k, v in old_map.items():
                if k not in new_map:
                    removed.append(v)
        else:
            # Hashable tuple set fallback
            def make_hashable(d):
                return tuple(sorted((x, str(y)) for x, y in d.items()))

            old_hashed = {make_hashable(r): r for r in old_records}
            new_hashed = {make_hashable(r): r for r in new_records}

            for h, r in new_hashed.items():
                if h not in old_hashed:
                    added.append(r)
            for h, r in old_hashed.items():
                if h not in new_hashed:
                    removed.append(r)

        return {
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
            "added_sample": added[:5],
            "removed_sample": removed[:5],
            "modified_sample": modified[:5]
        }
