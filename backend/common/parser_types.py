from enum import Enum

class ParserType(str, Enum):
    PDF = "PDF"
    EXCEL = "EXCEL"
    CSV = "CSV"
    JSON = "JSON"
    TEXT = "TEXT"
    IMAGE = "IMAGE"
    API = "API"
