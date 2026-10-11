"""Shared PDF-asset helpers.

A library, not a CLI: it exists so the xref de-duplication logic has one definition
instead of being copied into every script that walks a page's image list.

An embedded image is identified by its xref. The same xref can appear on several pages
(a repeated logo) and several times on one page; both `inspect_pdf_assets.py`
(inventory) and `extract_embedded_images.py` (dump) must collapse those to one object.
"""
from __future__ import annotations

from collections.abc import Iterator

import fitz


def iter_unique_images(page: fitz.Page) -> Iterator[tuple[int, tuple]]:
    """Yield (xref, image_tuple) for each distinct image xref on one page."""
    seen: set[int] = set()
    for img in page.get_images(full=True):
        xref = int(img[0])
        if xref in seen:
            continue
        seen.add(xref)
        yield xref, img


def unique_images(doc: fitz.Document) -> list[tuple[int, int, tuple]]:
    """Return [(xref, first_seen_page_1based, image_tuple)] over the whole document."""
    seen: set[int] = set()
    out: list[tuple[int, int, tuple]] = []
    for pno, page in enumerate(doc):
        for xref, img in iter_unique_images(page):
            if xref in seen:
                continue
            seen.add(xref)
            out.append((xref, pno + 1, img))
    return out
