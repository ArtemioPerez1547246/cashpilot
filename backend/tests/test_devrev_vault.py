"""Evidence tools: approved folders only, cite hash + lines, honest when data is missing."""
import json

import pytest

from app.devrev_board import vault


@pytest.fixture
def data(tmp_path, monkeypatch):
    (tmp_path / "transcripts").mkdir()
    (tmp_path / "transcripts" / "acme_qbr.json").write_text(json.dumps(
        {"account": "Acme Corp", "lines": ["Hi all", "We will send the revised SOW by Friday"]}))
    (tmp_path / "secret.txt").write_text("not approved")
    monkeypatch.setenv("EB_DATA_DIR", str(tmp_path))
    return tmp_path


def test_missing_data_is_reported_not_guessed(monkeypatch, tmp_path):
    monkeypatch.setenv("EB_DATA_DIR", str(tmp_path / "nope"))
    with pytest.raises(ValueError, match="not mounted"):
        vault.list_sources()


def test_lists_only_approved_folders(data):
    assert vault.list_sources()["sources"] == ["transcripts/acme_qbr.json"]


def test_search_then_read_gives_citable_source(data):
    hit = vault.search_evidence("revised sow")["matches"][0]
    assert hit["path"] == "transcripts/acme_qbr.json" and len(hit["sha256"]) == 64
    window = vault.read_evidence(hit["path"], start_line=max(1, hit["line"] - 2), max_lines=5)
    assert "revised SOW" in window["text"] and window["sha256"] == hit["sha256"]


def test_path_escape_and_unapproved_files_blocked(data):
    for bad in ["../etc/passwd", "secret.txt", "transcripts/../secret.txt"]:
        with pytest.raises(ValueError):
            vault.read_evidence(bad)


def test_verify_source_checks_files_hashes_and_lines(data):
    ok = vault.verify_source({"ref": "transcripts/acme_qbr.json", "lines": "1-3"})
    assert len(ok["sha256"]) == 64                                   # real hash filled in
    for bad in [{"ref": "transcripts/missing.json"},
                {"ref": "transcripts/acme_qbr.json", "sha256": "0" * 64},
                {"ref": "transcripts/acme_qbr.json", "lines": "900-950"}]:
        with pytest.raises(ValueError):
            vault.verify_source(bad)
    assert vault.verify_source({"ref": "MTG-1008-RIDGE"})["ref"] == "MTG-1008-RIDGE"      # record IDs pass
    assert vault.verify_source({"ref": "owner-note:T08:2026-10-21"})["ref"].startswith("owner-note")
