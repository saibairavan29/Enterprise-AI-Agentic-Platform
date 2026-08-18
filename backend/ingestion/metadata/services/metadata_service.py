import logging
from django.utils import timezone
import time

from ..exceptions.metadata_exceptions import MetadataExtractionException, MetadataValidationException
from ..extractors import (
    FileExtractor,
    PDFExtractor,
    ExcelExtractor,
    CSVExtractor,
    TextExtractor,
    ImageExtractor,
    OCRExtractor,
    SourceExtractor,
    LineageExtractor,
    StatisticsExtractor
)
from ..builders import MetadataBuilder
from ..validators import MetadataValidator

logger = logging.getLogger('enterprise')

class MetadataOrchestrationService:
    """
    Orchestrates the metadata extraction lifecycle.
    Triggers extractors, builds standard payloads, validates, and records logs.
    """
    def __init__(self):
        self.file_extractor = FileExtractor()
        self.pdf_extractor = PDFExtractor()
        self.excel_extractor = ExcelExtractor()
        self.csv_extractor = CSVExtractor()
        self.text_extractor = TextExtractor()
        self.image_extractor = ImageExtractor()
        self.ocr_extractor = OCRExtractor()
        self.source_extractor = SourceExtractor()
        self.lineage_extractor = LineageExtractor()
        self.statistics_extractor = StatisticsExtractor()

        self.builder = MetadataBuilder()
        self.validator = MetadataValidator()

    def extract(self, doc_obj, parser_output, ocr_output=None):
        logger.info("Metadata extraction process started.")
        start_time = time.perf_counter()
        warnings = []
        errors = []

        try:
            # 1. Run extractors independently
            file_data = self.file_extractor.extract(doc_obj, parser_output, ocr_output)
            pdf_data = self.pdf_extractor.extract(doc_obj, parser_output, ocr_output)
            excel_data = self.excel_extractor.extract(doc_obj, parser_output, ocr_output)
            csv_data = self.csv_extractor.extract(doc_obj, parser_output, ocr_output)
            text_data = self.text_extractor.extract(doc_obj, parser_output, ocr_output)
            img_data = self.image_extractor.extract(doc_obj, parser_output, ocr_output)
            ocr_data = self.ocr_extractor.extract(doc_obj, parser_output, ocr_output)
            source_data = self.source_extractor.extract(doc_obj, parser_output, ocr_output)
            lineage_data = self.lineage_extractor.extract(doc_obj, parser_output, ocr_output)
            stats_data = self.statistics_extractor.extract(doc_obj, parser_output, ocr_output)

            parser_type = parser_output.get("parser_type", "TEXT") if parser_output else "TEXT"

            # Propagate values or warnings from outputs
            if parser_output and parser_output.get("warnings"):
                warnings.extend(parser_output.get("warnings"))
            if ocr_output and ocr_output.get("warnings"):
                warnings.extend(ocr_output.get("warnings"))

            # 2. Build processing metrics segment
            elapsed = round(time.perf_counter() - start_time, 4)
            processing_data = {
                "parser_type": parser_type,
                "processing_time": elapsed,
                "metadata_version": "1.0",
                "schema_version": "1.0",
                "extraction_timestamp": timezone.now().isoformat(),
                "warnings": warnings,
                "errors": errors,
                "status": "METADATA_EXTRACTED"
            }

            # Merge document structural fields
            document_data = self._merge_doc_fields(pdf_data, excel_data, csv_data)

            # 3. Assembling via the builder
            metadata_obj = self.builder.build(
                file_data=file_data,
                doc_data=document_data,
                content_data=text_data,
                img_data=img_data,
                ocr_data=ocr_data,
                source_data=source_data,
                lineage_data=lineage_data,
                stats_data=stats_data,
                processing_data=processing_data,
                validation_passed=True,
                validation_errors=[]
            )

            # 4. Perform validations
            try:
                self.validator.validate(metadata_obj)
            except MetadataValidationException as mve:
                # Re-build to save validation errors in quality section
                metadata_obj = self.builder.build(
                    file_data=file_data,
                    doc_data=document_data,
                    content_data=text_data,
                    img_data=img_data,
                    ocr_data=ocr_data,
                    source_data=source_data,
                    lineage_data=lineage_data,
                    stats_data=stats_data,
                    processing_data=processing_data,
                    validation_passed=False,
                    validation_errors=[str(mve)]
                )
                raise mve

            # 5. Emit structured logging trace (never logs document raw content)
            doc_id = lineage_data.get("document_id") or "New"
            logger.info(
                f"METADATA_EXTRACTED | Document ID: {doc_id} | "
                f"Parser Type: {parser_type} | "
                f"Metadata Version: {processing_data['metadata_version']} | "
                f"Time: {elapsed}s | "
                f"Warnings: {len(warnings)} | "
                f"Errors: {len(errors)}"
            )

            return metadata_obj

        except MetadataValidationException as mve:
            # Re-raise validation errors directly
            raise mve
        except Exception as e:
            logger.error(f"Metadata extraction process failed: {str(e)}", exc_info=True)
            raise MetadataExtractionException(f"Failed to extract document metadata: {str(e)}")

    def _merge_doc_fields(self, pdf, excel, csv):
        """
        Combines PDF, Excel, and CSV specific metadata attributes into the document block.
        """
        title = pdf.get("title")
        author = pdf.get("author")
        subject = pdf.get("subject")
        keywords = pdf.get("keywords")
        version = pdf.get("version")
        pages = pdf.get("page_count", 0)

        sheets = excel.get("sheet_names", [])
        sheet_count = excel.get("worksheet_count", 0)
        
        # Calculate rows and columns depending on Excel or CSV
        rows = excel.get("row_count") if excel.get("row_count") is not None else csv.get("row_count")
        cols = excel.get("column_count") if excel.get("column_count") is not None else csv.get("column_count")

        return {
            "title": title,
            "author": author,
            "subject": subject,
            "keywords": keywords,
            "version": version,
            "page_count": pages,
            "worksheet_count": sheet_count,
            "sheet_names": sheets,
            "row_count": rows,
            "column_count": cols
        }
