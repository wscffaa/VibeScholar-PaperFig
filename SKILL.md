---
name: paper-fig
description: "论文架构图生成"
---

# paper-fig

Deterministic grid-based academic figure generation: grid coordinates -> pixel coordinates -> draw.io XML. Zero overlap by construction. AI visual review for iterative quality improvement.

Trigger keywords: `drawio`, `paper figure`, `架构图`, `路线图`, `论文图`, `模块图`, `流程图`, `diagram`, `architecture diagram`

## Workflow

```
 1. Read knowledge.md (mandatory, every session)
 2. Collect module info (from code / ledger / user description -- mixed mode)
 3. Build layout.json (using templates from plans/ as starting point)
 4. ASCII preview -> AskQuestion for user confirmation
 5. grid_engine.py -> output.drawio
 6. Export PNG via draw.io CLI
 7. visual_review.py -> score (5 dimensions, weighted average)
 8. AskQuestion for iteration limit (default 3)
 9. If score < threshold (default 7): adjust layout.json and retry (up to limit)
10. If score >= 8: auto-save to gallery/<type>/
11. AskQuestion for save path (default: semantic naming <type>/<date>-<slug>)
12. Open draw.io for user touch-up (only after final pass)
```

Input modes:
- Natural language: "画一个 FADPB 模块的架构图"
- Structured path: "用 plans/fadpb-grid.json 生成"
- Mixed: "参考 architecture-layered 模板，画 DpSsm 模块"

## Key Management

API credentials for visual_review.py (vision scoring):

```
Priority: CCSwitch DB (~/.cc-switch/cc-switch.db, codex provider is_current=1)
       -> Environment vars (PAPERFIG_API_KEY + PAPERFIG_API_BASE)
       -> Error (exit 1 with resolution instructions)
```

## Relationship

`ofr-paper-diagram` calls this skill as engine layer. When `ofr-paper-diagram` needs to generate a draw.io figure, it delegates grid layout + XML generation + visual review to `paper-fig`. The diagram skill handles higher-level orchestration (figure planning, thesis context, evidence mapping).

## File Layout

```
~/.claude/skills/paper-fig/
├── SKILL.md                <- This file
├── knowledge.md            <- Rules, gotchas, solutions (MUST read first)
├── scripts/
│   ├── grid_engine.py      <- Core: grid -> draw.io XML (--backend xml|drawpyo)
│   ├── visual_review.py    <- AI vision scoring (5 dims, iteration loop)
│   ├── postprocess.py      <- Post-processing pipeline (snap, overlap fix, anchors)
│   └── audit.py            <- Structural XML validation
├── plans/                  <- Reusable layout.json templates
│   ├── architecture-layered.json   (3-5 layer system)
│   ├── architecture-module.json    (single module internals)
│   ├── dataflow-pipeline.json      (left->right pipeline)
│   ├── flowchart-algorithm.json    (decision branches)
│   ├── comparison-ablation.json    (side-by-side)
│   ├── experimental-workflow.json  (train->eval->analyze)
│   └── fadpb-grid.json            (real case: FADPB_CAB)
├── gallery/                <- Auto-accumulated high-score outputs (>= 8)
│   ├── README.md
│   ├── architecture/
│   ├── dataflow/
│   ├── flowchart/
│   ├── ablation/
│   ├── module/
│   └── experimental/
└── tests/
```

## Commands

```bash
# ASCII preview (zero deps, instant)
python3 ~/.claude/skills/paper-fig/scripts/grid_engine.py layout.json --ascii

# Generate draw.io XML (default backend, zero deps)
python3 ~/.claude/skills/paper-fig/scripts/grid_engine.py layout.json -o output.drawio

# Generate via drawpyo (optional, needs: pip install drawpyo)
python3 ~/.claude/skills/paper-fig/scripts/grid_engine.py layout.json -o output.drawio --backend drawpyo

# Post-process (snap + overlap fix + anchor optimization)
python3 ~/.claude/skills/paper-fig/scripts/postprocess.py output.drawio -o output-pp.drawio

# Export PNG (requires draw.io desktop app)
/Applications/draw.io.app/Contents/MacOS/draw.io --export --format png --scale 1.5 --output preview.png output.drawio

# Structural audit (validates XML structure)
python3 ~/.claude/skills/paper-fig/scripts/audit.py output.drawio

# Visual review - single image scoring
python3 ~/.claude/skills/paper-fig/scripts/visual_review.py preview.png --threshold 7

# Visual review - full iteration loop (generate -> export -> score -> suggest)
python3 ~/.claude/skills/paper-fig/scripts/visual_review.py --iterate layout.json --max-iterations 3

# Visual review - JSON output for programmatic use
python3 ~/.claude/skills/paper-fig/scripts/visual_review.py preview.png --json
```

## Behavioral Rules

- Never call `open` during iteration -- only after final pass (step 12)
- Single file per figure -- overwrite, do not create versions
- Always run audit before declaring success
- Read knowledge.md before every generation session (step 1, non-negotiable)
- `html=0` is mandatory in all generated XML (R-08, blank PNG otherwise)
- Do NOT use swimlane containers (z-order issues) -- use plain rect fillColor=none
- Do NOT use `&#xa;` in labels (html=0 does not parse XML entities)

## Gallery Auto-Save

When visual review scores >= 8, auto-save to `gallery/<type>/`:
- `<timestamp>-layout.json` (reproducible grid definition)
- `<timestamp>.png` (rendered output)
- `<timestamp>-metadata.json` (score, dimensions, date, source)
