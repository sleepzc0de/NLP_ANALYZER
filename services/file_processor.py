import os
import fitz  # PyMuPDF
from docx import Document as DocxDocument


class FileProcessor:

    @staticmethod
    def extract_text_from_pdf(filepath: str) -> str:
        """Extract text from PDF using PyMuPDF (fitz)."""
        text_parts = []
        try:
            doc = fitz.open(filepath)
            for page in doc:
                text_parts.append(page.get_text("text"))
            doc.close()
        except Exception as e:
            raise RuntimeError(f"Failed to read PDF: {e}")
        return "\n".join(text_parts).strip()

    @staticmethod
    def extract_text_from_docx(filepath: str) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            doc = DocxDocument(filepath)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs).strip()
        except Exception as e:
            raise RuntimeError(f"Failed to read DOCX: {e}")

    @classmethod
    def extract_text(cls, filepath: str, file_ext: str) -> str:
        ext = file_ext.lower().lstrip(".")
        if ext == "pdf":
            return cls.extract_text_from_pdf(filepath)
        elif ext in ("docx", "doc"):
            return cls.extract_text_from_docx(filepath)
        else:
            raise ValueError(f"Unsupported file type: {ext}")