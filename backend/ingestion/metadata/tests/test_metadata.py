from django.test import TestCase
from django.utils import timezone
from unittest.mock import MagicMock

from ..services.metadata_service import MetadataOrchestrationService
from ..builders import MetadataBuilder
from ..validators import MetadataValidator
from ..exceptions.metadata_exceptions import MetadataValidationException, MetadataExtractionException
from ..extractors import (
    FileExtractor,
    PDFExtractor,
    ExcelExtractor,
    CSVExtractor,
    TextExtractor,
    ImageExtractor,
    OCRExtractor,
    SourceExtractor,
    LineageExtractor
)

class MetadataUnitTests(TestCase):
    """
    Unit tests for checking individual extractors, standard schema builders,
    validation logic boundaries, and full orchestrator service runs.
    """
    def setUp(self):
        self.service = MetadataOrchestrationService()
        self.doc_mock = {
            "id": 1,
            "document_id": "1",
            "original_name": "quarterly_financials.pdf",
            "stored_name": "raw/quarterly_financials.pdf",
            "file_size": 2048576,
            "file_hash": "a" * 64,  # Valid SHA-256 formatting
            "mime_type": "application/pdf",
            "uploaded_by": "1",
            "created_at": timezone.now().isoformat()
        }

    def test_file_extractor(self):
        """
        Verify that file properties are extracted cleanly.
        """
        extractor = FileExtractor()
        res = extractor.extract(self.doc_mock, {})
        self.assertEqual(res["original_name"], "quarterly_financials.pdf")
        self.assertEqual(res["size"], 2048576)
        self.assertEqual(res["extension"], "pdf")
        self.assertEqual(res["hash"], "a" * 64)

    def test_pdf_extractor(self):
        """
        Verify that PDF properties are resolved.
        """
        extractor = PDFExtractor()
        parser_output = {
            "parser_type": "PDF",
            "metadata": {
                "title": "Quarterly Financials",
                "author": "CEO Office",
                "page_count": 5,
                "pdf_version": "1.7"
            }
        }
        res = extractor.extract(self.doc_mock, parser_output)
        self.assertEqual(res["title"], "Quarterly Financials")
        self.assertEqual(res["author"], "CEO Office")
        self.assertEqual(res["page_count"], 5)
        self.assertEqual(res["version"], "1.7")

    def test_excel_extractor(self):
        """
        Verify that Excel sheets and dimensions compile.
        """
        extractor = ExcelExtractor()
        parser_output = {
            "parser_type": "EXCEL",
            "metadata": {
                "sheets": ["Sheet1", "Sheet2"],
                "sheet_count": 2
            },
            "structured_data": {
                "Sheet1": [{"col1": "val1"}, {"col1": "val2"}],
                "Sheet2": [{"col1": "val3"}]
            }
        }
        res = extractor.extract(self.doc_mock, parser_output)
        self.assertEqual(res["worksheet_count"], 2)
        self.assertEqual(res["sheet_names"], ["Sheet1", "Sheet2"])
        self.assertEqual(res["row_count"], 3)
        self.assertEqual(res["column_count"], 1)

    def test_csv_extractor(self):
        """
        Verify that CSV row/col totals are counted.
        """
        extractor = CSVExtractor()
        parser_output = {
            "parser_type": "CSV",
            "structured_data": {
                "records": [
                    {"Name": "Alice", "Role": "Admin"},
                    {"Name": "Bob", "Role": "User"}
                ]
            }
        }
        res = extractor.extract(self.doc_mock, parser_output)
        self.assertEqual(res["row_count"], 2)
        self.assertEqual(res["column_count"], 2)

    def test_text_extractor(self):
        """
        Verify that character and word counts match.
        """
        extractor = TextExtractor()
        parser_output = {
            "parser_type": "TEXT",
            "content": "This is raw extracted text from document parser.",
            "metadata": {"encoding": "utf-8"}
        }
        res = extractor.extract(self.doc_mock, parser_output)
        self.assertEqual(res["character_count"], len(parser_output["content"]))
        self.assertEqual(res["word_count"], 8)
        self.assertEqual(res["encoding"], "utf-8")

    def test_image_extractor(self):
        """
        Verify that Pillow image width, height, DPI, and modes are extracted.
        """
        extractor = ImageExtractor()
        parser_output = {
            "parser_type": "IMAGE",
            "metadata": {
                "width": 1920,
                "height": 1080,
                "color_space": "RGB",
                "dpi_horizontal": 300,
                "dpi_vertical": 300
            }
        }
        res = extractor.extract(self.doc_mock, parser_output)
        self.assertEqual(res["width"], 1920)
        self.assertEqual(res["height"], 1080)
        self.assertEqual(res["color_mode"], "RGB")
        self.assertEqual(res["dpi"], "300x300")

    def test_ocr_extractor(self):
        """
        Verify OCR metadata parser conversion.
        """
        extractor = OCRExtractor()
        ocr_mock = {
            "engine": "Tesseract",
            "language": "eng",
            "confidence": {"average": 88.5, "minimum": 70.0, "maximum": 95.0, "median": 89.0},
            "pages_processed": 1,
            "processing_time": 0.12,
            "ocr_status": "OCR_COMPLETED",
            "warnings": [],
            "errors": [],
            "execution_timestamp": timezone.now().isoformat()
        }
        res = extractor.extract(self.doc_mock, {}, ocr_mock)
        self.assertEqual(res["engine"], "Tesseract")
        self.assertEqual(res["confidence"]["average"], 88.5)
        self.assertEqual(res["ocr_status"], "OCR_COMPLETED")

    def test_metadata_validator_raises_on_invalid_hash(self):
        """
        Verify that MetadataValidator raises MetadataValidationException on corrupted hash inputs.
        """
        validator = MetadataValidator()
        corrupted_meta = {
            "file": {
                "original_name": "quarterly.pdf",
                "stored_name": "raw/quarterly.pdf",
                "size": 1024,
                "hash": "invalid_hash_string"
            },
            "lineage": {"document_id": "1"},
            "processing": {
                "metadata_version": "1.0",
                "schema_version": "1.0",
                "extraction_timestamp": timezone.now().isoformat()
            },
            "statistics": {
                "total_pages": 1,
                "total_tables": 0,
                "total_images": 0,
                "total_words": 10,
                "total_characters": 50
            },
            "quality": {
                "metadata_completeness": 90,
                "validation_passed": True,
                "missing_fields": [],
                "validation_errors": []
            }
        }
        with self.assertRaises(MetadataValidationException):
            validator.validate(corrupted_meta)

    def test_metadata_validator_raises_on_invalid_confidence(self):
        """
        Verify that MetadataValidator raises MetadataValidationException on confidence percentage out of range.
        """
        validator = MetadataValidator()
        corrupted_meta = {
            "file": {
                "original_name": "quarterly.pdf",
                "stored_name": "raw/quarterly.pdf",
                "size": 1024,
                "hash": "a" * 64
            },
            "lineage": {"document_id": "1"},
            "ocr": {
                "confidence": {"average": 150.0}  # Must be between 0.0 and 100.0
            },
            "processing": {
                "metadata_version": "1.0",
                "schema_version": "1.0",
                "extraction_timestamp": timezone.now().isoformat()
            },
            "statistics": {
                "total_pages": 1,
                "total_tables": 0,
                "total_images": 0,
                "total_words": 10,
                "total_characters": 50
            },
            "quality": {
                "metadata_completeness": 90,
                "validation_passed": True,
                "missing_fields": [],
                "validation_errors": []
            }
        }
        with self.assertRaises(MetadataValidationException):
            validator.validate(corrupted_meta)

    def test_full_orchestration_service_flow(self):
        """
        Verify the integrated metadata service execution loop builds nested documents successfully.
        """
        parser_output = {
            "parser_type": "PDF",
            "content": "CEO Report",
            "metadata": {
                "title": "Quarterly Financials",
                "author": "CEO Office",
                "page_count": 1,
                "pdf_version": "1.5"
            }
        }
        ocr_output = {
            "engine": "Tesseract",
            "language": "eng",
            "confidence": {"average": 91.5, "minimum": 75.0, "maximum": 99.0, "median": 92.0},
            "pages_processed": 1,
            "processing_time": 0.05,
            "ocr_status": "OCR_COMPLETED",
            "warnings": [],
            "errors": [],
            "execution_timestamp": timezone.now().isoformat()
        }
        
        result = self.service.extract(self.doc_mock, parser_output, ocr_output)
        
        self.assertEqual(result["file"]["original_name"], "quarterly_financials.pdf")
        self.assertEqual(result["document"]["title"], "Quarterly Financials")
        self.assertEqual(result["document"]["author"], "CEO Office")
        self.assertEqual(result["ocr"]["confidence"]["average"], 91.5)
        self.assertEqual(result["source"]["source_type"], "UPLOAD")
        self.assertEqual(result["lineage"]["document_id"], "1")
        self.assertEqual(result["processing"]["parser_type"], "PDF")
        self.assertEqual(result["statistics"]["total_pages"], 1)
        self.assertTrue(result["quality"]["validation_passed"])
        self.assertGreaterEqual(result["quality"]["metadata_completeness"], 50)
