import copy
from django.test import TestCase
from django.utils import timezone
from ..services.standardization_service import EnterpriseDataStandardizationService
from ..exceptions.standardization_exceptions import StandardizationValidationException, StandardizationException

class EnterpriseDataStandardizationTests(TestCase):
    """
    Unit tests evaluating date formats conversions, casing trims,
    boolean maps, recursive collection crawls, change statistics logs, and validation bounds.
    """
    def setUp(self):
        self.service = EnterpriseDataStandardizationService()
        self.canonical_wrapper_mock = {
            "records": [
                {
                    "document_id": "123",
                    "entity_type": "generic",
                    "canonical_fields": {
                        "employee_id": "EMP001",
                        "department": " hr ",          # Upper case + trim
                        "phone_number": "1234567890",
                        "email": "EMP@COMPANY.COM",     # Lower case
                        "joining_date": "01/01/2026",   # ISO convert
                        "salary": "$5,000.50"           # Numeric float convert
                    },
                    "relationships": {},
                    "additional_fields": {
                        "address": {
                            "city": " Chennai ",        # Recursive dict walk trim
                            "zip": 600001
                        },
                        "skills": ("Python", "Django"), # Tuple -> List
                        "is_active": "Yes"              # Boolean -> True
                    }
                }
            ],
            "mapping_statistics": {
                "total_fields": 9,
                "mapped_fields": 6,
                "unmapped_fields": 3,
                "mapping_accuracy": 66.7
            },
            "schema_information": {
                "schema_version": "1.0",
                "canonical_schema_version": "1.0"
            },
            "metadata": {
                "lineage": {
                    "document_id": "123",
                    "processing_stage": "CANONICAL_SCHEMA_MAPPED"
                }
            }
        }

    def test_full_standardization_flow(self):
        """
        Verify that fields are converted correctly and that statistics logs map updates.
        """
        res = self.service.standardize(self.canonical_wrapper_mock)
        
        std_rec = res["standardized_record"]
        self.assertEqual(std_rec["canonical_fields"]["department"], "HR")
        self.assertEqual(std_rec["canonical_fields"]["email"], "emp@company.com")
        self.assertEqual(std_rec["canonical_fields"]["joining_date"], "2026-01-01")
        self.assertEqual(std_rec["canonical_fields"]["salary"], 5000.5)

        # Check nested structures
        self.assertEqual(std_rec["additional_fields"]["address"]["city"], "Chennai")
        self.assertEqual(std_rec["additional_fields"]["skills"], ["Python", "Django"])
        self.assertEqual(std_rec["additional_fields"]["is_active"], True)

        # Verify Report
        report = res["standardization_report"]
        self.assertGreater(report["fields_standardized"], 0)
        self.assertEqual(report["fields_processed"], 9)
        self.assertEqual(res["metadata"]["lineage"]["processing_stage"], "STANDARDIZED")

        # Verify change log entries
        changes = [c["field"] for c in report["field_changes"]]
        self.assertIn("joining_date", changes)
        self.assertIn("department", changes)

    def test_immutability(self):
        """
        Verify that the input record dictionary is not mutated.
        """
        self.service.standardize(self.canonical_wrapper_mock)
        
        self.assertEqual(self.canonical_wrapper_mock["records"][0]["canonical_fields"]["department"], " hr ")
        self.assertEqual(self.canonical_wrapper_mock["records"][0]["additional_fields"]["address"]["city"], " Chennai ")

    def test_validator_fails_on_invalid_date(self):
        """
        Verify that validator raises validation exception on bad date formats.
        """
        invalid_wrapper = copy.deepcopy(self.canonical_wrapper_mock)
        invalid_wrapper["records"][0]["canonical_fields"]["joining_date"] = "not-a-date"
        
        with self.assertRaises(StandardizationValidationException):
            self.service.standardize(invalid_wrapper)

    def test_validator_fails_on_negative_salary(self):
        """
        Verify that validator raises validation exception on negative salary values.
        """
        invalid_wrapper = copy.deepcopy(self.canonical_wrapper_mock)
        invalid_wrapper["records"][0]["canonical_fields"]["salary"] = "-100.00"
        
        with self.assertRaises(StandardizationValidationException):
            self.service.standardize(invalid_wrapper)
