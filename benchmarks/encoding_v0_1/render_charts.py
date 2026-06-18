"""Chart generation for GeoTask Encoding Benchmark v0.1.

Generates 4 PNG charts comparing encoding formats across metrics.
Uses matplotlib only — no seaborn.
"""

import sys
from pathlib import Path

# Ensure benchmarks package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker


# ── Style constants ────────────────────────────────────────────────────

COLORS = {
    "natural_language": "#E74C3C",  # red
    "geotask_yaml": "#3498DB",      # blue
    "compact_dsl": "#2ECC71",       # green
}

ENCODING_LABELS = {
    "natural_language": "Natural\nLanguage",
    "geotask_yaml": "GeoTask\nYAML",
    "compact_dsl": "Compact\nDSL",
}

ENCODING_ORDER = ["natural_language", "geotask_yaml", "compact_dsl"]


def render_all_charts(rows: list[dict], aggregates: dict, output_dir: Path) -> dict[str, Path]:
    """Generate all 4 charts and return dict of name -> path."""
    output_dir.mkdir(parents=True, exist_ok=True)

    chart_paths = {}

    # Chart 1: Token cost by encoding
    path = _chart_token_cost(rows, output_dir)
    chart_paths["token_cost_by_encoding"] = path

    # Chart 2: Verification success by encoding
    path = _chart_verification_success(rows, output_dir)
    chart_paths["verification_success_by_encoding"] = path

    # Chart 3: Normalization success by encoding
    path = _chart_normalization_success(rows, output_dir)
    chart_paths["normalization_success_by_encoding"] = path

    # Chart 4: Benchmark score by encoding
    path = _chart_benchmark_score(rows, output_dir)
    chart_paths["benchmark_score_by_encoding"] = path

    return chart_paths


def _compute_encoding_avgs(rows: list[dict], key: str) -> dict[str, float]:
    """Compute average of `key` for each encoding type."""
    result = {}
    for enc in ENCODING_ORDER:
        enc_rows = [r for r in rows if r["encoding_type"] == enc]
        if enc_rows:
            result[enc] = sum(r[key] for r in enc_rows) / len(enc_rows)
        else:
            result[enc] = 0.0
    return result


def _bar_chart(
    data: dict[str, float],
    title: str,
    ylabel: str,
    output_path: Path,
    ylim: tuple | None = None,
    value_format: str = ".1f",
):
    """Generic bar chart helper."""
    fig, ax = plt.subplots(figsize=(8, 5))

    encodings = list(data.keys())
    values = list(data.values())
    colors = [COLORS.get(e, "#999999") for e in encodings]
    labels = [ENCODING_LABELS.get(e, e) for e in encodings]

    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=0.8, width=0.55)

    # Add value labels on top of bars
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + (max(values) * 0.02 if max(values) > 0 else 0.5),
            f"{val:{value_format}}",
            ha="center",
            va="bottom",
            fontsize=10,
            fontweight="bold",
        )

    ax.set_title(title, fontsize=14, fontweight="bold", pad=15)
    ax.set_ylabel(ylabel, fontsize=11)
    ax.set_xlabel("Encoding Type", fontsize=11)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if ylim:
        ax.set_ylim(*ylim)

    plt.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _chart_token_cost(rows: list[dict], output_dir: Path) -> Path:
    """Chart: Average total token estimate by encoding."""
    data = _compute_encoding_avgs(rows, "total_token_estimate")
    path = output_dir / "token_cost_by_encoding.png"
    _bar_chart(
        data=data,
        title="Average Token Cost by Encoding",
        ylabel="Estimated Tokens (input + output)",
        output_path=path,
        value_format=".0f",
    )
    return path


def _chart_verification_success(rows: list[dict], output_dir: Path) -> Path:
    """Chart: Status match rate by encoding."""
    data = {}
    for enc in ENCODING_ORDER:
        enc_rows = [r for r in rows if r["encoding_type"] == enc]
        if enc_rows:
            data[enc] = sum(1 for r in enc_rows if r["status_matched"]) / len(enc_rows)
        else:
            data[enc] = 0.0
    path = output_dir / "verification_success_by_encoding.png"
    _bar_chart(
        data=data,
        title="Verification Success (Status Match) by Encoding",
        ylabel="Status Match Rate",
        output_path=path,
        ylim=(0, 1.15),
        value_format=".2f",
    )
    return path


def _chart_normalization_success(rows: list[dict], output_dir: Path) -> Path:
    """Chart: Normalization success rate by encoding."""
    data = {}
    for enc in ENCODING_ORDER:
        enc_rows = [r for r in rows if r["encoding_type"] == enc]
        if enc_rows:
            data[enc] = sum(1 for r in enc_rows if r["normalized_success"]) / len(enc_rows)
        else:
            data[enc] = 0.0
    path = output_dir / "normalization_success_by_encoding.png"
    _bar_chart(
        data=data,
        title="Normalization Success by Encoding",
        ylabel="Normalization Success Rate",
        output_path=path,
        ylim=(0, 1.15),
        value_format=".2f",
    )
    return path


def _chart_benchmark_score(rows: list[dict], output_dir: Path) -> Path:
    """Chart: Average benchmark score by encoding."""
    data = _compute_encoding_avgs(rows, "benchmark_score")
    path = output_dir / "benchmark_score_by_encoding.png"
    _bar_chart(
        data=data,
        title="Benchmark Score by Encoding",
        ylabel="Benchmark Score (0–100)",
        output_path=path,
        ylim=(0, 110),
        value_format=".1f",
    )
    return path
