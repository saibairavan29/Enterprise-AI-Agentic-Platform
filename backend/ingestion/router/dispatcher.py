from common.parser_types import ParserType
from .registry import PARSER_REGISTRY

class ParserNotFoundException(Exception):
    """
    Raised when no parser strategy is registered for the requested ParserType.
    """
    pass

class UnsupportedParserException(Exception):
    """
    Raised when the document matches an invalid or unconfigured parser classification.
    """
    pass

class ParserDispatcher:
    """
    Factory Dispatcher resolving specific Document Parsers using the Strategy Pattern.
    """
    @staticmethod
    def get_parser(parser_type):
        """
        Resolves the parser class corresponding to the ParserType.
        
        :param parser_type: ParserType enum instance or its equivalent string value.
        :return: An instantiated instance of BaseDocumentParser.
        """
        if isinstance(parser_type, str):
            try:
                parser_type = ParserType(parser_type)
            except ValueError:
                raise UnsupportedParserException(f"Unsupported Parser Type classification: '{parser_type}'")

        if parser_type not in PARSER_REGISTRY:
            raise ParserNotFoundException(f"No parsing handler registered for parser type: '{parser_type.value}'")

        parser_class = PARSER_REGISTRY[parser_type]
        return parser_class()
