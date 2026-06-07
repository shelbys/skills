# Example BRIEFING.md Configurations

Use these templates to set up briefings for your own topics and sources.

## Example 1: AI/ML Engineering Briefing

**Purpose:** Track industry trends and engineering practices in agentic AI

```markdown
---
authors:
  - Boris Cherny (@bcherny)
  - Andrej Karpathy (@karpathy)
  - Dario Amodei (@damodei)

topics:
  - Claude Code
  - Agentic AI
  - AI-native engineering

sites:
  - https://claude.com/blog
  - https://www.anthropic.com/blog
  - https://newsletter.pragmaticengineer.com
---

# Instructions
- Focus on concrete engineering patterns, not hype
- Avoid speculation about future model capabilities
- Prioritize production patterns over research theory
- Exclude vibe coding and non-technical content

# Analyses
- Industry trends that will drive adoption decisions
- Concrete engineering patterns that scale to production
- Real-world wins and measurable business impact
```

---

## Example 2: ML Infrastructure Briefing

**Purpose:** Track systems design, infrastructure, and MLOps developments

```markdown
---
authors:
  - Andrej Karpathy (@karpathy)
  - Chip Huyen (@chipro)

topics:
  - ML infrastructure
  - ML systems design
  - MLOps
  - Distributed training

sites:
  - https://chip-huyen.com/blog
  - https://karpathy.ai
  - https://openai.com/research
  - https://anthropic.com/research
---

# Instructions
- Focus on systems-level insights
- Prioritize case studies and production learnings
- Include both open-source and proprietary approaches

# Analyses
- Data pipeline and feature engineering breakthroughs
- Training infrastructure and optimization strategies
- Monitoring, observability, and production reliability
- Cost efficiency and scale-out patterns
```

---

## Example 3: Startup/Product Briefing

**Purpose:** Track product strategy and startup trends in AI space

```markdown
---
authors:
  - Paul Graham (@paulg)
  - Naval Ravikant (@naval)
  - Patrick Collison (@patrickc)

topics:
  - AI startup strategy
  - Product market fit
  - AI-native applications

sites:
  - https://paulgraham.com/articles.html
  - https://news.ycombinator.com
  - https://a16z.com/articles
---

# Instructions
- Focus on product and business insights
- Prioritize founder/investor perspectives
- Include both successes and failures

# Analyses
- Emerging AI product categories and opportunities
- Go-to-market strategies that work for AI products
- Unit economics and sustainability patterns
- Lessons from successes and failures in the market
```

---

## Example 4: Security & Safety Briefing

**Purpose:** Track AI safety, security, and alignment research

```markdown
---
authors:
  - Dario Amodei (@damodei)
  - Stuart Russell (@srlCPU)
  - Paul Christiano

topics:
  - AI safety
  - AI alignment
  - AI security
  - Interpretability

sites:
  - https://www.alignmentresearchcenter.org
  - https://www.anthropic.com/research
  - https://openai.com/research
  - https://futureofhumanity.ox.ac.uk
---

# Instructions
- Focus on technical approaches and empirical results
- Exclude speculative doomism and unfounded claims
- Prioritize peer-reviewed research and rigorous analysis

# Analyses
- Technical progress in interpretability and mechanistic understanding
- Empirical evidence for/against alignment approaches
- Red-teaming results and vulnerability discoveries
- Policy implications and regulatory considerations
```

---

## Example 5: Personal Learning Briefing

**Purpose:** Track content on specific topic of personal interest

```markdown
---
authors:
  - Your Name or Expert Name

topics:
  - Your topic of interest

sites:
  - https://relevant-blog-1.com
  - https://relevant-blog-2.com
  - https://newsletter.example.com
---

# Instructions
- Avoid content older than 2 weeks
- Prioritize practical over theoretical

# Analyses
- Recent developments in [your topic]
- Practical applications and how-tos
- Thought leadership and opinion pieces
```

---

## Setup Instructions

1. **Choose a template** matching your interests
2. **Customize the sections:**
   - Replace authors with people you follow
   - List topics you care about
   - Add RSS feeds, blogs, or newsletters you want to monitor
   - Write instructions to filter content (optional)
   - List 2-3 analysis areas you want to track

3. **Save as BRIEFING.md:**
   - Default location: `~/.claude/BRIEFING.md`
   - Custom location: anywhere you want (use `/briefing /path/to/BRIEFING.md`)

4. **Run the briefing:**
   ```
   /briefing
   ```
   Or with custom path:
   ```
   /briefing ~/.config/briefings/ml-research.md
   ```

5. **Review results:**
   - New content appears in `BRIEFING_SECTIONS.md`
   - URLs are tracked in `BRIEFING_LINKS.md`
   - Run again next week—duplicates are auto-filtered

---

## Best Practices

### Authors
- Include 3-8 thought leaders in your field
- Mix established figures with emerging voices
- Include both individuals and organizations

### Topics
- Be specific (not "AI" but "Agentic AI")
- List 2-5 topics per briefing
- Avoid overlap across briefings

### Sites
- Include blogs, RSS feeds, and newsletters
- Mix primary sources with aggregators
- Include organization blogs, not just news sites

### Instructions
- Keep 2-3 guidelines max
- Focus on what to *exclude*, not include
- Be specific about quality thresholds

### Analyses
- List 2-4 analysis areas
- Make them orthogonal (non-overlapping)
- Use questions to guide research ("What patterns work?" not "Random insights")

### Cadence
- Run weekly for active topics
- Run bi-weekly for slower-moving topics
- Run monthly for comprehensive reviews

---

## Troubleshooting

**Q: "BRIEFING_LINKS.md is getting too long"**
A: It's append-only, which is intentional (no duplicate URLs ever re-appear). You can periodically trim old URLs, but it's designed for durability.

**Q: "I'm getting duplicate content across multiple briefings"**
A: Create separate BRIEFING.md files for each topic, keep them in different directories. The deduplication only works within a single briefing's BRIEFING_LINKS.md.

**Q: "How often should I run the briefing?"**
A: Depends on your sources. If sources update daily, run weekly. If monthly, run monthly. The deduplication means you can run as often as you want without seeing stale content.

**Q: "Can I customize the output format?"**
A: The Slack-ready markdown is fixed by design (clean, durable, portable). If you need different formatting, let me know the use case.

---

## Real-World Example

Here's a real briefing that was successfully maintained:

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
- Avoid vibe coding

# Analyses
- Industry trends that are likely to last
- Concrete workflow suggestions for agentic engineering
- Inspiring uses of agentic AI
```

**Results after 2 weeks:**
- 47 items discovered
- 3 duplicates caught (content republished across sites)
- 44 unique, fresh items archived
- Ran weekly, 0 overlap across runs
- Used for team standups and strategy discussions
