"""Convert a PDF file to a Markdown string."""

from __future__ import annotations

from pathlib import Path

import pymupdf
import pymupdf4llm


class ConversionError(Exception):
    """Raised when a PDF cannot be opened or converted."""


def convert_pdf(
    pdf_path: Path,
    *,
    pages: list[int] | None = None,
    password: str | None = None,
    write_images: bool = False,
    image_dir: Path | None = None,
    include_header: bool = True,
    include_footer: bool = True,
    page_separators: bool = False,
    force_ocr: bool = False,
    show_progress: bool = False,
) -> str:
    """Extract Markdown from ``pdf_path``.

    ``pages`` is a list of 0-based page indices. ``None`` means all pages.
    """
    path = Path(pdf_path)
    if not path.exists():
        raise ConversionError(f"File not found: {path}")
    if not path.is_file():
        raise ConversionError(f"Not a file: {path}")

    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise ConversionError(f"Could not open {path}: {exc}") from exc

    try:
        _unlock(document, password, path)
        kwargs: dict = {
            "pages": pages,
            "header": include_header,
            "footer": include_footer,
            "page_separators": page_separators,
            "show_progress": show_progress,
            "write_images": write_images,
        }
        if write_images:
            image_path = image_dir if image_dir is not None else path.parent
            image_path.mkdir(parents=True, exist_ok=True)
            kwargs["image_path"] = str(image_path)
            kwargs["filename"] = path.stem
        if force_ocr:
            kwargs["force_ocr"] = True

        markdown = pymupdf4llm.to_markdown(document, **kwargs)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Could not convert {path}: {exc}") from exc
    finally:
        document.close()

    if not isinstance(markdown, str):
        raise ConversionError(f"Unexpected converter output for {path}.")
    return markdown


def page_count(pdf_path: Path, password: str | None = None) -> int:
    """Return the number of pages in ``pdf_path``."""
    path = Path(pdf_path)
    try:
        document = pymupdf.open(path)
    except Exception as exc:
        raise ConversionError(f"Could not open {path}: {exc}") from exc
    try:
        _unlock(document, password, path)
        return document.page_count
    finally:
        document.close()


def write_markdown(output_path: Path, markdown: str) -> None:
    """Write UTF-8 Markdown, creating parent directories as needed."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8", newline="\n")


def default_output_path(pdf_path: Path, output_dir: Path | None = None) -> Path:
    """Map ``report.pdf`` to ``report.md`` in the same or given directory."""
    dest_dir = output_dir if output_dir is not None else pdf_path.parent
    return dest_dir / f"{pdf_path.stem}.md"


def _unlock(document: pymupdf.Document, password: str | None, path: Path) -> None:
    if not document.needs_pass:
        return
    if not password:
        raise ConversionError(f"{path} is encrypted. Pass --password.")
    if not document.authenticate(password):
        raise ConversionError(f"Invalid password for {path}.")
