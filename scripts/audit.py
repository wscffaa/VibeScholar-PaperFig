#!/usr/bin/env python3
"""smart-drawio 图表质量审查器"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict


def audit_drawio(filepath: str) -> dict:
    """审查 .drawio 文件质量，返回审查报告"""
    path = Path(filepath)
    if not path.exists():
        return {"pass": False, "errors": ["文件不存在"], "warnings": [], "stats": {}}

    content = path.read_text(encoding="utf-8")
    errors = []
    warnings = []
    stats = {}

    # 1. XML 结构完整性
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        return {"pass": False, "errors": [f"XML 解析失败: {e}"], "warnings": [], "stats": {}}

    # 2. 基本结构检查
    diagrams = root.findall(".//diagram")
    if not diagrams:
        errors.append("缺少 <diagram> 元素")
        return {"pass": False, "errors": errors, "warnings": [], "stats": {}}

    graph_model = root.find(".//mxGraphModel")
    if graph_model is None:
        errors.append("缺少 <mxGraphModel> 元素")
        return {"pass": False, "errors": errors, "warnings": [], "stats": {}}

    # 3. 统计元素
    cells = root.findall(".//{http://www.w3.org/1999/xhtml}mxCell") or root.findall(".//mxCell")
    nodes = []
    edges = []
    for cell in cells:
        cell_id = cell.get("id", "")
        if cell_id in ("0", "1"):
            continue
        style = cell.get("style", "")
        if "edgeStyle" in style or cell.get("edge") == "1":
            edges.append(cell)
        elif cell.get("vertex") == "1":
            nodes.append(cell)

    stats["total_cells"] = len(cells)
    stats["nodes"] = len(nodes)
    stats["edges"] = len(edges)

    # 4. 最低元素数量检查
    if len(nodes) < 3:
        errors.append(f"节点数过少 ({len(nodes)})，图表可能不完整")
    if len(edges) < 2:
        warnings.append(f"连接线过少 ({len(edges)})，模块间可能缺少连接")

    # 5. 重叠检测（简化版：检查相同坐标的节点）
    positions = defaultdict(list)
    for node in nodes:
        geo = node.find("mxGeometry") or node.find("{http://www.w3.org/1999/xhtml}mxGeometry")
        if geo is not None:
            x = geo.get("x", "0")
            y = geo.get("y", "0")
            w = geo.get("width", "0")
            h = geo.get("height", "0")
            positions[(x, y)].append(node.get("id", "?"))

    overlaps = {k: v for k, v in positions.items() if len(v) > 1}
    if overlaps:
        warnings.append(f"检测到 {len(overlaps)} 处坐标完全重叠")

    # 6. 边界框检查（是否有元素超出画布）
    page_w = int(graph_model.get("pageWidth", "1600"))
    page_h = int(graph_model.get("pageHeight", "1200"))
    out_of_bounds = 0
    for node in nodes:
        geo = node.find("mxGeometry") or node.find("{http://www.w3.org/1999/xhtml}mxGeometry")
        if geo is not None:
            x = float(geo.get("x", "0"))
            y = float(geo.get("y", "0"))
            if x < -50 or y < -50 or x > page_w + 200 or y > page_h + 200:
                out_of_bounds += 1

    if out_of_bounds > 0:
        warnings.append(f"{out_of_bounds} 个元素超出画布边界")

    # 7. 连接完整性（边是否有 source/target）
    dangling_edges = 0
    for edge in edges:
        src = edge.get("source")
        tgt = edge.get("target")
        if not src or not tgt:
            dangling_edges += 1

    if dangling_edges > len(edges) * 0.3:
        warnings.append(f"{dangling_edges}/{len(edges)} 条连接线缺少 source/target（可能是浮动箭头）")

    # 8. 文本内容检查（是否有空节点）
    empty_nodes = sum(1 for n in nodes if not n.get("value", "").strip())
    if empty_nodes > len(nodes) * 0.3:
        warnings.append(f"{empty_nodes}/{len(nodes)} 个节点无文本标签")

    # 9. 尺寸合理性（节点是否过小或过大）
    tiny_nodes = 0
    huge_nodes = 0
    for node in nodes:
        geo = node.find("mxGeometry") or node.find("{http://www.w3.org/1999/xhtml}mxGeometry")
        if geo is not None:
            w = float(geo.get("width", "100"))
            h = float(geo.get("height", "50"))
            if w < 20 or h < 15:
                tiny_nodes += 1
            if w > 800 or h > 600:
                huge_nodes += 1

    if tiny_nodes > 3:
        warnings.append(f"{tiny_nodes} 个节点尺寸过小（<20×15），可能不可读")
    if huge_nodes > 2:
        warnings.append(f"{huge_nodes} 个节点尺寸过大（>800×600），布局可能失衡")

    # 综合判定
    passed = len(errors) == 0 and len(warnings) <= 2
    stats["dangling_edges"] = dangling_edges
    stats["overlaps"] = len(overlaps)
    stats["out_of_bounds"] = out_of_bounds

    return {"pass": passed, "errors": errors, "warnings": warnings, "stats": stats}


def print_report(report: dict):
    """打印审查报告"""
    status = "✅ PASS" if report["pass"] else "❌ FAIL"
    print(f"\n{'='*50}")
    print(f"  图表质量审查: {status}")
    print(f"{'='*50}")

    stats = report["stats"]
    if stats:
        print(f"\n  统计: {stats.get('nodes',0)} 节点, {stats.get('edges',0)} 连接线")

    if report["errors"]:
        print(f"\n  错误 ({len(report['errors'])}):")
        for e in report["errors"]:
            print(f"    ❌ {e}")

    if report["warnings"]:
        print(f"\n  警告 ({len(report['warnings'])}):")
        for w in report["warnings"]:
            print(f"    ⚠️  {w}")

    if report["pass"]:
        print(f"\n  结论: 图表结构合格，可进入人工预览确认阶段")
    else:
        print(f"\n  结论: 图表存在问题，建议重新生成或修正")

    print(f"{'='*50}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 audit.py <file.drawio>")
        sys.exit(1)
    report = audit_drawio(sys.argv[1])
    print_report(report)
    sys.exit(0 if report["pass"] else 1)
