# smart-drawio

> AI 驱动的论文架构图自动生成。网格布局 → ASCII 确认 → 确定性渲染 → 视觉审查 → 用户微调连线。

## 触发条件

用户要求生成论文架构图、流程图、模块图、数据流图时触发。
关键词：drawio、架构图、AI画图、smart-drawio、画一个图。

## 前置条件

- **生成前必须读取 `knowledge.md`**，避免重复踩坑
- 网格引擎模式（默认）：无需任何后台服务
- AI 辅助模式（备用）：需 `~/VibeScholar/smart-drawio/serve.sh start`

## 流程纪律（MUST）

1. **不自动打开文件**：迭代过程中禁止调用 `open`，只在最终审查通过且用户确认后打开一次
2. **不启动不必要的服务**：网格引擎方案不需要 smart-drawio 网页服务
3. **单文件原则**：同一张图只维护一个 .drawio 文件，迭代覆盖而非创建多个版本
4. **审查驱动迭代**：每次修改后必须跑视觉审查，根据反馈调整，不盲目重试

## 工具链

```
.claude/skills/smart-drawio/
├── skill.md          ← 本文件
├── knowledge.md      ← 经验知识库（禁忌+已知问题+解决方案）
├── grid_engine.py    ← 网格布局引擎（核心，确定性生成）
├── generate.py       ← AI 辅助 API 客户端（备用）
├── composer.py       ← 分层组合器（备用）
├── audit.py          ← 结构审查
├── pipeline.py       ← 自动迭代管道
└── plans/            ← 预定义的 layout.json
├── composer.py       ← 分层组合器（多模块合并）
├── audit.py          ← 结构审查（XML 完整性）
├── pipeline.py       ← 自动迭代管道（生成→审查→迭代→定稿）
└── plans/            ← 预定义的 plan.json 模板

_workspace/03-scripts/
└── visual_review.py  ← 视觉质量审查（AI 视觉模型评分）
```

## 工作流程（五阶段门禁）

### Phase 1: 需求分析与复杂度判定

| 复杂度 | 模块数 | 嵌套 | 策略 | 工具 |
|--------|--------|------|------|------|
| 简单 | ≤5 | 0 | 单次生成 | generate.py |
| 中等 | 6-12 | 1 | 坐标约束单次 | generate.py + 显式坐标 |
| 复杂 | >12 | ≥2 | 分层组合 | composer.py + plan.json |

### Phase 2: Plan 构造

**简单模式**：直接写 prompt 文本
**分层模式**：构造 plan.json
```json
{
  "title": "模块名",
  "canvas": [宽, 高],
  "modules": [
    {"name": "子模块名", "prompt": "子模块描述", "width": W, "height": H, "x": X, "y": Y}
  ],
  "connections": [
    {"source_module": "A", "source_label": "节点文本",
     "target_module": "B", "target_label": "节点文本", "label": "连线标签"}
  ]
}
```

关键原则：
- 每个子模块 prompt 描述 ≤5 个元素（AI 画得好）
- 显式指定每个子模块的位置和尺寸
- 连接通过节点文本模糊匹配

### Phase 3: 自动迭代管道

```bash
python3 .claude/skills/smart-drawio/pipeline.py \
  <plan.json 或 prompt.txt> \
  -o <输出目录> \
  --max-iter 3 \
  --threshold 7
```

管道内部流程：
```
生成 drawio → 结构审查(audit.py) → 渲染 PNG → 视觉审查(visual_review.py)
                    ↓ FAIL                              ↓ FAIL
              调整 prompt 重试                    根据反馈优化 prompt 重试
                                                        ↓ PASS (score≥7)
                                              输出 final.drawio + PDF + SVG
```

### Phase 4: 人工确认（门禁，不可跳过）

管道通过后，向用户展示：
1. 预览 PNG 图片
2. 视觉审查评分和维度分数
3. 残留问题（如有）

**必须用户确认后才能移入编译层。**

### Phase 5: 定稿归档

用户确认后：
1. 复制 PDF 到编译层 `figures/chap0N/figX.Y-slug/`
2. 保留 .drawio 源文件在工作区（可后续编辑）
3. 清理中间产物（draft-iter*.drawio, preview-iter*.png）
4. 更新 FIGURE_INDEX.yaml

## 视觉审查评分维度

| 维度 | 权重 | 说明 |
|------|------|------|
| 布局清晰度 | 25% | 模块不重叠、间距合理、层次分明 |
| 文字可读性 | 20% | 字号合适、不被遮挡 |
| 连接线清晰度 | 20% | 不过度交叉、箭头方向明确 |
| 学术规范性 | 20% | 配色克制、无装饰、信息密度适当 |
| 整体美观度 | 15% | 视觉平衡、留白合理 |

通过阈值：≥7 分（可调）

## 迭代失败处理

| 情况 | 处理 |
|------|------|
| 3 次迭代仍 <7 分 | 降级为骨架图 + 提示用户手动编辑 |
| API 超时/502 | 重启服务后重试 |
| 视觉审查 API 失败 | 跳过视觉审查，仅做结构审查 + 人工确认 |

## 与 ofr-thesis-figure 的分工

| 场景 | 工具 |
|------|------|
| 定量图表（曲线、柱状图、消融表） | ofr-thesis-figure (matplotlib) |
| 架构图、模块图、数据流图 | smart-drawio |
| 定性对比图（视觉结果拼接） | ofr-thesis-figure (matplotlib) |
| 概念图、流程图 | smart-drawio |
| 频域分析图 | ofr-thesis-figure (matplotlib) |
