#!/usr/bin/env python3
"""
smart-drawio 网格布局引擎

核心思想：用网格坐标（row/col）定义布局，确定性转换为像素坐标。
网格系统从根本上避免重叠——两个元素不能占据同一格子。

用法:
    from grid_engine import GridLayout, render_ascii, grid_to_drawio_xml
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# 网格 → 像素的转换参数
CELL_WIDTH = 180   # 每格宽度
CELL_HEIGHT = 90   # 每格高度
GAP_X = 50         # 水平间距（增大避免连线贴边）
GAP_Y = 50         # 垂直间距（增大让箭头清晰）
MARGIN_X = 80      # 左边距
MARGIN_Y = 70      # 上边距

# 类型 → 样式映射（学术配色）
STYLE_MAP = {
    "input": {"fill": "#d4e1f5", "stroke": "#2C3E50", "shape": "parallelogram"},
    "output": {"fill": "#d5e8d4", "stroke": "#2C3E50", "shape": "parallelogram"},
    "processing": {"fill": "#dae8fc", "stroke": "#2C3E50", "shape": "rounded"},
    "innovation": {"fill": "#fff2cc", "stroke": "#d6b656", "shape": "rounded"},
    "baseline": {"fill": "#f5f5f5", "stroke": "#2C3E50", "shape": "rounded"},
    "loss": {"fill": "#f8cecc", "stroke": "#b85450", "shape": "rounded"},
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
    detail: str = ""  # 子标签/维度信息


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

    @classmethod
    def from_json(cls, path: str) -> "GridLayout":
        data = json.loads(Path(path).read_text())
        elements = [Element(**e) for e in data.get("elements", [])]
        connections = [Connection(**c) for c in data.get("connections", [])]
        groups = [Group(**g) for g in data.get("groups", [])]
        return cls(
            title=data["title"],
            cols=data["grid"]["cols"],
            rows=data["grid"]["rows"],
            elements=elements,
            connections=connections,
            groups=groups,
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


def grid_to_pixel(row: int, col: int, rowspan: int = 1, colspan: int = 1) -> dict:
    """网格坐标 → 像素坐标（确定性，无 AI 参与）"""
    x = MARGIN_X + col * (CELL_WIDTH + GAP_X)
    y = MARGIN_Y + row * (CELL_HEIGHT + GAP_Y)
    w = colspan * CELL_WIDTH + (colspan - 1) * GAP_X
    h = rowspan * CELL_HEIGHT + (rowspan - 1) * GAP_Y
    return {"x": x, "y": y, "width": w, "height": h}


def render_ascii(layout: GridLayout) -> str:
    """渲染 ASCII 预览图（用于用户确认）"""
    # 创建网格
    grid = [["" for _ in range(layout.cols)] for _ in range(layout.rows)]

    # 填充元素
    for elem in layout.elements:
        tag = {"input": "[I]", "output": "[O]", "processing": "[P]",
               "innovation": "[★]", "baseline": "[B]", "loss": "[L]"}.get(elem.type, "[?]")
        short_label = elem.label[:16]
        grid[elem.row][elem.col] = f"{tag} {short_label}"

    # 渲染
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

        # 连接线
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

    # 连接关系列表
    lines.append("")
    lines.append("  连接关系:")
    for conn in layout.connections:
        style = "──→" if conn.type == "solid" else "- -→"
        label = f" [{conn.label}]" if conn.label else ""
        lines.append(f"    {conn.source} {style} {conn.target}{label}")

    return "\n".join(lines)


def grid_to_drawio_xml(layout: GridLayout) -> str:
    """网格布局 → draw.io XML（确定性转换，无 AI）"""
    cells = []
    id_counter = 2

    def next_id():
        nonlocal id_counter
        id_counter += 1
        return str(id_counter)

    # 组/容器（用普通矩形+文本，不用 swimlane 避免 z-order 遮挡）
    for group in layout.groups:
        gid = next_id()
        pos = grid_to_pixel(group.row, group.col, group.rowspan, group.colspan)
        # 扩大容器边距
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
            f'<mxCell id="{gid}" value="{group.label}" '
            f'style="{style}" vertex="1" parent="1">\n'
            f'  <mxGeometry x="{pos["x"]}" y="{pos["y"]}" '
            f'width="{pos["width"]}" height="{pos["height"]}" as="geometry"/>\n'
            f'</mxCell>'
        )

    # 元素
    elem_ids = {}
    for elem in layout.elements:
        eid = next_id()
        elem_ids[elem.id] = eid
        pos = grid_to_pixel(elem.row, elem.col, elem.rowspan, elem.colspan)
        smap = STYLE_MAP.get(elem.type, STYLE_MAP["processing"])

        if smap["shape"] == "parallelogram":
            shape_style = "shape=parallelogram;perimeter=parallelogramPerimeter;fixedSize=1;"
        else:
            shape_style = "rounded=1;"

        label = elem.label
        if elem.detail:
            label = f"{elem.label}&#xa;{elem.detail}"

        style = (f"{shape_style}whiteSpace=wrap;html=0;"
                 f"fillColor={smap['fill']};strokeColor={smap['stroke']};"
                 f"strokeWidth=1.5;fontSize=12;fontFamily=Arial;align=center;")

        cells.append(
            f'<mxCell id="{eid}" value="{label}" '
            f'style="{style}" vertex="1" parent="1">\n'
            f'  <mxGeometry x="{pos["x"]}" y="{pos["y"]}" '
            f'width="{pos["width"]}" height="{pos["height"]}" as="geometry"/>\n'
            f'</mxCell>'
        )

    # 连接线
    for conn in layout.connections:
        cid = next_id()
        src = elem_ids.get(conn.source, "")
        tgt = elem_ids.get(conn.target, "")
        if not src or not tgt:
            continue

        dash = "dashed=1;dashPattern=12 6;" if conn.type == "dashed" else ""
        # Residual 跳连特殊处理：从右侧绕行
        if conn.type == "dashed":
            edge_style = (
                f"edgeStyle=elbowEdgeStyle;elbow=vertical;rounded=1;"
                f"html=0;strokeColor=#888888;strokeWidth=2;"
                f"fontSize=12;fontFamily=Arial;endArrow=blockThin;endSize=12;"
                f"endFill=1;dashed=1;dashPattern=10 5;"
                f"exitX=1;exitY=0.5;exitDx=0;exitDy=0;"
                f"entryX=1;entryY=0.5;entryDx=0;entryDy=0;"
            )
        else:
            edge_style = (
                f"edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;"
                f"jettySize=auto;html=0;strokeColor=#2C3E50;strokeWidth=2;"
                f"fontSize=12;fontFamily=Arial;endArrow=blockThin;endSize=12;"
                f"endFill=1;"
            )

        cells.append(
            f'<mxCell id="{cid}" value="{conn.label}" '
            f'style="{edge_style}" edge="1" parent="1" source="{src}" target="{tgt}">\n'
            f'  <mxGeometry relative="1" as="geometry"/>\n'
            f'</mxCell>'
        )

    # 组装
    canvas_w = MARGIN_X * 2 + layout.cols * (CELL_WIDTH + GAP_X)
    canvas_h = MARGIN_Y * 2 + layout.rows * (CELL_HEIGHT + GAP_Y)

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


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 grid_engine.py <layout.json> [-o output.drawio] [--ascii]")
        sys.exit(1)

    layout = GridLayout.from_json(sys.argv[1])

    if "--ascii" in sys.argv:
        print(render_ascii(layout))
    else:
        xml = grid_to_drawio_xml(layout)
        out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else "/dev/stdout"
        if out == "/dev/stdout":
            print(xml)
        else:
            Path(out).parent.mkdir(parents=True, exist_ok=True)
            Path(out).write_text(xml)
            print(f"已保存: {out}")
