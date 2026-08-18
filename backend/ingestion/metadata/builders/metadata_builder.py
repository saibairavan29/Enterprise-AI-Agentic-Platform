class MetadataBuilder:
    """
    Builder responsible for combining individual metadata components
    into a single standardized nested metadata dictionary and calculating
    metadata quality completeness and identifying missing fields.
    """
    def build(self, file_data, doc_data, content_data, img_data, ocr_data, source_data, lineage_data, stats_data, processing_data, validation_passed=True, validation_errors=None):
        """
        Assembles all segments into the final unified metadata payload,
        then evaluates leaf parameters to compute quality metrics.
        """
        if validation_errors is None:
            validation_errors = []

        res = {
            "file": file_data,
            "document": doc_data,
            "content": content_data,
            "image": img_data,
            "ocr": ocr_data,
            "source": source_data,
            "lineage": lineage_data,
            "statistics": stats_data,
            "processing": processing_data,
            "quality": {
                "metadata_completeness": 0,
                "validation_passed": validation_passed,
                "missing_fields": [],
                "validation_errors": validation_errors
            }
        }

        self._compute_quality_metrics(res)
        return res

    def _compute_quality_metrics(self, res):
        """
        Walks the metadata leaf paths for file, document, content, image, ocr,
        source, and lineage. Computes the completeness ratio.
        """
        leaves = {}
        target_sections = ["file", "document", "content", "image", "ocr", "source", "lineage"]
        
        for sec in target_sections:
            sec_dict = res.get(sec)
            if isinstance(sec_dict, dict):
                leaves.update(self._walk_dict(sec_dict, sec))

        if not leaves:
            res["quality"]["metadata_completeness"] = 100
            return

        missing = [path for path, val in leaves.items() if val is None or val == ""]
        total = len(leaves)
        completeness = int(round(((total - len(missing)) / total) * 100))

        res["quality"]["metadata_completeness"] = completeness
        res["quality"]["missing_fields"] = sorted(missing)

    def _walk_dict(self, d, prefix):
        leaves = {}
        for k, v in d.items():
            path = f"{prefix}.{k}"
            if isinstance(v, dict):
                leaves.update(self._walk_dict(v, path))
            else:
                leaves[path] = v
        return leaves
