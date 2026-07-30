"""Import official JUCE repository Markdown docs into the reference.

Copies or links ``JUCE/docs/*.md``, ``JUCE/README.md``, and
``JUCE/BREAKING_CHANGES.md``, adding minimal metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from juce_reference.source import JuceSource


@dataclass(frozen=True)
class RepoDocument:
    """A repository Markdown document ready for the output."""

    source_path: str  # relative path inside the JUCE checkout
    output_path: str  # relative path inside the reference output
    content: str


def _fix_relative_links(
    content: str,
    source_dir: Path,
    juce_root: Path,
    output_dir_prefix: str,
) -> str:
    """Rewrite Markdown links to other JUCE files so they work in the reference.

    Links to ``*.md`` files are converted to paths under the ``guides/`` directory.
    Links to source files retain paths relative to the JUCE root.
    """
    def _rewrite(m: re.Match[str]) -> str:
        text = m.group(1)
        url = m.group(2)
        # Skip external URLs.
        if url.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)

        # Resolve the target relative to the source file's directory.
        resolved = (source_dir / url).resolve()
        try:
            rel = resolved.relative_to(juce_root)
        except ValueError:
            # Outside JUCE root; keep as-is.
            return m.group(0)

        if rel.suffix == ".md":
            # Route to guides/
            new_url = f"./{output_dir_prefix}{rel.as_posix()}"
        else:
            # Keep as relative to JUCE root.
            new_url = f"../juce/{rel.as_posix()}"

        return f"[{text}]({new_url})"

    return re.sub(r"\[([^\]]*)\]\(([^)]+)\)", _rewrite, content)


def import_repository_docs(juce_source: JuceSource) -> list[RepoDocument]:
    """Import official JUCE Markdown documents.

    Searches:
    - ``JUCE/docs/*.md``
    - ``JUCE/README.md``
    - ``JUCE/BREAKING_CHANGES.md``

    Returns:
        List of ``RepoDocument`` instances ready for output.
    """
    docs: list[RepoDocument] = []

    # Docs directory
    docs_dir = juce_source.docs_dir
    if docs_dir.is_dir():
        for md_file in sorted(docs_dir.rglob("*.md")):
            rel_path = md_file.relative_to(juce_source.root)
            content = md_file.read_text(encoding="utf-8", errors="replace")
            # Add minimal frontmatter
            frontmatter = (
                f"---\nsource: {rel_path.as_posix()}\n"
                f"juce_commit: {juce_source.commit}\n---\n\n"
            )
            content = frontmatter + content

            # Fix relative links
            content = _fix_relative_links(
                content,
                source_dir=md_file.parent,
                juce_root=juce_source.root,
                output_dir_prefix="guides/",
            )

            output_path = f"guides/{rel_path.as_posix()}"
            docs.append(RepoDocument(
                source_path=rel_path.as_posix(),
                output_path=output_path,
                content=content,
            ))

    # README
    readme = juce_source.root / "README.md"
    if readme.is_file():
        content = readme.read_text(encoding="utf-8", errors="replace")
        frontmatter = f"---\nsource: README.md\njuce_commit: {juce_source.commit}\n---\n\n"
        content = frontmatter + content
        docs.append(RepoDocument(
            source_path="README.md",
            output_path="guides/README.md",
            content=content,
        ))

    # BREAKING_CHANGES
    breaking = juce_source.root / "BREAKING_CHANGES.md"
    if breaking.is_file():
        content = breaking.read_text(encoding="utf-8", errors="replace")
        frontmatter = (
            "---\nsource: BREAKING_CHANGES.md\n"
            f"juce_commit: {juce_source.commit}\n---\n\n"
        )
        content = frontmatter + content
        docs.append(RepoDocument(
            source_path="BREAKING_CHANGES.md",
            output_path="guides/BREAKING_CHANGES.md",
            content=content,
        ))

    return docs
