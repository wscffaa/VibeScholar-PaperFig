# paper-fig

确定性网格布局的学术论文图表生成工具。网格坐标 → 像素坐标 → draw.io XML，从构造上保证零重叠。

[English](README_EN.md)

## 工作原理

1. 用 `layout.json` 定义逻辑结构（网格位置、元素类型、连接关系）
2. 网格引擎确定性地转换为像素坐标（不可能重叠）
3. AI 视觉审查对渲染结果打分（5 维度，出版质量门禁）
4. 用户在 draw.io GUI 中微调连线路径（约 30 秒）

## 快速开始

```bash
# ASCII 预览（零依赖，即时反馈）
python3 scripts/grid_engine.py plans/fadpb-grid.json --ascii

# 生成 draw.io XML
python3 scripts/grid_engine.py plans/fadpb-grid.json -o output.drawio

# 导出 PNG（需要 draw.io 桌面版）
/Applications/draw.io.app/Contents/MacOS/draw.io --export --format png --scale 1.5 --output preview.png output.drawio

# AI 视觉审查（需要 OpenAI 兼容 API）
python3 scripts/visual_review.py preview.png --json
```

## 密钥管理

视觉审查需要支持视觉能力的 LLM API，配置方式：
- 环境变量：`PAPERFIG_API_KEY` + `PAPERFIG_API_BASE`
- 或 CCSwitch DB（集成工作流场景）

**禁止硬编码 API 密钥。**

## 元素类型

| 类型 | 颜色 | 形状 | 用途 |
|------|------|------|------|
| input | 钢蓝 #d4e1f5 | 平行四边形 | 输入数据/帧 |
| output | 浅绿 #d5e8d4 | 平行四边形 | 输出/重建结果 |
| processing | 蓝 #dae8fc | 圆角矩形 | 标准模块 |
| innovation | 橙 #fff2cc | 圆角矩形 | 创新贡献（高亮） |
| baseline | 灰 #f5f5f5 | 圆角矩形 | 已有组件 |
| loss | 红 #f8cecc | 圆角矩形 | 仅训练阶段 |

## 目录结构

```
├── SKILL.md              # Claude Code skill 定义
├── knowledge.md          # 经验知识库（规则、踩坑、解决方案）
├── scripts/
│   ├── grid_engine.py    # 核心：网格 → draw.io XML
│   ├── visual_review.py  # AI 视觉评分 + 迭代循环
│   ├── postprocess.py    # 后处理流水线
│   └── audit.py          # 结构性 XML 校验
├── plans/                # 可复用的 layout.json 模板
└── gallery/              # 自动沉淀的高分产出（≥8 分）
```

## 许可证

MIT
