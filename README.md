# JUCE Agent Reference Generator

Generates a deterministic, machine-readable API reference from a local JUCE
checkout using the official Doxygen configuration.

## Purpose

This tool produces a structured Markdown reference for programming agents
(LLMs, coding assistants) to reliably answer questions about JUCE APIs,
examples, and source locations.

## Requirements

- **Python** 3.12+
- **Doxygen** 1.9.5 (must match `toolchain.lock.json`)
- **Git** (for JUCE checkout validation)
- **SQLite** FTS5 support (for search index)

## Quick Start

```powershell
# Check your environment
juce-doc doctor --juce-root D:\SDK\JUCE

# Generate the reference
juce-doc generate --juce-root D:\SDK\JUCE --output D:\project\juce-reference

# Run the full verification pipeline
juce-doc all --juce-root D:\SDK\JUCE --output D:\project\juce-reference
```

## Commands

| Command          | Purpose                                          |
|------------------|--------------------------------------------------|
| `doctor`         | Check environment and JUCE checkout              |
| `generate`       | Generate the full JUCE reference                 |
| `validate`       | Validate generated output                        |
| `verify`         | Verify release against current JUCE checkout     |
| `symbol`         | Look up a symbol by qualified name               |
| `show`           | Show details for a specific symbol               |
| `search`         | Full-text search across API and examples         |
| `examples`       | Find official examples using a symbol            |
| `source`         | Locate declaration and definition                |
| `related`        | Find related symbols                             |
| `rebuild-index`  | Rebuild SQLite FTS5 cache from text indexes      |
| `smoke`          | Run smoke tests on generated reference           |
| `determinism`    | Run determinism tests                            |
| `test`           | Run local test suite (pytest + ruff + mypy)      |
| `all`            | Complete unified verification pipeline           |

## Output Structure

```
juce-reference/
├── README.md
├── AGENTS.md
├── docs.lock.json
├── manifest.json
├── current.json
├── releases/<commit>/
├── reference/
│   ├── INDEX.md
│   ├── modules/
│   ├── types/
│   ├── namespaces/
│   ├── pages/
│   └── files/
├── guides/
├── examples/
│   ├── INDEX.md
│   └── <category>.md
├── index/
│   ├── symbols.tsv
│   ├── symbols.jsonl
│   ├── relationships.jsonl
│   ├── examples.jsonl
│   ├── source-locations.jsonl
│   └── search.sqlite
└── reports/
    ├── validation.json
    ├── generation.json
    └── doxygen-warnings.log
```

## Architecture

```
JUCE checkout → Doxygen XML → XML Schema Validation → Canonical IR
→ Path Mapper → Markdown Renderer → Symbol & Relationship Indexes
→ Search Database → Output Validation → Atomic Publish
```

## V1 Known Exclusions

These capabilities are explicitly outside V1 scope (per `plan.md`):

- JUCE tutorial website crawling
- `docs.juce.com` HTML scraping
- JUCE forum ingestion
- Vector databases / embedding search
- MCP Server / HTTP Server / Web UI
- AI-generated summaries or examples
- Clang-based or Tree-sitter full-project indexing
- `JUCE/extras` deep analysis
- Multi-version JUCE hosting

## License

MIT
