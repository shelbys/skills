#!/usr/bin/env python3
"""
Ingest stage: read agent research results from stdin, deduplicate against
prior runs, format markdown, and append atomically to the tracking files.

Usage:
    cat results.json | python ingest.py \
        --run-id 2026-05-19T18:30:00Z \
        --briefing-dir /path/to/briefing/dir

Stdin (JSON object — preferred shape):
    {
      "tool_log": {"WebSearch": 8, "WebFetch": 15, "Read": 2},
      "results": [
        {
          "analysis": "Industry trends ...",
          "candidates": [
            {"title": "...", "url": "...", "date": "YYYY-MM-DD",
             "summary": "...", "source": "..."}
          ]
        },
        ...
      ]
    }

Stdin (JSON array — legacy shape, still accepted; tool_log unavailable):
    [{"analysis": "...", "candidates": [...]}, ...]

Prose preambles, trailing commentary, and ```-fenced blocks are tolerated —
the loader scans for the first embedded array/object that parses cleanly.

Side effects:
    - Appends a timestamped section to <briefing-dir>/BRIEFING_SECTIONS.md
    - Appends new URLs (one per line) to <briefing-dir>/BRIEFING_LINKS.md
    - Appends {url, title} JSONL lines to <briefing-dir>/BRIEFING_INDEX.jsonl

Stdout (plain text): per-analysis dedup summary + optional tool_log breakdown.
Exit codes: 0 ok, 2 bad input, 1 unexpected error.
"""

import argparse
import json
import sys
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urlencode

TITLE_SIMILARITY_THRESHOLD = 0.92
TRACKING_PARAMS = {"ref", "fbclid", "gclid", "mc_cid", "mc_eid"}

# Behavioral toggle. When True, dedup against BRIEFING_LINKS.md (URL) and
# BRIEFING_INDEX.jsonl (title) is bypassed — same article may resurface in
# any future run with a potentially new per-analysis framing. Intra-analysis
# dedup (same URL twice in one section) still applies. Flip to False to
# restore strict prior-run dedup. LINKS/INDEX are still written either way
# so the history is preserved.
ALLOW_PRIOR_DUPES = True


def die(msg: str, code: int = 2) -> None:
    sys.stderr.write(f"error: {msg}\n")
    sys.exit(code)


def normalize_url(url: str) -> str:
    """Strip protocol case, tracking params, and trailing slash for dedup."""
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return url.strip().rstrip("/").lower()

    kept = [
        (k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=False)
        if not k.startswith("utm_") and k not in TRACKING_PARAMS
    ]
    query = urlencode(sorted(kept))

    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/")
    base = f"{parsed.scheme.lower()}://{netloc}{path}"
    return f"{base}?{query}" if query else base


def read_existing_urls(links_path: Path) -> set[str]:
    if not links_path.exists():
        return set()
    out: set[str] = set()
    for line in links_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Tolerate legacy "- URL" entries as well as bare URLs.
        if line.startswith("- "):
            line = line[2:].strip()
        out.add(normalize_url(line))
    return out


def read_existing_titles(index_path: Path) -> list[str]:
    """Load titles from prior runs for cross-run title-dedup.

    Format is JSONL: one {"url": ..., "title": ...} per line. Tolerates a
    missing file (first run after this code lands) and skips unparseable
    lines so a manual edit can't break ingest.
    """
    if not index_path.exists():
        return []
    titles: list[str] = []
    for line in index_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        title = entry.get("title")
        if isinstance(title, str) and title.strip():
            titles.append(title.strip())
    return titles


def title_similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def is_title_dup(title: str, others: list[str]) -> bool:
    return any(
        title_similarity(title, other) > TITLE_SIMILARITY_THRESHOLD
        for other in others
    )


def dedup_candidates(
    candidates: list[dict],
    prior_urls: frozenset[str],
    run_urls: set[str],
    prior_titles: list[str],
    run_titles: list[str],
) -> tuple[list[dict], int, int, int, int]:
    """Return (kept, prior_url_dupes, intrarun_url_dupes, prior_title_dupes, intrarun_title_dupes).

    prior_urls / prior_titles: from previous runs (read-only).
    run_urls / run_titles: accumulated within this run (mutated as items are kept).
    """
    kept: list[dict] = []
    prior_url_dupes = intrarun_url_dupes = 0
    prior_title_dupes = intrarun_title_dupes = 0
    for item in candidates:
        url = item.get("url", "").strip()
        title = item.get("title", "").strip()
        if not url or not title:
            continue
        norm = normalize_url(url)
        if norm in prior_urls:
            prior_url_dupes += 1
            continue
        if norm in run_urls:
            intrarun_url_dupes += 1
            continue
        if is_title_dup(title, prior_titles):
            prior_title_dupes += 1
            continue
        if is_title_dup(title, run_titles):
            intrarun_title_dupes += 1
            continue
        run_urls.add(norm)
        run_titles.append(title)
        kept.append(item)
    return kept, prior_url_dupes, intrarun_url_dupes, prior_title_dupes, intrarun_title_dupes


def format_section(run_id: str, by_analysis: list[tuple[str, list[dict]]]) -> str:
    lines = ["", f"## {run_id}", ""]
    for analysis, items in by_analysis:
        lines.append(f"### {analysis}")
        lines.append("")
        if not items:
            lines.append("_No new findings this run._")
            lines.append("")
            continue
        for it in items:
            title = it.get("title", "").strip()
            url = it.get("url", "").strip()
            date = it.get("date", "").strip()
            source = it.get("source", "").strip()
            summary = it.get("summary", "").strip()
            meta_parts = [p for p in (source, date) if p]
            meta = f" _({' · '.join(meta_parts)})_" if meta_parts else ""
            lines.append(f"- 📌 **[{title}]({url})**{meta} — {summary}")
        lines.append("")
    return "\n".join(lines) + "\n"


def append_text(path: Path, text: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(text)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    p.add_argument("--run-id", required=True, help="ISO8601 UTC timestamp from plan.py")
    p.add_argument("--briefing-dir", required=True, type=Path)
    return p.parse_args()


def strip_fences(text: str) -> str:
    """Remove markdown code fences that models sometimes wrap JSON in."""
    s = text.strip()
    if s.startswith("```"):
        newline = s.find("\n")
        if newline != -1:
            s = s[newline + 1:]
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3].rstrip()
    return s


def _extract_embedded_value(text: str):
    """Scan for the first top-level JSON array OR object embedded in surrounding
    text. Returns whichever parses cleanly first, or None. Uses raw_decode so
    trailing prose after the value is ignored, and skips '[' / '{' chars that
    don't start valid JSON (e.g. brackets inside a prose preamble).
    """
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            data, _ = decoder.raw_decode(text[idx:])
        except json.JSONDecodeError:
            continue
        if isinstance(data, (list, dict)):
            return data
    return None


def load_results() -> tuple[list[dict], dict]:
    """Returns (results, tool_log).

    Accepts two top-level shapes:
      - JSON array: legacy shape. tool_log defaults to {}.
      - JSON object: {"results": [...], "tool_log": {...}}. tool_log is optional.
    """
    raw = sys.stdin.read()
    if not raw.strip():
        die("stdin is empty; expected agent output")
    text = strip_fences(raw)

    # Fast path: clean JSON (or ```-fenced JSON, after stripping).
    try:
        data = json.loads(text)
    except json.JSONDecodeError as fast_err:
        # Tolerant path: agents sometimes prepend a prose preamble or append
        # commentary despite "no prose" instructions. Find an embedded value.
        data = _extract_embedded_value(text)
        if data is None:
            die(f"stdin is not valid JSON and no embedded value found: {fast_err}")

    if isinstance(data, list):
        return data, {}
    if isinstance(data, dict):
        results = data.get("results")
        if not isinstance(results, list):
            die("top-level object is missing a 'results' array")
        tool_log = data.get("tool_log")
        if not isinstance(tool_log, dict):
            tool_log = {}
        return results, tool_log
    die("expected a JSON array or object at the top level")


def main() -> None:
    args = parse_args()
    briefing_dir: Path = args.briefing_dir.expanduser().resolve()
    if not briefing_dir.is_dir():
        die(f"briefing-dir does not exist: {briefing_dir}")

    links_path = briefing_dir / "BRIEFING_LINKS.md"
    sections_path = briefing_dir / "BRIEFING_SECTIONS.md"
    index_path = briefing_dir / "BRIEFING_INDEX.jsonl"

    results, tool_log = load_results()
    if ALLOW_PRIOR_DUPES:
        prior_urls: frozenset[str] = frozenset()
        prior_titles: list[str] = []
    else:
        prior_urls = frozenset(read_existing_urls(links_path))
        prior_titles = read_existing_titles(index_path)

    by_analysis: list[tuple[str, list[dict]]] = []
    new_entries: list[dict] = []
    summary_lines: list[str] = []
    total_found = total_kept = 0
    total_prior_url = total_intra_url = total_prior_title = total_intra_title = 0

    for task in results:
        analysis = (task.get("analysis") or task.get("task_id") or "Untitled").strip()
        candidates = task.get("candidates") or []
        if not isinstance(candidates, list):
            sys.stderr.write(f"warn: task {analysis!r} has non-list candidates; skipping\n")
            candidates = []

        # Fresh per-analysis sets — same URL may appear under multiple analyses
        # this run (e.g. a weekly changelog covering several features). Dedup
        # against prior runs stays global; intra-run dedup is per-analysis only.
        analysis_urls: set[str] = set()
        analysis_titles: list[str] = []

        kept, pu, iu, pt, it = dedup_candidates(
            candidates, prior_urls, analysis_urls, prior_titles, analysis_titles
        )
        by_analysis.append((analysis, kept))
        new_entries.extend(kept)

        total_found += len(candidates)
        total_kept += len(kept)
        total_prior_url += pu
        total_intra_url += iu
        total_prior_title += pt
        total_intra_title += it

        dup_parts = []
        if pu:
            dup_parts.append(f"{pu} prior-url")
        if iu:
            dup_parts.append(f"{iu} intra-analysis")
        if pt:
            dup_parts.append(f"{pt} prior-title")
        if it:
            dup_parts.append(f"{it} intra-analysis-title")
        dup_str = f" ({', '.join(dup_parts)})" if dup_parts else ""
        summary_lines.append(
            f"  - {analysis}: {len(kept)} new / {len(candidates)} found{dup_str}"
        )

    section_md = format_section(args.run_id, by_analysis)
    append_text(sections_path, section_md)
    if new_entries:
        # Same URL may appear in `new_entries` under multiple analyses; the
        # SECTIONS file shows each occurrence, but LINKS/INDEX only need one
        # row per URL so future prior-run dedup catches it cleanly.
        seen_urls: set[str] = set()
        unique_entries: list[dict] = []
        for e in new_entries:
            key = normalize_url(e["url"].strip())
            if key in seen_urls:
                continue
            seen_urls.add(key)
            unique_entries.append(e)

        append_text(links_path, "".join(f"{e['url'].strip()}\n" for e in unique_entries))
        append_text(
            index_path,
            "".join(
                json.dumps({"url": e["url"].strip(), "title": e["title"].strip()},
                           ensure_ascii=False) + "\n"
                for e in unique_entries
            ),
        )

    print(f"Briefing run {args.run_id}")
    print(f"Appended to: {sections_path}")
    total_intra = total_intra_url + total_intra_title
    if ALLOW_PRIOR_DUPES:
        prior_note = "prior-run dedup disabled"
    else:
        total_prior = total_prior_url + total_prior_title
        prior_note = f"{total_prior} prior-run dup"
    print(f"  {total_kept} new entries / {total_found} candidates"
          f" ({prior_note}, {total_intra} intra-analysis dup)")
    for line in summary_lines:
        print(line)

    if tool_log:
        tools_sorted = sorted(
            ((k, v) for k, v in tool_log.items() if isinstance(v, int) and v > 0),
            key=lambda kv: -kv[1],
        )
        if tools_sorted:
            total_calls = sum(v for _, v in tools_sorted)
            print(f"\nDiscovery agent tool usage ({total_calls} total):")
            for tool, count in tools_sorted:
                print(f"  {tool}: {count}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        die(f"unexpected: {e}", code=1)
