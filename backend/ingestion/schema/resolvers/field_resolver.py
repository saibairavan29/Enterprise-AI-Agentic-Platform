import re
from ..rules.mapping_loader import MappingLoader

class FieldResolver:
    """
    Resolver responsible for cleaning raw field names and matching them against
    mapping rules to identify their target canonical field and resolution confidence.
    """
    def __init__(self, rules=None):
        if rules is None:
            loader = MappingLoader()
            self.rules = loader.load_rules()
        else:
            self.rules = rules
            
        # Precompute clean mapping lists for optimal dict lookup
        self.clean_mappings = {}
        for canonical, aliases in self.rules.items():
            self.clean_mappings[canonical] = [self._clean(alias) for alias in aliases]

    def resolve(self, raw_field):
        """
        Resolves a raw field name to a canonical field.
        Returns a dict: {"resolved_field": "...", "resolution_confidence": "HIGH"|"MEDIUM"|"LOW"}
        or None if no match is identified.
        """
        if not raw_field:
            return None

        clean_raw = self._clean(raw_field)

        # Explicit exclusions to prevent false positive mappings
        if clean_raw == "name":
            return None

        # 1. Check direct exact match with canonical name
        for canonical in self.clean_mappings.keys():
            if clean_raw == self._clean(canonical):
                return {
                    "resolved_field": canonical,
                    "resolution_confidence": "HIGH"
                }

        # 2. Check exact matches in alias configurations
        for canonical, clean_aliases in self.clean_mappings.items():
            if clean_raw in clean_aliases:
                return {
                    "resolved_field": canonical,
                    "resolution_confidence": "HIGH"
                }

        # 3. Check partial substring matches (abbreviations / subsets)
        for canonical, clean_aliases in self.clean_mappings.items():
            for alias in clean_aliases:
                # If raw field is a substring of the alias, or vice-versa
                if (len(clean_raw) > 2 and clean_raw in alias) or (len(alias) > 2 and alias in clean_raw):
                    # Do not match generic substring if it's not a strong link
                    if clean_raw in ["role", "type", "date", "status"]:
                        continue
                    return {
                        "resolved_field": canonical,
                        "resolution_confidence": "MEDIUM"
                    }

        # 4. Check loose starts-with or ends-with matches
        for canonical, clean_aliases in self.clean_mappings.items():
            clean_canonical = self._clean(canonical)
            if len(clean_raw) >= 4:
                # Direct starts-with/ends-with
                if clean_raw.startswith(clean_canonical) or clean_canonical.startswith(clean_raw):
                    return {
                        "resolved_field": canonical,
                        "resolution_confidence": "LOW"
                    }
                # Shares first 4 characters with canonical
                if len(clean_canonical) >= 4 and clean_raw[:4] == clean_canonical[:4]:
                    if canonical == "employee_id" and any(x in clean_raw for x in ["status", "state", "type", "count"]):
                        continue
                    return {
                        "resolved_field": canonical,
                        "resolution_confidence": "LOW"
                    }
                # Shares first 4 characters with any alias
                for alias in clean_aliases:
                    if len(alias) >= 4 and clean_raw[:4] == alias[:4]:
                        if canonical == "employee_id" and any(x in clean_raw for x in ["status", "state", "type", "count"]):
                            continue
                        return {
                            "resolved_field": canonical,
                            "resolution_confidence": "LOW"
                        }

        return None

    def _clean(self, name):
        """
        Normalizes names: converts to lowercase, strips, and removes spaces/punctuation.
        """
        if not name:
            return ""
        return re.sub(r"[^a-z0-9]", "", str(name).lower().strip())
