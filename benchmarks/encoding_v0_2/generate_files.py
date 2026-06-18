#!/usr/bin/env python3
"""Auto-generate all input files and simulated outputs for v0.2 benchmark.

Reads cases.yaml and produces 72 input files + 72 output files.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
import yaml

BASE = Path(__file__).resolve().parent
CASES_FILE = BASE / "cases.yaml"
IN_DIR = BASE / "inputs"
OUT_DIR = BASE / "simulated_model_outputs"

ENCODINGS = ["natural_language", "geotask_yaml", "compact_dsl"]
EXT = {"natural_language": ".txt", "geotask_yaml": ".yaml", "compact_dsl": ".gt"}

def _obj_def(obj):
    t = obj.get("type","")
    if t=="point": return f"P({obj['xy'][0]},{obj['xy'][1]})"
    if t=="line":
        pts = ";".join(f"{p[0]},{p[1]}" for p in obj["points"])
        return f"L({pts})"
    if t=="rect": return f"R({obj['bbox'][0]},{obj['bbox'][1]},{obj['bbox'][2]},{obj['bbox'][3]})"
    if t=="time": return f"T({obj['interval'][0]},{obj['interval'][1]})"
    if t=="altitude": return f"A({obj['range'][0]},{obj['range'][1]})"
    return str(obj)

def _op_short(op):
    return {"distance_2d":"distance_2d","line_intersects_rect":"line_intersects_rect",
            "rect_contains_point":"rect_contains_point","point_to_line_distance_2d":"pt_line_dist",
            "time_overlap":"time_overlap","altitude_overlap":"altitude_overlap"}.get(op,op)

def _unit_str(chk):
    u=chk.get("unit","")
    return f"->{u}" if u else "->bool"

def _desc_objects(case):
    lines=[]
    for name,obj in case.get("scene",{}).get("objects",{}).items():
        t=obj.get("type","")
        if t=="point": lines.append(f"- {name} at ({obj['xy'][0]}, {obj['xy'][1]})")
        elif t=="line":
            pts=obj["points"]
            lines.append(f"- {name} from ({pts[0][0]},{pts[0][1]}) to ({pts[1][0]},{pts[1][1]})")
        elif t=="rect": lines.append(f"- {name} bbox [{obj['bbox'][0]},{obj['bbox'][1]},{obj['bbox'][2]},{obj['bbox'][3]}]")
        elif t=="time": lines.append(f"- {name} [{obj['interval'][0]} to {obj['interval'][1]}]")
        elif t=="altitude": lines.append(f"- {name} [{obj['range'][0]}m to {obj['range'][1]}m]")
    return "\n".join(lines)

def _op_desc(op):
    d={"distance_2d":"Euclidean distance sqrt((x1-x2)^2+(y1-y2)^2)",
       "line_intersects_rect":"whether line segment crosses or touches rectangle",
       "rect_contains_point":"whether point is inside rectangle boundary",
       "point_to_line_distance_2d":"shortest distance from point to line segment",
       "time_overlap":"whether time intervals overlap (boundary counts)",
       "altitude_overlap":"whether altitude ranges overlap (boundary counts)"}
    return d.get(op,op)

def gen_nl_input(case):
    objs=_desc_objects(case)
    chks=case.get("checks",[])
    qs="\n".join(f"- {c['name']} using {c['op']}" for c in chks)
    return f"""You are a spatial reasoning assistant. Given the following objects:

{objs}

Please calculate:
{qs}

Return each result with its value, unit (if applicable), and the operator used."""
# ── geotask_yaml input ──────────────────────────────────
def gen_yaml_input(case):
    scene=case.get("scene",{})
    objs=scene.get("objects",{})
    obj_lines=[]
    for name,obj in objs.items():
        t=obj.get("type","")
        if t=="point": obj_lines.append(f"  {name}:\n    type: point\n    xy: {obj['xy']}")
        elif t=="line": obj_lines.append(f"  {name}:\n    type: line\n    points: {obj['points']}")
        elif t=="rect": obj_lines.append(f"  {name}:\n    type: rect\n    bbox: {obj['bbox']}")
        elif t=="time": obj_lines.append(f"  {name}:\n    type: time\n    interval: {obj['interval']}")
        elif t=="altitude": obj_lines.append(f"  {name}:\n    type: altitude\n    range: {obj['range']}")
    chks=case.get("checks",[])
    ops=set(c["op"] for c in chks)
    op_lines="\n".join(f"  {op}: \"{_op_desc(op)}\"" for op in ops)
    qs="\n".join(f"    - \"{c['name']}\"" for c in chks)
    return f"""geotask:
  version: "0.1-lite"
  name: "{case['case_id']}"

space:
  crs: "local_xy_m"
  unit: "meter"

objects:
{chr(10).join(obj_lines)}

ops:
{op_lines}

task:
  questions:
{qs}"""
# ── compact_dsl input ────────────────────────────────────
def gen_dsl_input(case):
    objs=case.get("scene",{}).get("objects",{})
    chks=case.get("checks",[])
    obj_str="; ".join(f"{n}={_obj_def(o)}" for n,o in objs.items())
    chk_lines="; ".join(f"{c['name']}={c['op']}({','.join(c['args'])}){_unit_str(c)}" for c in chks)
    return f"OBJ {obj_str}\nCHK {chk_lines}\nASK return value, unit, operator, status"

# ═══════════════════════════════════════════════════════════
# SIMULATED MODEL OUTPUTS
# ═══════════════════════════════════════════════════════════

def _val_str(v,u=None):
    if isinstance(v,float): return f"{v:.2f}"
    return str(v).lower()

def _out_value(chk):
    mv=chk.get("model_output")
    if mv is not None: return mv
    return chk["expected"]

def gen_nl_output(case):
    chks=case.get("checks",[])
    grp=case.get("case_group","")
    lines=[]
    for c in chks:
        v=_out_value(c)
        u=c.get("unit","")
        lines.append(f"{c['name']}: {_val_str(v)} {u}".strip())
    cid=case["case_id"]
    if cid=="case_016_missing_operator":
        return "\n".join(lines)  # no operator references
    if cid=="case_017_missing_value":
        return "The calculation was performed but the exact value is not available."
    if cid=="case_018_missing_object_reference":
        return f"The distance is approximately {_val_str(_out_value(chks[0]))} meters."
    if cid=="case_019_invalid_operator":
        v=_out_value(chks[0])
        return f"Distance: {_val_str(v)} meter\nverified_by: haversine"
    if cid=="case_020_invalid_reference":
        v=_out_value(chks[0])
        return f"Distance from airport to school: {_val_str(v)} meter\nverified_by: distance_2d"
    if cid=="case_021_unit_mismatch":
        v=_out_value(chks[0])
        km=round(v/1000,3) if isinstance(v,(int,float)) else v
        return f"Distance: {km} km\nverified_by: distance_2d"
    if cid=="case_022_chinese_negative":
        return "起飞点到学校的距离为 144.22 米。\n航线与矩形区域不相交。\nverified_by: distance_2d, line_intersects_rect"
    if cid=="case_023_markdown_mixed":
        v1=_out_value(chks[0])
        return f"""## Spatial Analysis Results

**Distance Calculation**: The 2D distance is `{_val_str(v1)} meters`.

*Operator*: distance_2d"""
    if cid=="case_024_yaml_like_output":
        parts=[]
        for c in chks:
            v=_out_value(c)
            parts.append(f"  - name: {c['name']}\n    value: {_val_str(v)}\n    verified_by: {c['op']}")
        return "measurements:\n"+"\n".join(parts)
    # Default: with operator references
    ops=list(set(c["op"] for c in chks))
    lines.append(f"verified_by: {', '.join(ops)}")
    return "\n".join(lines)

def gen_yaml_output(case):
    chks=case.get("checks",[])
    cid=case["case_id"]
    parts=[]
    vby=[]
    for c in chks:
        v=_out_value(c)
        u=c.get("unit","")
        op=c["op"]
        parts.append(f"  - name: {c['name']}\n    value: {_val_str(v)}\n    unit: {u or 'null'}\n    verified_by: {op}")
        vby.append(f"  - operation: {op}\n    result: \"{_val_str(v)} {u}\"".strip())
    if cid=="case_016_missing_operator":
        parts=[p.replace("    verified_by:","    # verified_by:") for p in parts]
    if cid=="case_017_missing_value":
        parts=["  - name: takeoff_to_school_distance\n    value: null\n    unit: meter"]
    if cid=="case_019_invalid_operator":
        parts=[p.replace("verified_by: distance_2d","verified_by: haversine") for p in parts]
    if cid=="case_020_invalid_reference":
        parts=["  - name: airport_to_school_distance\n    value: 144.22\n    unit: meter\n    verified_by: distance_2d"]
    return f"measurements:\n{chr(10).join(parts)}\n\nconclusion:\n  summary: ok\n  external_data_used: false\n\nverified_by:\n{chr(10).join(vby)}"

def gen_dsl_output(case):
    chks=case.get("checks",[])
    cid=case["case_id"]
    if cid=="case_016_missing_operator":
        return "  ".join(f"{c['name']}={_val_str(_out_value(c))} {c.get('unit','')}".strip() for c in chks)
    if cid=="case_017_missing_value":
        return "d1=? meter"
    if cid=="case_019_invalid_operator":
        return f"d1={_val_str(_out_value(chks[0]))} meter haversine"
    if cid=="case_020_invalid_reference":
        return f"d1={_val_str(_out_value(chks[0]))} meter distance_2d (ref:airport)"
    parts=[]
    for c in chks:
        v=_out_value(c)
        u=c.get("unit","")
        parts.append(f"{c['name']}={_val_str(v)} {u} {c['op']}".strip())
    return "  ".join(parts)

# ═══════════════════════════════════════════════════════════

GEN_INPUT={"natural_language":gen_nl_input,"geotask_yaml":gen_yaml_input,"compact_dsl":gen_dsl_input}
GEN_OUTPUT={"natural_language":gen_nl_output,"geotask_yaml":gen_yaml_output,"compact_dsl":gen_dsl_output}

def main():
    with open(CASES_FILE,"r",encoding="utf-8") as f:
        data=yaml.safe_load(f)
    cases=data["cases"]
    total=0
    for enc in ENCODINGS:
        (IN_DIR/enc).mkdir(parents=True,exist_ok=True)
        (OUT_DIR/enc).mkdir(parents=True,exist_ok=True)
    for case in cases:
        cid=case["case_id"]
        for enc in ENCODINGS:
            inp=GEN_INPUT[enc](case)
            out=GEN_OUTPUT[enc](case)
            inp_file=IN_DIR/enc/f"{cid}{EXT[enc]}"
            out_file=OUT_DIR/enc/f"{cid}_output.md"
            inp_file.write_text(inp,encoding="utf-8")
            out_file.write_text(out,encoding="utf-8")
            total+=2
    print(f"Generated {total} files ({len(cases)} cases × {len(ENCODINGS)} encodings × 2)")
if __name__=="__main__":
    main()
