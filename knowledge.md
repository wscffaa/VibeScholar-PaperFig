# PaperFig Knowledge Base

> Hard-won rules from visual review iterations. Read before every generation session.

## Prohibitions (absolute, never violate)

| ID | Prohibition | Reason |
|----|-------------|--------|
| F-01 | Never delete Residual/Skip Connection edges | Residual connections are core structural elements |
| F-02 | Never merge functionally distinct modules into one box | Each independent module needs its own visual representation |
| F-03 | Never use decorative elements to replace structural ones | Diagrams must accurately reflect the actual method |
| F-04 | Never omit innovation module annotations | Novel contributions must be visually identifiable (orange/star) |
| F-05 | Never change data flow direction to "beautify" layout | Data flow must match actual forward pass direction |

## Fixed Rules (all figures must obey)

| ID | Rule | Explanation |
|----|------|-------------|
| R-01 | Input/Output use parallelogram shape | Distinguishes data nodes from processing nodes |
| R-02 | Innovation modules use orange (#fff2cc) | Visually highlights contribution points |
| R-03 | Baseline modules use gray (#f5f5f5) | Distinguishes existing components |
| R-04 | Residual edges use dashed + right-side bypass | Academic convention, avoids confusion with main trunk |
| R-05 | Main flow direction top->bottom | Vertical reading convention for academic papers |
| R-06 | Edge label font size >= 12px | Ensures readability after scaling |
| R-07 | Module spacing >= 50px | Avoids visual crowding |
| R-08 | html=0 (plain text labels) | draw.io CLI export does not render HTML labels |

## Known Issues and Solutions

| Issue | Cause | Solution | Version |
|-------|-------|----------|---------|
| Exported PNG is blank | html=1 HTML labels not rendered in headless CLI | Use html=0 + single-line text (no line breaks) | v3->v5 |
| swimlane container occludes children | z-order issue, swimlane renders on top | Use plain rect (fillColor=none) as container | v3->v4 |
| Visual review scores 0 | Image actually blank (above two issues) | Fix html=0 + remove swimlane | v3->v5 |
| Residual dashed line crosses entire diagram | Orthogonal routing takes shortest path | Use elbowEdgeStyle + exitX=1/entryX=1 for right bypass | v6->v8 |
| Group border confused with edges | swimlane/group border visually similar to edges | Remove border or use very thin line (strokeWidth=1) | v6->v8 |
| Branch merge point routing issues | Inherent limitation of orthogonal routing | Leave for user to adjust waypoints in GUI | v8 (accepted) |
| Edge labels too close to line | draw.io default label position | Increase font + white background (CLI has bugs), leave for user | v9 (accepted) |
| Parallelogram vs rounded rect inconsistency | Visual review suggested unifying | Keep parallelogram (I/O semantic distinction), review model scores higher | v10->v11 |
| &#xa; escape chars displayed literally | html=0 mode does not parse XML entities as newlines | Do not use &#xa;, use single-line short text | roadmap-v2->v3 |
| Chinese quotes break XML parsing | Chinese "" treated as quote terminators in XML attributes | Use _esc() function to escape all special characters | roadmap-v1 |
| Character arrows (====>) look unprofessional | Text-simulated arrows lack vector quality | Use separate box + edge connection for real arrows | roadmap-v2->v3 |

## Visual Review Score Baselines

| Configuration | Score | Notes |
|---------------|-------|-------|
| Grid engine + 3col + parallelogram I/O + no border + Residual right-bypass | 8/10 | Current best auto-generated config |
| Same but without Residual | 8/10 | connections +1 but violates F-01 |
| Same but with group border | 7/10 | Border interferes with edge identification |
| Same but unified rounded rect | 7/10 | Loses I/O semantic distinction |

## User-Responsible Adjustments (not auto-optimized)

- Edge waypoint routing (drag to adjust paths)
- Residual dashed line precise routing
- Local spacing fine-tuning
- Edge label positioning

## Auto-Optimized (skill handles)

- Module positioning (grid system, zero overlap)
- Color coding (type -> color mapping)
- Text labels and font sizing
- Overall layout direction and hierarchy
- Arrow styles and sizes
- Spacing uniformity

## Post-Processing Pipeline

After XML generation, optional post-processing:

```bash
python3 ~/.claude/skills/paper-fig/scripts/postprocess.py output.drawio -o output-pp.drawio
```

Pipeline steps (in order):
1. **XML repair** -- truncation detection + closing tag completion
2. **Grid snap** -- all coordinates snap to 10px grid
3. **Overlap fix** -- push apart along smaller penetration axis (max 5 rounds)
4. **Consistent spacing** -- same-layer elements evenly distributed
5. **Anchor optimization** -- angle-based edge exit/entry face selection + fan-out distribution
6. **Arrow normalization** -- endpoint classicBlock + remove start arrows (optional)
7. **Label background** -- edge labels get white background (optional)

## Layout Optimizer Parameters

| Constant | Value | Purpose |
|----------|-------|---------|
| GRID | 10px | Coordinate alignment unit |
| LAYER_GAP | 100px | Vertical gap between layers |
| NODE_GAP | 40px | Horizontal gap between same-layer nodes |
| MARGIN | 40px | Canvas margin on all sides |
| MAX_COLS | 4 | Max columns for disconnected nodes |

## Anchor Optimization Strategy

- Auto-select exit face (top/bottom/left/right) based on source->target angle
- Face selection threshold: rectangle diagonal angle `atan2(h, w)`
- Multiple edges on same face use fan-out: `spread = (i+1) / (count+1)`
- Anchor coords: top=(spread,0), bottom=(spread,1), left=(0,spread), right=(1,spread)

## Drawing Tricks

| Trick | Function | When to Use |
|-------|----------|-------------|
| gridSnap | Align coords to 10px | Always (default on) |
| orthogonalRouting | Orthogonal polyline routing | Academic figures default |
| consistentSpacing | Same-layer spacing equalization | Elements >= 3 |
| normalizeArrows | Unify arrow styles | Mixed-source XML |
| labelBackground | White background for labels | Edge labels overlap nodes |
| jumpCrossings | Crossing jump arcs | Unavoidable edge crossings |
| removeWaypoints | Clear manual waypoints | Before re-routing |

## Academic Mode Disabled Effects

Under research theme, these effects MUST be off:
- shadow
- gradient
- glass
- sketch (hand-drawn)
- rounded preset (but arcSize=10 slight rounding is kept)

## Academic 5-Color Scheme

| Scheme | Fill | Stroke | Semantic |
|--------|------|--------|----------|
| Grayscale (preferred) | #F7F9FC | #2C3E50 | B&W print friendly |
| Blue | #dae8fc | #3498DB | Processing / standard modules |
| Green | #d5e8d4 | #82b366 | Success / output / start |
| Yellow/Orange | #fff2cc | #d6b656 | Innovation / decision / warning |
| Red | #f8cecc | #E74C3C | Loss / bottleneck / emphasis |

Color-blind friendly: avoid red-green combos, prefer blue-orange. Text-background contrast >= 4.5:1.

## Template Library

`plans/` directory templates (use directly or as starting point):

| Template | Use Case |
|----------|----------|
| `architecture-layered.json` | 3-5 layer system architecture (Encoder-Core-Decoder) |
| `architecture-module.json` | Single module internals (CAB/Block level) |
| `dataflow-pipeline.json` | Data processing pipeline (left->right) |
| `flowchart-algorithm.json` | Algorithm flowchart (with decision branches) |
| `comparison-ablation.json` | Ablation comparison (side-by-side) |
| `experimental-workflow.json` | Experiment workflow (train->eval->analyze) |
| `fadpb-grid.json` | FADPB_CAB module (real case) |

## XML Format Constraints (draw.io compatibility)

- All coordinates must be multiples of 10 (gridSize=10)
- Node style must include `fontFamily=Arial;fontSize=12;`
- Edge style must include `edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;`
- Containers use plain rect `fillColor=none` (NOT swimlane, avoids z-order issues)
- Special characters must be XML-escaped (&, <, >, ", Chinese quotes)
- Aspect ratio: 4:3 or 16:9

## Backends

### XML Backend (default, zero dependencies)

The default backend generates raw draw.io XML using Python string formatting.
No external dependencies required. Output is a valid `.drawio` file.

```bash
python3 ~/.claude/skills/paper-fig/scripts/grid_engine.py layout.json -o output.drawio
```

### drawpyo Backend (optional)

[drawpyo](https://github.com/MerrimanInd/drawpyo) is a Python library for programmatic
draw.io file creation. It provides a higher-level API but requires installation.

Install: `pip install drawpyo`

```bash
python3 ~/.claude/skills/paper-fig/scripts/grid_engine.py layout.json -o output.drawio --backend drawpyo
```

Advantages of drawpyo:
- Proper object model (less string manipulation)
- Built-in style management
- Easier to extend with custom shapes

Limitations:
- Extra dependency (not always available in CI/server environments)
- Less control over exact XML output format
- May not preserve all custom style attributes from RESEARCH_THEME

Recommendation: Use `xml` backend (default) for production figures. Use `drawpyo` for
rapid prototyping or when you need programmatic manipulation of the diagram object model.

## Official draw.io XML Reference Rules

Based on the [jgraph/drawio](https://github.com/jgraph/drawio) source and MCP integration:

### Structure

```xml
<mxfile>
  <diagram id="..." name="Page-1">
    <mxGraphModel dx="..." dy="..." grid="1" gridSize="10" ...>
      <root>
        <mxCell id="0"/>                    <!-- root cell, always present -->
        <mxCell id="1" parent="0"/>         <!-- default layer -->
        <!-- vertices and edges here -->
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

### Vertex (Node) Rules

- `vertex="1"` marks a node
- `parent="1"` places it on the default layer
- `<mxGeometry x="..." y="..." width="..." height="..." as="geometry"/>` is required
- Style is a semicolon-separated key=value string
- `html=0` is MANDATORY for CLI export compatibility

### Edge Rules

- `edge="1"` marks a connection
- `source="id"` and `target="id"` reference vertex IDs
- `<mxGeometry relative="1" as="geometry"/>` for edges
- Waypoints go inside geometry as `<Array as="points"><mxPoint x="..." y="..."/></Array>`
- Exit/entry points: `exitX`, `exitY`, `entryX`, `entryY` (0-1 normalized)

### Style Key Reference

| Key | Values | Notes |
|-----|--------|-------|
| `rounded` | 0/1 | Rounded corners |
| `fillColor` | hex/#none | Background color |
| `strokeColor` | hex | Border color |
| `strokeWidth` | number | Border thickness |
| `fontFamily` | string | Font name |
| `fontSize` | number | Font size in px |
| `fontStyle` | 0/1/2/4 | 0=normal, 1=bold, 2=italic, 4=underline (bitmask) |
| `align` | left/center/right | Horizontal text alignment |
| `verticalAlign` | top/middle/bottom | Vertical text alignment |
| `whiteSpace` | wrap | Enable text wrapping |
| `html` | 0/1 | 0=plain text, 1=HTML (MUST be 0 for CLI) |
| `dashed` | 0/1 | Dashed border/edge |
| `dashPattern` | "N M" | Dash and gap lengths |
| `edgeStyle` | orthogonalEdgeStyle/elbowEdgeStyle/... | Edge routing algorithm |
| `endArrow` | block/blockThin/classic/open/none | Arrow head shape |
| `endSize` | number | Arrow head size |
| `endFill` | 0/1 | Filled arrow head |
| `shape` | mxgraph.xxx / parallelogram / ... | Custom shape |

### Gotchas from jgraph/drawio source

1. `id="0"` and `id="1"` are reserved (root + default layer)
2. Compressed diagrams use deflate+base64 in `<diagram>` text content -- we always use uncompressed
3. `pageWidth`/`pageHeight` in mxGraphModel define the visible canvas
4. `dx`/`dy` in mxGraphModel are scroll offsets, not canvas size (but we use them as canvas hints)
5. Styles are inherited: child cells inherit parent styles unless overridden
6. `swimlane` shape has special z-order behavior -- avoid for containers (use plain rect)
