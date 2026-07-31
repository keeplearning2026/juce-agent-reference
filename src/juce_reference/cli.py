"""CLI entry point — `juce-doc` and `python -m juce_reference`.

All commands route through here. Every public command is wired to real
business logic — no placeholder "not yet implemented" stubs remain.
"""

from __future__ import annotations

import json as _json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated, Any

import typer

from juce_reference.config import GeneratorConfig
from juce_reference.doctor import doctor_report_json, run_doctor
from juce_reference.errors import JuceReferenceError
from juce_reference.generator import generate
from juce_reference.logging import setup_logging
from juce_reference.output_validator import validate_output as _validate_output
from juce_reference.search import search_symbol as _search_symbol
from juce_reference.smoke_test import run_smoke_tests
from juce_reference.source import validate_juce_source
from juce_reference.util.json_io import json_lines

app = typer.Typer(
    name="juce-doc",
    help="JUCE Agent Reference Generator",
    no_args_is_help=True,
)

# ---- Shared option types ----
_JuceRoot = Annotated[
    str | None,
    typer.Option("--juce-root", help="Path to local JUCE checkout", envvar="JUCE_ROOT"),
]
_Output = Annotated[
    str | None,
    typer.Option("--output", help="Output directory", envvar="JUCE_REFERENCE_OUTPUT"),
]
_Reference = Annotated[
    str | None,
    typer.Option("--reference", help="Existing reference directory", envvar="JUCE_REFERENCE"),
]
_Json = Annotated[bool, typer.Option("--json", help="Output machine-readable JSON")]
_Limit = Annotated[int, typer.Option("--limit", min=1, max=100)]
_Verbose = Annotated[bool, typer.Option("--verbose", "-v")]
_NoColor = Annotated[bool, typer.Option("--no-color")]

_repo_root = Path(__file__).resolve().parent.parent.parent


def _resolve_reference(raw: str | None) -> Path:
    """Resolve ``--reference`` to a directory that contains ``index/search.sqlite``.

    1. If the path already contains ``index/search.sqlite``, return it as-is.
    2. If the path contains ``current.json``, follow it into ``releases/<commit>``.
    3. If the path contains a ``releases/`` child dir, pick the newest by mtime.
    4. Otherwise return the path unchanged (caller will report the missing file).
    """
    if raw is None:
        raise typer.Exit(code=2)

    path = Path(raw).resolve()

    if (path / "index" / "search.sqlite").is_file():
        return path

    current_json = path / "current.json"
    if current_json.is_file():
        try:
            data: dict[str, str] = _json.loads(current_json.read_text(encoding="utf-8"))
            rel: str = data.get("path", "")
            resolved: Path = path / rel
            if (resolved / "index" / "search.sqlite").is_file():
                return resolved
        except (KeyError, ValueError, OSError):
            pass

    releases_dir = path / "releases"
    if releases_dir.is_dir():
        dirs = sorted(
            [d for d in releases_dir.iterdir() if d.is_dir()],
            key=lambda d: d.stat().st_mtime, reverse=True,
        )
        if dirs:
            return dirs[0]

    return path


def _enrich(result: dict[str, Any], ref_root: Path) -> dict[str, Any]:
    """Add ``absolute_path`` with forward slashes, using the canonical
    ``JUCE_REFERENCE/current/``-based path when available.

    Removes redundant fields (short_name, owner, documented, access) from
    output to keep JSON response lean for agents.
    """
    # Use current/ symlink path when available: shorter, no commit hash.
    juce_ref = os.environ.get("JUCE_REFERENCE")
    base = Path(juce_ref).resolve() if juce_ref else ref_root
    current = base / "current"
    if current.is_dir():
        base = current

    doc_path = result.pop("documentation_path", "") or result.pop("path", "")
    if doc_path:
        result["absolute_path"] = (base / doc_path).as_posix()

    # Source-file paths (relative to JUCE checkout, not reference root).
    juce_root = _resolve_juce_root()
    for key in ("file", "body_file"):
        src = result.get(key, "")
        if src and juce_root:
            result[f"absolute_{key}"] = (juce_root / src).as_posix()

    # Remove internal fields agents don't need.
    for field in (
        "short_name", "owner", "documented", "access",
        "documentation_path", "path",
        "file", "body_file",
        "refid", "column",
        "source_refid", "target_refid",
    ):
        result.pop(field, None)

    return result


def _resolve_juce_root() -> Path | None:
    """Return the JUCE checkout root from JUCE_ROOT env var."""
    env = os.environ.get("JUCE_ROOT")
    if env:
        p = Path(env).resolve()
        if p.is_dir():
            return p
    return None


# ==================================================================
# doctor
# ==================================================================
@app.command("doctor")
def cmd_doctor(
    juce_root: _JuceRoot = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Check environment and JUCE checkout."""
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None:
        raise typer.Exit(code=2)
    root = Path(juce_root).resolve()

    # Load lock to verify Doxygen version.
    lock_path = _repo_root / "toolchain.lock.json"
    expected_doxygen: str | None = None
    if lock_path.is_file():
        lock = _json.loads(lock_path.read_text(encoding="utf-8"))
        expected_doxygen = lock.get("doxygen", {}).get("version")

    try:
        report = run_doctor(root, expected_doxygen=expected_doxygen)
    except JuceReferenceError as exc:
        err_data = {"passed": False, "error": str(exc), "exit_code": exc.exit_code,
                    "phase": exc.phase, "suggestion": exc.suggestion}
        typer.echo(_json.dumps(err_data, indent=2, ensure_ascii=False), err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    # Also validate the JUCE source.
    try:
        src = validate_juce_source(root)
        typer.echo(_json.dumps({"juce_commit": src.commit, "juce_dirty": src.dirty}, indent=2))
    except JuceReferenceError as exc:
        typer.echo(_json.dumps({"juce_error": str(exc)}, indent=2), err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    typer.echo(doctor_report_json(report))
    if not report.passed:
        raise typer.Exit(code=3)


# ==================================================================
# setup
# ==================================================================
@app.command("setup")
def cmd_setup(
    juce_root: _JuceRoot = None,
    reference: _Reference = None,
) -> None:
    """Persist JUCE_ROOT and JUCE_REFERENCE env vars for future sessions.

    Usage: juce-doc setup --juce-root <path> --reference <path>
    """
    if juce_root is None or reference is None:
        typer.echo("Usage: juce-doc setup --juce-root <path> --reference <path>",
                   err=True)
        raise typer.Exit(code=2)

    juce = str(Path(juce_root).resolve())
    ref = str(Path(reference).resolve())

    # Persist to user env (survives reboots, no admin needed).
    subprocess.run(["setx", "JUCE_ROOT", juce], capture_output=True)
    subprocess.run(["setx", "JUCE_REFERENCE", ref], capture_output=True)

    typer.echo(f"JUCE_ROOT      = {juce}")
    typer.echo(f"JUCE_REFERENCE  = {ref}")
    typer.echo("")
    typer.echo("Env vars persisted for future sessions.")
    typer.echo("Restart your terminal or run:")
    typer.echo(f'  $env:JUCE_ROOT = "{juce}"')
    typer.echo(f'  $env:JUCE_REFERENCE = "{ref}"')

# ==================================================================
@app.command("generate")
def cmd_generate(
    juce_root: _JuceRoot = None,
    output: _Output = None,
    allow_dirty: Annotated[bool, typer.Option("--allow-dirty")] = False,
    release: Annotated[bool, typer.Option("--release")] = False,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Generate the full JUCE agent reference from Doxygen XML."""
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None or output is None:
        typer.echo("--juce-root and --output are required", err=True)
        raise typer.Exit(code=2)

    cfg = GeneratorConfig(
        juce_root=Path(juce_root).resolve(),
        output_root=Path(output).resolve(),
        allow_dirty=allow_dirty,
        release=release,
    )
    stats = generate(cfg)
    typer.echo(_json.dumps(stats, indent=2, ensure_ascii=False))


# ==================================================================
# validate
# ==================================================================
@app.command("validate")
def cmd_validate(
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Validate generated reference output."""
    setup_logging(verbose=verbose, no_color=no_color)
    if reference is None:
        raise typer.Exit(code=2)
    root = _resolve_reference(reference)
    if not root.is_dir():
        typer.echo(f"Reference directory not found: {root}", err=True)
        raise typer.Exit(code=2)
    report = _validate_output(root)
    typer.echo(_json.dumps({"passed": report.passed, "statistics": report.statistics,
                            "issues": [{"severity": i.severity, "code": i.code,
                                        "message": i.message, "path": i.path}
                                       for i in report.issues]}, indent=2, ensure_ascii=False))
    if not report.passed:
        raise typer.Exit(code=9)


# ==================================================================
# verify
# ==================================================================
@app.command("verify")
def cmd_verify(
    juce_root: _JuceRoot = None,
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Verify reference against current JUCE checkout."""
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None or reference is None:
        raise typer.Exit(code=2)
    root = _resolve_reference(reference)
    issues: list[str] = []

    # Check manifest.json
    manifest_path = root / "manifest.json"
    if manifest_path.is_file():
        manifest = _json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_commit = manifest.get("juce_commit", "")
        juce_src = validate_juce_source(Path(juce_root).resolve())
        if juce_src.commit != expected_commit:
            issues.append(f"JUCE commit mismatch: ref={expected_commit} "
                          f"actual={juce_src.commit}")
    else:
        issues.append("manifest.json missing")

    # Check docs.lock.json
    lock_path = root / "docs.lock.json"
    if lock_path.is_file():
        lock = _json.loads(lock_path.read_text(encoding="utf-8"))
        lock_commit = lock.get("juce", {}).get("commit", "")
        juce_src_2 = validate_juce_source(Path(juce_root).resolve())
        if juce_src_2.commit != lock_commit:
            issues.append(f"docs.lock.json commit mismatch: "
                          f"lock={lock_commit} actual={juce_src_2.commit}")
    else:
        issues.append("docs.lock.json missing")

    # Check current.json points to existing release
    current_path = root / "current.json"
    if current_path.is_file():
        cur = _json.loads(current_path.read_text(encoding="utf-8"))
        release_dir = root / cur.get("path", "")
        if not release_dir.is_dir():
            issues.append(f"current.json points to nonexistent release: {cur.get('path')}")

    if issues:
        for i in issues:
            typer.echo(f"[FAIL] {i}", err=True)
        raise typer.Exit(code=14)
    typer.echo(_json.dumps({"verified": True, "commit": expected_commit}))


# ==================================================================
# symbol
# ==================================================================
@app.command("symbol")
def cmd_symbol(
    query: Annotated[str, typer.Argument(help="Symbol name or prefix")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
) -> None:
    """Look up a symbol by qualified name."""
    if reference is None:
        raise typer.Exit(code=2)
    ref_root = _resolve_reference(reference)
    db = ref_root / "index" / "search.sqlite"
    results = _search_symbol(query, db, limit=limit)
    if json_mode:
        output = [_enrich({"symbol": r.symbol, "kind": r.kind, "module": r.module,
                           "documentation_path": r.documentation_path, "anchor": r.anchor,
                           "brief": r.brief, "score": r.score}, ref_root)
                  for r in results]
        typer.echo(_json.dumps(output, indent=2, ensure_ascii=False))
    else:
        for r in results:
            typer.echo(f"{r.symbol}  [{r.kind}]  {r.module or ''}")
            if r.brief:
                typer.echo(f"  {r.brief[:120]}")


# ==================================================================
# show
# ==================================================================
@app.command("show")
def cmd_show(
    symbol: Annotated[str, typer.Argument(help="Fully qualified symbol")],
    reference: _Reference = None,
    json_mode: _Json = False,
    print_content: Annotated[bool, typer.Option("--print-content")] = False,
) -> None:
    """Show details for a specific symbol."""
    if reference is None:
        raise typer.Exit(code=2)
    ref_root = _resolve_reference(reference)
    symbols_path = ref_root / "index" / "symbols.jsonl"
    match = None
    for rec in json_lines(symbols_path):
        if rec.get("symbol") == symbol:
            match = rec
            break
    if match is None:
        typer.echo(f"Symbol not found: {symbol}", err=True)
        raise typer.Exit(code=7)

    if json_mode:
        _enrich(match, ref_root)
        typer.echo(_json.dumps(match, indent=2, ensure_ascii=False))
        return

    typer.echo(f"symbol:    {match['symbol']}")
    typer.echo(f"kind:      {match.get('kind', '')}")
    typer.echo(f"module:    {match.get('module', '')}")
    typer.echo(f"path:      {match.get('documentation_path', '')}")
    typer.echo(f"anchor:    {match.get('anchor', '')}")
    typer.echo(f"signature: {match.get('signature', '')}")
    typer.echo(f"brief:     {match.get('brief', '')}")

    if print_content and match.get("documentation_path"):
        md = ref_root / match["documentation_path"]
        if md.is_file():
            typer.echo("\n--- content ---")
            typer.echo(md.read_text(encoding="utf-8")[:2000])


# ==================================================================
# search
# ==================================================================
@app.command("search")
def cmd_search(
    query: Annotated[str, typer.Argument(help="Natural-language or symbol query")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
    kind: Annotated[str | None, typer.Option("--kind")] = None,
    module: Annotated[str | None, typer.Option("--module")] = None,
    public_only: Annotated[bool, typer.Option("--public-only")] = False,
) -> None:
    """Full-text search across symbols, documentation, and examples."""
    if reference is None:
        raise typer.Exit(code=2)
    ref_root = _resolve_reference(reference)
    db = ref_root / "index" / "search.sqlite"
    if not db.is_file():
        typer.echo("search.sqlite not found. Run 'juce-doc rebuild-index' first.", err=True)
        raise typer.Exit(code=7)
    results = _search_symbol(query, db, limit=limit, kind_filter=kind,
                              module_filter=module, public_only=public_only)
    if json_mode:
        output = [_enrich({"symbol": r.symbol, "kind": r.kind, "module": r.module,
                           "documentation_path": r.documentation_path, "anchor": r.anchor,
                           "brief": r.brief, "score": r.score,
                           "match_type": r.match_type}, ref_root)
                  for r in results]
        typer.echo(_json.dumps(output, indent=2, ensure_ascii=False))
    else:
        for r in results:
            typer.echo(f"{r.symbol}  [{r.kind}]  {r.module or ''}  ({r.match_type})")
            if r.brief:
                typer.echo(f"  {r.brief[:120]}")


# ==================================================================
# examples
# ==================================================================
@app.command("examples")
def cmd_examples(
    symbol: Annotated[str, typer.Argument(help="Symbol to find examples for")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
) -> None:
    """Find official JUCE examples using a symbol."""
    if reference is None:
        raise typer.Exit(code=2)
    ref_root = _resolve_reference(reference)
    examples_path = ref_root / "index" / "examples.jsonl"
    if not examples_path.is_file():
        typer.echo("examples.jsonl not found", err=True)
        raise typer.Exit(code=7)
    results = []
    for rec in json_lines(examples_path):
        if rec.get("symbol") == symbol:
            results.append(_enrich(dict(rec), ref_root))
        if len(results) >= limit:
            break
    if json_mode:
        typer.echo(_json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            typer.echo(
                f"{r['example_name']}  [{r['category']}]  "
                f"{r['file']}:{r['line']}  ({r['confidence']})")


# ==================================================================
# source
# ==================================================================
@app.command("source")
def cmd_source(
    symbol: Annotated[str, typer.Argument(help="Symbol to locate in source")],
    reference: _Reference = None,
    json_mode: _Json = False,
) -> None:
    """Locate declaration and definition of a symbol."""
    if reference is None:
        raise typer.Exit(code=2)
    ref_root = _resolve_reference(reference)
    sl_path = ref_root / "index" / "source-locations.jsonl"
    if not sl_path.is_file():
        typer.echo("source-locations.jsonl not found", err=True)
        raise typer.Exit(code=7)
    for rec in json_lines(sl_path):
        if rec.get("symbol") == symbol:
            if json_mode:
                typer.echo(_json.dumps(_enrich(dict(rec), ref_root),
                                       indent=2, ensure_ascii=False))
            else:
                typer.echo(f"symbol:     {rec['symbol']}")
                typer.echo(f"file:       {rec.get('file', '')}")
                typer.echo(f"line:       {rec.get('line', '')}")
                typer.echo(f"column:     {rec.get('column', '')}")
                body = rec.get("body_file")
                if body:
                    typer.echo(f"body file:  {body}")
                    typer.echo(f"body start: {rec.get('body_start', '')}")
                else:
                    typer.echo("definition: Definition not resolved")
            return
    typer.echo(f"Symbol not found: {symbol}", err=True)
    raise typer.Exit(code=7)


# ==================================================================
# related
# ==================================================================
@app.command("related")
def cmd_related(
    symbol: Annotated[str, typer.Argument(help="Symbol to find related items for")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
) -> None:
    """Find related symbols (bases, derived, module, examples)."""
    if reference is None:
        raise typer.Exit(code=2)
    ref_root = _resolve_reference(reference)
    rel_path = ref_root / "index" / "relationships.jsonl"
    if not rel_path.is_file():
        typer.echo("relationships.jsonl not found", err=True)
        raise typer.Exit(code=7)
    results = []
    for rec in json_lines(rel_path):
        if rec.get("source") == symbol or rec.get("target") == symbol:
            results.append(_enrich(dict(rec), ref_root))
        if len(results) >= limit:
            break
    if json_mode:
        typer.echo(_json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            typer.echo(f"{r['type']}: {r['source']} → {r['target']}  ({r.get('confidence','')})")


# ==================================================================
# rebuild-index
# ==================================================================
@app.command("rebuild-index")
def cmd_rebuild_index(
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Rebuild SQLite FTS5 search cache from text indexes."""
    setup_logging(verbose=verbose, no_color=no_color)
    if reference is None:
        raise typer.Exit(code=2)
    ref_root = _resolve_reference(reference)
    symbols_path = ref_root / "index" / "symbols.jsonl"
    if not symbols_path.is_file():
        typer.echo("symbols.jsonl not found", err=True)
        raise typer.Exit(code=7)
    db_path = ref_root / "index" / "search.sqlite"
    from juce_reference.alias_loader import load_aliases
    from juce_reference.search import build_search_db

    # Collect valid symbols from symbols.jsonl before loading aliases.
    all_syms = frozenset(s["symbol"] for s in json_lines(symbols_path))

    aliases_path = _repo_root / "config" / "aliases.yml"
    alias_cfg = load_aliases(aliases_path, all_syms) if aliases_path.is_file() else None
    count = build_search_db(symbols_path, db_path, alias_config=alias_cfg,
                            reference_root=ref_root)
    typer.echo(f"Rebuilt search index: {count} symbols")


# ==================================================================
# smoke
# ==================================================================
@app.command("smoke")
def cmd_smoke(
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run smoke tests on a generated reference."""
    setup_logging(verbose=verbose, no_color=no_color)
    if reference is None:
        raise typer.Exit(code=2)
    report = run_smoke_tests(_resolve_reference(reference))
    typer.echo(_json.dumps(report, indent=2, ensure_ascii=False))
    if not report["passed"]:
        raise typer.Exit(code=10)


# ==================================================================
# determinism
# ==================================================================
@app.command("determinism")
def cmd_determinism(
    juce_root: _JuceRoot = None,
    output: _Output = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run determinism tests (generate twice, compare outputs)."""
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None or output is None:
        raise typer.Exit(code=2)

    cfg = GeneratorConfig(
        juce_root=Path(juce_root).resolve(),
        output_root=Path(output).resolve(),
    )
    out1 = Path(output).resolve() / ".determinism_run1"
    out2 = Path(output).resolve() / ".determinism_run2"
    cfg1 = GeneratorConfig(juce_root=cfg.juce_root, output_root=out1)
    cfg2 = GeneratorConfig(juce_root=cfg.juce_root, output_root=out2)
    try:
        stats_a = generate(cfg1)
        stats_b = generate(cfg2)
        from juce_reference.determinism import compare_generations, compare_sqlite_logical
        cand_a = Path(stats_a["candidate_path"])
        cand_b = Path(stats_b["candidate_path"])
        result = compare_generations(cand_a, cand_b)
        if not result["passed"] or result.get("files_compared", 0) == 0:
            typer.echo(_json.dumps(result, indent=2, ensure_ascii=False), err=True)
            raise typer.Exit(code=12)
        sqla = cand_a / "index" / "search.sqlite"
        sqlb = cand_b / "index" / "search.sqlite"
        if sqla.is_file() and sqlb.is_file():
            sql_cmp = compare_sqlite_logical(sqla, sqlb)
            if not sql_cmp["passed"]:
                typer.echo(_json.dumps(sql_cmp, indent=2), err=True)
                raise typer.Exit(code=12)
        typer.echo(_json.dumps(result, indent=2, ensure_ascii=False))
    finally:
        shutil.rmtree(out1, ignore_errors=True)
        shutil.rmtree(out2, ignore_errors=True)


# ==================================================================
# test
# ==================================================================
@app.command("test")
def cmd_test(
    unit_only: Annotated[bool, typer.Option("--unit-only")] = False,
    integration: Annotated[bool, typer.Option("--integration")] = False,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run the test suite (pytest + ruff + mypy)."""
    setup_logging(verbose=verbose, no_color=no_color)
    passed = True

    r = subprocess.run(["python", "-m", "pytest", "tests/", "-q"],
                        cwd=str(_repo_root), text=True)
    if r.returncode != 0:
        typer.echo("pytest FAILED", err=True)
        passed = False

    r = subprocess.run(["python", "-m", "ruff", "check", "."],
                        cwd=str(_repo_root), text=True, capture_output=True)
    if r.returncode != 0:
        typer.echo(f"ruff:\n{r.stderr or r.stdout}", err=True)
        passed = False

    r = subprocess.run(["python", "-m", "mypy", "src", "--show-error-codes"],
                        cwd=str(_repo_root), text=True, capture_output=True)
    if r.returncode != 0:
        typer.echo(f"mypy:\n{r.stderr or r.stdout}", err=True)
        passed = False

    if not passed:
        raise typer.Exit(code=1)
    typer.echo("[OK] pytest, ruff, mypy all passed")


# ==================================================================
# all — the single unified verification pipeline
# ==================================================================
@app.command("all")
def cmd_all(
    juce_root: _JuceRoot = None,
    output: _Output = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run the complete unified verification pipeline.

    This is the single command that certifies a V1 release.
    If any step fails, the command exits non-zero immediately.
    """
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None or output is None:
        typer.echo("--juce-root and --output are required", err=True)
        raise typer.Exit(code=2)

    juce = Path(juce_root).resolve()
    out = Path(output).resolve()

    def _run(label: str, args: list[str], exit_code: int) -> None:
        typer.echo(f"\n=== {label} ===", err=True)
        r = subprocess.run(args, cwd=str(_repo_root), text=True,
                           capture_output=(label != "pytest"))
        if r.returncode != 0:
            typer.echo(r.stderr or r.stdout, err=True)
            typer.echo(f"[FAIL] {label}", err=True)
            raise typer.Exit(code=exit_code)
        typer.echo(f"[OK] {label}")

    # 1. doctor with locked Doxygen version
    _run("doctor", ["python", "-m", "juce_reference", "doctor",
                     "--juce-root", str(juce)], 3)

    # 2. unit tests
    _run("pytest", ["python", "-m", "pytest", "tests/", "-q"], 1)

    # 3. ruff
    _run("ruff", ["python", "-m", "ruff", "check", "."], 1)

    # 4. mypy
    _run("mypy", ["python", "-m", "mypy", "src", "--show-error-codes"], 1)

    # 5. generate real reference
    typer.echo("\n=== generate ===", err=True)
    cfg = GeneratorConfig(
        juce_root=juce, output_root=out,
        aliases_file=_repo_root / "config" / "aliases.yml",
        release=True,
    )
    try:
        stats = generate(cfg)
        candidate = Path(stats["candidate_path"])
        typer.echo(f"[OK] generate — {stats.get('parsed_compounds', 0)} compounds")
    except Exception as exc:
        typer.echo(f"[FAIL] generate: {exc}", err=True)
        raise typer.Exit(code=8) from exc

    # 6. validate output (use real candidate path from generate result)
    _run("validate", ["python", "-m", "juce_reference", "validate",
                       "--reference", str(candidate)], 9)

    # 7. smoke (use real candidate path)
    _run("smoke", ["python", "-m", "juce_reference", "smoke",
                    "--reference", str(candidate)], 10)

    # 8. search quality: exact + alias + concept queries
    typer.echo("\n=== search_quality ===", err=True)
    db = candidate / "index" / "search.sqlite"
    search_fail = False
    if db.is_file():
        checks = [
            ("exact rank 1", "juce::AudioProcessor", "juce::AudioProcessor", 1),
            ("alias APVTS top 3", "APVTS", "juce::AudioProcessorValueTreeState", 3),
            ("concept save state top 5", "save plugin parameter state",
             "juce::AudioProcessorValueTreeState", 5),
        ]
        for name, query_str, expected, top_k in checks:
            results = _search_symbol(query_str, db, limit=top_k)
            found = any(r.symbol == expected for r in results)
            if found:
                typer.echo(f"[OK] search_quality — {name}")
            else:
                typer.echo(
                    f"[FAIL] search_quality — {name}: '{expected}' not in "
                    f"top {top_k}, got {[r.symbol for r in results[:top_k]]}",
                    err=True)
                search_fail = True
    else:
        typer.echo("[FAIL] search_quality — search.sqlite missing", err=True)
        search_fail = True
    if search_fail:
        raise typer.Exit(code=11)

    # 9. determinism: generate twice, compare byte-for-byte
    typer.echo("\n=== determinism ===", err=True)
    run_a = out / ".determinism_run_a"
    run_b = out / ".determinism_run_b"
    cfg_a = GeneratorConfig(juce_root=juce, output_root=run_a)
    cfg_b = GeneratorConfig(juce_root=juce, output_root=run_b)
    try:
        stats_a = generate(cfg_a)
        stats_b = generate(cfg_b)
        from juce_reference.determinism import compare_generations, compare_sqlite_logical
        cand_a = Path(stats_a["candidate_path"])
        cand_b = Path(stats_b["candidate_path"])
        comp = compare_generations(cand_a, cand_b)
        if not comp["passed"] or comp.get("files_compared", 0) == 0:
            typer.echo(
                f"[FAIL] determinism — compared={comp.get('files_compared', 0)} "
                f"diffs={comp.get('differences', [])}", err=True)
            raise typer.Exit(code=12)
        sqla = cand_a / "index" / "search.sqlite"
        sqlb = cand_b / "index" / "search.sqlite"
        if sqla.is_file() and sqlb.is_file():
            sql_cmp = compare_sqlite_logical(sqla, sqlb)
            if not sql_cmp["passed"]:
                typer.echo(f"[FAIL] determinism sqlite — {sql_cmp.get('differences')}", err=True)
                raise typer.Exit(code=12)
        typer.echo(f"[OK] determinism — {comp.get('files_compared', 0)} files identical")
    finally:
        shutil.rmtree(run_a, ignore_errors=True)
        shutil.rmtree(run_b, ignore_errors=True)

    # 10. verify (commit, lock, file integrity)
    _run("verify", ["python", "-m", "juce_reference", "verify",
                     "--juce-root", str(juce), "--reference", str(candidate)], 14)

    # 11. Git cleanliness
    typer.echo("\n=== git_clean ===", err=True)
    r = subprocess.run(["git", "status", "--porcelain"], cwd=str(_repo_root),
                       text=True, capture_output=True)
    if r.stdout.strip():
        typer.echo(f"[FAIL] Git not clean:\n{r.stdout}", err=True)
        raise typer.Exit(code=15)
    typer.echo("[OK] git_clean")

    # 12. Blocker absence
    typer.echo("\n=== final_checks ===", err=True)
    blocker_path = _repo_root / ".agent" / "blocker.json"
    if blocker_path.is_file():
        typer.echo("[FAIL] blocker.json exists", err=True)
        raise typer.Exit(code=20)
    typer.echo("[OK] no blocker")

    # All passed
    juce_src = validate_juce_source(juce)
    result = {
        "passed": True,
        "juce_commit": juce_src.commit,
        "tests": {
            "pytest": "passed",
            "ruff": "passed",
            "mypy": "passed",
            "smoke": "passed",
            "search_quality": "passed",
            "determinism": "passed",
            "verify": "passed",
        },
    }
    typer.echo(_json.dumps(result, indent=2, ensure_ascii=False))


# ==================================================================
# main
# ==================================================================
def main() -> None:
    """Entry point for console_scripts."""
    try:
        app()
    except typer.Exit:
        raise
    except JuceReferenceError as exc:
        typer.echo(f"Error ({exc.exit_code}): {exc}", err=True)
        raise typer.Exit(code=exc.exit_code) from exc
    except Exception as exc:
        typer.echo(f"Unexpected error: {exc}", err=True)
        raise typer.Exit(code=1) from exc
