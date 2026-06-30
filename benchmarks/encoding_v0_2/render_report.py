"""Report generator v0.2."""
import sys; from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent.parent))

def render_report(rows,agg,outdir,repo_root):
    path=outdir/"encoding_benchmark_v0_2_report.md"
    by=agg.get("by_encoding",{})
    nl=by.get("natural_language",{}).get("avg_total_tokens",1)
    dsl=by.get("compact_dsl",{}).get("avg_total_tokens",1)
    red=(nl-dsl)/nl*100 if nl>0 else 0; comp=nl/dsl if dsl>0 else 0
    groups=agg.get("by_case_group",{})
    encs=["natural_language","geotask_yaml","compact_dsl"]
    l=[]
    l.append("# GeoTask Encoding Benchmark v0.2\n")
    l.append("> **Deterministic simulated benchmark.** Does not claim live LLM accuracy.\n")
    l.append("## Difference from v0.1\n")
    l.append(f"- Cases: 4 → {len({r['case_id'] for r in rows})}\n- Operators: 2 → 6\n- Groups: 5 (basic, new ops, contradicted, need_review, robustness)\n")
    l.append("## Key Findings\n")
    l.append(f"Compact DSL reduced avg tokens from {nl:.0f} to {dsl:.0f} ({red:.1f}% reduction, {comp:.1f}x compression) vs natural language.\n")
    l.append("## Aggregate Results\n")
    l.append("| Encoding | Avg Tokens | Norm Rate | Status Match | Score |")
    l.append("|----------|-----------|-----------|-------------|-------|")
    for enc in encs:
        a=by.get(enc,{}); 
        if a: l.append(f"| {enc} | {a['avg_total_tokens']:.0f} | {a['normalization_success_rate']:.2f} | {a['status_match_rate']:.2f} | {a['avg_benchmark_score']:.1f} |")
    l.append("\n## Case Group Success\n")
    for g,rate in groups.items(): l.append(f"- {g}: {rate:.0%}")
    l.append("\n## Charts\n")
    for ch in ["token_cost_by_encoding.png","verification_success_by_encoding.png","normalization_success_by_encoding.png","benchmark_score_by_encoding.png","status_distribution_by_encoding.png","token_reduction_by_encoding.png"]:
        l.append(f"![{ch}](charts/{ch})\n")
    l.append(
        "\n## Limitations\n"
        "- Simulated outputs, not real LLM\n"
        "- Approximate token counting\n"
        "- 24 cases, descriptive only\n"
        "- Benchmark scoring uses a benchmark-local verifier for deterministic "
        "case replay. This local verifier boundary is separate from the "
        "production Core verifier and must not be interpreted as live model, "
        "regulatory, or domain-specific validation.\n"
    )
    txt="\n".join(l)
    path.write_text(txt,encoding="utf-8")
    (repo_root/"docs"/"encoding_benchmark_v0_2.md").write_text(txt,encoding="utf-8")
    return path
