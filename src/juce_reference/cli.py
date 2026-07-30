"""CLI entry point — `juce-doc` and `python -m juce_reference`.

All commands route through here.  The CLI layer is the *only* place
allowed to call ``typer.Exit()``; core modules raise domain exceptions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from juce_reference.doctor import doctor_report_json, run_doctor
from juce_reference.errors import JuceReferenceError
from juce_reference.logging import setup_logging

app = typer.Typer(
    name="juce-doc",
    help="JUCE Agent Reference Generator",
    no_args_is_help=True,
)

# Shared option callbacks ---------------------------------------------------


def _resolve_juce_root(value: str | None) -> Path | None:
    if value is None:
        return None
    return Path(value).resolve()


def _resolve_output(value: str | None) -> Path | None:
    if value is None:
        return None
    return Path(value).resolve()


# Shared options decorator (applied to individual commands for clarity).
_JuceRoot = Annotated[
    str | None,
    typer.Option(
        "--juce-root",
        help="Path to local JUCE checkout",
        envvar="JUCE_ROOT",
    ),
]

_Output = Annotated[
    str | None,
    typer.Option(
        "--output",
        help="Output directory for generated reference",
        envvar="JUCE_REFERENCE_OUTPUT",
    ),
]

_Reference = Annotated[
    str | None,
    typer.Option(
        "--reference",
        help="Existing reference directory to query/verify",
        envvar="JUCE_REFERENCE",
    ),
]

_Json = Annotated[
    bool,
    typer.Option(
        "--json",
        help="Output machine-readable JSON",
    ),
]

_Limit = Annotated[
    int,
    typer.Option(
        "--limit",
        help="Maximum results to return",
        min=1,
        max=100,
    ),
]

_Verbose = Annotated[
    bool,
    typer.Option(
        "--verbose",
        "-v",
        help="Verbose output",
    ),
]

_NoColor = Annotated[
    bool,
    typer.Option(
        "--no-color",
        help="Disable colour output",
    ),
]


# ---------------------------------------------------------------------------
# doctor
# ---------------------------------------------------------------------------


@app.command("doctor")
def cmd_doctor(
    juce_root: _JuceRoot = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Check the environment and JUCE checkout."""
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None:
        raise typer.Exit(code=2)

    root = Path(juce_root).resolve()
    try:
        report = run_doctor(root)
    except JuceReferenceError as exc:
        err_data = {
            "passed": False,
            "error": str(exc),
            "exit_code": exc.exit_code,
            "phase": exc.phase,
            "suggestion": exc.suggestion,
        }
        typer.echo(json.dumps(err_data, indent=2, ensure_ascii=False), err=True)
        raise typer.Exit(code=exc.exit_code) from exc

    typer.echo(doctor_report_json(report))
    if not report.passed:
        raise typer.Exit(code=3)


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------


@app.command("generate")
def cmd_generate(
    juce_root: _JuceRoot = None,
    output: _Output = None,
    allow_dirty: Annotated[
        bool,
        typer.Option("--allow-dirty", help="Allow dirty JUCE checkout"),
    ] = False,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Generate the full JUCE agent reference from Doxygen XML."""
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None or output is None:
        typer.echo("--juce-root and --output are required", err=True)
        raise typer.Exit(code=2)

    typer.echo(
        "Phase 2+: Full generation pipeline not yet implemented. "
        "Run 'juce-doc doctor' to verify environment."
    )


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@app.command("validate")
def cmd_validate(
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Validate generated reference output."""
    setup_logging(verbose=verbose, no_color=no_color)
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 3+: Output validation not yet implemented.")


# ---------------------------------------------------------------------------
# verify
# ---------------------------------------------------------------------------


@app.command("verify")
def cmd_verify(
    juce_root: _JuceRoot = None,
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Verify generated release against current JUCE checkout."""
    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None or reference is None:
        typer.echo("--juce-root and --reference are required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 7+: Version verification not yet implemented.")


# ---------------------------------------------------------------------------
# symbol
# ---------------------------------------------------------------------------


@app.command("symbol")
def cmd_symbol(
    query: Annotated[str, typer.Argument(help="Symbol name or prefix")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
) -> None:
    """Look up a symbol by qualified name."""
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 5+: Symbol lookup not yet implemented.")


# ---------------------------------------------------------------------------
# show
# ---------------------------------------------------------------------------


@app.command("show")
def cmd_show(
    symbol: Annotated[str, typer.Argument(help="Fully qualified symbol")],
    reference: _Reference = None,
    json_mode: _Json = False,
    print_content: Annotated[
        bool,
        typer.Option("--print-content", help="Print Markdown section"),
    ] = False,
) -> None:
    """Show details for a specific symbol."""
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 5+: Show not yet implemented.")


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


@app.command("search")
def cmd_search(
    query: Annotated[str, typer.Argument(help="Natural-language or symbol query")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
    kind: Annotated[
        str | None,
        typer.Option("--kind", help="Filter by kind (class, function, enum, …)"),
    ] = None,
    module: Annotated[
        str | None,
        typer.Option("--module", help="Filter by module name"),
    ] = None,
    public_only: Annotated[
        bool,
        typer.Option("--public-only", help="Only show public symbols"),
    ] = False,
) -> None:
    """Full-text search across symbols, documentation, and examples."""
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 5+: Search not yet implemented.")


# ---------------------------------------------------------------------------
# examples
# ---------------------------------------------------------------------------


@app.command("examples")
def cmd_examples(
    symbol: Annotated[str, typer.Argument(help="Symbol to find examples for")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
) -> None:
    """Find official JUCE examples using a symbol."""
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 6+: Example lookup not yet implemented.")


# ---------------------------------------------------------------------------
# source
# ---------------------------------------------------------------------------


@app.command("source")
def cmd_source(
    symbol: Annotated[str, typer.Argument(help="Symbol to locate in source")],
    reference: _Reference = None,
    json_mode: _Json = False,
) -> None:
    """Locate declaration and definition of a symbol."""
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 6+: Source location not yet implemented.")


# ---------------------------------------------------------------------------
# related
# ---------------------------------------------------------------------------


@app.command("related")
def cmd_related(
    symbol: Annotated[str, typer.Argument(help="Symbol to find related items for")],
    reference: _Reference = None,
    json_mode: _Json = False,
    limit: _Limit = 20,
) -> None:
    """Find related symbols (bases, derived, module, examples)."""
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 5+: Related not yet implemented.")


# ---------------------------------------------------------------------------
# rebuild-index
# ---------------------------------------------------------------------------


@app.command("rebuild-index")
def cmd_rebuild_index(
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Rebuild SQLite FTS5 search cache from text indexes."""
    setup_logging(verbose=verbose, no_color=no_color)
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 5+: Index rebuild not yet implemented.")


# ---------------------------------------------------------------------------
# smoke
# ---------------------------------------------------------------------------


@app.command("smoke")
def cmd_smoke(
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run smoke tests on a generated reference."""
    setup_logging(verbose=verbose, no_color=no_color)
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Phase 8+: Smoke tests not yet implemented.")


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------


@app.command("determinism")
def cmd_determinism(
    reference: _Reference = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run determinism tests (generate twice, compare outputs)."""
    setup_logging(verbose=verbose, no_color=no_color)
    if reference is None:
        typer.echo("--reference is required", err=True)
        raise typer.Exit(code=2)
    typer.echo("Determinism tests require a full generation pipeline. "
               "Run 'juce-doc generate' first.")


# ---------------------------------------------------------------------------
# test
# ---------------------------------------------------------------------------


@app.command("test")
def cmd_test(
    unit_only: Annotated[
        bool,
        typer.Option("--unit-only", help="Only run unit tests (pytest)"),
    ] = False,
    integration: Annotated[
        bool,
        typer.Option("--integration", help="Run integration tests"),
    ] = False,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run the test suite (pytest + ruff + mypy)."""
    setup_logging(verbose=verbose, no_color=no_color)
    import subprocess
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent.parent
    passed = True

    # pytest
    pytest_args = ["python", "-m", "pytest", "tests/", "-q"]
    r = subprocess.run(pytest_args, cwd=str(repo_root), text=True)
    if r.returncode != 0:
        typer.echo("pytest FAILED", err=True)
        passed = False

    # ruff
    r = subprocess.run(
        ["python", "-m", "ruff", "check", "."], cwd=str(repo_root), text=True,
        capture_output=True,
    )
    if r.returncode != 0:
        typer.echo(f"ruff FAILED:\n{r.stderr or r.stdout}", err=True)
        passed = False

    # mypy
    r = subprocess.run(
        ["python", "-m", "mypy", "src", "--show-error-codes"],
        cwd=str(repo_root), text=True, capture_output=True,
    )
    if r.returncode != 0:
        typer.echo(f"mypy FAILED:\n{r.stderr or r.stdout}", err=True)
        passed = False

    if not passed:
        raise typer.Exit(code=1)
    typer.echo("All checks passed.")


# ---------------------------------------------------------------------------
# all
# ---------------------------------------------------------------------------


@app.command("all")
def cmd_all(
    juce_root: _JuceRoot = None,
    output: _Output = None,
    verbose: _Verbose = False,
    no_color: _NoColor = False,
) -> None:
    """Run the complete unified verification pipeline."""
    import json as _json_mod
    import subprocess

    setup_logging(verbose=verbose, no_color=no_color)
    if juce_root is None or output is None:
        typer.echo("--juce-root and --output are required", err=True)
        raise typer.Exit(code=2)

    juce = Path(juce_root).resolve()
    repo_root = Path(__file__).resolve().parent.parent.parent
    passed = True

    steps = [
        ("doctor", ["python", "-m", "juce_reference", "doctor", "--juce-root", str(juce)]),
    ]

    for name, args in steps:
        typer.echo(f"--- {name} ---")
        r = subprocess.run(args, cwd=str(repo_root), text=True, capture_output=True)
        if r.returncode != 0:
            typer.echo(r.stderr or r.stdout, err=True)
            typer.echo(f"[FAIL] {name}", err=True)
            passed = False
        else:
            typer.echo(f"[OK] {name}")

    typer.echo("\n--- pytest ---")
    r = subprocess.run(
        ["python", "-m", "pytest", "tests/", "-q"],
        cwd=str(repo_root), text=True, capture_output=True,
    )
    if r.returncode != 0:
        typer.echo(r.stderr or r.stdout, err=True)
        passed = False
    else:
        typer.echo("[OK] pytest")

    typer.echo("\n--- ruff ---")
    r = subprocess.run(
        ["python", "-m", "ruff", "check", "."],
        cwd=str(repo_root), text=True, capture_output=True,
    )
    if r.returncode != 0:
        typer.echo(r.stderr or r.stdout, err=True)
        passed = False
    else:
        typer.echo("[OK] ruff")

    typer.echo("\n--- mypy ---")
    r = subprocess.run(
        ["python", "-m", "mypy", "src", "--show-error-codes"],
        cwd=str(repo_root), text=True, capture_output=True,
    )
    if r.returncode != 0:
        typer.echo(r.stderr or r.stdout, err=True)
        passed = False
    else:
        typer.echo("[OK] mypy")

    result = {"passed": passed, "juce_commit": "",
              "tests": {"pytest": "passed" if passed else "failed",
                        "ruff": "", "mypy": "",
                        "smoke": "", "search_quality": "",
                        "determinism": "", "verify": ""}}
    typer.echo(_json_mod.dumps(result, indent=2, ensure_ascii=False))

    if not passed:
        raise typer.Exit(code=1)
    typer.echo("\nAll checks passed.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


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
