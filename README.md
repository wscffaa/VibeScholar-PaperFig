# smart-drawio-skill

学术论文架构图自动生成工具链。基于网格布局引擎 + 视觉审查迭代，生成 draw.io 格式的论文图表。

## 特点

- **网格布局引擎**：用行列坐标定义布局，确定性转换为像素坐标，从根本上避免重叠
- **视觉审查**：AI 视觉模型自动评分（布局/可读性/连线/学术规范/美观），≥7 分通过
- **经验知识库**：积累禁忌规则和已知问题解决方案，持续迭代提升质量
- **ASCII 预览**：生成前先出 ASCII 框图确认布局，零成本迭代
- **draw.io 原生格式**：输出 .drawio XML，可用桌面版精细编辑

## 工作流

```
用户需求 → 读取 knowledge.md → 构造 layout.json → ASCII 预览确认
→ grid_engine 生成 drawio XML → 导出 PNG → 视觉审查
→ 不合格则调整参数重试 → 通过后打开 draw.io 供用户微调连线
```

## 文件说明

| 文件 | 功能 |
|------|------|
| `grid_engine.py` | 核心：网格布局 → draw.io XML 确定性转换 |
| `audit.py` | 结构审查：XML 完整性、元素数量、重叠检测 |
| `visual_review.py` | 视觉审查：AI 视觉模型评分（需 OpenAI 兼容 API） |
| `knowledge.md` | 经验知识库：禁忌、规则、已知问题 |
| `skill.md` | Skill 定义：触发条件、工作流、工具链 |
| `plans/` | 预定义的 layout.json 模板 |

## 快速使用

```bash
# 1. ASCII 预览
python3 grid_engine.py plans/fadpb-grid.json --ascii

# 2. 生成 drawio
python3 grid_engine.py plans/fadpb-grid.json -o output.drawio

# 3. 导出 PNG（需要 draw.io 桌面版）
/Applications/draw.io.app/Contents/MacOS/draw.io --export --format png --scale 1.5 --output preview.png output.drawio

# 4. 视觉审查（需要 OpenAI 兼容 API）
python3 visual_review.py preview.png --json

# 5. 结构审查
python3 audit.py output.drawio
```

## layout.json 格式

```json
{
  "title": "模块名称",
  "grid": {"cols": 3, "rows": 9},
  "elements": [
    {"id": "input", "label": "Input", "type": "input", "row": 0, "col": 1, "colspan": 1}
  ],
  "connections": [
    {"source": "input", "target": "encoder", "type": "solid", "label": ""}
  ],
  "groups": []
}
```

元素类型与配色：
- `input`: 钢蓝 #d4e1f5（平行四边形）
- `output`: 浅绿 #d5e8d4（平行四边形）
- `processing`: 蓝 #dae8fc
- `innovation`: 橙 #fff2cc（创新贡献）
- `baseline`: 灰 #f5f5f5
- `loss`: 红 #f8cecc

## 依赖

- Python 3.10+（标准库即可运行 grid_engine 和 audit）
- draw.io 桌面版（导出 PNG/PDF/SVG）
- OpenAI 兼容 API（visual_review 视觉审查，可选）
- `openai` Python SDK（visual_review 需要）

## 设计原则

1. **Skill 负责**：模块布局、颜色、文字、层次、间距、箭头
2. **用户负责**：连线路径微调（draw.io 里拖 waypoint）
3. **禁止**：删除结构性连线、合并不同功能模块、用装饰替代结构

## License

MIT
