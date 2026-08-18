from django.test import TestCase
from django.utils import timezone
from ..services.schema_service import EnterpriseSchemaMappingService
from ..resolvers.field_resolver import FieldResolver
from ..exceptions.schema_exceptions import SchemaValidationException, SchemaMappingException
from ..rules.mapping_loader import MappingLoader
from ..validators.schema_validator import SchemaValidator

class EnterpriseSchemaMappingTests(TestCase):
    """
    Unit tests for evaluating key resolving, loaders, schema mapping,
    response wraps, conflict boundaries, and mapping accuracy statistics.
    """
    def setUp(self):
        self.service = EnterpriseSchemaMappingService()
        self.metadata_mock = {
            "file": {
                "original_name": "quarterly_financials.pdf",
                "stored_name": "raw/quarterly_financials.pdf",
                "size": 2048576,
                "hash": "a" * 64
            },
            "lineage": {
                "document_id": "123",
                "parser": "PDFParser"
            },
            "processing": {
                "parser_type": "PDF",
                "metadata_version": "1.0",
                "schema_version": "1.0",
                "extraction_timestamp": timezone.now().isoformat()
            }
        }

    def test_rule_loader(self):
        """
        Verify that mapping rules load correctly from mapping_rules.json file.
        """
        loader = MappingLoader()
        rules = loader.load_rules()
        self.assertIn("employee_id", rules)
        self.assertIn("salary", rules)
        self.assertIsInstance(rules["employee_id"], list)

    def test_field_resolver_confidence_levels(self):
        """
        Verify resolver accuracy assignments: HIGH, MEDIUM, and LOW confidence tags.
        """
        # Exact alias match -> HIGH
        res_exact = self.service.resolver.resolve("Employee_ID")
        self.assertEqual(res_exact["resolved_field"], "employee_id")
        self.assertEqual(res_exact["resolution_confidence"], "HIGH")

        # Substring/partial match -> MEDIUM
        res_med = self.service.resolver.resolve("join_date_info")
        self.assertEqual(res_med["resolved_field"], "joining_date")
        self.assertEqual(res_med["resolution_confidence"], "MEDIUM")

        # Starts with match -> LOW
        res_low = self.service.resolver.resolve("sala_bonus")
        self.assertEqual(res_low["resolved_field"], "salary")
        self.assertEqual(res_low["resolution_confidence"], "LOW")

        # No match found -> None
        res_none = self.service.resolver.resolve("completely_unrelated_custom_field")
        self.assertIsNone(res_none)

    def test_mapping_statistics_and_additional_fields(self):
        """
        Verify mapped count, accuracy calculations, and additional_fields captures.
        """
        parsed_content = [
            {
                "Emp_ID": "EMP001",
                "Department Name": "HR",
                "salary": 6000.0,
                "ProjectXYZ": "ABC001"  # Unmapped
            }
        ]
        
        result = self.service.map_schema(parsed_content, self.metadata_mock)
        
        self.assertEqual(len(result["records"]), 1)
        record = result["records"][0]
        self.assertEqual(record["canonical_fields"]["employee_id"], "EMP001")
        self.assertEqual(record["canonical_fields"]["department"], "HR")
        self.assertEqual(record["additional_fields"]["ProjectXYZ"], "ABC001")

        # Evaluate Statistics
        stats = result["mapping_statistics"]
        self.assertEqual(stats["total_fields"], 4)
        self.assertEqual(stats["mapped_fields"], 3)
        self.assertEqual(stats["unmapped_fields"], 1)
        self.assertEqual(stats["mapping_accuracy"], 75.0)

    def test_schema_versioning(self):
        """
        Verify version payload headers.
        """
        result = self.service.map_schema([{"Emp_ID": "E1"}], self.metadata_mock)
        self.assertEqual(result["schema_information"]["schema_version"], "1.0")
        self.assertEqual(result["schema_information"]["canonical_schema_version"], "1.0")

    def test_schema_validation_raises_on_value_conflict(self):
        """
        Verify that SchemaValidator raises exception when different values attempt to write to employee_id.
        """
        parsed_content = [
            {
                "Emp_ID": "EMP001",
                "employee id": "EMP002"
            }
        ]
        with self.assertRaises(SchemaValidationException):
            self.service.map_schema(parsed_content, self.metadata_mock)
