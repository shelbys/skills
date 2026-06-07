# Deduplication strategy

Describes what `scripts/ingest.py` actually does. Source of truth is `dedup_candidates` in `ingest.py` — if this doc disagrees with the code, the code wins.

## Two checks, in order

For each candidate in an analysis's candidate list:

1. **URL dedup.** Normalize the URL and reject if it's already in `BRIEFING_LINKS.md` (any prior run) or already kept *in this analysis* (intra-analysis only — the same URL is allowed across different analyses, see below).
2. **Title dedup.** Reject if its title is >0.92 similar (`difflib.SequenceMatcher`) to any title already kept in `BRIEFING_INDEX.jsonl` (prior runs, global) or in this analysis (intra-analysis only). The threshold is deliberately tight because series titles like `Week 16` vs `Week 17` legitimately differ by one character — the older 0.85 default caught them as duplicates.

Survivors are written to `BRIEFING_SECTIONS.md` under their per-analysis section. After all analyses are processed, the unique-by-URL set is appended to `BRIEFING_LINKS.md` and `{url, title}` records to `BRIEFING_INDEX.jsonl` so future runs can dedup against them.

## Cross-analysis URL repeats are allowed (intentional)

A single URL may appear under multiple analyses in the same run, with a per-analysis summary highlighting the aspect that fits that analysis. This matters for sources like weekly changelogs that pack several distinct features per page: the same URL belongs in "Industry Trends" *and* "Workflow Suggestions" with two different summaries. Intra-run dedup is scoped per-analysis to permit this.

Prior-run dedup (against `BRIEFING_LINKS.md` / `BRIEFING_INDEX.jsonl`) is globally controlled by the `ALLOW_PRIOR_DUPES` constant at the top of `ingest.py`. When `True` (current default), prior-run checks are bypassed and the same article may resurface in any later run with potentially new per-analysis framing — useful when sources publish round-ups or revisit themes and the agent has new things to say about an old URL. Flip to `False` to restore strict prior-run dedup. `BRIEFING_LINKS.md` and `BRIEFING_INDEX.jsonl` are written either way so history is preserved and the toggle can be flipped without data loss.

## URL normalization

`normalize_url` does exactly this:

- Lowercase the scheme and netloc (path is preserved as-is).
- Strip the trailing slash from the path.
- Drop tracking query params: anything starting with `utm_`, plus `ref`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`.
- Sort the remaining query params for stable comparison.
- URLs missing a scheme or netloc fall back to lowercased + trailing-slash-stripped raw string.

## File formats

- `BRIEFING_LINKS.md` — bare URLs, one per line. Reader tolerates legacy `- URL` lines and `#` comments; writer only emits bare URLs.
- `BRIEFING_INDEX.jsonl` — one `{"url": ..., "title": ...}` per line. Reader skips unparseable lines so a manual edit can't break ingest. Title-only index; we don't store summaries/dates here.

If `BRIEFING_INDEX.jsonl` is missing or sparser than `BRIEFING_LINKS.md` (e.g., the file predates the index), title-dedup silently degrades to batch-local for the missing entries. URL-dedup is unaffected.

## Deliberate non-features

These were considered and not built — don't add them without a concrete failure case:

- **Content hashing.** Would require ingest to fetch pages. The whole point of the script-heavy split is that ingest is offline and deterministic.
- **`http → https` rewrite.** Sites sometimes serve different content on each; treating them as the same is unsafe.
- **Source-quality ranking** (primary vs. aggregator). The subagent is asked in its prompt to prefer primary sources; ranking again at ingest would duplicate that judgment with worse signal.
- **Timestamp-based "updated content" detection.** No reliable cross-site signal; would invite false positives.

## Reporting

`ingest.py` prints, per analysis: `N new / M found (X url-dup, Y title-dup)`. There is no separate "filtered" category — anything not new or not dup-rejected is kept.
