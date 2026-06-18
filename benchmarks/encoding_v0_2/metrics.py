"""Metrics v2 for Encoding Benchmark."""
import sys; from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent/"src"))
from geotask_core.result_schema import STATUS_VERIFIED, STATUS_CONTRADICTED, STATUS_NEED_REVIEW

def compute_case_metrics(case, encoding_type, input_text, model_output, geotask_result, all_token_costs):
    from benchmarks.encoding_v0_2.token_counter import estimate_tokens
    cid=case["case_id"]; exp=case.get("expected",{}); enc=encoding_type
    itok=estimate_tokens(input_text); otok=estimate_tokens(model_output); ttot=itok+otok
    all_token_costs.setdefault(cid,{})[enc]=ttot
    meas=geotask_result.get("measurements",[]); conc=geotask_result.get("conclusion",{})
    ns=len(meas)>=1
    ost=conc.get("overall_status",STATUS_NEED_REVIEW)
    eost=case.get("expected_overall_status","verified")
    sm=(ost==eost)
    vc=sum(1 for m in meas if m.get("status")==STATUS_VERIFIED)
    cc=sum(1 for m in meas if m.get("status")==STATUS_CONTRADICTED)
    nr=sum(1 for m in meas if m.get("status")==STATUS_NEED_REVIEW)
    nd=0; io=0; ir=0
    rr=conc.get("review_reasons",[])
    if "invalid_operator" in str(rr): io=1
    if "invalid_reference" in str(rr): ir=1
    vsr=vc/len(meas) if meas else 0.0
    return {"case_id":cid,"case_group":case.get("case_group",""),"encoding_type":enc,
            "input_token_estimate":itok,"output_token_estimate":otok,"total_token_estimate":ttot,
            "normalized_success":ns,"overall_status":ost,"expected_overall_status":eost,
            "status_matched":sm,"measurements_count":len(meas),"verified_count":vc,
            "contradicted_count":cc,"need_review_count":nr,"need_data_count":nd,
            "invalid_operator_count":io,"invalid_reference_count":ir,"review_reasons":rr,
            "benchmark_score":0.0}

def finalize_token_efficiency(rows):
    groups={}
    for r in rows: groups.setdefault(r["case_id"],[]).append(r)
    for cid,grows in groups.items():
        mt=min(r["total_token_estimate"] for r in grows) if grows else 1
        for r in grows:
            te=mt/r["total_token_estimate"] if r["total_token_estimate"]>0 else 1.0
            r["token_efficiency_score"]=round(te,3)
            vsr=r["verified_count"]/r["measurements_count"] if r["measurements_count"]>0 else 0.0
            rr_detected=1 if r.get("review_reasons") and len(r["review_reasons"])>0 else 0
            s=0.0
            if r["status_matched"]: s+=35
            if r["normalized_success"]: s+=20
            s+=20*vsr
            s+=20*te
            s+=5*rr_detected
            r["benchmark_score"]=round(s,1)
    return rows

def aggregate_metrics(rows):
    encs=["natural_language","geotask_yaml","compact_dsl"]
    r={"by_encoding":{},"overall":{}}
    for enc in encs:
        er=[x for x in rows if x["encoding_type"]==enc]
        if not er: continue
        n=len(er)
        r["by_encoding"][enc]={
            "case_count":n,"avg_input_tokens":round(sum(x["input_token_estimate"] for x in er)/n,1),
            "avg_output_tokens":round(sum(x["output_token_estimate"] for x in er)/n,1),
            "avg_total_tokens":round(sum(x["total_token_estimate"] for x in er)/n,1),
            "normalization_success_rate":round(sum(1 for x in er if x["normalized_success"])/n,2),
            "status_match_rate":round(sum(1 for x in er if x["status_matched"])/n,2),
            "avg_benchmark_score":round(sum(x["benchmark_score"] for x in er)/n,1),
            "avg_token_efficiency":round(sum(x.get("token_efficiency_score",0) for x in er)/n,3),
            "verified_total":sum(x["verified_count"] for x in er),
            "contradicted_total":sum(x["contradicted_count"] for x in er),
            "need_review_total":sum(x["need_review_count"] for x in er),
        }
    # Case group success
    groups={}
    for row in rows: groups.setdefault(row.get("case_group",""),[]).append(row)
    r["by_case_group"]={}
    for g,gr in groups.items():
        n=len(gr); r["by_case_group"][g]=round(sum(1 for x in gr if x["status_matched"])/n,2) if n else 0
    return r
