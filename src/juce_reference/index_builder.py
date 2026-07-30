"""Build deterministic symbol and relationship indexes.

Produces:
- ``index/symbols.tsv``
- ``index/symbols.jsonl``
- ``index/relationships.jsonl``
- ``index/source-locations.jsonl``
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from juce_reference.model import Compound, SourceLocation


def build_symbols_tsv(
    compounds: list[Compound],
    output_path: Path,
    path_info: dict[str, str] | None = None,
) -> int:
    if path_info is None:
        path_info = _default_paths(compounds)
    rows: list[list[str]] = []
    _collect_symbol_rows(compounds, rows, path_info)
    rows.sort(key=lambda r: (r[0].casefold(), r[3], r[8], r[6], r[7]))
    with output_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t", lineterminator="\n")
        writer.writerow([
            "qualified_name", "short_name", "owner", "kind", "access",
            "module", "documentation_path", "anchor", "signature",
            "documented", "brief",
        ])
        for row in rows:
            writer.writerow(row)
    return len(rows)


def build_symbols_jsonl(
    compounds: list[Compound],
    output_path: Path,
    path_info: dict[str, str] | None = None,
) -> int:
    if path_info is None:
        path_info = _default_paths(compounds)
    records: list[dict[str, Any]] = []
    _collect_symbol_records(compounds, records, path_info)
    records.sort(key=lambda r: (
        str(r.get("symbol", "")).casefold(),
        str(r.get("kind", "")),
        str(r.get("signature", "")),
        str(r.get("documentation_path", "")),
        str(r.get("anchor", "")),
    ))
    with output_path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")

    return len(records)


def build_relationships_jsonl(compounds: list[Compound], output_path: Path) -> int:
    """Write ``relationships.jsonl`` with inheritance, containment, and
    member-of relationships.

    Returns the number of lines written.
    """
    lines: list[dict[str, Any]] = []

    for c in compounds:
        # Bases
        for base in c.bases:
            if base.refid:
                lines.append(_rel("derived-from", c.qualified_name, base.text,
                                  c.refid, base.refid, "doxygen"))
                lines.append(_rel("base-of", base.text, c.qualified_name,
                                  base.refid, c.refid, "doxygen"))

        # Inner compounds
        for inner in c.inner_compounds:
            if inner.refid:
                lines.append(_rel("contains", c.qualified_name, inner.text,
                                  c.refid, inner.refid, "doxygen"))

        # Members
        for m in c.members:
            lines.append(_rel("member-of", m.qualified_name, c.qualified_name,
                              m.refid, c.refid, "doxygen"))

        # Module
        if c.module:
            lines.append(_rel("module-of", c.qualified_name, c.module,
                              c.refid, "", "doxygen"))

    lines.sort(key=lambda r: (r["type"], r["source"], r["target"]))

    with output_path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")

    return len(lines)


def build_source_locations_jsonl(compounds: list[Compound], output_path: Path) -> int:
    """Write ``source-locations.jsonl`` for all entities that have a source location.

    Returns the number of lines written.
    """
    lines: list[dict[str, Any]] = []

    for c in compounds:
        if c.location and c.location.file:
            lines.append(_source_loc(c.qualified_name, c.refid, c.location))

        for m in c.members:
            if m.location and m.location.file:
                lines.append(_source_loc(m.qualified_name, m.refid, m.location))

    lines.sort(key=lambda r: str(r.get("symbol", "")).casefold())

    with output_path.open("w", encoding="utf-8") as fh:
        for line in lines:
            fh.write(json.dumps(line, ensure_ascii=False, sort_keys=True) + "\n")

    return len(lines)


def build_manifest(
    compounds: list[Compound],
    doc_count: int,
    symbol_count: int,
    example_count: int,
    juce_commit: str,
    output_path: Path,
) -> None:
    """Write ``manifest.json``."""
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "juce_commit": juce_commit,
        "statistics": {
            "compounds": len(compounds),
            "documents": doc_count,
            "symbols": symbol_count,
            "examples": example_count,
            "members": sum(len(c.members) for c in compounds),
        },
    }
    tmp = output_path.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    tmp.replace(output_path)


# -- Internal helpers ---------------------------------------------------------


def _default_paths(compounds: list[Compound]) -> dict[str, str]:
    """Compute refid → output path mapping matching PathMap and path_mapper."""
    from juce_reference.path_mapper import build_path_map
    pm = build_path_map(compounds)
    return {t.refid: t.path for t in pm.compounds.values()}


def _short_name(full: str) -> str:
    return full.rsplit("::", maxsplit=1)[-1]


def _brief_text(brief: tuple[object, ...]) -> str:
    """Extract one-line text from brief DocNode tuple."""
    parts: list[str] = []
    for node in brief:
        if hasattr(node, "value"):
            parts.append(str(node.value))
        elif hasattr(node, "children"):
            for child in node.children:
                if hasattr(child, "value"):
                    parts.append(str(child.value))
    return " ".join(parts)[:200]


def _collect_symbol_rows(
    compounds: list[Compound], rows: list[list[str]], path_info: dict[str, str],
) -> None:
    for c in compounds:
        c_path = path_info.get(c.refid, "")
        owner = "::".join(c.qualified_name.split("::")[:-1]) if "::" in c.qualified_name else ""
        rows.append([
            c.qualified_name, _short_name(c.qualified_name), owner,
            c.kind, "", c.module or "", c_path,
            "", "", str(c.documented).lower(), _brief_text(c.brief),
        ])
        for m in c.members:
            rows.append([
                m.qualified_name, m.name, c.qualified_name,
                m.kind, m.access, c.module or "", c_path,
                f"m-{_hash10(m.refid)}",
                m.signature, str(m.documented).lower(), _brief_text(m.brief),
            ])


def _collect_symbol_records(
    compounds: list[Compound], records: list[dict[str, Any]], path_info: dict[str, str],
) -> None:
    for c in compounds:
        c_path = path_info.get(c.refid, "")
        records.append(_symbol_record(c.qualified_name, _short_name(c.qualified_name),
                                       "", c.kind, "", c.module or "", c_path,
                                       "", "", c.documented, _brief_text(c.brief)))
        for m in c.members:
            records.append(_symbol_record(
                m.qualified_name, m.name, c.qualified_name,
                m.kind, m.access, c.module or "",
                c_path,
                f"m-{_hash10(m.refid)}", m.signature,
                m.documented, _brief_text(m.brief),
            ))


def _symbol_record(symbol: str, short_name: str, owner: str, kind: str,
                   access: str, module: str, doc_path: str, anchor: str,
                   signature: str, documented: bool, brief: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "short_name": short_name,
        "owner": owner,
        "kind": kind,
        "access": access,
        "module": module,
        "documentation_path": doc_path,
        "anchor": anchor,
        "signature": signature,
        "documented": documented,
        "brief": brief,
    }


def _hash10(refid: str) -> str:
    from juce_reference.util.hashing import short_id
    return short_id(refid, 10)


def _rel(rel_type: str, source: str, target: str,
         source_refid: str, target_refid: str, confidence: str) -> dict[str, str]:
    return {
        "type": rel_type,
        "source": source,
        "target": target,
        "source_refid": source_refid,
        "target_refid": target_refid,
        "confidence": confidence,
    }


def _source_loc(symbol: str, refid: str, loc: SourceLocation) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "refid": refid,
        "file": loc.file,
        "line": loc.line,
        "column": loc.column,
        "body_file": loc.body_file,
        "body_start": loc.body_start,
        "body_end": loc.body_end,
    }
