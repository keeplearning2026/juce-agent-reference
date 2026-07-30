"""Search implementation with SQLite FTS5 and text-index fallback.

Supports exact symbol lookup, alias resolution, concept search, and
full-text search with deterministic ranking.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from juce_reference.alias_loader import AliasConfig, generate_auto_aliases
from juce_reference.util.json_io import json_lines


@dataclass(frozen=True)
class SearchResult:
    """A single search result."""

    symbol: str
    short_name: str
    kind: str
    module: str | None
    documentation_path: str
    anchor: str | None
    signature: str | None
    brief: str
    score: float
    match_type: str  # "exact", "alias", "concept", "signature", "brief", "body"


def build_search_db(
    symbols_path: Path,
    output_path: Path,
    alias_config: AliasConfig | None = None,
) -> int:
    """Build a SQLite FTS5 search database from symbols.jsonl.

    Args:
        symbols_path: Path to ``symbols.jsonl``.
        output_path: Path for the ``search.sqlite`` output.
        alias_config: Optional alias config for enriched search.

    Returns:
        Number of symbols indexed.
    """
    symbols = json_lines(symbols_path)

    conn = sqlite3.connect(str(output_path))
    conn.execute("PRAGMA journal_mode=WAL")

    # Drop existing tables for clean rebuild.
    conn.execute("DROP TABLE IF EXISTS symbol_fts")
    conn.execute("DROP TABLE IF EXISTS symbols")

    # Regular table
    conn.execute("""
        CREATE TABLE symbols (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            short_name TEXT NOT NULL,
            kind TEXT,
            access TEXT,
            module TEXT,
            documentation_path TEXT,
            anchor TEXT,
            signature TEXT,
            documented INTEGER,
            brief TEXT
        )
    """)

    # FTS table
    conn.execute("""
        CREATE VIRTUAL TABLE symbol_fts USING fts5(
            symbol, short_name, aliases, concepts, kind, module,
            signature, brief, documentation_path, anchor
        )
    """)

    alias_config = alias_config or AliasConfig(symbols={}, alias_to_symbol={})

    for idx, sym in enumerate(symbols):
        symbol = sym.get("symbol", "")
        short_name = sym.get("short_name", "")
        auto_aliases = generate_auto_aliases(symbol)
        entry = alias_config.symbols.get(symbol)
        manual_aliases = list(entry.aliases) if entry else []
        concepts = list(entry.concepts) if entry else []
        all_aliases = " ".join(manual_aliases + auto_aliases)
        all_concepts = " ".join(concepts)

        conn.execute(
            "INSERT INTO symbols VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                idx + 1, symbol, short_name, sym.get("kind"),
                sym.get("access", ""), sym.get("module"),
                sym.get("documentation_path"), sym.get("anchor"),
                sym.get("signature"),
                1 if sym.get("documented") else 0, sym.get("brief"),
            ),
        )
        conn.execute(
            "INSERT INTO symbol_fts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                symbol, short_name, all_aliases, all_concepts,
                sym.get("kind"), sym.get("module"), sym.get("signature"),
                sym.get("brief"), sym.get("documentation_path"),
                sym.get("anchor"),
            ),
        )

    conn.commit()
    conn.close()
    return len(symbols)


def search_symbol(
    query: str,
    db_path: Path,
    *,
    limit: int = 20,
    kind_filter: str | None = None,
    module_filter: str | None = None,
    public_only: bool = False,
) -> list[SearchResult]:
    """Search the FTS5 database and return ranked results.

    Args:
        query: User query string.
        db_path: Path to ``search.sqlite``.
        limit: Maximum results.
        kind_filter: Optional kind filter.
        module_filter: Optional module filter.
        public_only: Exclude non-public symbols.

    Returns:
        Ranked list of ``SearchResult`` items.
    """
    if not db_path.is_file():
        return []

    conn = sqlite3.connect(str(db_path))
    results: list[SearchResult] = []

    # Try exact match first.
    exact = _exact_lookup(conn, query)
    if exact:
        results.append(exact)

    # FTS5 search
    fts_query = _build_fts_query(query)
    where_clauses = ["symbol_fts MATCH ?"]
    params: list[Any] = [fts_query]

    if kind_filter:
        where_clauses.append("kind = ?")
        params.append(kind_filter)
    if module_filter:
        where_clauses.append("module = ?")
        params.append(module_filter)
    if public_only:
        where_clauses.append("(access IS NULL OR access = 'public')")

    sql = f"""
        SELECT s.symbol, s.short_name, s.kind, s.module,
               s.documentation_path, s.anchor, s.signature, s.brief,
               rank
        FROM symbol_fts
        JOIN symbols s ON symbol_fts.rowid = s.id
        WHERE {' AND '.join(where_clauses)}
        ORDER BY rank
        LIMIT ?
    """
    params.append(limit)

    try:
        for row in conn.execute(sql, params):
            if row[0] not in {r.symbol + (r.anchor or "") for r in results}:
                results.append(SearchResult(
                    symbol=row[0], short_name=row[1], kind=row[2] or "",
                    module=row[3], documentation_path=row[4],
                    anchor=row[5], signature=row[6], brief=row[7] or "",
                    score=float(row[8]) if row[8] else 0.0,
                    match_type="body",
                ))
    except sqlite3.OperationalError:
        # FTS5 query malformed; fall through.
        pass

    conn.close()
    return results[:limit]


def _exact_lookup(conn: sqlite3.Connection, query: str) -> SearchResult | None:
    """Try exact symbol match."""
    row = conn.execute(
        "SELECT symbol, short_name, kind, module, documentation_path, "
        "anchor, signature, brief FROM symbols WHERE symbol = ?",
        (query,),
    ).fetchone()
    if row:
        return SearchResult(
            symbol=row[0], short_name=row[1], kind=row[2] or "",
            module=row[3], documentation_path=row[4],
            anchor=row[5], signature=row[6], brief=row[7] or "",
            score=0.0, match_type="exact",
        )
    return None


def _build_fts_query(query: str) -> str:
    """Build a safe FTS5 query string."""
    # Clean and quote tokens for FTS5.
    tokens = query.split()
    safe_tokens: list[str] = []
    for tok in tokens:
        tok = tok.strip('"\'*')
        if not tok:
            continue
        # Escape double-quotes
        tok = tok.replace('"', '""')
        safe_tokens.append(f'"{tok}"')
    return " OR ".join(safe_tokens) if safe_tokens else '""'
