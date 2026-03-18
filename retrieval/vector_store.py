"""Domain-isolated in-memory vector store facade."""
from __future__ import annotations

from collections import defaultdict

from schemas import SourceDoc

_STORE: dict[str, list[SourceDoc]] = defaultdict(list)


def reset_store() -> None:
    _STORE.clear()


def ingest(domain: str, docs: list[SourceDoc]) -> None:
    if not docs:
        raise RuntimeError("empty docs ingest")
    for doc in docs:
        if doc["domain"] != domain:
            raise RuntimeError("cross domain ingest blocked")
    _STORE[domain].extend(docs)


def query(domain: str, queries: list[str]) -> list[SourceDoc]:
    if not queries:
        return []
    corpus = _STORE.get(domain, [])
    if not corpus:
        return []

    tokens = [tok for q in queries for tok in q.lower().split() if len(tok) >= 2]
    scored: list[tuple[int, SourceDoc]] = []
    for doc in corpus:
        hay = f"{doc['title']} {doc['excerpt']}".lower()
        score = 0
        for token in tokens:
            if token in hay:
                score += 1
        if score > 0:
            scored.append((score, doc))

    if not scored:
        return corpus[:6]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [doc for _, doc in scored[:8]]
