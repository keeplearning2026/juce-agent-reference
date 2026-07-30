"""Generation orchestrator — the full pipeline from JUCE checkout to output.

This is the single entry point that wires together:
    source validation → Doxygen → XML validation → parsing →
    path mapping → rendering → index building → output validation
"""

from __future__ import annotations

import json as _json
import time
from typing import Any

from juce_reference.config import GeneratorConfig
from juce_reference.doxygen_runner import classify_doxygen_warnings, run_doxygen
from juce_reference.errors import GenerationError
from juce_reference.index_builder import (
    build_manifest,
    build_relationships_jsonl,
    build_source_locations_jsonl,
    build_symbols_jsonl,
    build_symbols_tsv,
)
from juce_reference.markdown_renderer import render_compound
from juce_reference.output_validator import validate_output
from juce_reference.path_mapper import build_path_map
from juce_reference.publisher import publish_release
from juce_reference.repository_docs import import_repository_docs
from juce_reference.search import build_search_db
from juce_reference.source import validate_juce_source
from juce_reference.util.hashing import sha256_hex
from juce_reference.xml_parser import parse_compound, parse_index
from juce_reference.xml_validator import validate_xml_output


def generate(config: GeneratorConfig) -> dict[str, Any]:
    """Run the complete generation pipeline.

    Args:
        config: Immutable generator configuration.

    Returns:
        A dict with generation statistics suitable for reports/generation.json.

    Raises:
        GenerationError: If any stage fails.
    """
    stats: dict[str, Any] = {
        "started_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "config": {
            "juce_root": str(config.juce_root),
            "output_root": str(config.output_root),
            "allow_dirty": config.allow_dirty,
        },
    }

    # ---- 1. Validate JUCE source ----
    juce_source = validate_juce_source(config.juce_root, allow_dirty=config.allow_dirty)
    stats["juce_commit"] = juce_source.commit
    stats["juce_dirty"] = juce_source.dirty

    # ---- 2. Create build context ----
    build_id = sha256_hex(f"{juce_source.commit}-{time.monotonic()}")[:12]
    build_dir = config.juce_root.parent / ".build" / build_id
    build_dir.mkdir(parents=True, exist_ok=True)
    output_root = config.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    # ---- 3. Run Doxygen ----
    doxy_result = run_doxygen(juce_source, build_dir)
    stats["doxygen_warnings"] = classify_doxygen_warnings(doxy_result.warnings_file)

    # ---- 4. Validate XML ----
    xml_report = validate_xml_output(doxy_result.xml_dir)
    if not xml_report.all_valid:
        raise GenerationError(
            f"XML validation failed: {xml_report.valid_compound_count}/{xml_report.compound_count} valid, "
            f"{len(xml_report.issues)} issues",
        )
    stats["xml_validation"] = {
        "compounds": xml_report.compound_count,
        "valid": xml_report.valid_compound_count,
        "issues": len(xml_report.issues),
    }

    # ---- 5. Parse index & compounds ----
    index_entries = parse_index(doxy_result.xml_dir / "index.xml")
    compounds = []
    parse_errors = 0
    for entry in index_entries:
        compound_path = doxy_result.xml_dir / f"{entry.refid}.xml"
        try:
            compound = parse_compound(compound_path)
            compounds.append(compound)
        except Exception:
            parse_errors += 1
    if parse_errors > 0:
        raise GenerationError(f"Failed to parse {parse_errors} compounds")
    stats["parsed_compounds"] = len(compounds)
    stats["parsed_members"] = sum(len(c.members) for c in compounds)

    # ---- 6. Build path map ----
    path_map = build_path_map(compounds)

    # ---- 7. Render Markdown ----
    reference_dir = output_root / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    doc_count = 0
    for compound in compounds:
        target = path_map.compounds.get(compound.refid)
        if not target:
            continue
        doc = render_compound(compound, path_map, juce_commit=juce_source.commit)
        out_path = output_root / target.path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(doc.content, encoding="utf-8")
        doc_count += 1

    # ---- 8. Import repository docs ----
    repo_docs = import_repository_docs(juce_source)
    guides_dir = output_root / "guides"
    guides_dir.mkdir(parents=True, exist_ok=True)
    for rd in repo_docs:
        out_path = output_root / rd.output_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rd.content, encoding="utf-8")
    stats["guides_imported"] = len(repo_docs)

    # ---- 9. Build indexes ----
    index_dir = output_root / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    symbol_count = build_symbols_tsv(compounds, index_dir / "symbols.tsv")
    build_symbols_jsonl(compounds, index_dir / "symbols.jsonl")
    build_relationships_jsonl(compounds, index_dir / "relationships.jsonl")
    build_source_locations_jsonl(compounds, index_dir / "source-locations.jsonl")
    build_manifest(compounds, doc_count, symbol_count, 0, juce_source.commit,
                   output_root / "manifest.json")

    # ---- 10. Build search DB ----
    build_search_db(index_dir / "symbols.jsonl", index_dir / "search.sqlite")

    # ---- 11. Validate output ----
    validation = validate_output(output_root)
    stats["output_validation"] = {
        "passed": validation.passed,
        "errors": validation.statistics.get("errors", 0),
        "warnings": validation.statistics.get("warnings", 0),
    }
    if not validation.passed:
        raise GenerationError(
            f"Output validation failed with {validation.statistics.get('errors', 0)} errors"
        )

    # ---- 12. Publish ----
    publish_result = publish_release(
        output_root, output_root,
        juce_source.commit,
        release=config.release,
    )
    stats["published"] = publish_result.published

    # Write generation report
    reports_dir = output_root / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "generation.json").write_text(
        _json.dumps(stats, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return stats
