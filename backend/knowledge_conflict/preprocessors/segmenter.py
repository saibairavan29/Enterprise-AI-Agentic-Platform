import re
from abc import ABC, abstractmethod
from ..exceptions.exceptions import SegmentationException

class BaseSegmenter(ABC):
    """
    Abstract Base Class for text segmenter strategies.
    Defines interface for document text splitting.
    """
    @abstractmethod
    def segment(self, text: str, source_id: str = "") -> list:
        """
        Segment plain text into list of structural components.
        Returns a list of segment dictionaries:
        [
            {
                "segment_id": str,
                "text": str,
                "type": "paragraph" | "sentence" | "section",
                "page": int | None,
                "section": str | None
            }
        ]
        """
        pass


class RegexSegmenter(BaseSegmenter):
    """
    Rules-based Text Segmenter using regular expressions to split text into
    paragraphs, sentences, and sections.
    """
    def segment(self, text: str, source_id: str = "") -> list:
        if text is None:
            raise SegmentationException("Input text cannot be None.")

        segments = []
        try:
            # Clean Carriage returns
            cleaned_text = text.replace('\r\n', '\n').replace('\r', '\n')
            
            # --- 1. Section Segmenting ---
            # Split text by Markdown-like headings (e.g., # Heading, ## Subheading)
            section_matches = list(re.finditer(r'(?:^|\n)(#{1,6}\s+.*)', cleaned_text))
            
            # --- 2. Paragraph Segmenting ---
            # Paragraphs are blocks separated by double or more newlines
            paragraphs = re.split(r'\n\s*\n+', cleaned_text)
            para_index = 1
            
            current_section = "Main"
            for para in paragraphs:
                para_clean = para.strip()
                if not para_clean:
                    continue
                
                # Check if this paragraph is actually a header section
                header_match = re.match(r'^#{1,6}\s+(.*)', para_clean)
                if header_match:
                    current_section = header_match.group(1).strip()
                    segments.append({
                        "segment_id": f"{source_id}-sec-{para_index}",
                        "text": para_clean,
                        "type": "section",
                        "page": 1,
                        "section": current_section
                    })
                    para_index += 1
                    continue
                
                # Register paragraph segment
                segments.append({
                    "segment_id": f"{source_id}-para-{para_index}",
                    "text": para_clean,
                    "type": "paragraph",
                    "page": 1,
                    "section": current_section
                })
                
                # Split paragraph into sentences, ignoring abbreviations and decimals
                # Match punctuation followed by space, avoiding lookbehinds on abbreviations
                sentence_endings = re.split(r'(?<!\bdept)(?<!\bcorp)(?<!\be\.g)(?<!\bi\.e)(?<!\binc)(?<!\bmr)(?<!\bms)(?<!\bdr)(?<!\bvs)(?<!\bco)\.\s+(?=[A-Z])', para_clean)
                
                sent_index = 1
                for sent in sentence_endings:
                    sent_clean = sent.strip()
                    if not sent_clean:
                        continue
                    
                    # Ensure period is appended if it was stripped
                    if not sent_clean.endswith(('.', '?', '!')):
                        sent_clean += '.'
                        
                    segments.append({
                        "segment_id": f"{source_id}-para-{para_index}-sent-{sent_index}",
                        "text": sent_clean,
                        "type": "sentence",
                        "page": 1,
                        "section": current_section
                    })
                    sent_index += 1
                
                para_index += 1

            return segments
        except Exception as e:
            raise SegmentationException(f"Failed to segment text blocks: {str(e)}")
