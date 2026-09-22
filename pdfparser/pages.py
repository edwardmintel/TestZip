"""Parse 1-based page ranges into 0-based page indices."""

from __future__ import annotations


class PageSpecError(ValueError):
    """Raised when a page range string is invalid."""


def parse_page_spec(spec: str, page_count: int) -> list[int]:
    """Convert a 1-based page spec into sorted, unique 0-based indices.

    Accepted forms: ``1``, ``1-3``, ``1,3,5-8``, ``-3`` (first 3),
    ``4-`` (page 4 through the end).
    """
    if page_count < 1:
        raise PageSpecError("Document has no pages.")
    if not spec or not spec.strip():
        raise PageSpecError("Page range is empty.")

    indices: set[int] = set()
    for raw_part in spec.split(","):
        part = raw_part.strip()
        if not part:
            raise PageSpecError(f"Invalid page range: {spec!r}")
        if "-" in part:
            start_s, end_s = part.split("-", 1)
            start = _parse_bound(start_s, default=1, label="start", spec=part)
            end = _parse_bound(end_s, default=page_count, label="end", spec=part)
            if start > end:
                raise PageSpecError(f"Invalid range {part!r}: start is after end.")
            _check_in_range(start, page_count)
            _check_in_range(end, page_count)
            indices.update(range(start - 1, end))
        else:
            page = _parse_int(part, spec=part)
            _check_in_range(page, page_count)
            indices.add(page - 1)

    return sorted(indices)


def _parse_bound(value: str, *, default: int, label: str, spec: str) -> int:
    text = value.strip()
    if text == "":
        return default
    return _parse_int(text, spec=spec)


def _parse_int(value: str, *, spec: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise PageSpecError(f"Invalid page number in {spec!r}.") from exc
    if number < 1:
        raise PageSpecError("Page numbers are 1-based.")
    return number


def _check_in_range(page: int, page_count: int) -> None:
    if page > page_count:
        raise PageSpecError(
            f"Page {page} is out of range (document has {page_count} page"
            f"{'' if page_count == 1 else 's'})."
        )
