#!/usr/bin/env python3
"""GeoTask Encoding Benchmark v0.1 — Runner.

Compares three encoding formats (natural_language, geotask_yaml, compact_dsl)
across 4 test cases using simulated model outputs.

Does NOT call any external LLM API. Uses existing GeoTask Normalizer + Verifier.
"""

import csv
import json
import os
import sys
from pathlib import Path

# Ensure src is importable from repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

import yaml

from geotask_core.normalizer import normalize_model_output
from geotask_core.parser import load_geotask
from benchmarks.encoding_v0_1.token_counter import estimate_tokens
from benchmarks.encoding_v0_1.metrics import (
    compute_case_metrics,
    finalize_token_efficiency,
    aggregate_metrics,
)

# ── Paths ─────────────────────────────────────────────────────────────

BENCHMARK_DIR = Path(__file__).resolve().parent
CASES_FILE = BENCHMARK_DIR / "cases.yaml"
INPUTS_DIR = BENCHMARK_DIR / "inputs"
OUTPUTS_DIR = BENCHMARK_DIR / "simulated_model_outputs"
RESULTS_DIR = BENCHMARK_DIR / "outputs"
CHARTS_DIR = RESULTS_DIR / "charts"

# GeoTask ground truth file (for verifier)
GEOTASK_FILE = REPO_ROOT / "examples" / "geotask_core_lite.yaml"

# Patent evidence destination
PATENT_EVIDENCE_DIR = REPO_ROOT / "patent_evidence" / "03_benchmark"

ENCODING_TYPES = ["natural_language", "geotask_yaml", "compact_dsl"]

INPUT_EXTENSIONS = {
    "natural_language": ".txt",
    "geotask_yaml": ".yaml",
    "compact_dsl": ".gt",
}

OUTPUT_EXTENSION = "_output.md"


# ── Main ──────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("GeoTask Encoding Benchmark v0.1")
    print("=" * 60)
    print()

    # Ensure output directories exist
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    PATENT_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

    # Load cases
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        cases_data = yaml.safe_load(f)
    cases = cases_data["cases"]
    print(f"Loaded {len(cases)} cases from cases.yaml")

    # Load ground truth GeoTask data
    geotask_data = load_geotask(GEOTASK_FILE)
    print(f"Loaded geotask ground truth from {GEOTASK_FILE}")
    print()

    # Run all cases × encodings
    all_rows = []
    all_token_costs: dict[str, dict[str, int]] = {}

    for case in cases:
        case_id = case["case_id"]
        print(f"--- {case_id}: {case['description']} ---")

        for enc in ENCODING_TYPES:
            ext = INPUT_EXTENSIONS[enc]
            input_file = INPUTS_DIR / enc / f"{case_id}{ext}"
            output_file = OUTPUTS_DIR / enc / f"{case_id}{OUTPUT_EXTENSION}"

            if not input_file.exists():
                print(f"  [{enc}] SKIP: input file not found: {input_file}")
                continue
            if not output_file.exists():
                print(f"  [{enc}] SKIP: output file not found: {output_file}")
                continue

            input_text = input_file.read_text(encoding="utf-8")
            model_output = output_file.read_text(encoding="utf-8")

            # Run normalizer + verifier
            result = normalize_model_output(model_output, geotask_data=geotask_data)

            # Compute metrics
            row = compute_case_metrics(
                case=case,
                encoding_type=enc,
                input_text=input_text,
                model_output_text=model_output,
                geotask_result=result,
                all_token_costs=all_token_costs,
            )

            all_rows.append(row)

            status_icon = "PASS" if row["status_matched"] else "FAIL"
            print(
                f"  [{enc:20s}] tokens={row['total_token_estimate']:4d}  "
                f"norm={'OK' if row['normalized_success'] else 'FAIL':4s}  "
                f"status={row['overall_status']:12s}  "
                f"score={row['benchmark_score']:5.1f}  {status_icon}"
            )

        print()

    # Finalize token efficiency (needs all encodings for each case)
    all_rows = finalize_token_efficiency(all_rows)

    # Aggregate metrics
    aggregates = aggregate_metrics(all_rows)

    # ── Write results ─────────────────────────────────────────────────

    # CSV
    csv_path = RESULTS_DIR / "encoding_benchmark_v0_1_results.csv"
    _write_csv(all_rows, csv_path)
    print(f"CSV written: {csv_path}")

    # JSON
    json_path = RESULTS_DIR / "encoding_benchmark_v0_1_results.json"
    json_output = {
        "benchmark": "GeoTask Encoding Benchmark v0.1",
        "cases": len(cases),
        "encoding_types": ENCODING_TYPES,
        "results": all_rows,
        "aggregates": aggregates,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_output, f, indent=2, ensure_ascii=False)
    print(f"JSON written: {json_path}")

    # Markdown summary
    summary_path = RESULTS_DIR / "encoding_benchmark_v0_1_summary.md"
    _write_summary_md(all_rows, aggregates, summary_path)
    print(f"Summary written: {summary_path}")

    # ── Copy to patent evidence ────────────────────────────────────────

    import shutil
    shutil.copy2(csv_path, PATENT_EVIDENCE_DIR / "encoding_benchmark_v0_1_results.csv")
    shutil.copy2(json_path, PATENT_EVIDENCE_DIR / "encoding_benchmark_v0_1_results.json")
    shutil.copy2(summary_path, PATENT_EVIDENCE_DIR / "encoding_benchmark_v0_1_summary.md")
    print(f"Results copied to patent_evidence/03_benchmark/")

    # ── Print aggregate summary ────────────────────────────────────────

    print()
    print("=" * 60)
    print("AGGREGATE RESULTS")
    print("=" * 60)
    print()
    _print_aggregates(aggregates)

    # ── Generate charts ─────────────────────────────────────────────────

    try:
        from benchmarks.encoding_v0_1.render_charts import render_all_charts
        chart_paths = render_all_charts(all_rows, aggregates, CHARTS_DIR)
        for name, path in chart_paths.items():
            print(f"Chart [{name}]: {path}")
    except ImportError as e:
        print(f"WARNING: Chart generation skipped — {e}")
        print("  Install matplotlib for chart generation: pip install matplotlib")
    except Exception as e:
        print(f"WARNING: Chart generation failed — {e}")

    # ── Generate report ─────────────────────────────────────────────────

    try:
        from benchmarks.encoding_v0_1.render_report import render_report
        report_path = render_report(all_rows, aggregates, RESULTS_DIR, REPO_ROOT)
        print(f"Report written: {report_path}")
    except Exception as e:
        print(f"WARNING: Report generation failed — {e}")

    print()
    print("Benchmark complete.")
    return 0


# ── Helpers ────────────────────────────────────────────────────────────

def _write_csv(rows: list[dict], path: Path):
    """Write benchmark results to CSV."""
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_summary_md(rows: list[dict], aggregates: dict, path: Path):
    """Write a Markdown summary of benchmark results."""
    lines = []
    lines.append("# GeoTask Encoding Benchmark v0.1 — Summary")
    lines.append("")
    lines.append("## Per-Case Results")
    lines.append("")
    lines.append(
        "| Case | Encoding | Input Tokens | Output Tokens | Total Tokens | "
        "Norm OK | Status | Expected | Match | Score |"
    )
    lines.append(
        "|------|----------|-------------|---------------|--------------|"
        "--------|--------|----------|-------|-------|"
    )
    for row in rows:
        match_icon = "PASS" if row["status_matched"] else "FAIL"
        norm_icon = "OK" if row["normalized_success"] else "FAIL"
        lines.append(
            f"| {row['case_id']} | {row['encoding_type']} | "
            f"{row['input_token_estimate']} | {row['output_token_estimate']} | "
            f"{row['total_token_estimate']} | {norm_icon} | "
            f"{row['overall_status']} | {row['expected_overall_status']} | "
            f"{match_icon} | {row['benchmark_score']:.1f} |"
        )

    lines.append("")
    lines.append("## Aggregate by Encoding")
    lines.append("")

    by_enc = aggregates.get("by_encoding", {})
    lines.append(
        "| Encoding | Cases | Avg Input Tokens | Avg Output Tokens | Avg Total Tokens | "
        "Norm Rate | Status Match | Avg Score | Token Eff |"
    )
    lines.append(
        "|----------|-------|-----------------|------------------|-----------------|"
        "----------|-------------|-----------|-----------|"
    )
    for enc, agg in by_enc.items():
        lines.append(
            f"| {enc} | {agg['case_count']} | "
            f"{agg['avg_input_tokens']:.0f} | {agg['avg_output_tokens']:.0f} | "
            f"{agg['avg_total_tokens']:.0f} | "
            f"{agg['normalization_success_rate']:.2f} | "
            f"{agg['status_match_rate']:.2f} | "
            f"{agg['avg_benchmark_score']:.1f} | "
            f"{agg['avg_token_efficiency']:.3f} |"
        )

    lines.append("")
    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- Model outputs are deterministic simulated outputs for benchmark reproducibility. "
        "This benchmark evaluates encoding cost, normalization, and verification behavior, "
        "not live LLM quality."
    )
    lines.append(
        "- Token counts are approximate and used only for relative comparison "
        "between encoding formats."
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_aggregates(aggregates: dict):
    """Print aggregate results to stdout."""
    by_enc = aggregates.get("by_encoding", {})
    print(f"{'Encoding':25s} {'Avg Tokens':>10s} {'Norm OK':>8s} {'Status OK':>10s} {'Score':>8s} {'Tok Eff':>8s}")
    print("-" * 75)
    for enc, agg in by_enc.items():
        print(
            f"{enc:25s} {agg['avg_total_tokens']:10.0f} "
            f"{agg['normalization_success_rate']:8.2f} "
            f"{agg['status_match_rate']:10.2f} "
            f"{agg['avg_benchmark_score']:8.1f} "
            f"{agg['avg_token_efficiency']:8.3f}"
        )
    print()


if __name__ == "__main__":
    sys.exit(main())
