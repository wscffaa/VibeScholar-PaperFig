# paper-fig

Deterministic grid-based academic figure generation for draw.io. Grid coordinates → pixel coordinates → draw.io XML. Zero overlap by construction.

[中文](README.md)

## What It Does

1. Define logical structure in `layout.json` (grid positions, element types, connections)
2. Grid engine deterministically converts to pixel coordinates (no overlap possible)
3. AI visual review scores the rendered output (5 dimensions, publication-quality gate)
4. Final touch-up on connection routing in draw.io GUI (~30 seconds)

## Quick Start

```bash
# ASCII preview (zero deps, instant feedback)
python3 scripts/grid_engine.py plans/fadpb-grid.json --ascii

# Generate draw.io XML
python3 scripts/grid_engine.py plans/fadpb-grid.json -o output.drawio

# Export PNG (requires draw.io desktop)
/Applications/draw.io.app/Contents/MacOS/draw.io --export --format png --scale 1.5 --output preview.png output.drawio

# AI visual review (requires OpenAI-compatible API via env vars)
python3 scripts/visual_review.py preview.png --json
```

## Key Management

Visual review requires a vision-capable LLM API. Configure via:
- Environment variables: `PAPERFIG_API_KEY` + `PAPERFIG_API_BASE`
- Or CCSwitch DB (for integrated workflows)

**Never hardcode API keys.**

## Element Types

| Type | Color | Shape | Use For |
|------|-------|-------|---------|
| input | Steel blue #d4e1f5 | Parallelogram | Input data/frames |
| output | Light green #d5e8d4 | Parallelogram | Output/reconstructed |
| processing | Blue #dae8fc | Rounded rect | Standard modules |
| innovation | Orange #fff2cc | Rounded rect | Novel contributions |
| baseline | Gray #f5f5f5 | Rounded rect | Existing components |
| loss | Red #f8cecc | Rounded rect | Training-only |

## Directory Structure

```
├── SKILL.md              # Claude Code skill definition
├── knowledge.md          # Accumulated rules and gotchas
├── scripts/
│   ├── grid_engine.py    # Core: grid → draw.io XML
│   ├── visual_review.py  # AI vision scoring + iteration loop
│   ├── postprocess.py    # Post-processing pipeline
│   └── audit.py          # Structural XML validation
├── plans/                # Reusable layout.json templates
└── gallery/              # Auto-accumulated high-score outputs (≥8)
```

## License

MIT
