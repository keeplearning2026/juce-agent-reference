"""Generation orchestrator — the full pipeline from JUCE checkout to output.

Sequence:
1. validate source    6. path mapping      11. examples scan
2. run Doxygen        7. render Markdown    12. search DB
3. validate XML       8. repo docs          13. validate output
4. parse XML          9. symbol indexes     14. docs.lock.json
5. canonical IR      10. relationship idx   15. publish (atomic)
"""

from __future__ import annotations

import json as _json
import time
from pathlib import Path
from typing import Any

from juce_reference.alias_loader import load_aliases
from juce_reference.config import GeneratorConfig
from juce_reference.doxygen_runner import classify_doxygen_warnings, run_doxygen
from juce_reference.errors import GenerationError
from juce_reference.example_scanner import (
    build_examples_jsonl,
    build_examples_markdown,
    find_example_symbols,
    scan_examples,
)
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
from juce_reference.xml_parser import get_warnings, parse_compound, parse_index, reset_warnings
from juce_reference.xml_validator import validate_xml_output


def generate(config: GeneratorConfig) -> dict[str, Any]:
    """Run the complete generation pipeline into a build candidate directory,
    then atomically publish to the release root.

    The intermediate candidate directory is ``.build/<build-id>/candidate/``.
    The final release directory is ``<output_root>/releases/<commit>/``.
    """
    stats: dict[str, Any] = {
        "started_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "config": {
            "juce_root": str(config.juce_root),
            "output_root": str(config.output_root),
            "allow_dirty": config.allow_dirty,
        },
    }

    # ---- 0. Reset warning accumulators ----
    reset_warnings()

    # ---- 1. Validate JUCE source ----
    juce_source = validate_juce_source(config.juce_root, allow_dirty=config.allow_dirty)
    stats["juce_commit"] = juce_source.commit
    stats["juce_dirty"] = juce_source.dirty

    # ---- 2. Build directories ----
    build_id = sha256_hex(f"{juce_source.commit}-{time.monotonic()}")[:12]
    build_dir = config.juce_root.parent / ".build" / build_id
    candidate_dir = build_dir / "candidate"
    candidate_dir.mkdir(parents=True, exist_ok=True)
    output_root = config.output_root

    # ---- 3. Run Doxygen ----
    doxy_result = run_doxygen(juce_source, build_dir)
    stats["doxygen_warnings"] = classify_doxygen_warnings(doxy_result.warnings_file)

    # ---- 4. Validate XML ----
    xml_report = validate_xml_output(doxy_result.xml_dir)
    if not xml_report.all_valid:
        raise GenerationError(
            f"XML validation failed: {xml_report.valid_compound_count}/"
            f"{xml_report.compound_count} valid, {len(xml_report.issues)} issues"
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
    reference_dir = candidate_dir / "reference"
    reference_dir.mkdir(parents=True, exist_ok=True)
    doc_count = 0
    for compound in compounds:
        target = path_map.compounds.get(compound.refid)
        if not target:
            continue
        doc = render_compound(compound, path_map, juce_commit=juce_source.commit)
        out_path = candidate_dir / target.path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(doc.content, encoding="utf-8")
        doc_count += 1

    # ---- 8. Import repository docs ----
    repo_docs = import_repository_docs(juce_source)
    guides_dir = candidate_dir / "guides"
    guides_dir.mkdir(parents=True, exist_ok=True)
    for rd in repo_docs:
        out_path = candidate_dir / rd.output_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rd.content, encoding="utf-8")
    stats["guides_imported"] = len(repo_docs)

    # ---- 9. Scan examples ----
    example_count = 0
    example_uses: list[Any] = []
    known_symbols = frozenset(c.qualified_name for c in compounds)
    known_symbols |= frozenset(m.qualified_name for c in compounds for m in c.members)
    if juce_source.examples_dir and juce_source.examples_dir.is_dir():
        examples = scan_examples(juce_source.examples_dir)
        example_uses = find_example_symbols(examples, juce_source.examples_dir, known_symbols)
        # Write examples.jsonl
        examples_dir = candidate_dir / "index"
        examples_dir.mkdir(parents=True, exist_ok=True)
        build_examples_jsonl([], example_uses, examples_dir / "examples.jsonl")
        # Write example navigation pages
        ex_nav_dir = candidate_dir / "examples"
        ex_nav_dir.mkdir(parents=True, exist_ok=True)
        build_examples_markdown(examples, example_uses, ex_nav_dir)
        example_count = len(examples)
    stats["examples_found"] = example_count
    stats["example_symbol_uses"] = len(example_uses)

    # ---- 10. Build symbol indexes ----
    index_dir = candidate_dir / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    path_info = {t.refid: t.path for t in path_map.compounds.values()}
    symbol_count = build_symbols_tsv(compounds, index_dir / "symbols.tsv", path_info)
    build_symbols_jsonl(compounds, index_dir / "symbols.jsonl", path_info)
    build_relationships_jsonl(compounds, index_dir / "relationships.jsonl")
    build_source_locations_jsonl(compounds, index_dir / "source-locations.jsonl")

    # ---- 11. Build search DB with aliases (always load default) ----
    all_syms = frozenset(
        c.qualified_name for c in compounds
    ) | frozenset(
        m.qualified_name for c in compounds for m in c.members
    )
    aliases_path = config.aliases_file or (config.output_root.parent / "config" / "aliases.yml")
    if not aliases_path.is_file():
        # fallback: repo root config/aliases.yml
        aliases_path = Path(__file__).parent.parent.parent / "config" / "aliases.yml"
    alias_config = load_aliases(aliases_path, all_syms) if aliases_path.is_file() else None
    build_search_db(index_dir / "symbols.jsonl", index_dir / "search.sqlite",
                    alias_config=alias_config, reference_root=candidate_dir)

    # ---- 12. Write AGENTS.md and README.md for downstream agents ----
    _write_agents_md(candidate_dir, juce_source.commit, doc_count)
    _write_reference_readme(candidate_dir, juce_source.commit, doc_count,
                            symbol_count, example_count)

    # ---- 13. Write docs.lock.json ----
    _write_docs_lock(candidate_dir, juce_source.commit, juce_source.dirty)

    # ---- 14. Write manifest.json ----
    build_manifest(compounds, doc_count, symbol_count, example_count,
                   juce_source.commit, candidate_dir / "manifest.json")

    # ---- 15. Collect formatting warnings ----
    fmt_warnings = get_warnings()
    reports_dir = candidate_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "formatting-warnings.json").write_text(
        _json.dumps(fmt_warnings, indent=2, ensure_ascii=False), encoding="utf-8")
    stats["formatting_warnings"] = len(fmt_warnings)

    # ---- 16. Write generation report first (required by validator) ----
    _write_generation_report(reports_dir, stats)

    # ---- 17. Validate output ----
    validation = validate_output(candidate_dir)
    stats["output_validation"] = {
        "passed": validation.passed,
        "errors": validation.statistics.get("errors", 0),
        "warnings": validation.statistics.get("warnings", 0),
    }
    # Write validation report
    (reports_dir / "validation.json").write_text(
        _json.dumps({
            "passed": validation.passed,
            "statistics": validation.statistics,
            "issues": [
                {"severity": i.severity, "code": i.code,
                 "message": i.message, "path": i.path, "symbol": i.symbol}
                for i in validation.issues[:500]
            ],
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if not validation.passed:
        raise GenerationError(
            f"Output validation failed with "
            f"{validation.statistics.get('errors', 0)} errors"
        )

    # ---- 17. Publish (atomic) ----
    publish_result = publish_release(
        candidate_dir, output_root,
        juce_source.commit,
        allow_dirty=config.allow_dirty,
        release=config.release,
    )
    stats["published"] = publish_result.published
    stats["candidate_path"] = str(candidate_dir)
    stats["published_path"] = str(publish_result.release_path)

    return stats


# ---- report helper ----

def _write_generation_report(reports_dir: Path, stats: dict[str, Any]) -> None:
    _nondeterministic = {"started_at_iso", "config"}
    det_stats = {k: v for k, v in stats.items() if k not in _nondeterministic}
    (reports_dir / "generation.json").write_text(
        _json.dumps(det_stats, indent=2, ensure_ascii=False), encoding="utf-8")


# ---- docs.lock.json builder ----

def _write_docs_lock(output_dir: Path, commit: str, dirty: bool) -> None:
    import subprocess
    import sys

    from juce_reference import __version__ as gen_ver

    doxy_ver = ""
    try:
        r = subprocess.run(["doxygen", "--version"], capture_output=True, text=True)
        doxy_ver = r.stdout.strip()
    except Exception:
        pass

    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    lock = {
        "schema_version": 1,
        "juce": {"commit": commit, "dirty": dirty},
        "toolchain": {"python": py_ver, "doxygen": doxy_ver, "generator": gen_ver},
        "schemas": {"ir": 1, "markdown": 1, "index": 1},
    }
    (output_dir / "docs.lock.json").write_text(
        _json.dumps(lock, indent=2, ensure_ascii=False), encoding="utf-8")


# ---- AGENTS.md writer (for downstream coding agents) ----

def _write_agents_md(
    output_dir: Path, juce_commit: str, doc_count: int,
) -> None:
    """Write ``AGENTS.md`` — the protocol file that downstream coding
    agents read to learn how to use this reference efficiently."""

    content = f"""# JUCE Agent Reference — Usage Protocol

## Version

JUCE commit: `{juce_commit}`

---

## 1. Never read the whole reference

There are {doc_count} Markdown files under ``reference/``.
**Do not load them all into context.**

Instead, use ``juce-doc`` CLI commands to locate the exact files you need,
then read only those files.

---

## 2. The standard query workflow

When given a JUCE task, follow this order:

### Step 1 — Know the exact symbol name

```powershell
juce-doc show "juce::AudioProcessor" --json
juce-doc show "juce::AudioProcessor" --print-content
```

Returns: kind, module, documentation_path, anchor, signature, brief.

### Step 2 — Only know a partial name

```powershell
juce-doc symbol "Slider" --limit 10 --json
```

Returns all matching qualified symbols.

### Step 3 — Know a concept but not the class name

```powershell
juce-doc search "save plugin parameter state" --limit 5 --json
juce-doc search "DSP processor chain" --limit 10 --json
```

Search covers symbol names, briefs, full Markdown body text,
aliases, and concept tags.

Filter by kind or module:

```powershell
juce-doc search "process audio" --kind function --public-only --limit 20 --json
```

### Step 4 — Find official examples

```powershell
juce-doc examples "juce::AudioProcessorValueTreeState" --json
```

Returns example name, category, source file, line number.

### Step 5 — Locate source files

```powershell
juce-doc source "juce::AudioProcessor::processBlock" --json
```

Returns declaration file/line and definition file/line.
When the definition cannot be resolved reliably, it says
"Definition not resolved" instead of guessing.

### Step 6 — Explore relationships

```powershell
juce-doc related "juce::AudioProcessor" --json
```

Returns base-of, derived-from, member-of, contains, module-of.

### Step 7 — Read only the relevant Markdown

After any query, use the returned ``documentation_path``:

```powershell
Get-Content "$env:JUCE_REFERENCE\\<documentation_path>"
```

---

## 3. Environment setup

Set ``JUCE_REFERENCE`` to point at the release root so you can omit
``--reference``:

```powershell
$Root = "D:\\project\\juce-reference"
$Current = Get-Content "$Root\\current.json" | ConvertFrom-Json
$env:JUCE_REFERENCE = Join-Path $Root $Current.path
```

Or point it at the generated candidate directory directly.

---

## 4. Rules

1. **Do not invent JUCE APIs.** Every API claim must be verifiable
   from this reference or the source at commit ``{juce_commit}``.
2. **Prefer the locked local reference over model memory.**
3. **Use ``search`` to discover symbols, then ``show`` / ``source`` /
   ``examples`` / ``related`` to drill in.**
4. **Read only the Markdown files returned by queries.** Do not
   bulk-load or scan the reference tree.
5. **If a symbol is missing from the index,** it does not exist in
   this JUCE commit. Do not guess it exists.
6. **Use ``--json`` for programmatic consumption.**
"""
    (output_dir / "AGENTS.md").write_text(content, encoding="utf-8")


# ---- README.md writer (reference overview) ----

def _write_reference_readme(
    output_dir: Path,
    juce_commit: str,
    doc_count: int,
    symbol_count: int,
    example_count: int,
) -> None:
    """Write ``README.md`` — a human-readable overview of this
    generated reference."""

    content = f"""# JUCE Agent Reference

Generated from JUCE commit `{juce_commit}`.

## Statistics

| Item | Count |
|------|-------|
| Documents | {doc_count} |
| Symbols | {symbol_count} |
| Examples | {example_count} |

## Directory layout

```
reference/         ← API Markdown (types, modules, namespaces, files, pages)
guides/            ← Imported JUCE repo docs (README, BREAKING_CHANGES, etc.)
examples/          ← Example index by category
  INDEX.md
index/             ← Machine-readable indexes
  symbols.tsv          Tab-separated symbol index
  symbols.jsonl        Newline-delimited JSON symbol index
  relationships.jsonl  Inheritance / containment / member-of
  examples.jsonl       Symbol → example associations
  source-locations.jsonl  Declaration / definition locations
  search.sqlite        SQLite FTS5 full-text search database
reports/            ← Generation and validation reports
  generation.json
  validation.json
docs.lock.json      ← Toolchain version lock
manifest.json       ← Generation manifest
```

## Quick start for agents

See **AGENTS.md** for the usage protocol.

The standard workflow:

```text
search → show → examples → source → related
```

Example:

```powershell
juce-doc search "audio processor" --limit 5 --json
juce-doc show "juce::AudioProcessor" --json
juce-doc examples "juce::AudioProcessor" --json
```

## Rebuilding the search index

```powershell
juce-doc rebuild-index --reference <path>
```

This rebuilds ``index/search.sqlite`` from ``index/symbols.jsonl``
and the rendered Markdown body text.
"""
    (output_dir / "README.md").write_text(content, encoding="utf-8")
