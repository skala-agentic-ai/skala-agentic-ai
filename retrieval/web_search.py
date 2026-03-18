# MODIFIED: web search를 SerpAPI 전용으로 단순화하고 E2E 안정성 보강
"""Web search adapter returning SourceDoc-shaped results."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from schemas import SourceDoc, validate_source_doc

logger = logging.getLogger(__name__)

MAX_RESULTS_PER_QUERY = 5
REQUEST_TIMEOUT_SEC = 30
MAX_QUERY_CHARS = 400
MAX_QUERIES_PER_CALL = 3


def _extract_year(date_text: str | None, default: str) -> str:
    if not date_text:
        return default
    return str(date_text).strip()[:4] or default


def _build_source_doc(result: dict, retrieved_at: str, query: str) -> SourceDoc:
    source_url = str(result.get("url", "")).strip()
    published_at = str(result.get("published_date") or "0000-01-01")
    title = str(result.get("title", "")).strip()
    content = str(result.get("content", "")).strip()
    source_name = title or f"web:{query[:24]}"
    doc = {
        "source_type": "web",
        "source_url": source_url,
        "published_at": published_at,
        "retrieved_at": retrieved_at,
        "source_name": source_name,
        "domain": "market",
        "title": title or source_name,
        "excerpt": content,
        "year": _extract_year(published_at, "0000"),
        # Backward-compatible extra field for callers/tests expecting `content`.
        "content": content,
    }
    return validate_source_doc(doc)


def _normalize_queries(queries: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in queries:
        for part in str(raw).split("|"):
            q = " ".join(part.strip().split())
            if not q:
                continue
            if len(q) > MAX_QUERY_CHARS:
                logger.warning(
                    {
                        "event": "web_search_query_truncated",
                        "original_length": len(q),
                        "max_length": MAX_QUERY_CHARS,
                    }
                )
                q = q[:MAX_QUERY_CHARS].rstrip()
            if q in seen:
                continue
            seen.add(q)
            normalized.append(q)
            if len(normalized) >= MAX_QUERIES_PER_CALL:
                return normalized
    return normalized


def search(queries: list[str], force_fail: bool = False) -> list[SourceDoc]:
    if force_fail:
        return []
    api_key = os.getenv("SERP_API_KEY") or os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "Web search requires SERP_API_KEY (or SERPAPI_API_KEY). "
            "Set environment variable before running."
        )

    from serpapi import GoogleSearch

    results: list[SourceDoc] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()

    normalized_queries = _normalize_queries(queries)
    for query in normalized_queries:
        try:
            params = {
                "q": query,
                "api_key": api_key,
                "num": MAX_RESULTS_PER_QUERY,
                "timeout": REQUEST_TIMEOUT_SEC,
            }
            response = GoogleSearch(params).get_dict()
            items = response.get("organic_results", [])
            for item in items:
                source_url = str(item.get("link", "")).strip()
                published_at_raw = str(item.get("date") or "").strip()
                published_at = published_at_raw if published_at_raw else retrieved_at[:10]
                title = str(item.get("title", "")).strip()
                snippet = str(item.get("snippet", "")).strip()
                source_name = title or f"web:{query[:24]}"
                doc = {
                    "source_type": "web",
                    "source_url": source_url,
                    "published_at": published_at,
                    "retrieved_at": retrieved_at,
                    "source_name": source_name,
                    "domain": "market",
                    "title": title or source_name,
                    "excerpt": snippet,
                    "year": _extract_year(published_at, retrieved_at[:4]),
                    # Backward-compatible extra field for callers/tests expecting `content`.
                    "content": snippet,
                }
                parsed = validate_source_doc(doc)
                if parsed["source_url"]:
                    results.append(parsed)
            logger.info(
                {
                    "event": "serp_search_success",
                        "query": query,
                        "result_count": len(items),
                    }
                )
        except Exception as exc:
            logger.error(
                {
                    "event": "serp_search_query_failed",
                    "query": query,
                    "error": str(exc),
                }
            )
    return results
