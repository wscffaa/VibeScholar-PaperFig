#!/usr/bin/env python3
"""
论文图表视觉质量审查工具

用法:
    python visual_review.py <png_path>
    python visual_review.py <png_path> --threshold 8
    python visual_review.py <png_path> --json
"""

import argparse
import base64
import json
import sys
from pathlib import Path

from openai import OpenAI

API_BASE_URL = "REDACTED_API_BASE"
API_KEY = "REDACTED_API_KEY"
MODEL = "gpt-5.4"
DEFAULT_THRESHOLD = 7

REVIEW_PROMPT = """\
你是一位学术论文图表质量审查专家。请对这张架构图/流程图进行视觉质量评估。

评估维度（每项 1-10 分）：
1. 布局清晰度：模块是否重叠、间距是否合理、层次是否分明
2. 文字可读性：字号是否合适、文字是否被遮挡、中英文混排是否协调
3. 连接线清晰度：连线是否过度交叉、箭头方向是否明确、线条粗细是否一致
4. 学术规范性：是否符合学术论文图表风格（配色克制、无装饰性元素、信息密度适当）
5. 整体美观度：视觉重心是否平衡、留白是否合理、整体是否专业

请严格按以下 JSON 格式输出，不要输出其他内容：
{
  "scores": {
    "layout": <int 1-10>,
    "readability": <int 1-10>,
    "connections": <int 1-10>,
    "academic_style": <int 1-10>,
    "aesthetics": <int 1-10>
  },
  "overall_score": <int 1-10, 五项加权平均取整>,
  "issues": ["问题1", "问题2", ...],
  "suggestions": ["建议1", "建议2", ...]
}

评分标准：
- 9-10: 可直接用于正式论文
- 7-8: 基本合格，有小瑕疵
- 5-6: 需要修改后才能使用
- 1-4: 需要重新设计
"""


def encode_image(image_path: Path) -> str:
    """将图片文件编码为 base64 字符串"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def review_image(image_path: Path, threshold: int = DEFAULT_THRESHOLD) -> dict:
    """
    对图片进行视觉质量审查

    Args:
        image_path: PNG 图片路径
        threshold: 通过阈值，score >= threshold 为通过

    Returns:
        {score: int, pass: bool, issues: list, suggestions: list,
         scores: dict, raw_response: str}
    """
    if not image_path.exists():
        raise FileNotFoundError(f"图片不存在: {image_path}")

    if not image_path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError(f"不支持的图片格式: {image_path.suffix}")

    base64_image = encode_image(image_path)
    mime_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"

    client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": REVIEW_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{base64_image}",
                        },
                    },
                ],
            }
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content.strip()

    # 解析 JSON（兼容模型输出带 markdown code fence 的情况）
    json_str = raw
    if "```json" in json_str:
        json_str = json_str.split("```json")[1].split("```")[0].strip()
    elif "```" in json_str:
        json_str = json_str.split("```")[1].split("```")[0].strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # 解析失败时返回原始响应供调试
        return {
            "score": 0,
            "pass": False,
            "issues": ["模型返回格式异常，无法解析"],
            "suggestions": ["请检查 raw_response 字段"],
            "scores": {},
            "raw_response": raw,
        }

    score = data.get("overall_score", 0)

    return {
        "score": score,
        "pass": score >= threshold,
        "issues": data.get("issues", []),
        "suggestions": data.get("suggestions", []),
        "scores": data.get("scores", {}),
        "raw_response": raw,
    }


def main():
    parser = argparse.ArgumentParser(description="论文图表视觉质量审查")
    parser.add_argument("image", type=str, help="PNG 图片路径")
    parser.add_argument(
        "--threshold", type=int, default=DEFAULT_THRESHOLD, help=f"通过阈值 (默认 {DEFAULT_THRESHOLD})"
    )
    parser.add_argument("--json", action="store_true", help="输出纯 JSON 格式")
    args = parser.parse_args()

    image_path = Path(args.image).resolve()

    try:
        result = review_image(image_path, threshold=args.threshold)
    except (FileNotFoundError, ValueError) as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"API 调用失败: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        # 纯 JSON 输出，方便管道处理
        output = {k: v for k, v in result.items() if k != "raw_response"}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        # 人类可读格式
        status = "通过" if result["pass"] else "不通过"
        print(f"\n{'='*50}")
        print(f"图表质量审查结果: {status} ({result['score']}/{args.threshold})")
        print(f"{'='*50}")

        if result["scores"]:
            print("\n分项评分:")
            labels = {
                "layout": "布局清晰度",
                "readability": "文字可读性",
                "connections": "连接线清晰",
                "academic_style": "学术规范性",
                "aesthetics": "整体美观度",
            }
            for key, label in labels.items():
                s = result["scores"].get(key, "N/A")
                print(f"  {label}: {s}/10")

        if result["issues"]:
            print("\n发现问题:")
            for i, issue in enumerate(result["issues"], 1):
                print(f"  {i}. {issue}")

        if result["suggestions"]:
            print("\n改进建议:")
            for i, sug in enumerate(result["suggestions"], 1):
                print(f"  {i}. {sug}")

        print()

    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
