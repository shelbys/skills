# Briefing troubleshooting

Load this file only when a run has failed or the user reports something off.

## Errors from `plan.py`

| Message | Cause | Fix |
|---|---|---|
| `BRIEFING.md not found: <path>` | File missing | Create it (see `references/example-briefings.md`) or pass an explicit path: `/briefing /custom/path/BRIEFING.md` |
| `expected frontmatter starting with '---'` | File has no YAML frontmatter | Wrap the config in `---` lines at the top of the file |
| `frontmatter not closed with '---'` | Missing closing `---` | Add a closing `---` after the config block |
| `missing required field '<field>'` | One of `authors` / `topics` / `sites` / `Analyses` absent | Add the field; all four are required |
| `'<field>' must be a non-empty list` | Field present but empty | Add at least one entry |
| `<path>:<line>: expected '- item'` | Indented line that isn't a list item | Use `  - value` form for list entries |
| `<path>:<line>: expected 'key:' or 'key: value'` | Top-level line missing a colon | Fix the YAML shape — only `key: value` or `key:` + indented bullets are supported |

`plan.py`'s parser deliberately supports only the documented shape (top-level
keys with inline strings or bullet lists). Nested maps, flow sequences, or
multiline scalars will fail. This is intentional — the schema is small.

## Errors from `ingest.py`

| Message | Cause | Fix |
|---|---|---|
| `stdin is empty` | No subagent results piped in | Verify the agent collected results before invoking `ingest.py` |
| `stdin is not valid JSON and no embedded array found: <err>` | Agent returned text with no parseable JSON array anywhere (e.g. "I cannot do this task") | Re-run the discovery agent; if it keeps refusing, tighten the prompt or check tool availability |
| `expected a JSON array at the top level` | Subagent returned a single object | Wrap in `[ ... ]` — the contract is an array of task results |
| `briefing-dir does not exist` | Bad `--briefing-dir` argument | Use the path from `plan.json`'s `briefing_dir` field verbatim |

## Behavioral surprises (not errors)

**"Run completed but no new findings"**
All candidates were already in `BRIEFING_LINKS.md`. This is correct on a quick
re-run. Wait a week, or broaden the analyses/sites.

**"A duplicate article slipped through on a later run"**
Should be rare: title-dedup checks against `BRIEFING_INDEX.jsonl` from all prior
runs. If it does happen, either (a) the index was deleted/corrupted, (b) the
duplicate's title differs by >8% from the original (similarity threshold is
0.92 — deliberately tight so series titles like "Week 16"/"Week 17" don't
collide), or (c) the original was kept before the index existed. Inspect
`BRIEFING_INDEX.jsonl` to confirm what titles are being compared against.

**"BRIEFING_LINKS.md is growing large"**
Append-only by design. Safe to manually trim entries older than ~6 months;
they'll be re-discovered if still relevant.

**"All my subagents returned `candidates: []`"**
Either the sites have no recent content matching the analyses, or the
authors/topics are too narrow. Check by running one subagent's prompt
manually in a fresh agent and inspecting what it sees.

**"Results read like marketing copy"**
The agent prompt asks subagents to prefer primary sources and write summaries
in their own words. If output drifts toward press-release tone, tighten the
`Instructions:` list in `BRIEFING.md` (e.g., "Reject vendor announcements
unless they include technical detail").

## When to suspect the dedup logic vs. the agent

- **Same URL appearing twice in BRIEFING_SECTIONS.md across runs** → dedup
  bug; check that `BRIEFING_LINKS.md` is being read and written.
- **Same URL appearing twice in *one* run** → subagent returned dupes; the
  in-batch URL dedup should catch this — check `ingest.py`'s `seen` set is
  initialized from `BRIEFING_LINKS.md`.
- **Plausible-looking results with broken URLs** → subagent fabricated;
  tighten the prompt's "verify the URL resolves" instruction or switch to a
  subagent type that actually fetches pages.
