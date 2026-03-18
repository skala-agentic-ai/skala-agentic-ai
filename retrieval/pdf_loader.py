"""PDF loader for domain-scoped ingestion."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from constants import MAX_INGEST_PAGES
from schemas import SourceDoc, ValidationError, validate_source_doc

ALLOWED_DOMAINS = {"market", "LGES", "CATL"}


def _normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    return cleaned


def _extract_pages(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader  # type: ignore

        reader = PdfReader(str(path))
        pages: list[str] = []
        for page in reader.pages:
            pages.append(_normalize_text(page.extract_text() or ""))
        return pages
    except Exception:
        # Fallback: byte-level extraction for environments without parser.
        data = path.read_bytes()
        if not data.startswith(b"%PDF"):
            raise ValueError("corrupted pdf")
        rough = _normalize_text(data.decode("latin-1", errors="ignore"))
        if not rough:
            raise ValueError("unreadable pdf pages")
        # Keep single pseudo-page fallback to avoid ingestion failure.
        return [rough[:2000]]


def _infer_published_at(file_stem: str) -> str:
    year = "2026"
    for token in file_stem.replace("_", " ").split():
        if token.isdigit() and len(token) == 4:
            year = token
            break
    return f"{year}-01-01"


def load_pdfs_from_dir(data_dir: str | Path, domain: str) -> list[SourceDoc]:
    if domain not in ALLOWED_DOMAINS:
        raise ValidationError(f"invalid domain: {domain}")

    root = Path(data_dir)
    if root.name != domain:
        raise ValidationError(f"cross ingest blocked: path={root.name}, domain={domain}")

    out: list[SourceDoc] = []
    total_pages = 0
    for path in sorted(root.glob("*.pdf")):
        try:
            pages = _extract_pages(path)
            published_at = _infer_published_at(path.stem)
            year = published_at[:4]
            for idx, page_text in enumerate(pages, start=1):
                if total_pages >= MAX_INGEST_PAGES:
                    break
                excerpt = page_text[:500] if page_text else f"{path.stem} page {idx}"
                if not excerpt.strip():
                    continue
                doc = {
                    "source_type": "pdf",
                    "source_url": f"{str(path.resolve())}#page={idx}",
                    "published_at": published_at,
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "source_name": f"{path.name} p.{idx}",
                    "domain": domain,
                    "title": path.stem,
                    "excerpt": excerpt,
                    "year": year,
                }
                out.append(validate_source_doc(doc))
                total_pages += 1
        except Exception:
            # Skip corrupted/unsupported PDF without stopping pipeline.
            continue
    return out
