from common.parser_types import ParserType
from ..parsers import (
    PDFParser,
    ExcelParser,
    CSVParser,
    JSONParser,
    TextParser,
    ImageParser,
    APIParser
)

# Registry mapping ParserType enum choices to their concrete parsing strategy classes.
# This follows the Open-Closed SOLID principle: new parsers can be added without modifying dispatcher logic.
PARSER_REGISTRY = {
    ParserType.PDF: PDFParser,
    ParserType.EXCEL: ExcelParser,
    ParserType.CSV: CSVParser,
    ParserType.JSON: JSONParser,
    ParserType.TEXT: TextParser,
    ParserType.IMAGE: ImageParser,
    ParserType.API: APIParser,
}
