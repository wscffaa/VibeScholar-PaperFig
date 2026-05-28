#!/usr/bin/env python3
"""
draw.io XML 后处理流水线

从 smart-drawio-next 提取的核心后处理算法，适配纯 Python 本地执行。
包含：网格对齐、重叠修复、间距一致化、锚点优化、XML 修复。
"""

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional


GRID = 10
LAYER_GAP = 100
NODE_GAP = 40
MARGIN = 40


def snap(v: float, grid: int = GRID) -> int:
    """对齐到网格"""
    return round(v / grid) * grid


# ─── Grid Snap ───────────────────────────────────────────────────────────────

def grid_snap(xml: str, grid_size: int = GRID) -> str:
    """所有坐标对齐到 grid_size 网格"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    for geo in root.iter("mxGeometry"):
        for attr in ("x", "y", "width", "height"):
            val = geo.get(attr)
            if val:
                geo.set(attr, str(snap(float(val), grid_size)))

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ─── Overlap Fix ─────────────────────────────────────────────────────────────

@dataclass
class _Rect:
    id: str
    x: float
    y: float
    w: float
    h: float
    parent: str = "1"


def _extract_rects(root) -> list[_Rect]:
    """提取所有顶点的几何信息（跳过 group 容器和 annotation）"""
    rects = []
    for cell in root.iter("mxCell"):
        cid = cell.get("id", "")
        if cid in ("0", "1"):
            continue
        if cell.get("vertex") != "1":
            continue
        style = cell.get("style", "")
        if "fillColor=none" in style:
            continue
        geo = cell.find("mxGeometry")
        if geo is None:
            continue
        rects.append(_Rect(
            id=cid,
            x=float(geo.get("x", "0")),
            y=float(geo.get("y", "0")),
            w=float(geo.get("width", "100")),
            h=float(geo.get("height", "50")),
            parent=cell.get("parent", "1"),
        ))
    return rects


def overlap_fix(xml: str, max_rounds: int = 5) -> str:
    """检测并修复重叠节点（沿穿透量较小的轴推开）"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    rects = _extract_rects(root)
    if len(rects) < 2:
        return xml

    for _ in range(max_rounds):
        moved = False
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                a, b = rects[i], rects[j]
                if a.parent != b.parent:
                    continue
                sep_x = max(a.x, b.x) - min(a.x + a.w, b.x + b.w)
                sep_y = max(a.y, b.y) - min(a.y + a.h, b.y + b.h)
                if sep_x < 0 and sep_y < 0:
                    pen_x = -sep_x
                    pen_y = -sep_y
                    if pen_x < pen_y:
                        shift = (pen_x / 2) + NODE_GAP / 2
                        if a.x < b.x:
                            a.x -= shift
                            b.x += shift
                        else:
                            a.x += shift
                            b.x -= shift
                    else:
                        shift = (pen_y / 2) + NODE_GAP / 2
                        if a.y < b.y:
                            a.y -= shift
                            b.y += shift
                        else:
                            a.y += shift
                            b.y -= shift
                    a.x = snap(a.x)
                    a.y = snap(a.y)
                    b.x = snap(b.x)
                    b.y = snap(b.y)
                    moved = True
        if not moved:
            break

    rect_map = {r.id: r for r in rects}
    for cell in root.iter("mxCell"):
        cid = cell.get("id", "")
        if cid in rect_map:
            geo = cell.find("mxGeometry")
            if geo is not None:
                r = rect_map[cid]
                geo.set("x", str(int(r.x)))
                geo.set("y", str(int(r.y)))

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ─── Consistent Spacing ──────────────────────────────────────────────────────

def consistent_spacing(xml: str, tolerance: int = 20) -> str:
    """同层元素间距一致化（按 Y 坐标分组，tolerance=20px）"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    rects = _extract_rects(root)
    if len(rects) < 3:
        return xml

    layers: dict[int, list[_Rect]] = {}
    for r in rects:
        layer_key = snap(r.y, tolerance)
        layers.setdefault(layer_key, []).append(r)

    for layer_rects in layers.values():
        if len(layer_rects) < 2:
            continue
        layer_rects.sort(key=lambda r: r.x)
        total_span = (layer_rects[-1].x + layer_rects[-1].w) - layer_rects[0].x
        total_width = sum(r.w for r in layer_rects)
        if total_span <= total_width:
            continue
        avg_gap = (total_span - total_width) / (len(layer_rects) - 1)
        current_x = layer_rects[0].x + layer_rects[0].w + avg_gap
        for r in layer_rects[1:]:
            r.x = snap(current_x)
            current_x = r.x + r.w + avg_gap

    rect_map = {r.id: r for r in rects}
    for cell in root.iter("mxCell"):
        cid = cell.get("id", "")
        if cid in rect_map:
            geo = cell.find("mxGeometry")
            if geo is not None:
                geo.set("x", str(int(rect_map[cid].x)))

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ─── Normalize Arrows ─────────────────────────────────────────────────────────

def normalize_arrows(xml: str) -> str:
    """统一箭头样式：终点 classicBlock + 移除起点箭头"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    for cell in root.iter("mxCell"):
        if cell.get("edge") != "1":
            continue
        style = cell.get("style", "")
        style = re.sub(r"endArrow=[^;]*;?", "", style)
        style = re.sub(r"startArrow=[^;]*;?", "", style)
        style = re.sub(r"endFill=[^;]*;?", "", style)
        style = re.sub(r"startFill=[^;]*;?", "", style)
        style += "endArrow=classicBlock;endFill=1;startArrow=none;"
        cell.set("style", style)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ─── Label Background ─────────────────────────────────────────────────────────

def label_background(xml: str, bg_color: str = "#ffffff") -> str:
    """连线标签添加白色背景提升可读性"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    for cell in root.iter("mxCell"):
        if cell.get("edge") != "1":
            continue
        value = cell.get("value", "")
        if not value.strip():
            continue
        style = cell.get("style", "")
        if "labelBackgroundColor" not in style:
            style += f"labelBackgroundColor={bg_color};"
            cell.set("style", style)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ─── Orthogonal Routing ───────────────────────────────────────────────────────

def orthogonal_routing(xml: str) -> str:
    """确保所有连线使用正交折线路由"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    for cell in root.iter("mxCell"):
        if cell.get("edge") != "1":
            continue
        style = cell.get("style", "")
        style = re.sub(r"edgeStyle=[^;]*;?", "", style)
        style = re.sub(r"curved=[^;]*;?", "", style)
        style = "edgeStyle=orthogonalEdgeStyle;orthogonalLoop=1;jettySize=auto;" + style
        cell.set("style", style)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ─── Anchor Optimizer ─────────────────────────────────────────────────────────

def _angle_to_face(angle: float, w: float, h: float) -> str:
    """角度 → 出口面（基于矩形对角线角度阈值）"""
    diag = math.atan2(h, w)
    abs_angle = abs(angle)
    if abs_angle < diag:
        return "right"
    elif abs_angle > math.pi - diag:
        return "left"
    elif angle > 0:
        return "bottom"
    else:
        return "top"


def _face_to_anchor(face: str, spread: float) -> tuple[float, float]:
    """面 + 分布位置 → 锚点坐标 (0-1)"""
    if face == "top":
        return (spread, 0)
    elif face == "bottom":
        return (spread, 1)
    elif face == "left":
        return (0, spread)
    else:
        return (1, spread)


def optimize_anchors(xml: str) -> str:
    """基于角度的连线锚点优化 + 扇出均匀分布"""
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return xml

    vertices = {}
    for cell in root.iter("mxCell"):
        if cell.get("vertex") != "1":
            continue
        cid = cell.get("id", "")
        geo = cell.find("mxGeometry")
        if geo is None:
            continue
        x = float(geo.get("x", "0"))
        y = float(geo.get("y", "0"))
        w = float(geo.get("width", "100"))
        h = float(geo.get("height", "50"))
        vertices[cid] = {"x": x, "y": y, "w": w, "h": h,
                         "cx": x + w / 2, "cy": y + h / 2}

    edges = []
    for cell in root.iter("mxCell"):
        if cell.get("edge") != "1":
            continue
        style = cell.get("style", "")
        if "dashed=1" in style:
            continue
        src = cell.get("source", "")
        tgt = cell.get("target", "")
        if src in vertices and tgt in vertices:
            edges.append({"cell": cell, "src": src, "tgt": tgt})

    if not edges:
        return xml

    buckets: dict[str, list] = {}
    for edge in edges:
        sv = vertices[edge["src"]]
        tv = vertices[edge["tgt"]]
        exit_angle = math.atan2(tv["cy"] - sv["cy"], tv["cx"] - sv["cx"])
        entry_angle = math.atan2(sv["cy"] - tv["cy"], sv["cx"] - tv["cx"])
        exit_face = _angle_to_face(exit_angle, sv["w"], sv["h"])
        entry_face = _angle_to_face(entry_angle, tv["w"], tv["h"])
        edge["exit_face"] = exit_face
        edge["entry_face"] = entry_face

        exit_key = f"{edge['src']}:{exit_face}:exit"
        entry_key = f"{edge['tgt']}:{entry_face}:entry"
        buckets.setdefault(exit_key, []).append(edge)
        buckets.setdefault(entry_key, []).append(edge)

    for key, bucket in buckets.items():
        node_id, face, role = key.split(":")
        count = len(bucket)
        if count <= 1:
            continue
        if face in ("top", "bottom"):
            bucket.sort(key=lambda e: vertices[e["tgt" if role == "exit" else "src"]]["cx"])
        else:
            bucket.sort(key=lambda e: vertices[e["tgt" if role == "exit" else "src"]]["cy"])

        for i, edge in enumerate(bucket):
            spread = (i + 1) / (count + 1)
            ax, ay = _face_to_anchor(face, spread)
            style = edge["cell"].get("style", "")
            if role == "exit":
                style = re.sub(r"exitX=[^;]*;?", "", style)
                style = re.sub(r"exitY=[^;]*;?", "", style)
                style += f"exitX={ax:.2f};exitY={ay:.2f};exitDx=0;exitDy=0;"
            else:
                style = re.sub(r"entryX=[^;]*;?", "", style)
                style = re.sub(r"entryY=[^;]*;?", "", style)
                style += f"entryX={ax:.2f};entryY={ay:.2f};entryDx=0;entryDy=0;"
            edge["cell"].set("style", style)

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


# ─── XML Repair ──────────────────────────────────────────────────────────────

def repair_xml(xml: str) -> tuple[str, str]:
    """修复截断的 draw.io XML，返回 (修复后XML, 状态)"""
    xml = xml.strip()

    xml = re.sub(r'^```(?:xml)?\s*', '', xml)
    xml = re.sub(r'\s*```\s*$', '', xml)

    start = xml.find('<mxfile')
    if start > 0:
        xml = xml[start:]

    if xml.endswith('</mxfile>'):
        try:
            ET.fromstring(xml)
            return xml, "complete"
        except ET.ParseError:
            pass

    last_close = max(xml.rfind('/>'), xml.rfind('</mxCell>'))
    if last_close > 0:
        cut_point = last_close + 2 if xml[last_close:last_close+2] == '/>' else last_close + len('</mxCell>')
        xml = xml[:cut_point]

    closers = ['</root>', '</mxGraphModel>', '</diagram>', '</mxfile>']
    for tag in closers:
        if tag not in xml:
            xml += f'\n{tag}'

    try:
        ET.fromstring(xml)
        return xml, "repaired"
    except ET.ParseError:
        return xml, "invalid"


# ─── Pipeline ─────────────────────────────────────────────────────────────────

@dataclass
class PostProcessResult:
    xml: str
    status: str
    repairs: list[str]


def postprocess_pipeline(
    raw_xml: str,
    do_grid_snap: bool = True,
    do_overlap_fix: bool = False,
    do_spacing: bool = False,
    do_anchors: bool = False,
    do_arrows: bool = False,
    do_labels: bool = False,
) -> PostProcessResult:
    """后处理流水线（默认只做安全步骤：repair + grid_snap）"""
    repairs = []

    xml, status = repair_xml(raw_xml)
    if status == "repaired":
        repairs.append("XML 截断已修复")
    elif status == "invalid":
        return PostProcessResult(xml=raw_xml, status="invalid", repairs=["XML 无法修复"])

    if do_grid_snap:
        xml = grid_snap(xml)
        repairs.append("网格对齐")

    if do_overlap_fix:
        xml = overlap_fix(xml)
        repairs.append("重叠修复")

    if do_spacing:
        xml = consistent_spacing(xml)
        repairs.append("间距一致化")

    if do_anchors:
        xml = optimize_anchors(xml)
        repairs.append("锚点优化")

    if do_arrows:
        xml = normalize_arrows(xml)
        repairs.append("箭头统一")

    if do_labels:
        xml = label_background(xml)
        repairs.append("标签背景")

    return PostProcessResult(xml=xml, status="ok", repairs=repairs)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 postprocess.py <input.drawio> [-o output.drawio]")
        sys.exit(1)

    from pathlib import Path
    content = Path(sys.argv[1]).read_text()
    result = postprocess_pipeline(content)

    out = sys.argv[sys.argv.index("-o") + 1] if "-o" in sys.argv else None
    if out:
        Path(out).write_text(result.xml)
        print(f"后处理完成: {', '.join(result.repairs)}")
        print(f"已保存: {out}")
    else:
        print(result.xml)
