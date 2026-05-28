# PaperFig Gallery

Auto-accumulated high-quality figure outputs. Figures scoring >= 8 in visual review are automatically saved here for reuse as reference layouts.

## Directory Structure

```
gallery/
├── architecture/    # System architecture diagrams (encoder-decoder, U-Net, etc.)
├── dataflow/        # Data pipeline / forward pass diagrams
├── flowchart/       # Algorithm flowcharts with decision branches
├── ablation/        # Ablation comparison layouts (side-by-side)
├── module/          # Single module internal structure (CAB, Block level)
└── experimental/    # Experiment workflow diagrams
```

## Auto-Accumulation Rule

When visual_review.py scores a figure >= 8/10, the following are saved:

```
gallery/<type>/<YYYY-MM-DD>-<slug>/
├── layout.json      # Grid layout definition (reproducible)
├── preview.png      # Rendered PNG preview
└── metadata.json    # Score, date, source project, notes
```

## metadata.json Schema

```json
{
  "score": 8,
  "date": "2026-05-28",
  "source_project": "010-defmamba",
  "figure_type": "architecture",
  "template_base": "architecture-layered",
  "notes": "3-col layout, FADPB module highlighted"
}
```

## Usage

Browse gallery entries to find similar layouts before creating new figures. Copy and adapt the layout.json rather than starting from scratch.
