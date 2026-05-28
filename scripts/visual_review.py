#!/usr/bin/env python3
"""Visual review scorer for paper-fig outputs.

Scores exported PNG figures on 5 dimensions using a vision-capable LLM.
Key resolution: CCSwitch DB -> env vars -> error.

Usage:
    python3 visual_review.py preview.png
    python3 visual_review.py preview.png --threshold 7 --json
    python3 visual_review.py --iterate layout.json --max-iterations 3
"""

import argparse
import base64
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# CCSwitch key resolution
# ---------------------------------------------------------------------------

CCSWITCH_DB = Path.home() / ".cc-switch" / "cc-switch.db"

SCORING_PROMPT = """\
You are a publication-quality figure reviewer for academic papers (computer vision / deep learning).

Score this figure on 5 dimensions (1-10 each):

1. **Layout Clarity** - Are modules well-separated? Is the flow direction obvious? No overlaps?
2. **Label Readability** - Are all text labels legible at print size? Consistent font sizing?
3. **Connection Logic** - Do arrows/connections clearly show data flow? No ambiguous paths?
4. **Visual Hierarchy** - Is there a clear primary path? Are sub-modules visually grouped?
5. **Publication Readiness** - Would this pass peer review? Proper use of whitespace, alignment, and style?

Return ONLY valid JSON (no markdown fences):
{
  "layout_clarity": <int 1-10>,
  "label_readability": <int 1-10>,
  "connection_logic": <int 1-10>,
  "visual_hierarchy": <int 1-10>,
  "publication_readiness": <int 1-10>,
  "overall": <float, weighted average>,
  "strengths": ["..."],
  "weaknesses": ["..."],
  "suggestions": ["actionable fix 1", "actionable fix 2", ...]
}
"""

ITERATION_SUGGESTION_PROMPT = """\
Based on the weaknesses identified, provide specific layout.json adjustments.
Return ONLY valid JSON (no markdown fences):
{
  "adjustments": [
    {"target": "<element_id or description>", "action": "<move|resize|restyle|reconnect>", "detail": "..."},
    ...
  ],
  "priority": "highest-impact adjustment first"
}
"""


def resolve_ccswitch_config() -> Optional[dict]:
    """Read active codex provider config from CCSwitch DB.

    The settings_config column is JSON: {"auth": {"OPENAI_API_KEY": "..."}, "config": "<TOML string>"}
    The TOML string contains base_url and model fields.

    Returns dict with keys: api_key, base_url, model or None.
    """
    if not CCSWITCH_DB.exists():
        return None

    try:
        conn = sqlite3.connect(str(CCSWITCH_DB))
        cur = conn.cursor()
        cur.execute(
            "SELECT settings_config FROM providers "
            "WHERE app_type = 'codex' AND is_current = 1 LIMIT 1"
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        # settings_config is JSON with auth dict + config TOML string
        parsed = json.loads(row[0])
        result = {}

        # Extract API key from auth section
        auth = parsed.get("auth", {})
        api_key = auth.get("OPENAI_API_KEY")
        if api_key:
            result["api_key"] = api_key

        # Extract base_url and model from TOML config string
        config_toml = parsed.get("config", "")

        url_match = re.search(r'base_url\s*=\s*"([^"]+)"', config_toml)
        if url_match:
            result["base_url"] = url_match.group(1)

        model_match = re.search(r'^model\s*=\s*"([^"]+)"', config_toml, re.MULTILINE)
        if model_match:
            result["model"] = model_match.group(1)

        if "api_key" in result and "base_url" in result:
            return result
        return None

    except (sqlite3.Error, json.JSONDecodeError, Exception):
        return None


def resolve_credentials(model_override: Optional[str] = None) -> dict:
    """Resolve API credentials. Priority: CCSwitch -> env vars -> error.

    Returns dict with: api_key, base_url, model
    """
    # 1. Try CCSwitch DB
    cc_config = resolve_ccswitch_config()
    if cc_config:
        config = {
            "api_key": cc_config["api_key"],
            "base_url": cc_config["base_url"],
            "model": model_override or cc_config.get("model", "gpt-4o"),
        }
        return config

    # 2. Try environment variables
    api_key = os.environ.get("PAPERFIG_API_KEY")
    api_base = os.environ.get("PAPERFIG_API_BASE")
    if api_key and api_base:
        config = {
            "api_key": api_key,
            "base_url": api_base,
            "model": model_override or os.environ.get("PAPERFIG_MODEL", "gpt-4o"),
        }
        return config

    # 3. Neither available
    print(
        "ERROR: No API credentials found.\n"
        "Resolution order:\n"
        "  1. CCSwitch DB (~/.cc-switch/cc-switch.db) - codex provider with is_current=1\n"
        "  2. Environment: PAPERFIG_API_KEY + PAPERFIG_API_BASE\n\n"
        "Fix: configure a codex provider in CCSwitch, or export PAPERFIG_API_KEY and PAPERFIG_API_BASE.",
        file=sys.stderr,
    )
    sys.exit(1)


# ---------------------------------------------------------------------------
# Vision scoring
# ---------------------------------------------------------------------------


def encode_image(image_path: Path) -> str:
    """Base64 encode an image file."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def score_image(image_path: Path, credentials: dict) -> dict:
    """Send image to vision model and get structured score."""
    try:
        from openai import OpenAI
    except ImportError:
        print("ERROR: openai package not installed. Run: pip install openai", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=credentials["api_key"], base_url=credentials["base_url"])

    b64_image = encode_image(image_path)
    suffix = image_path.suffix.lower().lstrip(".")
    mime = f"image/{suffix}" if suffix in ("png", "jpeg", "jpg", "webp", "gif") else "image/png"

    response = client.chat.completions.create(
        model=credentials["model"],
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": SCORING_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64_image}", "detail": "high"},
                    },
                ],
            }
        ],
        max_tokens=1024,
        temperature=0.2,
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown fences if present
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {
            "layout_clarity": 0,
            "label_readability": 0,
            "connection_logic": 0,
            "visual_hierarchy": 0,
            "publication_readiness": 0,
            "overall": 0.0,
            "strengths": [],
            "weaknesses": ["Failed to parse model response"],
            "suggestions": [],
            "_raw_response": raw,
        }

    # Compute overall if not provided or zero
    if not result.get("overall"):
        dims = [
            result.get("layout_clarity", 0),
            result.get("label_readability", 0),
            result.get("connection_logic", 0),
            result.get("visual_hierarchy", 0),
            result.get("publication_readiness", 0),
        ]
        weights = [0.25, 0.15, 0.20, 0.20, 0.20]
        result["overall"] = round(sum(d * w for d, w in zip(dims, weights)), 2)

    return result


def get_adjustment_suggestions(image_path: Path, score_result: dict, credentials: dict) -> dict:
    """Get specific layout adjustment suggestions for iteration."""
    try:
        from openai import OpenAI
    except ImportError:
        return {"adjustments": [], "priority": "openai package not installed"}

    client = OpenAI(api_key=credentials["api_key"], base_url=credentials["base_url"])

    b64_image = encode_image(image_path)
    suffix = image_path.suffix.lower().lstrip(".")
    mime = f"image/{suffix}" if suffix in ("png", "jpeg", "jpg", "webp", "gif") else "image/png"

    context = (
        f"Current score: {score_result['overall']}/10\n"
        f"Weaknesses: {json.dumps(score_result.get('weaknesses', []))}\n"
        f"Suggestions: {json.dumps(score_result.get('suggestions', []))}\n\n"
        f"{ITERATION_SUGGESTION_PROMPT}"
    )

    response = client.chat.completions.create(
        model=credentials["model"],
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": context},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64_image}", "detail": "high"},
                    },
                ],
            }
        ],
        max_tokens=1024,
        temperature=0.3,
    )

    raw = response.choices[0].message.content.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"adjustments": [], "priority": "parse_error", "_raw": raw}


# ---------------------------------------------------------------------------
# Iteration loop
# ---------------------------------------------------------------------------

GRID_ENGINE = Path(__file__).parent / "grid_engine.py"
DRAWIO_CLI = "/Applications/draw.io.app/Contents/MacOS/draw.io"
GALLERY_DIR = Path(__file__).parent.parent / "gallery"


def export_png(drawio_path: Path, png_path: Path) -> bool:
    """Export drawio to PNG via draw.io CLI."""
    if not Path(DRAWIO_CLI).exists():
        print(f"WARNING: draw.io CLI not found at {DRAWIO_CLI}", file=sys.stderr)
        return False

    cmd = [
        DRAWIO_CLI,
        "--export",
        "--format", "png",
        "--scale", "1.5",
        "--output", str(png_path),
        str(drawio_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def save_to_gallery(layout_path: Path, png_path: Path, score_result: dict):
    """Save high-scoring output to gallery."""
    # Determine category from layout
    category = "architecture"
    if layout_path.exists():
        try:
            layout = json.loads(layout_path.read_text())
            category = layout.get("metadata", {}).get("type", "architecture")
        except (json.JSONDecodeError, KeyError):
            pass

    gallery_cat = GALLERY_DIR / category
    gallery_cat.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest_png = gallery_cat / f"{timestamp}.png"
    dest_layout = gallery_cat / f"{timestamp}-layout.json"
    dest_meta = gallery_cat / f"{timestamp}-metadata.json"

    shutil.copy2(png_path, dest_png)
    if layout_path.exists():
        shutil.copy2(layout_path, dest_layout)

    metadata = {
        "score": score_result["overall"],
        "dimensions": {
            "layout_clarity": score_result.get("layout_clarity"),
            "label_readability": score_result.get("label_readability"),
            "connection_logic": score_result.get("connection_logic"),
            "visual_hierarchy": score_result.get("visual_hierarchy"),
            "publication_readiness": score_result.get("publication_readiness"),
        },
        "date": datetime.now().isoformat(),
        "source_layout": str(layout_path),
    }
    dest_meta.write_text(json.dumps(metadata, indent=2, ensure_ascii=False))
    print(f"Saved to gallery: {dest_png}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Iteration loop runner
# ---------------------------------------------------------------------------


def run_iteration_loop(
    layout_path: Path,
    threshold: float,
    max_iterations: int,
    credentials: dict,
    output_json: bool,
) -> int:
    """Run generate -> export -> score -> adjust loop.

    Returns exit code: 0 if threshold met, 1 otherwise.
    """
    drawio_path = layout_path.with_suffix(".drawio")
    png_path = layout_path.with_suffix(".png")

    for iteration in range(1, max_iterations + 1):
        if not output_json:
            print(f"\n--- Iteration {iteration}/{max_iterations} ---", file=sys.stderr)

        # 1. Generate drawio from layout
        gen_cmd = [
            sys.executable, str(GRID_ENGINE), str(layout_path), "-o", str(drawio_path)
        ]
        gen_result = subprocess.run(gen_cmd, capture_output=True, text=True, timeout=60)
        if gen_result.returncode != 0:
            err = {"error": "grid_engine failed", "stderr": gen_result.stderr, "iteration": iteration}
            if output_json:
                print(json.dumps(err, indent=2))
            else:
                print(f"ERROR: grid_engine failed: {gen_result.stderr}", file=sys.stderr)
            return 1

        # 2. Export PNG
        if not export_png(drawio_path, png_path):
            err = {"error": "PNG export failed", "iteration": iteration}
            if output_json:
                print(json.dumps(err, indent=2))
            else:
                print("ERROR: PNG export failed", file=sys.stderr)
            return 1

        # 3. Score
        score_result = score_image(png_path, credentials)
        overall = score_result.get("overall", 0)

        if not output_json:
            print(f"  Score: {overall}/10", file=sys.stderr)

        # 4. Check threshold
        if overall >= threshold:
            result = {
                "status": "success",
                "iteration": iteration,
                "score": score_result,
                "drawio": str(drawio_path),
                "png": str(png_path),
            }
            if output_json:
                print(json.dumps(result, indent=2))
            else:
                print(f"  PASS (>= {threshold}) at iteration {iteration}", file=sys.stderr)
                print_score_report(score_result)

            # Auto-save to gallery if score >= 8
            if overall >= 8:
                save_to_gallery(layout_path, png_path, score_result)

            return 0

        # 5. Get adjustment suggestions if more iterations remain
        if iteration < max_iterations:
            suggestions = get_adjustment_suggestions(png_path, score_result, credentials)
            if output_json:
                iter_result = {
                    "status": "below_threshold",
                    "iteration": iteration,
                    "score": score_result,
                    "adjustments": suggestions,
                }
                print(json.dumps(iter_result, indent=2))
            else:
                print(f"  Below threshold ({overall} < {threshold}), suggesting adjustments...", file=sys.stderr)
                if suggestions.get("adjustments"):
                    for adj in suggestions["adjustments"]:
                        print(f"    - [{adj.get('action')}] {adj.get('target')}: {adj.get('detail')}", file=sys.stderr)
            # In automated mode, we output suggestions but cannot auto-apply
            # The caller (skill orchestrator) applies adjustments to layout.json
            return 2  # Signal: needs adjustment

    # Exhausted iterations
    final = {
        "status": "max_iterations_reached",
        "iteration": max_iterations,
        "score": score_result,
        "drawio": str(drawio_path),
        "png": str(png_path),
    }
    if output_json:
        print(json.dumps(final, indent=2))
    else:
        print(f"\n  Max iterations reached. Final score: {overall}/10", file=sys.stderr)
        print_score_report(score_result)
    return 1


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def print_score_report(result: dict):
    """Print human-readable score report."""
    print(f"\n{'='*50}")
    print(f"  Visual Review Score: {result.get('overall', 0)}/10")
    print(f"{'='*50}")
    print(f"  Layout Clarity:        {result.get('layout_clarity', '?')}/10")
    print(f"  Label Readability:     {result.get('label_readability', '?')}/10")
    print(f"  Connection Logic:      {result.get('connection_logic', '?')}/10")
    print(f"  Visual Hierarchy:      {result.get('visual_hierarchy', '?')}/10")
    print(f"  Publication Readiness: {result.get('publication_readiness', '?')}/10")

    if result.get("strengths"):
        print(f"\n  Strengths:")
        for s in result["strengths"]:
            print(f"    + {s}")

    if result.get("weaknesses"):
        print(f"\n  Weaknesses:")
        for w in result["weaknesses"]:
            print(f"    - {w}")

    if result.get("suggestions"):
        print(f"\n  Suggestions:")
        for s in result["suggestions"]:
            print(f"    > {s}")

    print(f"{'='*50}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Visual review scorer for paper-fig outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  %(prog)s preview.png                     Score a single image
  %(prog)s preview.png --threshold 7       Fail if score < 7
  %(prog)s preview.png --json              Output JSON only
  %(prog)s --iterate layout.json           Run generate-score loop
  %(prog)s --iterate layout.json --max-iterations 5 --model gpt-4o
""",
    )

    parser.add_argument("image", nargs="?", help="Path to PNG/image to score")
    parser.add_argument("--threshold", type=float, default=7.0, help="Minimum passing score (default: 7.0)")
    parser.add_argument("--json", action="store_true", dest="output_json", help="Output JSON only")
    parser.add_argument("--model", type=str, default=None, help="Override model from CCSwitch")
    parser.add_argument("--max-iterations", type=int, default=3, help="Max iteration attempts (default: 3)")
    parser.add_argument(
        "--iterate", type=str, metavar="LAYOUT_JSON",
        help="Run iteration loop: generate -> export -> score -> suggest",
    )

    args = parser.parse_args()

    # Validate args
    if not args.image and not args.iterate:
        parser.print_help()
        sys.exit(1)

    # Resolve credentials
    credentials = resolve_credentials(model_override=args.model)

    # Iteration mode
    if args.iterate:
        layout_path = Path(args.iterate)
        if not layout_path.exists():
            print(f"ERROR: layout file not found: {layout_path}", file=sys.stderr)
            sys.exit(1)
        exit_code = run_iteration_loop(
            layout_path=layout_path,
            threshold=args.threshold,
            max_iterations=args.max_iterations,
            credentials=credentials,
            output_json=args.output_json,
        )
        sys.exit(exit_code)

    # Single image scoring mode
    image_path = Path(args.image)
    if not image_path.exists():
        print(f"ERROR: image not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    result = score_image(image_path, credentials)
    overall = result.get("overall", 0)

    if args.output_json:
        output = {
            "image": str(image_path),
            "score": result,
            "pass": overall >= args.threshold,
            "threshold": args.threshold,
        }
        print(json.dumps(output, indent=2))
    else:
        print_score_report(result)
        if overall >= args.threshold:
            print(f"  PASS (score {overall} >= threshold {args.threshold})")
        else:
            print(f"  FAIL (score {overall} < threshold {args.threshold})")

    # Auto-save to gallery if score >= 8
    if overall >= 8:
        save_to_gallery(Path("unknown-layout.json"), image_path, result)

    sys.exit(0 if overall >= args.threshold else 1)


if __name__ == "__main__":
    main()
