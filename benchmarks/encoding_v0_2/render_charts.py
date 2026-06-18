"""Render charts v0.2 — 6 PNG charts."""
import sys; from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent.parent.parent))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

COLS={"natural_language":"#E74C3C","geotask_yaml":"#3498DB","compact_dsl":"#2ECC71"}
LABS={"natural_language":"Natural\nLanguage","geotask_yaml":"GeoTask\nYAML","compact_dsl":"Compact\nDSL"}
ORDER=["natural_language","geotask_yaml","compact_dsl"]

def _avgs(rows,key):
    r={}
    for e in ORDER:
        er=[x for x in rows if x["encoding_type"]==e]
        r[e]=sum(x[key] for x in er)/len(er) if er else 0
    return r

def _bar(data,title,ylabel,path,ylim=None,vfmt=".1f"):
    fig,ax=plt.subplots(figsize=(8,5))
    encs=list(data.keys()); vals=list(data.values())
    bars=ax.bar([LABS.get(e,e) for e in encs],vals,color=[COLS.get(e,"#999") for e in encs],edgecolor="white",width=0.55)
    for b,v in zip(bars,vals): ax.text(b.get_x()+b.get_width()/2,b.get_height()+max(vals)*0.02,f"{v:{vfmt}}",ha="center",va="bottom",fontsize=10,fontweight="bold")
    ax.set_title(title,fontsize=14,fontweight="bold"); ax.set_ylabel(ylabel); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    if ylim: ax.set_ylim(*ylim)
    fig.savefig(path,dpi=150,bbox_inches="tight"); plt.close(fig)

def render_all_charts(rows,agg,outdir):
    outdir.mkdir(parents=True,exist_ok=True)
    r={}
    r["token_cost"]=outdir/"token_cost_by_encoding.png"
    _bar(_avgs(rows,"total_token_estimate"),"Average Token Cost by Encoding","Estimated Tokens",r["token_cost"],vfmt=".0f")
    r["norm_success"]=outdir/"normalization_success_by_encoding.png"
    d={}; 
    for e in ORDER:
        er=[x for x in rows if x["encoding_type"]==e]
        d[e]=sum(1 for x in er if x["normalized_success"])/len(er) if er else 0
    _bar(d,"Normalization Success by Encoding","Success Rate",r["norm_success"],ylim=(0,1.15),vfmt=".2f")
    r["verif_success"]=outdir/"verification_success_by_encoding.png"
    d={}; 
    for e in ORDER:
        er=[x for x in rows if x["encoding_type"]==e]
        d[e]=sum(1 for x in er if x["status_matched"])/len(er) if er else 0
    _bar(d,"Verification Success by Encoding","Status Match Rate",r["verif_success"],ylim=(0,1.15),vfmt=".2f")
    r["score"]=outdir/"benchmark_score_by_encoding.png"
    _bar(_avgs(rows,"benchmark_score"),"Benchmark Score by Encoding","Score (0-100)",r["score"],ylim=(0,110),vfmt=".1f")
    # Status distribution
    r["status_dist"]=outdir/"status_distribution_by_encoding.png"
    fig,ax=plt.subplots(figsize=(10,5))
    cats=["verified","contradicted","need_review"]
    x=range(len(ORDER)); w=0.25
    for i,cat in enumerate(cats):
        vals=[]
        for e in ORDER:
            er=[x for x in rows if x["encoding_type"]==e]
            vals.append(sum(x[f"{cat}_count"] for x in er))
        ax.bar([p+i*w for p in x],vals,w,label=cat,color=["#2ECC71","#E74C3C","#F39C12"][i])
    ax.set_xticks([p+w for p in x]); ax.set_xticklabels([LABS.get(e,e) for e in ORDER])
    ax.set_title("Status Distribution by Encoding",fontweight="bold"); ax.legend(); ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    fig.savefig(r["status_dist"],dpi=150,bbox_inches="tight"); plt.close(fig)
    # Token reduction
    r["token_red"]=outdir/"token_reduction_by_encoding.png"
    by=agg.get("by_encoding",{})
    nl=by.get("natural_language",{}).get("avg_total_tokens",1)
    d={}
    for e in ORDER:
        a=by.get(e,{}); t=a.get("avg_total_tokens",1)
        d[e]=(nl-t)/nl*100 if nl>0 else 0
    _bar(d,"Token Reduction vs Natural Language","Reduction %",r["token_red"],vfmt=".1f")
    return r
