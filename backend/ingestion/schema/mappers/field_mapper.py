from .base import BaseMapper
from ..schemas.enterprise_schema import CANONICAL_FIELDS

class FieldMapper(BaseMapper):
    """
    Concrete mapper that maps parsed record values into generic canonical fields
    and resolves unmapped parameters into an additional_fields bucket.
    """
    def map_record(self, raw_record, resolver):
        if not isinstance(raw_record, dict):
            return {}, {}, {"duplicates": [], "conflicts": []}

        canonical_fields = dict(CANONICAL_FIELDS)
        additional_fields = {}
        
        duplicates = []
        conflicts = []
        
        # Track raw fields mapped to each canonical target to detect duplicates/conflicts
        resolved_sources = {}

        for raw_key, raw_val in raw_record.items():
            resolution = resolver.resolve(raw_key)
            
            if resolution:
                canonical_key = resolution["resolved_field"]
                
                # Check for duplicate target mappings
                if canonical_key in resolved_sources:
                    original_raw_key = resolved_sources[canonical_key]
                    duplicates.append(raw_key)
                    
                    # If the duplicate mapping attempts to write a different value, flag as conflict
                    existing_val = canonical_fields[canonical_key]
                    if existing_val != raw_val:
                        conflicts.append({
                            "canonical_field": canonical_key,
                            "attempted_key": raw_key,
                            "existing_key": original_raw_key,
                            "attempted_value": raw_val,
                            "existing_value": existing_val
                        })
                    # Route duplicate/conflicting secondary key to additional_fields to preserve data
                    additional_fields[raw_key] = raw_val
                    continue
                else:
                    resolved_sources[canonical_key] = raw_key
                
                canonical_fields[canonical_key] = raw_val
            else:
                additional_fields[raw_key] = raw_val

        mapping_metadata = {
            "duplicates": duplicates,
            "conflicts": conflicts,
            "total_raw_fields": len(raw_record),
            "mapped_count": len(resolved_sources),
            "unmapped_count": len(additional_fields)
        }

        return canonical_fields, additional_fields, mapping_metadata
