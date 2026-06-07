# Discovery agent prompt

Use this template for `plan.tasks[0]` — there is exactly one discovery task per
run. Spawn a single subagent; it runs one search pass and classifies each
candidate into the best-fit analysis.

Recommended `subagent_type`: `general-purpose` (it has WebSearch + WebFetch).

## Substitution

Replace the `{{...}}` placeholders with the corresponding fields from the task.
Lists render as `\n- item` bullets. `filters_block` and `hints_block` are
pre-rendered markdown strings (already include their own `## Header` lines, or
empty string if the user defined no extras); substitute them verbatim.

## Template

```
You are running a discovery pass for a curated briefing. Find fresh content in
ONE search pass, then classify each item into the best-fit analysis below.
Return STRICT JSON only — no prose, no markdown fences, no commentary.

## ⛔ HARD CONSTRAINT — Already covered, do NOT return ({{known_urls_count}} URLs)
These URLs have been included in prior briefings. They will be auto-dropped
by the dedup pipeline. **Read this list first.** Every URL you return that
appears below is a wasted WebFetch — your job is to find content NOT on this
list:
{{known_urls}}

## Sources to scan
Authors:
{{authors}}

Topics:
{{topics}}

Sites (constrain searches to these domains when possible):
{{sites}}

## Editorial guidance
{{instructions}}
{{filters_block}}
{{hints_block}}
## Analyses to populate
Place each candidate under any analyses where it genuinely fits. If a single
page covers multiple analyses with distinct framing (e.g. a weekly changelog
where one feature is industry-trend and another is workflow advice), include
the same URL under each relevant analysis with a per-analysis summary
highlighting that specific aspect. Within a single analysis, do not repeat the
same URL.
{{analyses}}

## Your task
1. Run ONE search pass covering the sources above. Find content published in
   the last ~30 days (fresher is better), written by one of the Authors or
   hosted on one of the Sites, on one of the Topics.
2. For each candidate, verify the URL resolves and read enough of the page to
   write a one-sentence summary in your own words. Do NOT fabricate.
3. Prefer primary sources (author's own blog, official docs) over aggregators.
4. Classify each candidate into the best-fit Analysis. Aim for 3–5 per
   analysis. Quality over quantity — an analysis may have 0 if nothing
   genuinely fits. Never invent results to fill a quota.
5. Output a single JSON object with `tool_log` (per-tool call counts you
   accumulated during this task) and `results` (one element per Analysis,
   in the order listed).

## Output contract (STRICT JSON OBJECT)
{
  "tool_log": {
    "WebSearch": <integer count of WebSearch calls you made>,
    "WebFetch": <integer count of WebFetch calls you made>,
    "Read": <count of Read calls, or 0>,
    "<other tool names>": <count>
  },
  "results": [
    {
      "analysis": "<analysis text, copied verbatim from the list above>",
      "candidates": [
        {
          "title": "Exact title from the page",
          "url": "Canonical URL (no tracking params if you can help it)",
          "date": "YYYY-MM-DD publication date (best effort)",
          "summary": "One sentence, your own words, ≤25 words",
          "source": "Site or author name, e.g. 'claude.com' or 'Boris Cherny'"
        }
      ]
    }
  ]
}

Include every analysis in `results` even if its `candidates` array is empty.
Include `tool_log` with honest counts of every tool you invoked while
researching this task — used by the orchestrator to report cost/effort.
```

## What the orchestrating agent does with the result

- The agent's JSON array is already in the shape `ingest.py` consumes — pipe
  it straight in. `ingest.py` tolerates stray code fences, prose preambles,
  and trailing commentary by extracting the first embedded JSON array.
- If the subagent returns no text or unparseable JSON, the run is lost.
  Surface the error to the user and stop — re-runs are cheap.

## Note on the design

This replaces an older pattern where one subagent was spawned per analysis.
Same sources searched N times wasted tokens and produced overlapping
candidates that then had to be deduped. One agent over the same source set,
with classification at output time, costs less and covers more ground.
