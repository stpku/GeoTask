#!/usr/bin/env python3
"""GeoTask Encoding Benchmark v0.2 — Runner. 24 cases × 3 encodings."""
import argparse, csv, json, shutil, sys
from pathlib import Path
REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO/"src")); sys.path.insert(0, str(REPO))
import yaml
from geotask_core.normalizer import normalize_model_output
from geotask_core.parser import load_geotask
from benchmarks.encoding_v0_2.metrics import compute_case_metrics, finalize_token_efficiency, aggregate_metrics

BENCH = Path(__file__).resolve().parent
CASES = BENCH/"cases.yaml"; IN_DIR = BENCH/"inputs"; OUT_DIR = BENCH/"simulated_model_outputs"
RES = BENCH/"outputs"; CHART_DIR = RES/"charts"
GEOTASK_FILE = REPO/"examples"/"geotask_core_lite.yaml"
PATENT = REPO/"patent_evidence"/"03_benchmark"
ENCS = ["natural_language","geotask_yaml","compact_dsl"]
EXT = {"natural_language":".txt","geotask_yaml":".yaml","compact_dsl":".gt"}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--use-tiktoken",action="store_true")
    p.add_argument("--case",type=str)
    p.add_argument("--encoding",type=str)
    args=p.parse_args()
    RES.mkdir(parents=True,exist_ok=True); CHART_DIR.mkdir(parents=True,exist_ok=True); PATENT.mkdir(parents=True,exist_ok=True)
    with open(CASES,"r",encoding="utf-8") as f: cases=yaml.safe_load(f)["cases"]
    gd=load_geotask(GEOTASK_FILE) if GEOTASK_FILE.exists() else None
    print(f"GeoTask Encoding Benchmark v0.2 — {len(cases)} cases")
    all_rows=[]; all_tc={}
    for case in cases:
        cid=case["case_id"]
        if args.case and args.case not in cid: continue
        print(f"\n--- {cid}: {case['description']} ---")
        for enc in ENCS:
            if args.encoding and args.encoding!=enc: continue
            inp_file=IN_DIR/enc/f"{cid}{EXT[enc]}"
            out_file=OUT_DIR/enc/f"{cid}_output.md"
            if not inp_file.exists() or not out_file.exists():
                print(f"  [{enc}] SKIP: file missing"); continue
            inp_txt=inp_file.read_text(encoding="utf-8")
            out_txt=out_file.read_text(encoding="utf-8")
            result=normalize_model_output(out_txt,geotask_data=gd)
            from benchmarks.encoding_v0_2.local_verifier import verify_case
            result=verify_case(case,out_txt,geotask_data=gd)
            row=compute_case_metrics(case,enc,inp_txt,out_txt,result,all_tc)
            row["tiktoken_input_tokens"]=None; row["tiktoken_output_tokens"]=None; row["tiktoken_total_tokens"]=None
            if args.use_tiktoken:
                from benchmarks.encoding_v0_2.token_counter import estimate_tokens_tiktoken
                ti=estimate_tokens_tiktoken(inp_txt); to=estimate_tokens_tiktoken(out_txt)
                if ti is not None and to is not None:
                    row["tiktoken_input_tokens"]=ti; row["tiktoken_output_tokens"]=to; row["tiktoken_total_tokens"]=ti+to
            all_rows.append(row)
            icon="PASS" if row["status_matched"] else "FAIL"
            print(f"  [{enc:20s}] tok={row['total_token_estimate']:4d}  norm={'OK' if row['normalized_success'] else 'FAIL'}  status={row['overall_status']:12s}  score={row['benchmark_score']:5.1f}  {icon}")
    all_rows=finalize_token_efficiency(all_rows)
    agg=aggregate_metrics(all_rows)
    _write_csv(all_rows,RES/"encoding_benchmark_v0_2_results.csv")
    _write_json(all_rows,agg,RES/"encoding_benchmark_v0_2_results.json")
    _write_md(all_rows,agg,RES/"encoding_benchmark_v0_2_summary.md")
    shutil.copy2(RES/"encoding_benchmark_v0_2_results.csv",PATENT/"encoding_benchmark_v0_2_results.csv")
    shutil.copy2(RES/"encoding_benchmark_v0_2_results.json",PATENT/"encoding_benchmark_v0_2_results.json")
    shutil.copy2(RES/"encoding_benchmark_v0_2_summary.md",PATENT/"encoding_benchmark_v0_2_summary.md")
    print("\n"+_agg_str(agg))
    try:
        from benchmarks.encoding_v0_2.render_charts import render_all_charts
        for n,p in render_all_charts(all_rows,agg,CHART_DIR).items(): print(f"Chart [{n}]: {p}")
    except Exception as e: print(f"WARNING: charts failed — {e}")
    try:
        from benchmarks.encoding_v0_2.render_report import render_report
        print(f"Report: {render_report(all_rows,agg,RES,REPO)}")
    except Exception as e: print(f"WARNING: report failed — {e}")
    print("\nBenchmark complete."); return 0

def _write_csv(rows,path):
    if not rows: return
    with open(path,"w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def _write_json(rows,agg,path):
    with open(path,"w",encoding="utf-8") as f: json.dump({"benchmark":"GeoTask Encoding Benchmark v0.2","cases":len({r["case_id"] for r in rows}),"results":rows,"aggregates":agg},f,indent=2,ensure_ascii=False)

def _write_md(rows,agg,path):
    l=[]; l.append("# GeoTask Encoding Benchmark v0.2 — Summary\n")
    l.append("> Deterministic simulated benchmark. Does not claim live LLM accuracy.\n")
    l.append("## Aggregate by Encoding\n")
    l.append("| Encoding | Cases | Avg In Tok | Avg Out Tok | Avg Tot Tok | Norm Rate | Status Match | Score |")
    l.append("|----------|-------|-----------|------------|------------|-----------|-------------|-------|")
    for enc in ENCS:
        a=agg["by_encoding"].get(enc,{})
        if a: l.append(f"| {enc} | {a['case_count']} | {a['avg_input_tokens']:.0f} | {a['avg_output_tokens']:.0f} | {a['avg_total_tokens']:.0f} | {a['normalization_success_rate']:.2f} | {a['status_match_rate']:.2f} | {a['avg_benchmark_score']:.1f} |")
    l.append("\n## Token Reduction\n"); by=agg.get("by_encoding",{})
    nl=by.get("natural_language",{}).get("avg_total_tokens",1)
    for enc in ["geotask_yaml","compact_dsl"]:
        a=by.get(enc,{}); t=a.get("avg_total_tokens",1)
        if a: l.append(f"- {enc} vs NL: {(nl-t)/nl*100:.1f}% reduction, {nl/t:.1f}x compression")
    l.append("\n## Notes\n- Model outputs are deterministic simulated outputs.\n- Token counts approximate, relative comparison only.")
    path.write_text("\n".join(l),encoding="utf-8")

def _agg_str(agg):
    l=[]; l.append(f"{'Encoding':25s} {'Avg Tok':>8s} {'Norm':>6s} {'Match':>6s} {'Score':>7s}")
    l.append("-"*55)
    for enc in ENCS:
        a=agg["by_encoding"].get(enc,{})
        if a: l.append(f"{enc:25s} {a['avg_total_tokens']:8.0f} {a['normalization_success_rate']:6.2f} {a['status_match_rate']:6.2f} {a['avg_benchmark_score']:7.1f}")
    return "\n".join(l)

if __name__=="__main__": sys.exit(main())
