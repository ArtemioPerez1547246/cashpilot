"""Read-only Enterprise-Bench evidence (adapted from DevRev's Evidence Vault starter).

Serves only the approved export folders under EB_DATA_DIR. Every result carries the file path,
its sha256 and the line range, so each follow-up can cite exactly where a promise was made.
Standard library only.
"""
import hashlib
import json
import os
from pathlib import Path

ALLOWED = {"crm_json_data", "pm_json_data", "maple_kb", "transcripts", "internal_docs"}
EXTENSIONS = {".json", ".md", ".txt", ".csv"}
MAX_BYTES = 2_000_000


def data_dir():
    raw = os.getenv("EB_DATA_DIR", "")
    p = Path(raw).resolve() if raw else None
    if not p or not p.is_dir() or not any((p / f).is_dir() for f in ALLOWED):
        raise ValueError("Enterprise-Bench export is not mounted on the server (EB_DATA_DIR). "
                         "Tell the user the evidence connector has no data yet; do not guess.")
    return p


def safe_path(relative):
    data = data_dir()
    path = (data / relative).resolve()
    if not path.is_relative_to(data):
        raise ValueError("Path outside the dataset is forbidden")
    rel = path.relative_to(data)
    if not rel.parts or rel.parts[0] not in ALLOWED:
        raise ValueError("Only approved Enterprise-Bench data folders are allowed")
    if path.suffix.lower() not in EXTENSIONS or not path.is_file():
        raise ValueError("Unsupported or missing source file")
    return path


def source_paths(prefix=""):
    data = data_dir()
    for folder in sorted(ALLOWED):
        root = data / folder
        if not root.is_dir():
            continue
        for p in sorted(root.rglob("*")):
            if p.is_file() and p.suffix.lower() in EXTENSIONS:
                rel = p.relative_to(data).as_posix()
                if rel.startswith(prefix):
                    safe_path(rel)  # rejects symlinks escaping the dataset
                    yield rel


def read_source(relative):
    p = safe_path(relative)
    if p.stat().st_size > MAX_BYTES:
        raise ValueError("File exceeds the demo size limit")
    raw = p.read_bytes()
    text = raw.decode("utf-8")
    if p.suffix.lower() == ".json":
        text = json.dumps(json.loads(text), ensure_ascii=False, indent=2)
    return hashlib.sha256(raw).hexdigest(), text.splitlines()


def list_sources(prefix="", offset=0, limit=20):
    if offset < 0 or not 1 <= limit <= 50:
        raise ValueError("Invalid pagination")
    paths = list(source_paths(prefix))
    return {"sources": paths[offset:offset + limit], "total_sources": len(paths),
            "next_offset": offset + limit if offset + limit < len(paths) else None}


def search_evidence(query, prefix="", offset=0, limit=10):
    if not 2 <= len(query) <= 200 or offset < 0 or not 1 <= limit <= 20:
        raise ValueError("Use a 2-200 character query and valid pagination")
    hits, skipped, q = [], [], query.casefold()
    for path in source_paths(prefix):
        try:
            digest, lines = read_source(path)
        except (ValueError, UnicodeError, OSError):
            skipped.append(path)
            continue
        for n, line in enumerate(lines, 1):
            if q in line.casefold():
                hits.append({"path": path, "sha256": digest, "line": n, "snippet": line[:350]})
                break
    return {"matches": hits[offset:offset + limit], "matching_files": len(hits),
            "skipped_sources": skipped,
            "next_offset": offset + limit if offset + limit < len(hits) else None,
            "notice": "One hit per file. Matching files are not counts of business records; "
                      "read the context with read_evidence before claiming anything."}


def read_evidence(path, start_line=1, max_lines=60):
    if start_line < 1 or not 1 <= max_lines <= 100:
        raise ValueError("Invalid line window")
    digest, lines = read_source(path)
    if start_line > len(lines):
        raise ValueError("start_line exceeds the source length")
    end = min(start_line - 1 + max_lines, len(lines))
    return {"path": path, "sha256": digest, "start_line": start_line, "end_line": end,
            "total_lines": len(lines), "text": "\n".join(lines[start_line - 1:end]),
            "next_start_line": end + 1 if end < len(lines) else None}
