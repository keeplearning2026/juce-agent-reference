"""Tests for progress persistence."""

from pathlib import Path

from juce_reference.progress import read_progress, update_progress, write_progress


def test_default_progress_on_missing_file(tmp_path: Path) -> None:
    data = read_progress(tmp_path)
    assert data["schema_version"] == 1
    assert data["completed"] is False
    assert data["current_phase"] == 0
    assert data["completed_phases"] == []


def test_write_and_read_progress(tmp_path: Path) -> None:
    # Create .agent directory structure
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()

    data = {"test": True, "phase": 1}
    write_progress(tmp_path, data)

    result = read_progress(tmp_path)
    assert result == data


def test_update_progress_merges(tmp_path: Path) -> None:
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()

    update_progress(tmp_path, current_phase=2, next_action="Test verification")
    result = read_progress(tmp_path)
    assert result["current_phase"] == 2
    assert result["next_action"] == "Test verification"
    assert result["schema_version"] == 1  # from defaults


def test_update_progress_atomic(tmp_path: Path) -> None:
    agent_dir = tmp_path / ".agent"
    agent_dir.mkdir()

    update_progress(tmp_path, current_phase=3)
    result = read_progress(tmp_path)
    assert result["current_phase"] == 3
    # Ensure no .tmp file is left behind
    assert not (agent_dir / "progress.json.tmp").exists()
