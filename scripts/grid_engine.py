#!/usr/bin/env python3
"""
PaperFig Grid Layout Engine

Core: grid coordinates -> pixel coordinates (deterministic, zero overlap by construction).
Backends: xml (default, zero deps) | drawpyo (optional, requires `pip install drawpyo`).

Usage:
    from grid_engine import GridLayout, render_ascii, grid_to_drawio_xml
    # or CLI:
    python3 grid_engine.py layout.json -o output.drawio [--ascii] [--backend xml|drawpyo]
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# Grid -> pixel conversion parameters
CELL_WIDTH = 180
CELL_HEIGHT = 90
GAP_X = 50
GAP_Y = 50
MARGIN_X = 80
MARGIN_Y = 70

# --- Academic Research Theme ---
RESEARCH_THEME = {
    "primary": "#2C3E50",
    "accent": "#3498DB",
    "bg": "#F7F9FC",
    "text": "#2C3E50",
    "muted": "#525252",
    "font_family": "Arial",
    "font_size": 12,
    "font_size_title": 14,
    "stroke_width": 1.5,
    "edge_stroke_width": 2,
    "end_arrow": "blockThin",
    "end_size": 12,
}

# Academic 5-color scheme (fill + stroke pairs)
ACADEMIC_SCHEMES = {
    "grayscale": {"fill": "#F7F9FC", "stroke": "#2C3E50"},
    "blue": {"fill": "#dae8fc", "stroke": "#3498DB"},
    "green": {"fill": "#d5e8d4", "stroke": "#82b366"},
    "yellow": {"fill": "#fff2cc", "stroke": "#d6b656"},
    "red": {"fill": "#f8cecc", "stroke": "#E74C3C"},
}

# Type -> style mapping (academic color coding)
STYLE_MAP = {
    "input": {"fill": "#d4e1f5", "stroke": "#2C3E50", "shape": "parallelogram"},
    "output": {"fill": "#d5e8d4", "stroke": "#2C3E50", "shape": "parallelogram"},
    "processing": {"fill": "#dae8fc", "stroke": "#2C3E50", "shape": "rounded"},
    "innovation": {"fill": "#fff2cc", "stroke": "#d6b656", "shape": "rounded"},
    "baseline": {"fill": "#f5f5f5", "stroke": "#2C3E50", "shape": "rounded"},
    "loss": {"fill": "#f8cecc", "stroke": "#b85450", "shape": "rounded"},
    "decision": {"fill": "#fff2cc", "stroke": "#d6b656", "shape": "rhombus"},
    "start_end": {"fill": "#d5e8d4", "stroke": "#2C3E50", "shape": "ellipse"},
    "datastore": {"fill": "#dae8fc", "stroke": "#2C3E50", "shape": "cylinder"},
    "annotation": {"fill": "none", "stroke": "none", "shape": "text"},
    "group": {"fill": "#F7F9FC", "stroke": "#2C3E50", "shape": "swimlane"},
}


@dataclass
class Element:
    id: str
    label: str
    type: str  # input/output/processing/innovation/baseline/loss
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    detail: str = ""  # subtitle / dimension info


@dataclass
class Connection:
    source: str
    target: str
    label: str = ""
    type: str = "solid"  # solid/dashed/skip


@dataclass
class Group:
    id: str
    label: str
    row: int
    col: int
    rowspan: int
    colspan: int
    dashed: bool = True


@dataclass
class GridLayout:
    title: str
    cols: int
    rows: int
    elements: list[Element] = field(default_factory=list)
    connections: list[Connection] = field(default_factory=list)
    groups: list[Group] = field(default_factory=list)
    cell_width: int = CELL_WIDTH
    cell_height: int = CELL_HEIGHT
    gap_x: int = GAP_X
    gap_y: int = GAP_Y

    @classmethod
    def from_json(cls, path: str) -> "GridLayout":
        data = json.loads(Path(path).read_text())
        elements = [Element(**{k: v for k, v in e.items() if k in Element.__dataclass_fields__}) for e in data.get("elements", [])]
        connections = [Connection(**{k: v for k, v in c.items() if k in Connection.__dataclass_fields__}) for c in data.get("connections", [])]
        groups = [Group(**{k: v for k, v in g.items() if k in Group.__dataclass_fields__}) for g in data.get("groups", [])]
        title = data.get("title") or data.get("description") or data.get("templateId", "Untitled")
        defaults = data.get("defaults", {})
        return cls(
            title=title,
            cols=data["grid"]["cols"],
            rows=data["grid"]["rows"],
            elements=elements,
            connections=connections,
            groups=groups,
            cell_width=defaults.get("cellWidth", CELL_WIDTH),
            cell_height=defaults.get("cellHeight", CELL_HEIGHT),
            gap_x=defaults.get("gapX", GAP_X),
            gap_y=defaults.get("gapY", GAP_Y),
        )

    def to_json(self, path: str):
        data = {
            "title": self.title,
            "grid": {"cols": self.cols, "rows": self.rows},
            "elements": [vars(e) for e in self.elements],
            "connections": [vars(c) for c in self.connections],
            "groups": [vars(g) for g in self.groups],
        }
        Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def grid_to_pixel(row: int, col: int, rowspan: int = 1, colspan: int = 1,
                  cw: int = CELL_WIDTH, ch: int = CELL_HEIGHT,
                  gx: int = GAP_X, gy: int = GAP_Y) -> dict:
    """Grid coordinates -> pixel coordinates (deterministic, no AI involved)."""
    x = MARGIN_X + col * (cw + gx)
    y = MARGIN_Y + row * (ch + gy)
    w = colspan * cw + (colspan - 1) * gx
    h = rowspan * ch + (rowspan - 1) * gy
    return {"x": x, "y": y, "width": w, "height": h}


def _esc(text: str) -> str:
    """XML attribute escaping."""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")
            .replace("“", "&quot;").replace("”", "&quot;"))


def render_ascii(layout: GridLayout) -> str:
    """Render ASCII preview for user confirmation before XML generation."""
    grid = [["" for _ in range(layout.cols)] for _ in range(layout.rows)]

    for elem in layout.elements:
        tag = {"input": "[I]", "output": "[O]", "processing": "[P]",
               "innovation": "[*]", "baseline": "[B]", "loss": "[L]"}.get(elem.type, "[?]")
        short_label = elem.label[:16]
        grid[elem.row][elem.col] = f"{tag} {short_label}"

    lines = []
    lines.append(f"  {'─' * 60}")
    lines.append(f"  {layout.title}")
    lines.append(f"  {'─' * 60}")
    lines.append("")

    col_width = 22
    for r in range(layout.rows):
        row_cells = []
        for c in range(layout.cols):
            cell = grid[r][c]
            if cell:
                row_cells.append(f"┌{'─' * (col_width-2)}┐")
            else:
                row_cells.append(" " * col_width)
        lines.append("  " + "  ".join(row_cells))

        row_cells = []
        for c in range(layout.cols):
            cell = grid[r][c]
            if cell:
                padded = cell[:col_width-4].center(col_width-4)
                row_cells.append(f"│ {padded} │")
            else:
                row_cells.append(" " * col_width)
        lines.append("  " + "  ".join(row_cells))

        row_cells = []
        for c in range(layout.cols):
            cell = grid[r][c]
            if cell:
                row_cells.append(f"└{'─' * (col_width-2)}┘")
            else:
                row_cells.append(" " * col_width)
        lines.append("  " + "  ".join(row_cells))

        if r < layout.rows - 1:
            arrow_row = []
            for c in range(layout.cols):
                if grid[r][c] and grid[r+1][c]:
                    arrow_row.append(f"{'│':^{col_width}}")
                elif grid[r][c]:
                    has_conn = any(
                        conn.source == next((e.id for e in layout.elements if e.row == r and e.col == c), "")
                        for conn in layout.connections
                    )
                    arrow_row.append(f"{'↓' if has_conn else ' ':^{col_width}}")
                else:
                    arrow_row.append(" " * col_width)
            lines.append("  " + "  ".join(arrow_row))

    lines.append("")
    lines.append("  Connections:")
    for conn in layout.connections:
        style = "──→" if conn.type == "solid" else "- -→"
        label = f" [{conn.label}]" if conn.label else ""
        lines.append(f"    {conn.source} {style} {conn.target}{label}")

    return "\n".join(lines)


def grid_to_drawio_xml(layout: GridLayout) -> str:
    """Grid layout -> draw.io XML (deterministic, no AI). html=0 enforced."""
    cells = []
    id_counter = 2

    def next_id():
        nonlocal id_counter
        id_counter += 1
        return str(id_counter)

    cw, ch, gx, gy = layout.cell_width, layout.cell_height, layout.gap_x, layout.gap_y

    # Groups (plain rect with fillColor=none, NOT swimlane to avoid z-order issues)
    for group in layout.groups:
        gid = next_id()
        pos = grid_to_pixel(group.row, group.col, group.rowspan, group.colspan, cw, ch, gx, gy)
        pos["x"] -= 20
        pos["y"] -= 40
        pos["width"] += 40
        pos["height"] += 60
        dash = "dashed=1;dashPattern=8 6;" if group.dashed else ""
        style = (f"rounded=1;whiteSpace=wrap;html=0;{dash}"
                 f"fillColor=none;strokeColor=#2C3E50;"
                 f"strokeWidth=1.5;fontSize=14;fontFamily=Arial;"
                 f"verticalAlign=top;align=center;spacingTop=8;fontStyle=1;")
        cells.append(
            f'<mxCell id="{gid}" value="{_esc(group.label)}" '
            f'style="{style}" vertex="1" parent="1">\n'
            f'  <mxGeometry x="{pos["x"]}" y="{pos["y"]}" '
            f'width="{pos["width"]}" height="{pos["height"]}" as="geometry"/>\n'
            f'</mxCell>'
        )

    # Elements
    elem_ids = {}
    for elem in layout.elements:
        eid = next_id()
        elem_ids[elem.id] = eid
        pos = grid_to_pixel(elem.row, elem.col, elem.rowspan, elem.colspan, cw, ch, gx, gy)
        smap = STYLE_MAP.get(elem.type, STYLE_MAP["processing"])

        shape = smap["shape"]
        if shape == "parallelogram":
            shape_style = "shape=parallelogram;perimeter=parallelogramPerimeter;fixedSize=1;"
        elif shape == "rhombus":
            shape_style = "rhombus;perimeter=rhombusPerimeter;"
        elif shape == "ellipse":
            shape_style = "ellipse;perimeter=ellipsePerimeter;"
        elif shape == "cylinder":
            shape_style = "shape=cylinder3;whiteSpace=wrap;boundedLbl=1;size=15;direction=south;"
        elif shape == "text":
            shape_style = "text;strokeColor=none;fillColor=none;"
        else:
            shape_style = "rounded=1;"

        label = _esc(elem.label)
        if elem.detail:
            label = f"{_esc(elem.label)} ({_esc(elem.detail)})"

        fill_part = f"fillColor={smap['fill']};" if smap['fill'] != "none" else "fillColor=none;"
        stroke_part = f"strokeColor={smap['stroke']};" if smap['stroke'] != "none" else "strokeColor=none;"
        style = (f"{shape_style}whiteSpace=wrap;html=0;"
                 f"{fill_part}{stroke_part}"
                 f"strokeWidth={RESEARCH_THEME['stroke_width']};fontSize={RESEARCH_THEME['font_size']};"
                 f"fontFamily={RESEARCH_THEME['font_family']};align=center;")

        cells.append(
            f'<mxCell id="{eid}" value="{label}" '
            f'style="{style}" vertex="1" parent="1">\n'
            f'  <mxGeometry x="{pos["x"]}" y="{pos["y"]}" '
            f'width="{pos["width"]}" height="{pos["height"]}" as="geometry"/>\n'
            f'</mxCell>'
        )

    # Edges
    T = RESEARCH_THEME
    for conn in layout.connections:
        cid = next_id()
        src = elem_ids.get(conn.source, "")
        tgt = elem_ids.get(conn.target, "")
        if not src or not tgt:
            continue

        conn_label = _esc(conn.label) if conn.label else ""
        if conn.type == "dashed":
            edge_style = (
                f"edgeStyle=elbowEdgeStyle;elbow=vertical;rounded=1;"
                f"html=0;strokeColor=#888888;strokeWidth={T['edge_stroke_width']};"
                f"fontSize={T['font_size']};fontFamily={T['font_family']};"
                f"endArrow={T['end_arrow']};endSize={T['end_size']};"
                f"endFill=1;dashed=1;dashPattern=10 5;"
                f"exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                f"entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
            )
        elif conn.type == "skip":
            edge_style = (
                f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
                f"jettySize=auto;html=0;strokeColor={T['accent']};strokeWidth={T['edge_stroke_width']};"
                f"fontSize={T['font_size']};fontFamily={T['font_family']};"
                f"endArrow={T['end_arrow']};endSize={T['end_size']};"
                f"endFill=1;dashed=1;dashPattern=6 4;"
            )
        else:
            edge_style = (
                f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
                f"jettySize=auto;html=0;strokeColor={T['primary']};strokeWidth={T['edge_stroke_width']};"
                f"fontSize={T['font_size']};fontFamily={T['font_family']};"
                f"endArrow={T['end_arrow']};endSize={T['end_size']};"
                f"endFill=1;"
            )

        cells.append(
            f'<mxCell id="{cid}" value="{conn_label}" '
            f'style="{edge_style}" edge="1" parent="1" source="{src}" target="{tgt}">\n'
            f'  <mxGeometry relative="1" as="geometry"/>\n'
            f'</mxCell>'
        )

    # Assemble full XML
    canvas_w = MARGIN_X * 2 + layout.cols * (cw + gx)
    canvas_h = MARGIN_Y * 2 + layout.rows * (ch + gy)

    xml = (
        f'<mxfile>\n'
        f'  <diagram id="grid-layout" name="Page-1">\n'
        f'    <mxGraphModel dx="{canvas_w}" dy="{canvas_h}" grid="1" gridSize="10" '
        f'guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" '
        f'pageScale="1" pageWidth="{canvas_w}" pageHeight="{canvas_h}" math="0" shadow="0">\n'
        f'      <root>\n'
        f'        <mxCell id="0"/>\n'
        f'        <mxCell id="1" parent="0"/>\n'
    )
    for cell in cells:
        xml += f'        {cell}\n'
    xml += '      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>'

    return xml


# --- drawpyo optional backend ---

def _check_drawpyo() -> bool:
    """Check if drawpyo is available."""
    try:
        import drawpyo  # noqa: F401
        return True
    except ImportError:
        return False


def grid_to_drawpyo(layout: GridLayout, output_path: str) -> str:
    """Grid layout -> draw.io file via drawpyo library (optional backend).
    Returns the output path on success, raises ImportError if drawpyo unavailable.
    """
    try:
        import drawpyo
        from drawpyo.diagram import File, Page
    except ImportError:
        raise ImportError(
            "drawpyo not installed. Install with: pip install drawpyo\n"
            "Or use the default xml backend: --backend xml"
        )

    file = File()
    file.file_path = output_path
    page = Page(file=file, name="Page-1")

    cw, ch, gx, gy = layout.cell_width, layout.cell_height, layout.gap_x, layout.gap_y

    elem_objects = {}
    for elem in layout.elements:
        pos = grid_to_pixel(elem.row, elem.col, elem.rowspan, elem.colspan, cw, ch, gx, gy)
        smap = STYLE_MAP.get(elem.type, STYLE_MAP["processing"])

        label = elem.label
        if elem.detail:
            label = f"{elem.label} ({elem.detail})"

        obj = drawpyo.diagram.Object(
            page=page,
            value=label,
            position=(pos["x"], pos["y"]),
            size=(pos["width"], pos["height"]),
        )
        obj.fill_color = smap["fill"] if smap["fill"] != "none" else None
        obj.stroke_color = smap["stroke"] if smap["stroke"] != "none" else None
        elem_objects[elem.id] = obj

    for conn in layout.connections:
        src_obj = elem_objects.get(conn.source)
        tgt_obj = elem_objects.get(conn.target)
        if not src_obj or not tgt_obj:
            continue
        edge = drawpyo.diagram.Edge(
            page=page,
            source=src_obj,
            target=tgt_obj,
            label=conn.label or "",
        )
        if conn.type == "dashed":
            edge.dashed = True

    file.write()
    return output_path


# --- CLI entry point ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="PaperFig Grid Engine")
    parser.add_argument("layout", help="Path to layout.json")
    parser.add_argument("-o", "--output", default=None, help="Output .drawio path")
    parser.add_argument("--ascii", action="store_true", help="Print ASCII preview only")
    parser.add_argument("--backend", choices=["xml", "drawpyo"], default="xml",
                        help="Rendering backend (default: xml, zero deps)")
    args = parser.parse_args()

    layout = GridLayout.from_json(args.layout)

    if args.ascii:
        print(render_ascii(layout))
        return

    if args.backend == "drawpyo":
        if not _check_drawpyo():
            print("ERROR: drawpyo not installed. Use --backend xml or: pip install drawpyo",
                  file=sys.stderr)
            sys.exit(1)
        out = args.output or "output.drawio"
        grid_to_drawpyo(layout, out)
        print(f"Saved (drawpyo): {out}")
    else:
        xml = grid_to_drawio_xml(layout)
        if args.output:
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            Path(args.output).write_text(xml)
            print(f"Saved: {args.output}")
        else:
            print(xml)


if __name__ == "__main__":
    main()
