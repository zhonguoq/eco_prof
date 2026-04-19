# Wiki Schema — Personal Economics Knowledge Base

This document defines the structure conventions, workflows, and LLM behavioral rules for this project.
**The LLM MUST follow this schema** and help update it as conventions evolve.

---

## Directory Structure

```
eco_knowladge_base/
├── raw/                    # Source documents (read-only, LLM never modifies)
│   ├── assets/             # Images, PDFs, attachments
│   └── *.md / *.pdf / ...  # Raw source files
├── wiki/                   # LLM-maintained knowledge base (the "financial brain")
│   ├── index.md            # Global index (updated after every ingest)
│   ├── log.md              # Operation log (append-only)
│   ├── concepts/           # Economic concepts, theories, models
│   ├── thinkers/           # Economist profile pages
│   ├── schools/            # School of thought overviews
│   ├── sources/            # Summary page for each source document
│   └── analyses/           # Cross-source analyses, comparisons, syntheses
├── lab/                    # Lab: tools, data, reports (the practice layer)
│   ├── tools/              # Data-fetching scripts and analysis tools
│   ├── data/               # Fetched raw data (csv/json — exclude from git or manage separately)
│   └── reports/            # Analysis snapshots (valuable conclusions may be archived to wiki/analyses/)
├── CLAUDE.md               # LLM Wiki pattern document + project bootstrap instructions
└── SCHEMA.md               # This file: concrete schema conventions
```

---

## Page Format

All wiki pages use YAML frontmatter:

```yaml
---
title: Page title
type: concept | thinker | school | source | analysis
tags: [macroeconomics, monetary-policy, ...]
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [source-filename, ...]   # raw sources that support this page
---
```

### Content structure by page type

**concept**
- Definition (Chinese + English)
- Core mechanism
- Related concepts (internal links)
- Representative thinkers (internal links)
- School affiliation (internal links)
- Source citations

**thinker**
- Bio (birth/death years, nationality, school)
- Core contributions
- Major works
- Key concepts (internal links)
- Controversies and criticisms
- Source citations

**school**
- Origins and background
- Core claims
- Representative figures (internal links)
- Key concepts (internal links)
- Disagreements with other schools
- Source citations

**source**
- Metadata (author, year, type)
- Core arguments (3–7 bullets)
- Key concepts (internal links)
- Relation to existing wiki content: what it supports or challenges
- Questions worth exploring further

**analysis**
- Problem / goal
- Method
- Key findings
- Conclusions
- Wiki pages cited

---

## Internal Link Conventions

Use standard Markdown link format: `[Page Title](../concepts/page.md)`.
Prefer relative paths for compatibility with both Obsidian and standard Markdown renderers.

---

## Workflows

### Ingest (processing a new source)

1. Read the new source file from `raw/`
2. Discuss key takeaways with the user (optional)
3. Create a source summary page in `wiki/sources/`
4. Update or create related pages in `concepts/`, `thinkers/`, `schools/`
5. Add an index entry to `wiki/index.md` and update counts
6. Append a log entry to `wiki/log.md`

### Query

1. Read `wiki/index.md` to identify relevant pages
2. Read those pages and synthesize an answer
3. If the answer has standalone value, propose saving it as a page in `analyses/`

### Lint (health check)

Check for:
- Concepts referenced by internal links but lacking their own page (dangling links)
- Orphan pages with no inbound links
- Contradictory claims across pages
- Concepts cited by ≥ 2 sources but still lacking a dedicated page
- Web search directions that could fill data gaps

---

## Lab Rules

### Separation of concerns

`lab/` is where theory meets practice. It is strictly separate from `wiki/`:

| | wiki (brain) | lab (practice) |
|---|---|---|
| Content | Knowledge, frameworks, principles | Programs, data, reports |
| Longevity | Long-lived | Time-sensitive, changes with markets |
| Author | LLM, guided by user thinking | Scripts + LLM collaborative analysis |
| Change rate | Slow, deliberate | Fast, follows market data |

### One-way reference principle

```
wiki (theory) ──referenced by──→ lab/tools (implements framework indicators)
                                        ↓ produces data and reports
                                 lab/reports/
                                        ↓ archive highlights (user confirms)
                                 wiki/analyses/ (permanent knowledge)
```

- `lab/tools/` scripts **reference** wiki frameworks but never modify the wiki
- `lab/data/` holds raw fetched data — intermediate artifacts
- `lab/reports/` holds analysis snapshots; when a report yields a **permanently valuable conclusion**, the LLM proposes archiving it to `wiki/analyses/`

### Lab file naming conventions

- Tool scripts: `tools/<description>.py` — e.g. `fetch_us_indicators.py`
- Data files: `data/<source>_<indicator>_<date>.csv` — e.g. `fred_yield_curve_20260412.csv`
- Report files: `reports/<YYYY-MM-DD>_<topic>.md` — e.g. `2026-04-12_us-debt-cycle-diagnosis.md`

### Lab workflows

**Fetch**
1. Run the relevant script in `lab/tools/`
2. Save output to `lab/data/`
3. Append a data-update entry to `wiki/log.md`

**Analyze**
1. LLM reads the latest files in `lab/data/`
2. Cross-references against relevant framework pages in `wiki/analyses/`
3. Writes diagnostic conclusions to `lab/reports/`
4. If conclusions have long-term value, proposes archiving to `wiki/analyses/`

**Alert**
- When a key indicator hits a danger threshold defined in the wiki framework, the LLM proactively flags it
- Alert records are appended to `wiki/log.md`

---

## Language Conventions

- **Instruction files** (CLAUDE.md, SCHEMA.md): English
- **Wiki page titles**: bilingual — `中文名 (English Name)`, e.g. `边际效用 (Marginal Utility)`
- **Thinker and school titles**: English primary, Chinese translation in parentheses
- **Wiki body text**: Chinese primary, with English technical terms on first use
- **Source summary pages**: match the language of the original source

---

## Economics Taxonomy (for tagging)

Main domains covered in this wiki:

- Microeconomics / Macroeconomics
- Monetary Economics / Fiscal Policy
- Behavioral Economics
- Development Economics
- International Economics / Trade Theory
- Political Economy
- Game Theory
- Information Economics
- Institutional Economics
- History of Economic Thought
