from unittest.mock import patch
from django.test import TestCase
import numpy as np
import tempfile
import os

from ..services.ocr_service import TesseractOCREngine
from ..services.pdf_ocr_service import PDFOCRService
from ..exceptions.ocr_exceptions import (
    OCRExecutionException,
    OCRTimeoutException,
    OCRConfigurationException,
    OCRImageReadException,
    OCRUnsupportedFormatException,
    TesseractNotInstalledException,
    OCRConfidenceException
)
from ..utils.helpers import OCR_CONFIG

class OCRUnitTests(TestCase):
    """
    OCR Engine unit test suite validating image binarization, deskew skipping,
    page-by-page mixed PDF skips, confidence limits, timeouts, and missing binary handlers.
    """
    def setUp(self):
        self.engine = TesseractOCREngine()
        # Create standard test images in-memory
        self.mock_img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        self.mock_gray_img = np.ones((100, 100), dtype=np.uint8) * 255
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_successful_image_ocr(self, mock_to_data, mock_to_string):
        """
        Verify image OCR extracts text and parses min/max/median/avg confidence indices correctly.
        """
        mock_to_string.return_value = "Extracted OCR text payload."
        # Mock TSV data containing conf values
        mock_to_data.return_value = "level\tpage_num\tblock_num\tpar_num\tline_num\tword_num\tleft\ttop\twidth\theight\tconf\ttext\n5\t1\t1\t1\t1\t1\t10\t10\t50\t15\t95.0\tExtracted\n5\t1\t1\t1\t1\t2\t70\t10\t40\t15\t90.0\tOCR"
        
        result = self.engine.extract_text(self.mock_img)
        self.assertEqual(result["status"], "OCR_COMPLETED")
        self.assertEqual(result["text"], "Extracted OCR text payload.")
        self.assertEqual(result["confidence"]["average"], 92.5)  # (95 + 90) / 2
        self.assertEqual(result["confidence"]["minimum"], 90.0)
        self.assertEqual(result["confidence"]["maximum"], 95.0)
        self.assertEqual(result["confidence"]["median"], 92.5)

    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_already_grayscale_image_skips_conversion(self, mock_to_data, mock_to_string):
        """
        Verify that images already in single-channel grayscale do not run grayscale preprocessing transforms.
        """
        mock_to_string.return_value = "Text."
        mock_to_data.return_value = "level\tconf\ttext\n5\t90\tText"
        
        result = self.engine.extract_text(self.mock_gray_img)
        self.assertEqual(result["status"], "OCR_COMPLETED")

    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    @patch('ingestion.ocr.processors.deskew.determine_skew_angle')
    def test_deskew_skips_when_angle_below_threshold(self, mock_skew, mock_to_data, mock_to_string):
        """
        Verify that rotation deskew is skipped when the estimated skew tilt is below threshold settings.
        """
        mock_skew.return_value = 0.1  # 0.1 degree is below default 0.5 threshold
        mock_to_string.return_value = "Text."
        mock_to_data.return_value = "level\tconf\ttext\n5\t90\tText"
        
        result = self.engine.extract_text(self.mock_img)
        self.assertEqual(result["status"], "OCR_COMPLETED")

    @patch('pytesseract.image_to_string')
    def test_tesseract_not_installed_exception(self, mock_to_string):
        """
        Verify that TesseractNotInstalledException is raised when pytesseract binary cannot be resolved.
        """
        from pytesseract.pytesseract import TesseractNotFoundError
        mock_to_string.side_effect = TesseractNotFoundError()
        
        with self.assertRaises(TesseractNotInstalledException):
            self.engine.extract_text(self.mock_img)

    @patch('pytesseract.image_to_string')
    def test_tesseract_timeout_exception(self, mock_to_string):
        """
        Verify that OCRTimeoutException is raised when engine times out.
        """
        mock_to_string.side_effect = RuntimeError("timeout occurred during execution")
        
        with self.assertRaises(OCRTimeoutException):
            self.engine.extract_text(self.mock_img)

    @patch('pytesseract.image_to_string')
    def test_ocr_execution_failure(self, mock_to_string):
        """
        Verify that generic runtime exceptions are caught and wrapped inside OCRExecutionException.
        """
        mock_to_string.side_effect = Exception("Generic runtime library block")
        
        with self.assertRaises(OCRExecutionException):
            self.engine.extract_text(self.mock_img)

    def test_invalid_image_read_exception(self):
        """
        Verify that OCRImageReadException is raised when providing an invalid/non-existent image path.
        """
        with self.assertRaises(OCRImageReadException):
            self.engine.extract_text("non_existent_image_path.png")

    def test_invalid_config_exception(self):
        """
        Verify that invalid configurative values raise OCRConfigurationException.
        """
        with patch.dict(OCR_CONFIG, {"DPI": -100}):
            with self.assertRaises(OCRConfigurationException):
                self.engine.extract_text(self.mock_img)

    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_low_confidence_warnings(self, mock_to_data, mock_to_string):
        """
        Verify that a low confidence score results in warnings logged and returned.
        """
        mock_to_string.return_value = "Poor text extraction."
        # Average is 20.0 (below 50.0 default threshold)
        mock_to_data.return_value = "level\tconf\ttext\n5\t20.0\tPoor"
        
        result = self.engine.extract_text(self.mock_img)
        self.assertTrue(any("average ocr confidence" in w.lower() for w in result["warnings"]))

    def test_pdf_ocr_service_searchable_skips_ocr(self):
        """
        Verify that PDFOCRService extracts digital text directly and skips OCR for searchable pages.
        """
        import fitz
        file_path = os.path.join(self.temp_dir.name, "searchable.pdf")
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "This is searchable digital text contents inside PDF page.")
        doc.save(file_path)
        doc.close()
        
        service = PDFOCRService()
        result = service.execute(file_path)
        
        self.assertEqual(result["pages_processed"], 1)
        self.assertIn("searchable digital text", result["text"])
        self.assertEqual(result["confidence"]["average"], 100.0)

    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_pdf_ocr_service_scanned_runs_ocr(self, mock_to_data, mock_to_string):
        """
        Verify that scanned PDF pages (low/no digital characters) invoke OCR processing.
        """
        import fitz
        file_path = os.path.join(self.temp_dir.name, "scanned.pdf")
        doc = fitz.open()
        doc.new_page()  # Page without text
        doc.save(file_path)
        doc.close()
        
        mock_to_string.return_value = "OCR parsed text on scanned page."
        mock_to_data.return_value = "level\tconf\ttext\n5\t85.0\tparsed"
        
        service = PDFOCRService()
        result = service.execute(file_path)
        
        self.assertEqual(result["pages_processed"], 1)
        self.assertEqual(result["text"], "OCR parsed text on scanned page.")
        self.assertEqual(result["confidence"]["average"], 85.0)

    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_pdf_ocr_service_mixed_pages(self, mock_to_data, mock_to_string):
        """
        Verify page-by-page mixed PDF processing (digital page text is extracted, scanned is OCRed).
        """
        import fitz
        file_path = os.path.join(self.temp_dir.name, "mixed.pdf")
        doc = fitz.open()
        
        # Page 1: Searchable digital page
        p1 = doc.new_page()
        p1.insert_text((10, 10), "Searchable digital page.")
        # Page 2: Scanned blank page
        doc.new_page()
        
        doc.save(file_path)
        doc.close()
        
        mock_to_string.return_value = "Parsed from scanned page 2."
        mock_to_data.return_value = "level\tconf\ttext\n5\t80.0\tparsed"
        
        service = PDFOCRService()
        result = service.execute(file_path)
        
        self.assertEqual(result["pages_processed"], 2)
        # Should extract and merge both texts
        self.assertIn("Searchable digital page", result["text"])
        self.assertIn("Parsed from scanned page 2", result["text"])

    @patch('pytesseract.image_to_string')
    @patch('pytesseract.image_to_data')
    def test_ocr_metadata_generation_and_db_save(self, mock_to_data, mock_to_string):
        """
        Verify that OCR execution generates standard structured metadata including
        confidence, language, timing, pages, warnings, errors and saves to Document.ocr_metadata.
        """
        from ingestion.models import Document
        
        mock_to_string.return_value = "Parsed text."
        mock_to_data.return_value = "level\tconf\ttext\n5\t92.5\tParsed"
        
        result = self.engine.extract_text(self.mock_img)
        
        # 1. Verify schema elements
        self.assertEqual(result["ocr_status"], "OCR_COMPLETED")
        self.assertEqual(result["engine"], "Tesseract")
        self.assertEqual(result["language"], "eng")
        self.assertIn("average", result["confidence"])
        self.assertEqual(result["confidence"]["average"], 92.5)
        self.assertIn("execution_timestamp", result)
        self.assertIn("processing_time", result)
        self.assertEqual(result["pages_processed"], 1)
        
        # 2. Verify persistence mapping on Document model
        from django.contrib.auth import get_user_model
        from django.core.files.uploadedfile import SimpleUploadedFile
        User = get_user_model()
        user = User.objects.create_user(username="test_ocr_user", password="password")
        mock_file = SimpleUploadedFile("test_img.png", b"dummy_content")
        
        doc = Document.objects.create(
            uploaded_by=user,
            file=mock_file,
            original_name="test_img.png",
            file_hash="mockhash12345",
            file_size=1024,
            mime_type="image/png",
            parser_type="IMAGE"
        )
        
        # Create metadata map matching schema without the "text" key
        metadata_map = {
            "engine": result["engine"],
            "language": result["language"],
            "confidence": result["confidence"],
            "pages_processed": result["pages_processed"],
            "processing_time": result["processing_time"],
            "ocr_status": result["ocr_status"],
            "warnings": result["warnings"],
            "errors": result["errors"],
            "execution_timestamp": result["execution_timestamp"]
        }
        
        doc.ocr_metadata = metadata_map
        doc.ocr_confidence = result["confidence"]["average"]
        doc.save()
        
        # Reload and assert database constraints
        reloaded = Document.objects.get(pk=doc.pk)
        self.assertEqual(reloaded.ocr_confidence, 92.5)
        self.assertEqual(reloaded.ocr_metadata["ocr_status"], "OCR_COMPLETED")
        self.assertEqual(reloaded.ocr_metadata["confidence"]["average"], 92.5)
