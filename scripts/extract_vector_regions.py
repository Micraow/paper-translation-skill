#!/usr/bin/env python3
"""Extract selected page regions as standalone vector-preserving PDFs.

Manifest format:
{
  "source": "../sources/original.pdf",
  "output_dir": "../figures",
  "assets": [
    {"output":"fig1.pdf", "page":3, "bbox":[x0,y0,x1,y1], "label":"...",
     "kind":"figure", "allow_overlap_with":["fig1b.pdf"]}
  ]
}
Paths are resolved relative to the manifest file. `page` is 1-based; `bbox` is in PDF
points with a top-left origin.

Degenerate-input checks run here, before any file is written, because they are the only
crop checks that can live in CI and they catch operator slip-ups (box on the wrong page,
two boxes accidentally covering one figure, an empty box). They deliberately make **no**
judgement about whether a crop is *framed well* — that needs eyes on the render:

1. every region is non-empty and inside its page's MediaBox;
2. output names are unique and pages are in range;
3. two regions on one page must not overlap unless `allow_overlap_with` names the other;
4. each region must actually contain text, vector art or an image on its source page —
   an empty crop means the box or the page is wrong.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import fitz


def resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def preview_pdf(pdf_path: Path, out_png: Path, dpi: int = 180) -> None:
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    pix.save(out_png)
    doc.close()


def overlaps(a: fitz.Rect, b: fitz.Rect) -> bool:
    inter = a & b
    return inter.width > 0 and inter.height > 0


def region_has_content(page: fitz.Page, clip: fitz.Rect) -> bool:
    """True when the source page carries text, vector art or an image inside `clip`.

    This must be measured on the *source* page. A page built with `show_pdf_page`
    still enumerates the whole referenced page's text and drawings, so an empty crop
    would look non-empty if inspected through the extraction output.
    """
    if page.get_text("text", clip=clip).strip():
        return True
    if any(d.get("rect") and overlaps(fitz.Rect(d["rect"]), clip) for d in page.get_drawings()):
        return True
    try:
        return any(overlaps(fitz.Rect(info["bbox"]), clip) for info in page.get_image_info())
    except Exception:  # pragma: no cover - get_image_info can fail on odd PDFs
        return True


def normalized_name(raw: str, seen: dict[str, str]) -> str:
    name = raw if raw.lower().endswith(".pdf") else raw + ".pdf"
    key = name.lower()
    if key in seen:
        raise ValueError(f"duplicate output name {raw!r} (already used by {seen[key]!r})")
    seen[key] = raw
    return name


def parse_assets(assets: list[dict], doc: fitz.Document) -> list[dict]:
    parsed: list[dict] = []
    seen: dict[str, str] = {}
    for item in assets:
        page_no = int(item["page"])
        if not 1 <= page_no <= len(doc):
            raise ValueError(f"{item.get('output')}: page {page_no} out of range (1..{len(doc)})")
        coords = item["bbox"]
        if len(coords) != 4:
            raise ValueError(f"{item.get('output')}: bbox must contain four numbers")
        clip = fitz.Rect(*map(float, coords))
        page_rect = doc[page_no - 1].rect
        if clip.is_empty or not page_rect.contains(clip):
            raise ValueError(
                f"{item.get('output')}: bbox {tuple(round(v, 2) for v in clip)} "
                f"is empty or outside page bounds {tuple(round(v, 2) for v in page_rect)}"
            )
        parsed.append({
            "name": normalized_name(item["output"], seen),
            "page": page_no,
            "clip": clip,
            "label": item.get("label", ""),
            "allow_overlap_with": {str(x).lower() for x in item.get("allow_overlap_with", [])},
        })
    for i, a in enumerate(parsed):
        for b in parsed[i + 1:]:
            if a["page"] != b["page"]:
                continue
            inter = a["clip"] & b["clip"]
            if inter.is_empty or inter.get_area() <= 0:
                continue
            allowed = (b["name"].lower() in a["allow_overlap_with"]
                       or a["name"].lower() in b["allow_overlap_with"])
            if not allowed:
                raise ValueError(
                    f"{a['name']} and {b['name']} overlap on page {a['page']} "
                    f"(area {inter.get_area():.1f}pt²). Fix the boxes, or record "
                    f'"allow_overlap_with" on one of them if the overlap is intentional.'
                )
    return parsed


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--preview-dir", type=Path)
    args = ap.parse_args()

    manifest_path = args.manifest.resolve()
    base = manifest_path.parent
    cfg = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = cfg.get("assets", [])
    if not assets:
        print("No regions configured; skipping vector extraction")
        return
    source = resolve(base, cfg["source"])
    output_dir = resolve(base, cfg.get("output_dir", "../figures"))
    output_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(source)
    try:
        parsed = parse_assets(assets, doc)
        for item in parsed:
            src_page = doc[item["page"] - 1]
            if not region_has_content(src_page, item["clip"]):
                raise ValueError(
                    f"{item['name']}: the crop contains no text, vector art or image — the "
                    f"bbox or the page is probably wrong; fix the manifest."
                )
            dst = output_dir / item["name"]
            out = fitz.open()
            new_page = out.new_page(width=item["clip"].width, height=item["clip"].height)
            new_page.show_pdf_page(
                new_page.rect,
                doc,
                item["page"] - 1,
                clip=item["clip"],
                keep_proportion=False,
            )
            out.save(dst, garbage=4, deflate=True)
            out.close()
            print(f"extracted {dst.name} from page {item['page']} {item['label']}")
            if args.preview_dir:
                preview_pdf(dst, args.preview_dir / f"{Path(item['name']).stem}.png")
        print(f"Extracted {len(parsed)} vector-preserving regions -> {output_dir}")
    except ValueError as exc:
        raise SystemExit(f"ERROR: {exc}") from None
    finally:
        doc.close()


if __name__ == "__main__":
    main()
