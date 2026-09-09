import time
import logging
from django.utils import timezone

from ..rules.mapping_loader import MappingLoader
from ..resolvers.field_resolver import FieldResolver
from ..mappers.field_mapper import FieldMapper
from ..builders.schema_builder import SchemaBuilder
from ..validators.schema_validator import SchemaValidator
from ..response.builder import ResponseBuilder
from ..exceptions.schema_exceptions import SchemaMappingException, SchemaValidationException

logger = logging.getLogger('enterprise')

class EnterpriseSchemaMappingService:
    """
    Orchestration service coordinating canonical schema resolution,
    field validations, and final analytics wrapper compile steps.
    """
    def __init__(self):
        self.loader = MappingLoader()
        self.rules = self.loader.load_rules()
        self.resolver = FieldResolver(self.rules)
        
        self.mapper = FieldMapper()
        self.schema_builder = SchemaBuilder()
        self.validator = SchemaValidator()
        self.response_builder = ResponseBuilder()

    def map_schema(self, parsed_content, enterprise_metadata):
        """
        Converts parsed inputs and metadata parameters into canonical records lists.
        Does not save to database.
        """
        start_time = time.perf_counter()
        logger.info("Schema mapping service execution started.")

        try:
            # 1. Resolve document metadata parameters
            doc_id = None
            if enterprise_metadata:
                lineage = enterprise_metadata.get("lineage", {})
                doc_id = lineage.get("document_id")
                
            if not doc_id and enterprise_metadata:
                doc_id = enterprise_metadata.get("file", {}).get("stored_name", "unknown")

            entity_type = "generic"
            if enterprise_metadata:
                parser_type = enterprise_metadata.get("processing", {}).get("parser_type")
                if parser_type:
                    entity_type = parser_type.lower()

            # 2. Extract records list from parsed content structure shape
            raw_records = []
            
            if isinstance(parsed_content, list):
                raw_records = parsed_content
            elif isinstance(parsed_content, dict):
                structured_data = parsed_content.get("structured_data", {})
                if isinstance(structured_data, list):
                    raw_records = structured_data
                elif isinstance(structured_data, dict):
                    if parsed_content.get("parser_type") == "EXCEL":
                        for sheet_name, sheet_records in structured_data.items():
                            if isinstance(sheet_records, list):
                                raw_records.extend(sheet_records)
                    else:
                        records = structured_data.get("records")
                        data_val = structured_data.get("data")
                        if isinstance(records, list):
                            raw_records = records
                        elif isinstance(data_val, list):
                            raw_records = data_val
                        elif isinstance(data_val, dict):
                            raw_records = [data_val]
                        elif isinstance(records, dict):
                            raw_records = [records]
                        else:
                            raw_records = [structured_data]
                
                if not raw_records and "content" in parsed_content:
                    content_val = parsed_content.get("content")
                    if isinstance(content_val, dict):
                        raw_records = [content_val]
                    elif isinstance(content_val, list):
                        raw_records = content_val
                    elif isinstance(structured_data, list):
                        raw_records = structured_data
                    else:
                        raw_records = [{"raw_text": parsed_content.get("content")}]
            else:
                raw_records = [{"raw_text": str(parsed_content)}]

            if not raw_records:
                raw_records = [{}]

            # 3. Process records loop
            mapped_records = []
            aggregated_metadata = {
                "total_raw_fields": 0,
                "mapped_count": 0,
                "unmapped_count": 0,
                "duplicates": [],
                "conflicts": []
            }

            for raw_record in raw_records:
                canon, additional, meta = self.mapper.map_record(raw_record, self.resolver)
                
                canon_record = self.schema_builder.build_record(
                    document_id=doc_id,
                    entity_type=entity_type,
                    canonical_fields=canon,
                    additional_fields=additional,
                    metadata=meta
                )

                # Validate record
                self.validator.validate(canon_record, meta)
                
                mapped_records.append(canon_record)

                # Aggregate metrics
                aggregated_metadata["total_raw_fields"] += meta.get("total_raw_fields", 0)
                aggregated_metadata["mapped_count"] += meta.get("mapped_count", 0)
                aggregated_metadata["unmapped_count"] += meta.get("unmapped_count", 0)
                aggregated_metadata["duplicates"].extend(meta.get("duplicates", []))
                aggregated_metadata["conflicts"].extend(meta.get("conflicts", []))

            # 4. Compile final analytics wrapper
            execution_time = round(time.perf_counter() - start_time, 4)
            result = self.response_builder.build(
                mapped_records=mapped_records,
                metadata=aggregated_metadata,
                execution_time=execution_time,
                doc_id=doc_id,
                entity_type=entity_type
            )

            logger.info(
                f"CANONICAL_SCHEMA_MAPPED | Document ID: {doc_id} | Parser Type: {entity_type.upper()} | "
                f"Records Mapped: {len(mapped_records)} | Accuracy: {result['analytics_summary']['mapping_accuracy_percent']}% | "
                f"Time: {execution_time}s | Warnings: {len(result['analytics_summary']['warnings'])}"
            )

            return result

        except SchemaValidationException as sve:
            logger.warning(f"Schema mapping validation failed: {str(sve)}")
            raise sve
        except Exception as e:
            logger.error(f"Failed mapping canonical schema: {str(e)}", exc_info=True)
            raise SchemaMappingException(f"Schema mapping failed: {str(e)}")
