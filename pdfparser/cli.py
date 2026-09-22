"""Command-line interface for PDF-to-Markdown conversion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pdfparser import __version__
from pdfparser.convert import (
    ConversionError,
    convert_pdf,
    default_output_path,
    page_count,
    write_markdown,
)
from pdfparser.pages import PageSpecError, parse_page_spec


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.output is not None and len(args.pdfs) > 1:
        _error("Use --output-dir when converting more than one PDF.")
        return 2
    if args.stdout and len(args.pdfs) > 1:
        _error("Use --stdout with a single PDF.")
        return 2
    if args.stdout and args.output is not None:
        _error("Choose either --stdout or --output, not both.")
        return 2

    failures = 0
    for pdf_path in args.pdfs:
        try:
            _convert_one(pdf_path, args)
        except (ConversionError, PageSpecError, OSError) as exc:
            _error(str(exc))
            failures += 1

    if failures:
        if len(args.pdfs) > 1:
            _error(f"Failed to convert {failures} of {len(args.pdfs)} file(s).")
        return 1
    return 0


def _convert_one(pdf_path: Path, args: argparse.Namespace) -> None:
    total_pages = page_count(pdf_path, password=args.password)
    pages = None
    if args.pages:
        pages = parse_page_spec(args.pages, total_pages)

    markdown = convert_pdf(
        pdf_path,
        pages=pages,
        password=args.password,
        write_images=args.write_images,
        image_dir=args.image_dir,
        include_header=not args.no_header,
        include_footer=not args.no_footer,
        page_separators=args.page_separators,
        force_ocr=args.force_ocr,
        show_progress=args.verbose,
    )

    extracted = len(pages) if pages is not None else total_pages
    if args.stdout:
        sys.stdout.write(markdown)
        if not markdown.endswith("\n"):
            sys.stdout.write("\n")
        return

    output_path = args.output if args.output is not None else default_output_path(
        pdf_path, args.output_dir
    )
    write_markdown(output_path, markdown)
    if not args.quiet:
        print(f"Wrote {output_path} ({extracted} page{'' if extracted == 1 else 's'})")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdfparser",
        description="Extract text from PDF files and write Markdown.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  pdfparser report.pdf\n"
            "  pdfparser report.pdf -o notes.md\n"
            "  pdfparser a.pdf b.pdf --output-dir ./md\n"
            "  pdfparser report.pdf --pages 1-5,8\n"
        ),
    )
    parser.add_argument(
        "pdfs",
        nargs="+",
        type=_pdf_path,
        metavar="PDF",
        help="PDF file(s) to convert",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        metavar="PATH",
        help="output Markdown path (single PDF only; default: same name as the PDF)",
    )
    parser.add_argument(
        "-d",
        "--output-dir",
        type=Path,
        metavar="DIR",
        help="directory for output .md files (useful for multiple PDFs)",
    )
    parser.add_argument(
        "-p",
        "--pages",
        metavar="RANGE",
        help="1-based pages to extract, e.g. 1,3,5-8",
    )
    parser.add_argument(
        "--password",
        help="password for encrypted PDFs",
    )
    parser.add_argument(
        "--write-images",
        action="store_true",
        help="extract images and insert Markdown image references",
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        metavar="DIR",
        help="directory for extracted images (used with --write-images)",
    )
    parser.add_argument(
        "--no-header",
        action="store_true",
        help="omit repeating page headers",
    )
    parser.add_argument(
        "--no-footer",
        action="store_true",
        help="omit repeating page footers",
    )
    parser.add_argument(
        "--page-separators",
        action="store_true",
        help="insert a marker between pages",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="OCR every page (needs a Tesseract install for scanned PDFs)",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="print Markdown to stdout instead of writing a file",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="do not print the output path after writing",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show conversion progress",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def _pdf_path(value: str) -> Path:
    path = Path(value)
    if not path.exists():
        raise argparse.ArgumentTypeError(f"file not found: {path}")
    if not path.is_file():
        raise argparse.ArgumentTypeError(f"not a file: {path}")
    if path.suffix.lower() != ".pdf":
        raise argparse.ArgumentTypeError(f"not a PDF: {path}")
    return path


def _error(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
