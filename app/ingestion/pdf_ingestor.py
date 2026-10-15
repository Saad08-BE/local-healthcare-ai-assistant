"""Local PDF document extractor, cleaner, and boundary-aware chunker."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from pathlib import Path
import re
from typing import Sequence


class PDFExtractionError(RuntimeError):
    """Raised when a PDF cannot be read or parsed locally."""


@dataclass(frozen=True)
class DocumentPage:
    """Raw text extracted from a single page of a local document."""

    doc_id: str
    filename: str
    page_number: int
    total_pages: int
    text: str


@dataclass(frozen=True)
class DocumentChunk:
    """A semantic chunk derived from a document page with citation metadata."""

    chunk_id: str
    doc_id: str
    filename: str
    page_number: int
    chunk_index: int
    text: str
    char_count: int

    @property
    def citation(self) -> str:
        """Formatted human-readable citation."""
        return f"{self.filename} (Page {self.page_number})"


class PDFIngestor:
    """Extracts text from local PDFs and splits it into citation-aware chunks."""

    def __init__(self, chunk_size: int = 600, chunk_overlap: int = 100) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive.")
        if not 0 <= chunk_overlap < chunk_size:
            raise ValueError("chunk_overlap must be non-negative and less than chunk_size.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def _generate_doc_id(self, file_path: Path) -> str:
        """Generate deterministic doc ID from file path and size."""
        hasher = hashlib.md5(f"{file_path.name}_{file_path.stat().st_size}".encode("utf-8"))
        return hasher.hexdigest()[:12]

    def extract_pages(self, pdf_path: Path) -> list[DocumentPage]:
        """Extract text from all pages of a PDF file."""
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        if pdf_path.stat().st_size == 0:
            raise PDFExtractionError(f"PDF file is empty: {pdf_path.name}")

        doc_id = self._generate_doc_id(pdf_path)
        pages: list[DocumentPage] = []

        try:
            import fitz  # PyMuPDF

            doc = fitz.open(str(pdf_path))
            total_pages = len(doc)
            if total_pages == 0:
                raise PDFExtractionError(f"PDF contains no pages: {pdf_path.name}")

            for page_idx in range(total_pages):
                page = doc.load_page(page_idx)
                text = page.get_text("text") or ""
                cleaned_text = self._clean_text(text)
                if cleaned_text:
                    pages.append(
                        DocumentPage(
                            doc_id=doc_id,
                            filename=pdf_path.name,
                            page_number=page_idx + 1,
                            total_pages=total_pages,
                            text=cleaned_text,
                        )
                    )
            doc.close()
        except ImportError:
            # Fallback for plain text or minimal PDF stream extraction
            pages = self._fallback_extract(pdf_path, doc_id)
        except Exception as exc:
            raise PDFExtractionError(f"Failed to read PDF '{pdf_path.name}': {exc}") from exc

        if not pages:
            # Document had pages but zero extractable text (e.g. scanned image-only PDF)
            raise PDFExtractionError(
                f"No extractable text found in '{pdf_path.name}'. The PDF may be a scanned image or empty."
            )

        return pages

    def _fallback_extract(self, file_path: Path, doc_id: str) -> list[DocumentPage]:
        """Simple text fallback extractor if PyMuPDF is not yet installed."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # Filter non-printable / binary junk
            printable = "".join(c for c in content if c.isprintable() or c in "\n\r\t")
            cleaned = self._clean_text(printable)
            if cleaned:
                return [
                    DocumentPage(
                        doc_id=doc_id,
                        filename=file_path.name,
                        page_number=1,
                        total_pages=1,
                        text=cleaned,
                    )
                ]
        except Exception as exc:
            raise PDFExtractionError(f"Fallback extraction failed for '{file_path.name}': {exc}") from exc
        return []

    def _clean_text(self, text: str) -> str:
        """Normalize whitespace and remove non-printable artifacts."""
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def chunk_page(self, page: DocumentPage) -> list[DocumentChunk]:
        """Split a single DocumentPage into sliding window chunks with sentence awareness."""
        text = page.text.strip()
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [
                DocumentChunk(
                    chunk_id=f"{page.doc_id}_p{page.page_number}_c1",
                    doc_id=page.doc_id,
                    filename=page.filename,
                    page_number=page.page_number,
                    chunk_index=1,
                    text=text,
                    char_count=len(text),
                )
            ]

        chunks: list[DocumentChunk] = []
        step = self.chunk_size - self.chunk_overlap
        start = 0
        chunk_idx = 1

        while start < len(text):
            end = start + self.chunk_size
            chunk_slice = text[start:end]

            # Try to break cleanly at sentence or newline boundary if near the end
            if end < len(text):
                split_candidates = [
                    chunk_slice.rfind(". "),
                    chunk_slice.rfind(".\n"),
                    chunk_slice.rfind("\n\n"),
                    chunk_slice.rfind("; "),
                ]
                best_break = max(split_candidates)
                # Break at sentence only if it doesn't shrink chunk too aggressively (> 50% chunk_size)
                if best_break > self.chunk_size * 0.5:
                    chunk_slice = chunk_slice[: best_break + 1]
                    end = start + len(chunk_slice)

            chunk_text = chunk_slice.strip()
            if chunk_text:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{page.doc_id}_p{page.page_number}_c{chunk_idx}",
                        doc_id=page.doc_id,
                        filename=page.filename,
                        page_number=page.page_number,
                        chunk_index=chunk_idx,
                        text=chunk_text,
                        char_count=len(chunk_text),
                    )
                )
                chunk_idx += 1

            start += step

        return chunks

    def process_file(self, pdf_path: Path) -> list[DocumentChunk]:
        """Extract and chunk all pages of a PDF."""
        pages = self.extract_pages(pdf_path)
        all_chunks: list[DocumentChunk] = []
        for page in pages:
            all_chunks.extend(self.chunk_page(page))
        return all_chunks

    def process_directory(self, directory: Path) -> list[DocumentChunk]:
        """Extract and chunk all PDF files in a directory."""
        if not directory.exists():
            return []

        pdf_files = list(directory.glob("*.pdf")) + list(directory.glob("*.PDF"))
        chunks: list[DocumentChunk] = []
        for pdf in sorted(pdf_files):
            try:
                chunks.extend(self.process_file(pdf))
            except PDFExtractionError as exc:
                print(f"Skipping '{pdf.name}': {exc}")
        return chunks
