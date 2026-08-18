from unittest.mock import patch
from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import Document
from .services.routing_service import IngestionRoutingService
from .router.dispatcher import ParserDispatcher, ParserNotFoundException, UnsupportedParserException
from common.parser_types import ParserType

User = get_user_model()

class IngestionUploadTests(APITestCase):
    """
    Ingestion unit test suite verifying user upload APIs, duplicate content SHA-256 blocks,
    file header signature inspections, and size/extension boundary validations.
    """
    def setUp(self):
        self.upload_url = reverse('document_upload')
        
        # Create standard user profile
        self.user = User.objects.create_user(
            username="analyst_tester",
            email="tester@enterprise.ai",
            password="securepassword123",
            role="analyst"
        )
        
        # Obtain JWT access token
        login_url = reverse('token_obtain_pair')
        login_res = self.client.post(
            login_url, 
            {"username": "analyst_tester", "password": "securepassword123"}, 
            format='json'
        )
        self.access_token = login_res.data['data']['access']

    def test_upload_requires_authentication(self):
        """
        Verify that unauthenticated upload requests are denied.
        """
        file = SimpleUploadedFile("sample.pdf", b"%PDF-1.5 header content", content_type="application/pdf")
        response = self.client.post(self.upload_url, {"file": file}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @patch('ingestion.orchestration.services.orchestration_service.IngestionOrchestrationService.process_document')
    def test_successful_pdf_upload(self, mock_process):
        """
        Verify that a valid PDF file under authenticated user session uploads successfully.
        """
        mock_process.return_value = {"success": True}
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Starts with %PDF (valid PDF magic bytes)
        file = SimpleUploadedFile("report.pdf", b"%PDF-1.5 binary content payload stream", content_type="application/pdf")
        response = self.client.post(self.upload_url, {"file": file}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['file_name'], "report.pdf")
        self.assertEqual(response.data['data']['processing_status'], "UPLOADED")
        
        # Check DB entry exists and has properties
        doc = Document.objects.get(original_name="report.pdf")
        self.assertEqual(doc.parser_type, ParserType.PDF.value)
        self.assertEqual(doc.processing_status, "UPLOADED")

    def test_spoofed_extension_signature_mismatch(self):
        """
        Verify that files spoofing extensions but having mismatching header bytes are blocked.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Spoof: extension is PDF but headers contain arbitrary plain text
        file = SimpleUploadedFile("spoof.pdf", b"plain text content lacking pdf markers", content_type="application/pdf")
        response = self.client.post(self.upload_url, {"file": file}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn("File signature mismatch", response.data['message'])

    def test_unsupported_file_extension(self):
        """
        Verify that unsupported file extensions (e.g. .exe) are blocked.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        file = SimpleUploadedFile("executable.exe", b"MZ binary execution blocks", content_type="application/octet-stream")
        response = self.client.post(self.upload_url, {"file": file}, format='multipart')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn("is not supported", response.data['message'])

    @patch('ingestion.orchestration.services.orchestration_service.IngestionOrchestrationService.process_document')
    def test_deduplication_prevents_duplicate_uploads(self, mock_process):
        """
        Verify that duplicate file contents matching identical SHA-256 hashes are blocked.
        """
        mock_process.return_value = {"success": True}
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')
        
        # Setup first file
        file1 = SimpleUploadedFile("doc1.pdf", b"%PDF-1.5 same content stream", content_type="application/pdf")
        res1 = self.client.post(self.upload_url, {"file": file1}, format='multipart')
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Upload duplicate contents (triggers deduplication block)
        file2 = SimpleUploadedFile("doc2.pdf", b"%PDF-1.5 same content stream", content_type="application/pdf")
        res2 = self.client.post(self.upload_url, {"file": file2}, format='multipart')
        
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(res2.data['success'])
        self.assertIn("same content", res2.data['message'])

    def test_routing_service_dispatches_successfully(self):
        """
        Verify that the routing service resolves the parser type and transitions state to VALIDATED.
        """
        # Manually create a document
        doc = Document.objects.create(
            uploaded_by=self.user,
            file="raw/test.pdf",
            file_hash="fakehash123",
            original_name="test.pdf",
            file_size=123,
            mime_type="application/pdf",
            parser_type=ParserType.PDF.value,
            processing_status="UPLOADED"
        )
        
        routing_service = IngestionRoutingService()
        updated_doc = routing_service.execute(doc.id)
        
        self.assertEqual(updated_doc.processing_status, "VALIDATED")

    def test_unsupported_parser_type_exception(self):
        """
        Verify that attempting to resolve an unregistered/unconfigured parser string raises UnsupportedParserException.
        """
        with self.assertRaises(UnsupportedParserException):
            ParserDispatcher.get_parser("EXE_PARSER")

    def test_parser_not_found_exception(self):
        """
        Verify that requesting an enum type absent from registry raises ParserNotFoundException.
        """
        # Patch PARSER_REGISTRY to be empty to simulate registration missing
        with patch('ingestion.router.dispatcher.PARSER_REGISTRY', {}):
            with self.assertRaises(ParserNotFoundException):
                ParserDispatcher.get_parser(ParserType.PDF)


class IngestionParserTests(TestCase):
    """
    Parser strategy unit test suite validating digital PDF extractions, Excel worksheets,
    CSV encoding fallbacks, nested JSON, plain text cleanups, and image dimensions.
    """
    def setUp(self):
        # Create temp folder for testing parser file loads
        import tempfile
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_pdf_parser_digital_text(self):
        """
        Verify that PDFParser extracts text programmatically and handles metadata structures.
        """
        import os
        import fitz
        
        # Programmatically write a tiny PDF file
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Standard digital text inside PDF page.")
        file_path = os.path.join(self.temp_dir.name, "test.pdf")
        doc.save(file_path)
        doc.close()

        from ingestion.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        result = parser.parse(file_path)

        self.assertEqual(result["parser_type"], "PDF")
        self.assertEqual(result["processing_status"], "PARSED")
        self.assertIn("Standard digital text", result["content"])
        self.assertFalse(result["metadata"]["is_scanned"])
        self.assertEqual(result["metadata"]["page_count"], 1)

    def test_pdf_parser_scanned_flag(self):
        """
        Verify that PDFs without text content are flagged as is_scanned=True.
        """
        import os
        import fitz
        
        # Create blank PDF (no text = scanned simulation)
        doc = fitz.open()
        doc.new_page()
        file_path = os.path.join(self.temp_dir.name, "scanned.pdf")
        doc.save(file_path)
        doc.close()

        from ingestion.parsers.pdf_parser import PDFParser
        parser = PDFParser()
        result = parser.parse(file_path)

        self.assertTrue(result["metadata"]["is_scanned"])

    def test_excel_parser_sheets_and_types(self):
        """
        Verify that ExcelParser extracts worksheets preserving numeric datatypes.
        """
        import os
        import pandas as pd
        
        file_path = os.path.join(self.temp_dir.name, "test.xlsx")
        df1 = pd.DataFrame({"ID": [101, 102], "Name": ["Alice", "Bob"]})
        df2 = pd.DataFrame({"Value": [9.99, 14.50]})
        
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            df1.to_excel(writer, sheet_name="Data", index=False)
            df2.to_excel(writer, sheet_name="Prices", index=False)

        from ingestion.parsers.excel_parser import ExcelParser
        parser = ExcelParser()
        result = parser.parse(file_path)

        self.assertEqual(result["parser_type"], "EXCEL")
        self.assertEqual(result["metadata"]["sheet_count"], 2)
        self.assertIn("Data", result["metadata"]["sheets"])
        self.assertEqual(result["structured_data"]["Data"][0]["Name"], "Alice")
        self.assertEqual(result["structured_data"]["Prices"][1]["Value"], 14.50)

    def test_csv_parser_and_nan_mapping(self):
        """
        Verify that CSVParser handles custom encodings and translates NaN fields to None.
        """
        import os
        import pandas as pd
        
        file_path = os.path.join(self.temp_dir.name, "test.csv")
        # Include None/NaN to verify mapping conversion
        df = pd.DataFrame({"Key": ["k1", "k2"], "Value": ["v1", None]})
        df.to_csv(file_path, index=False)

        from ingestion.parsers.csv_parser import CSVParser
        parser = CSVParser()
        result = parser.parse(file_path)

        self.assertEqual(result["parser_type"], "CSV")
        self.assertEqual(result["metadata"]["row_count"], 2)
        self.assertIsNone(result["structured_data"]["records"][1]["Value"])

    def test_json_parser_nesting_and_validation(self):
        """
        Verify that JSONParser preserves nested dictionaries and raises ValidationError on syntax errors.
        """
        import os
        import json
        from django.core.exceptions import ValidationError
        
        file_path_valid = os.path.join(self.temp_dir.name, "valid.json")
        data = {"root": {"nested": "value", "list": [1, 2]}}
        with open(file_path_valid, "w") as f:
            json.dump(data, f)

        from ingestion.parsers.json_parser import JSONParser
        parser = JSONParser()
        result = parser.parse(file_path_valid)

        self.assertEqual(result["parser_type"], "JSON")
        self.assertEqual(result["structured_data"]["root"]["nested"], "value")
        self.assertTrue(result["metadata"]["is_nested"])

        # Invalid structure
        file_path_invalid = os.path.join(self.temp_dir.name, "invalid.json")
        with open(file_path_invalid, "w") as f:
            f.write("{invalid_syntax:")
            
        with self.assertRaises(ValidationError):
            parser.parse(file_path_invalid)

    def test_text_parser_cleanup(self):
        """
        Verify that TextParser decodes files and trims whitespaces.
        """
        import os
        file_path = os.path.join(self.temp_dir.name, "test.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(" \n Content spacing test context.   ")

        from ingestion.parsers.text_parser import TextParser
        parser = TextParser()
        result = parser.parse(file_path)

        self.assertEqual(result["parser_type"], "TEXT")
        self.assertEqual(result["content"], "Content spacing test context.")

    def test_image_parser_dimensions(self):
        """
        Verify that ImageParser extracts PIL metadata without executing OCR.
        """
        import os
        from PIL import Image
        
        file_path = os.path.join(self.temp_dir.name, "test.png")
        img = Image.new('RGB', (100, 50), color='blue')
        img.save(file_path)

        from ingestion.parsers.image_parser import ImageParser
        parser = ImageParser()
        result = parser.parse(file_path)

        self.assertEqual(result["parser_type"], "IMAGE")
        self.assertEqual(result["metadata"]["width"], 100)
        self.assertEqual(result["metadata"]["height"], 50)
        self.assertEqual(result["metadata"]["color_space"], "RGB")

    def test_api_parser_mapping(self):
        """
        Verify that APIParser correctly processes stored REST payload files.
        """
        import os
        import json
        
        file_path = os.path.join(self.temp_dir.name, "api.json")
        data = {"code": 200, "payload": {"user": "analyst"}}
        with open(file_path, "w") as f:
            json.dump(data, f)

        from ingestion.parsers.api_parser import APIParser
        parser = APIParser()
        result = parser.parse(file_path)

        self.assertEqual(result["parser_type"], "API")
        self.assertEqual(result["structured_data"]["code"], 200)
        self.assertEqual(result["metadata"]["source"], "REST_API_ENDPOINT")

