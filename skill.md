---
name: VibeScholar-PaperFig
description: "Generate publication-quality academic paper figures (architecture diagrams, thesis roadmaps, module flowcharts, data pipeline charts) as draw.io XML using a deterministic grid-based layout engine with AI visual review. Use this skill whenever the user asks to draw, create, or generate any diagram for a paper or thesis — including architecture overviews, method flowcharts, research roadmaps, chapter structure figures, or module detail diagrams. Also trigger when the user mentions drawio, paper figure, 架构图, 路线图, 论文图, 模块图, 流程图, or wants to visualize paper/thesis structure. This skill handles the full pipeline: ASCII wireframe preview → grid layout → draw.io XML generation → PNG export → AI visual scoring → iterative refinement → final delivery for user touch-up in draw.io GUI."
---

# VibeScholar-PaperFig

Academic paper figure generation toolkit. Converts structured layout descriptions into publication-ready draw.io diagrams through a deterministic grid engine and AI-driven visual quality iteration.

GitHub: https://github.com/wscffaa/VibeScholar-PaperFig

## How It Works

The core insight: LLMs are bad at pixel coordinates but good at describing structure. So we separate concerns:

1. **You** define the logical structure (what modules exist, how they connect, their types)
2. **Grid engine** deterministically converts grid positions to pixel coordinates (zero overlap by construction)
3. **AI visual review** scores the rendered output and provides actionable feedback
4. **You** do final touch-up on connection line routing in draw.io GUI (30 seconds of dragging)

## Workflow

```
Step 1: Read knowledge.md (mandatory — contains hard-won lessons)
Step 2: Collect module info from code/ledger/craft files
Step 3: Build layout.json (grid coordinates, element types, connections)
Step 4: Show ASCII preview to user for layout confirmation
Step 5: Run grid_engine.py → output.drawio
Step 6: Export PNG via draw.io CLI
Step 7: Run visual_review.py → score + feedback
Step 8: If score < 7: adjust layout.json based on feedback, goto Step 5
Step 9: If score ≥ 7: open draw.io for user to adjust connection lines
```

Important behavioral rules:
- Never call `open` during iteration — only after final pass
- Single file per figure — overwrite, don't create versions
- Always run visual review before declaring success
- Read knowledge.md before every generation session

## File Layout

```
.claude/skills/VibeScholar-PaperFig/
├── skill.md              ← This file
├── knowledge.md          ← Accumulated rules, gotchas, and solutions
├── grid_engine.py        ← Core: grid coords → draw.io XML
├── audit.py              ← Structural XML validation
└── plans/                ← Reusable layout.json templates

_workspace/03-scripts/
└── visual_review.py      ← AI vision model scoring (needs OpenAI-compatible API)
```

## layout.json Schema

```json
{
  "title": "Figure Title",
  "grid": {"cols": 3, "rows": 9},
  "elements": [
    {
      "id": "unique_id",
      "label": "Display Text",
      "type": "input|output|processing|innovation|baseline|loss",
      "row": 0,
      "col": 1,
      "rowspan": 1,
      "colspan": 2,
      "detail": "Optional subtitle text"
    }
  ],
  "connections": [
    {
      "source": "element_id",
      "target": "element_id",
      "label": "optional edge label",
      "type": "solid|dashed"
    }
  ],
  "groups": [
    {
      "id": "group_id",
      "label": "Group Label",
      "row": 0, "col": 0, "rowspan": 9, "colspan": 3,
      "dashed": true
    }
  ]
}
```

Element types map to academic color coding:
| Type | Color | Shape | Use For |
|------|-------|-------|---------|
| input | Steel blue #d4e1f5 | Parallelogram | Input data/frames |
| output | Light green #d5e8d4 | Parallelogram | Output/reconstructed |
| processing | Blue #dae8fc | Rounded rect | Standard modules |
| innovation | Orange #fff2cc | Rounded rect | Novel contributions (highlight) |
| baseline | Gray #f5f5f5 | Rounded rect | Existing/borrowed components |
| loss | Red #f8cecc | Rounded rect | Training-only components |

## Commands

```bash
# ASCII preview (zero cost, confirm layout before generation)
python3 .claude/skills/VibeScholar-PaperFig/grid_engine.py layout.json --ascii

# Generate draw.io XML
python3 .claude/skills/VibeScholar-PaperFig/grid_engine.py layout.json -o output.drawio

# Export PNG (requires draw.io desktop)
/Applications/draw.io.app/Contents/MacOS/draw.io --export --format png --scale 1.5 --output preview.png output.drawio

# Visual review (requires OpenAI-compatible vision API)
python3 _workspace/03-scripts/visual_review.py preview.png --json

# Structural audit
python3 .claude/skills/VibeScholar-PaperFig/audit.py output.drawio
```

## When Visual Review Fails

The visual review returns specific issues. Map them to layout.json adjustments:

| Feedback | Fix |
|----------|-----|
| "modules overlap" | Impossible with grid engine — check if groups overlap elements |
| "text too small" | Shorten label text, grid engine uses fixed 12px |
| "connections crossing" | Rearrange grid positions to minimize crossings |
| "too crowded" | Increase grid dimensions, add empty rows/cols as spacing |
| "color too many" | Reduce element type variety, use fewer categories |
| "residual line interferes" | Use elbowEdgeStyle with exitX=1/entryX=1 for right-side bypass |

## Responsibility Split

What this skill handles automatically:
- Module positioning (grid system, zero overlap guaranteed)
- Color coding (type → color mapping)
- Text labels and font sizing
- Overall layout direction and hierarchy
- Arrow styles and sizes
- Spacing uniformity

What the user handles in draw.io GUI (takes ~30 seconds):
- Connection line waypoint routing (drag to adjust paths)
- Residual/skip connection precise routing
- Minor spacing tweaks
- Edge label positioning

## Relationship to Other Figure Skills

| Figure Type | Tool |
|-------------|------|
| Architecture diagrams, roadmaps, flowcharts | **VibeScholar-PaperFig** |
| Quantitative charts (curves, bars, ablation tables) | ofr-thesis-figure (matplotlib) |
| Qualitative comparison grids (visual results) | ofr-thesis-figure (matplotlib) |
| Frequency analysis plots | ofr-thesis-figure (matplotlib) |

## Critical: Read knowledge.md First

Before generating any figure, read `knowledge.md` in this skill directory. It contains:
- **Prohibitions** (F-01 to F-05): Things that must never be done (e.g., never delete residual connections)
- **Fixed rules** (R-01 to R-08): Mandatory style conventions
- **Known issues**: Problems encountered and their proven solutions
- **Scoring baselines**: What configurations achieve what scores

Skipping this step leads to repeating solved problems.
