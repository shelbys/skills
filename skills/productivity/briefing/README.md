# Briefing Automation Skill

**Version:** 1.0  
**Status:** Production Ready  
**Package:** briefing.skill (17.7 KB)

Automate research discovery, deduplication, and archival for curated briefings on any topic.

## Quick Start

### 1. Install
- Download `briefing.skill`
- Import into Claude Code

### 2. Configure
Create `~/.claude/BRIEFING.md`:

```markdown
---
authors:
  - Boris Cherny (@bcherny)

topics:
  - Claude Code

sites:
  - https://claude.com/blog
---

# Instructions
- Focus on concrete, actionable insights
- Avoid speculation

# Analyses
- Industry trends that are likely to last
- Concrete suggestions for workflow improvements
- Inspiring uses of agentic AI
```

Frontmatter list entries use the `  - item` form (two-space indent); body section bullets use `- item` at column 0. `plan.py` validates strictly. Any frontmatter field outside `authors`/`topics`/`sites` becomes a **Filter** passed to the agent; any body heading outside `# Instructions`/`# Analyses` becomes a **Hint**.

### 3. Run
```
/briefing
```

Results appear in:
- `~/.claude/BRIEFING_SECTIONS.md` — Timestamped archive (the briefing itself)
- `~/.claude/BRIEFING_LINKS.md` — Bare URLs of everything kept, one per line (URL-based freshness filter)
- `~/.claude/BRIEFING_INDEX.jsonl` — `{url, title}` per line (title-based dedup; catches mirrors of prior articles on new URLs)

## What It Does

### Research Discovery
- Reads your BRIEFING.md configuration
- Spawns one discovery agent that scans authors/topics/sites in a single pass
- The agent classifies each find into the best-fit analysis area

### Deduplication
- **URL normalization** — Removes tracking params, normalizes protocol/slashes
- **Title similarity** — Detects republished content (>92% match)
- **Freshness checking** — Includes updated content, skips stale duplicates
- **Result:** Only truly new/updated content appears in briefings

### Archival
- Appends timestamped entries to BRIEFING_SECTIONS.md
- Tracks discovered URLs in BRIEFING_LINKS.md (append-only, durable)
- Safe for concurrent runs (atomic file operations)

### Formatting
- Slack-ready markdown with emojis
- Clean structure: source, title, snippet per item
- 3-5 items per analysis area (auto-selected by relevance)

## Configuration

See `references/example-briefings.md` for templates covering:
- AI/ML engineering briefings
- ML infrastructure tracking
- Startup/product strategy
- Security & safety research
- Personal learning topics

### BRIEFING.md Format

```markdown
---
# Required frontmatter — who and what to research
authors:
  - Person Name (@handle)

topics:
  - Topic Name

sites:
  - https://example.com/blog

# Optional extras — any other frontmatter list becomes a "Filter"
# constraint passed to the agent (e.g. `avoids:`, `prefer:`).
---

# Instructions
- Focus on [what you care about]
- Avoid [what you don't want]

# Analyses
- [Area 1 to research]
- [Area 2 to research]
- [Area 3 to research]

# Optional — any other `# Heading` becomes a "Hint" block passed to the agent.
```

### Custom Paths

Use a different BRIEFING.md for different topics:

```
/briefing /path/to/custom/BRIEFING.md
```

Results go to `/path/to/custom/BRIEFING_SECTIONS.md` and `/path/to/custom/BRIEFING_LINKS.md`.

## Output

### BRIEFING_SECTIONS.md (Append-Only Archive)

```markdown
## 2026-05-19T14:30:00Z

### 💼 Industry Trends

**[Source: Article Title](https://url)**
One sentence on what changed, one on why it matters.

**[Source: Another Title](https://url)**
Snippet explaining the insight.
```

### BRIEFING_LINKS.md (URL Tracker)

```
- https://example.com/article-1
- https://another.com/story
- https://third-site.org/post
```

Simple, append-only format. Prevents duplicates in future runs.

## How Deduplication Works

**First run:** All content is new, 0 duplicates  
**Second run:** Same sources checked against BRIEFING_LINKS.md

When you run again a week later:
- URLs already in BRIEFING_LINKS.md are skipped
- New content from same sources is included
- Republished articles (same content, different URL) detected via title similarity
- Updated articles (same URL, newer timestamp) are included

**Example:**
```
Week 1: Find TechCrunch article + Reddit aggregation (same content)
→ Keep TechCrunch (primary), skip Reddit (detected via title similarity)

Week 2: Same content not found anywhere new
→ Skip both URLs (already in BRIEFING_LINKS.md)

Week 3: Original article updated with new data
→ Include if publish timestamp is newer

Week 4: Different take on same topic from different author
→ Include (different content, even if similar title)
```

## Advanced Usage

### Multiple Briefings

Create separate BRIEFING.md files for different topics:

```
~/.claude/briefings/
  ├── ml-infrastructure.md
  ├── agentic-ai.md
  └── startup-strategy.md
```

Run each separately:
```
/briefing ~/.claude/briefings/ml-infrastructure.md
/briefing ~/.claude/briefings/agentic-ai.md
/briefing ~/.claude/briefings/startup-strategy.md
```

Results stay separate (no cross-contamination).

### Scheduled Briefings

Set up a schedule to run weekly:
```
/schedule /briefing at 9am every Monday
```

### Integration with Workflows

BRIEFING_SECTIONS.md is Slack-ready markdown. Share directly:
- Paste in Slack/Discord
- Include in weekly newsletters
- Commit to git for team visibility
- Feed into downstream tools (RSS readers, aggregators)

## Trigger Phrases

The skill auto-triggers when you mention:
- "run a briefing"
- "update my digest"
- "scan sources for fresh content"
- "track research on [topic]"
- "maintain a curated newsletter"
- "automate content discovery"
- "update BRIEFING_LINKS.md"
- References to BRIEFING.md or BRIEFING_LINKS.md

## Troubleshooting

**Q: "No results found"**
- Check that sources are valid (blogs, RSS feeds, newsletters exist)
- Verify authors have recent public content
- Check that analyses are specific enough

**Q: "All results are duplicates"**
- This is correct behavior if you ran the briefing recently
- Run again next week—only new content will appear

**Q: "BRIEFING_LINKS.md is getting large"**
- Normal and expected (append-only by design)
- Prevents duplicates indefinitely
- You can periodically trim very old URLs if you want

**Q: "Different briefings showing similar content"**
- Use specific authors/topics per briefing to avoid overlap
- Keep sources unique across briefings when possible

**Q: "I want different output format"**
- The Slack-ready markdown is fixed (design choice for durability)
- Feature request? Let me know your use case

## Files Included

- **SKILL.md** — Skill definition and the 4-stage workflow (plan → research → ingest → report)
- **scripts/plan.py** — Validates `BRIEFING.md`, ensures tracking files exist, self-heals the title-dedup index, emits a single discovery task as JSON
- **scripts/ingest.py** — Reads the agent's grouped result from stdin, dedupes against `BRIEFING_LINKS.md` / `BRIEFING_INDEX.jsonl`, formats and appends
- **references/agent-prompt-template.md** — Strict-JSON prompt template for the single discovery agent (classifies finds into analyses)
- **references/troubleshooting.md** — Errors from each script plus behavioral surprises
- **references/example-briefings.md** — Configuration templates
- **references/deduplication_strategy.md** — Technical documentation
- **evals/** — Test cases and evaluation fixtures

## Technical Details

### Dependencies
None. `plan.py` and `ingest.py` use only the Python standard library.

### File Format
- BRIEFING.md: strict-schema frontmatter (top-level keys with inline strings or `  - item` bullet lists; nested maps not supported)
- BRIEFING_LINKS.md: plain text, one URL per line (append-safe; legacy `- URL` lines tolerated on read)
- BRIEFING_INDEX.jsonl: one `{"url": ..., "title": ...}` per line (append-safe; unparseable lines silently skipped)
- BRIEFING_SECTIONS.md: markdown with timestamps (portable)

### Performance
- Deduplication: O(n) URL lookups + title similarity scoring
- File operations: Atomic (temp write + move, no corruption risk)
- Concurrency: Safe for parallel briefing runs

### Durability
- Append-only design prevents data loss
- No external dependencies (works offline)
- Human-readable formats (no binary files)
- Compatible with git version control

## Support & Feedback

For issues, feature requests, or questions:
- Check `references/example-briefings.md` for configuration help
- Review `references/deduplication_strategy.md` for how dedup works
- See test results in `evals/` for validation

## License

[Your choice of open-source license, or "Internal Use Only"]

---

**Created:** May 2026  
**Last Updated:** 2026-05-19  
**Status:** Tested and production-ready
