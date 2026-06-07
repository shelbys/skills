---
name: briefing
description: |
  Run a curated research briefing on the topics/authors/sites configured in BRIEFING.md.
  Discovers fresh content, deduplicates against prior runs, and appends timestamped
  findings to BRIEFING_SECTIONS.md.

  Use when the user asks for a briefing, weekly digest, or research roundup, or invokes
  `/briefing` (defaults to ~/.claude/BRIEFING.md) or `/briefing /path/to/BRIEFING.md`.
---

# Briefing

Three deterministic scripts bracket one LLM step (research). Do not reorder or skip stages.

## Workflow

### 1. Plan (script)

Run `${SKILL_DIR}/scripts/plan.sh {path/to/BRIEFING.md}`

Validates config, ensures `BRIEFING_LINKS.md` and `BRIEFING_SECTIONS.md` exist, and
prints a JSON plan with one `task` per analysis. On config errors it exits non-zero
with a message — surface that to the user verbatim and stop.

### 2. Research (you)

`plan.tasks` contains exactly one discovery task. Spawn ONE subagent using the
prompt template in `references/agent-prompt-template.md`, substituting the
task fields (including `{{analyses}}` and `{{known_urls}}`).

The subagent runs a single search pass over the shared authors/topics/sites
and classifies each candidate into the best-fit analysis. It returns a JSON
object with a `tool_log` (per-tool call counts) and a `results` array in the
shape `./scripts/ingest.sh` consumes:

```json
{
  "tool_log": {"WebSearch": 8, "WebFetch": 15, "Read": 2},
  "results": [
    {"analysis": "Industry trends...", "candidates": [{"title": "...", "url": "...", ...}]},
    {"analysis": "Concrete suggestions...", "candidates": [...]},
    ...
  ]
}
```

`./scripts/ingest.sh` prints the tool_log counts as part of its summary so you can show
the user how much research effort the run took.

Pipe the raw response straight to ingest — it tolerates stray code fences,
prose preambles, and trailing commentary by extracting the embedded JSON
array. If the subagent fails or returns no text, surface the error to the
user and stop; re-runs are cheap.

### 3. Ingest (script)

```
echo '<agent-response>' | ${SKILL_DIR}/scripts/ingest.sh \
  --run-id <plan.run_id> --briefing-dir <plan.briefing_dir>
```

Normalizes URLs, drops URLs already in `BRIEFING_LINKS.md`, dedups by title
similarity, formats markdown, and atomically appends to both tracking files.
Prints a summary (counts per analysis, duplicates dropped).

### 4. Report

Print the ingest summary back to the user, plus the path to `BRIEFING_SECTIONS.md`.

## Rules

- **Never** write to `BRIEFING_LINKS.md` or `BRIEFING_SECTIONS.md` yourself — only `./scripts/ingest.sh` does.
- **Never** edit `BRIEFING.md` unless the user explicitly asks.
- If `./scripts/plan.sh` reports `initialized: [...]`, mention it in the final report (first run).
- If `./scripts/plan.sh` reports `backfilled_index_count > 0`, mention it (one-time self-heal of the title-dedup index).
- The single task includes `analyses` and `known_urls` — substitute both like any other list field.
- If the subagent fails or returns malformed JSON, the run is lost — surface the error and stop. No retry; re-runs are cheap.

## References (load only when needed)

- `references/agent-prompt-template.md` — the per-task research prompt
- `references/example-briefings.md` — sample BRIEFING.md configs
- `references/troubleshooting.md` — common errors and fixes
