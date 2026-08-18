from .base import BaseExtractor

class ImageExtractor(BaseExtractor):
    """
    Extractor responsible for image dimension properties:
    width, height, dpi, and color_mode.
    """
    def extract(self, doc_obj, parser_output, ocr_output=None):
        res = {
            "width": None,
            "height": None,
            "dpi": None,
            "color_mode": None
        }

        if not parser_output or parser_output.get("parser_type") != "IMAGE":
            return res

        parser_meta = parser_output.get("metadata", {})
        res["width"] = parser_meta.get("width") or None
        res["height"] = parser_meta.get("height") or None
        res["color_mode"] = parser_meta.get("color_space") or parser_meta.get("color_mode") or None
        
        # Resolve DPI resolution
        dpi_h = parser_meta.get("dpi_horizontal")
        dpi_v = parser_meta.get("dpi_vertical")
        if dpi_h and dpi_v:
            res["dpi"] = f"{dpi_h}x{dpi_v}"
        elif parser_meta.get("dpi"):
            res["dpi"] = str(parser_meta.get("dpi"))

        return res
