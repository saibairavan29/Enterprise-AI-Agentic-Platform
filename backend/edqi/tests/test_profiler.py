from django.test import TestCase
from edqi.profilers.data_profiler import DataProfiler

class DataProfilerTestCase(TestCase):
    def setUp(self):
        self.profiler = DataProfiler()
        self.sample_records = [
            {"employee_id": "1", "email": "alice@company.com", "salary": "5000", "department": "HR"},
            {"employee_id": "2", "email": "bob@company.com", "salary": "6000", "department": "Sales"},
            {"employee_id": "3", "email": "charles@company.com", "salary": "7000", "department": "Sales"},
            {"employee_id": "4", "email": None, "salary": "null", "department": "Engineering"},
            {"employee_id": "1", "email": "alice@company.com", "salary": "5000", "department": "HR"} # duplicate record
        ]

    def test_profile_statistics(self):
        stats, profiles = self.profiler.profile_records(self.sample_records)
        
        self.assertEqual(stats["total_records"], 5)
        self.assertEqual(stats["total_fields"], 4)
        self.assertTrue(stats["null_percentage"] > 0.0)
        self.assertEqual(stats["duplicate_percentage"], 20.0) # 1 duplicate out of 5 records

    def test_field_profiles(self):
        stats, profiles = self.profiler.profile_records(self.sample_records)

        # Check department types
        self.assertEqual(profiles["department"]["datatype"], "String")
        self.assertEqual(profiles["department"]["null_percentage"], 0.0)
        
        # Check salary ranges and types
        self.assertEqual(profiles["salary"]["datatype"], "Integer")
        self.assertEqual(profiles["salary"]["min_value"], 5000.0)
        self.assertEqual(profiles["salary"]["max_value"], 7000.0)
        
        # Check email nulls
        # Null values are: None (Bob's email is bob@company.com, charles@company.com, none, alice twice)
        # Email has: alice (idx 0), bob (idx 1), charles (idx 2), None (idx 3), alice (idx 4)
        # So 1 null out of 5 = 20.0%
        self.assertEqual(profiles["email"]["null_percentage"], 20.0)
