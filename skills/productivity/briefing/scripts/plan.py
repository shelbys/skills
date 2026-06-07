#!/usr/bin/env python3
"""
Plan stage: read BRIEFING.md, validate it, ensure tracking files exist,
and emit a JSON plan that tells the agent which research tasks to run.

Usage:
    python plan.py [path/to/BRIEFING.md]

If no path is given, defaults to ~/.claude/BRIEFING.md.

Output (stdout, JSON):
    {
      "run_id": "2026-05-19T18:30:00Z",
      "briefing_dir": "/abs/path",
      "links_path": "/abs/path/BRIEFING_LINKS.md",
      "sections_path": "/abs/path/BRIEFING_SECTIONS.md",
      "seen_url_count": 42,
      "backfilled_index_count": 0,
      "initialized": ["/abs/path/BRIEFING_LINKS.md"],
      "tasks": [
        {
          "task_id": "discover",
          "analyses": ["Industry trends...", "Concrete suggestions...", ...],
          "authors": [...],
          "topics": [...],
          "sites": [...],
          "instructions": [...],
          "known_urls": ["https://...", ...]
        }
      ]
    }

Errors are written to stderr and the process exits with code 2 for
config errors, 1 for unexpected errors.
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_FRONTMATTER_LISTS = ("authors", "topics", "sites")
REQUIRED_BODY_HEADINGS = ("Analyses",)
OPTIONAL_BODY_HEADINGS = ("Instructions",)
BODY_ONLY_HEADINGS = REQUIRED_BODY_HEADINGS + OPTIONAL_BODY_HEADINGS
DEFAULT_CONFIG_PATH = Path.home() / ".claude" / "BRIEFING.md"
RECENT_URL_LIMIT = 100
BOLD_LINK_RE = re.compile(r"\*\*\[([^\]]+)\]\([^\)]+\)\*\*")
BOLD_RE = re.compile(r"\*\*([^*\n]+?)\*\*")
URL_RE = re.compile(r"https?://\S+")
URL_TRIM_CHARS = ".,;:)>\"'"


def die(msg: str, code: int = 2) -> None:
    sys.stderr.write(f"error: {msg}\n")
    sys.exit(code)


def _unquote(s: str) -> str:
    """Strip a matching pair of outer quotes; leave unmatched quotes intact.

    YAML-style: `"foo"` → `foo`, `'foo'` → `foo`. But `"foo" bar` stays
    `"foo" bar` (the trailing ` bar` means the leading `"` isn't a wrapper)
    — the older behavior stripped the leading `"` independently and produced
    `foo" bar`, leaving a stray quote mid-string.
    """
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        return s[1:-1]
    return s


def parse_frontmatter(text: str, path: Path) -> dict:
    """Parse the constrained subset of YAML used by BRIEFING.md.

    Supported shape only:
        key: <inline string>
        key:
          - item one
          - item two

    Anything else (nested maps, flow sequences, multiline scalars) is a config
    error — the schema is deliberately small.
    """
    config: dict = {}
    current_key: str | None = None
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        if line.startswith(" ") or line.startswith("\t"):
            stripped = line.lstrip()
            if not stripped.startswith("- "):
                die(f"{path}:{lineno}: expected '- item', got: {raw!r}")
            if current_key is None or not isinstance(config.get(current_key), list):
                die(f"{path}:{lineno}: list item with no preceding key")
            config[current_key].append(_unquote(stripped[2:].strip()))
            continue

        if ":" not in line:
            die(f"{path}:{lineno}: expected 'key:' or 'key: value', got: {raw!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        if value:
            config[key] = _unquote(value)
            current_key = None
        else:
            config[key] = []
            current_key = key
    return config


def parse_markdown_sections(text: str) -> dict[str, list[str]]:
    """Parse every top-level `# Key` section with `- item` bullets from the body.

    Returns a dict of {heading_name: [item, ...]} for ALL headings encountered.
    The caller decides which headings are known and which become hints.
    """
    result: dict[str, list[str]] = {}
    current_key: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            current_key = line[2:].strip()
            result.setdefault(current_key, [])
        elif current_key is not None and line.startswith("- "):
            result[current_key].append(_unquote(line[2:].strip()))
    return result


def load_config(path: Path) -> dict:
    """Parse BRIEFING.md into a config dict.

    Schema:
      - Frontmatter `authors`, `topics`, `sites`: required non-empty lists.
      - Frontmatter Instructions/Analyses: rejected (they belong in body sections).
      - Any other frontmatter list → entry in `filters` dict.
      - Body `# Analyses`: required non-empty list of bullets.
      - Body `# Instructions`: optional list of bullets.
      - Any other body heading → entry in `hints` dict.
    """
    if not path.exists():
        die(f"BRIEFING.md not found: {path}")

    text = path.read_text()
    if not text.lstrip().startswith("---"):
        die(f"{path}: expected frontmatter starting with '---'")

    body = text.lstrip()[3:]
    end = body.find("\n---")
    if end == -1:
        die(f"{path}: frontmatter not closed with '---'")

    raw_frontmatter = parse_frontmatter(body[:end], path)
    raw_body = parse_markdown_sections(body[end + 4:])

    for reserved in BODY_ONLY_HEADINGS:
        if reserved in raw_frontmatter:
            die(f"{path}: '{reserved}' must be a '# {reserved}' body section, "
                f"not a frontmatter field")

    config: dict = {}
    filters: dict[str, list[str]] = {}
    for key, value in raw_frontmatter.items():
        if key in REQUIRED_FRONTMATTER_LISTS:
            config[key] = value
        else:
            filters[key] = value if isinstance(value, list) else [value]

    hints: dict[str, list[str]] = {}
    for key, value in raw_body.items():
        if key in BODY_ONLY_HEADINGS:
            config[key] = value
        else:
            hints[key] = value

    for field in REQUIRED_FRONTMATTER_LISTS:
        value = config.get(field)
        if value is None:
            die(f"{path}: missing required frontmatter field '{field}'")
        if not isinstance(value, list) or len(value) == 0:
            die(f"{path}: frontmatter '{field}' must be a non-empty list")

    for field in REQUIRED_BODY_HEADINGS:
        value = config.get(field)
        if value is None:
            die(f"{path}: missing required body section '# {field}'")
        if not isinstance(value, list) or len(value) == 0:
            die(f"{path}: body section '# {field}' must contain at least one '- item'")

    for field in OPTIONAL_BODY_HEADINGS:
        config.setdefault(field, [])

    config["_filters"] = filters
    config["_hints"] = hints
    return config


def ensure_tracking_files(briefing_dir: Path) -> tuple[Path, Path, Path, list[str]]:
    links = briefing_dir / "BRIEFING_LINKS.md"
    sections = briefing_dir / "BRIEFING_SECTIONS.md"
    index = briefing_dir / "BRIEFING_INDEX.jsonl"
    initialized: list[str] = []

    for f in (links, sections, index):
        if not f.exists():
            f.touch()
            initialized.append(str(f))

    return links, sections, index, initialized


def count_seen_urls(links_path: Path) -> int:
    if not links_path.exists():
        return 0
    return sum(
        1 for line in links_path.read_text().splitlines() if line.strip()
    )


def _read_url_lines(links_path: Path) -> list[str]:
    """Bare URLs from BRIEFING_LINKS.md in append order. Tolerates legacy `- URL` form."""
    if not links_path.exists():
        return []
    out: list[str] = []
    for raw in links_path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        out.append(line)
    return out


def _match_key(url: str) -> str:
    return url.strip().rstrip("/").lower()


def recent_urls(links_path: Path, limit: int = RECENT_URL_LIMIT) -> list[str]:
    """Most-recent N URLs from LINKS, for hinting subagents to skip them."""
    return _read_url_lines(links_path)[-limit:]


def backfill_index(sections_path: Path, links_path: Path, index_path: Path) -> int:
    """Populate BRIEFING_INDEX.jsonl from existing SECTIONS for any URL in LINKS
    that has no INDEX entry yet. One-time self-heal for briefings that predate
    the index. Idempotent: no-op once every LINKS url has been indexed.
    Returns the number of entries appended.
    """
    links_urls = _read_url_lines(links_path)
    if not links_urls:
        return 0

    indexed: set[str] = set()
    if index_path.exists():
        for raw in index_path.read_text().splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            url = entry.get("url")
            if isinstance(url, str):
                indexed.add(_match_key(url))

    missing = [u for u in links_urls if _match_key(u) not in indexed]
    if not missing or not sections_path.exists():
        return 0

    # Build URL → title map by walking SECTIONS line-by-line. Handles both
    # `- 📌 **[Title](url)** — summary` (current ingest format) and
    # `- 📌 **Title** — summary [Read](url)` (older / hand-edited format).
    target_keys = {_match_key(u) for u in missing}
    url_to_title: dict[str, str] = {}
    for line in sections_path.read_text().splitlines():
        urls = [u.rstrip(URL_TRIM_CHARS) for u in URL_RE.findall(line)]
        relevant = [u for u in urls if _match_key(u) in target_keys]
        if not relevant:
            continue
        m = BOLD_LINK_RE.search(line) or BOLD_RE.search(line)
        if not m:
            continue
        title = m.group(1).strip()
        if not title:
            continue
        for url in relevant:
            url_to_title.setdefault(_match_key(url), title)

    new_entries = [
        {"url": u, "title": url_to_title[_match_key(u)]}
        for u in missing
        if _match_key(u) in url_to_title
    ]
    if not new_entries:
        return 0

    with index_path.open("a", encoding="utf-8") as f:
        for entry in new_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return len(new_entries)


def _render_section_block(title: str, sections: dict[str, list[str]]) -> str:
    """Render a {name: [item, ...]} dict as a markdown block with ### subheadings.
    Empty input → empty string so the template renders cleanly with no extras."""
    if not sections:
        return ""
    lines = [f"\n## {title}\n"]
    for name, values in sections.items():
        lines.append(f"### {name}")
        for v in values:
            lines.append(f"- {v}")
        lines.append("")
    return "\n".join(lines)


def build_tasks(config: dict, known_urls: list[str]) -> list[dict]:
    """One discovery task covering all analyses. A single subagent runs one
    search pass over the shared authors/topics/sites and classifies each
    candidate into the best-fit analysis. This replaces the older fan-out
    (N agents × same web searches) — see references/agent-prompt-template.md.
    """
    filters_block = _render_section_block(
        "Filters (additional constraints from BRIEFING.md frontmatter)",
        config.get("_filters", {}),
    )
    hints_block = _render_section_block(
        "Hints (additional context from BRIEFING.md body sections)",
        config.get("_hints", {}),
    )
    return [
        {
            "task_id": "discover",
            "analyses": list(config["Analyses"]),
            "authors": list(config["authors"]),
            "topics": list(config["topics"]),
            "sites": list(config["sites"]),
            "instructions": list(config["Instructions"]),
            "known_urls": list(known_urls),
            "known_urls_count": len(known_urls),
            "filters_block": filters_block,
            "hints_block": hints_block,
        }
    ]


def main() -> None:
    config_path = Path(sys.argv[1]).expanduser() if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    config_path = config_path.resolve()

    config = load_config(config_path)
    briefing_dir = config_path.parent
    links_path, sections_path, index_path, initialized = ensure_tracking_files(briefing_dir)
    backfilled = backfill_index(sections_path, links_path, index_path)
    known_urls = recent_urls(links_path)

    plan = {
        "run_id": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "briefing_dir": str(briefing_dir),
        "config_path": str(config_path),
        "links_path": str(links_path),
        "sections_path": str(sections_path),
        "index_path": str(index_path),
        "seen_url_count": count_seen_urls(links_path),
        "backfilled_index_count": backfilled,
        "initialized": initialized,
        "tasks": build_tasks(config, known_urls),
    }

    json.dump(plan, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        die(f"unexpected: {e}", code=1)
