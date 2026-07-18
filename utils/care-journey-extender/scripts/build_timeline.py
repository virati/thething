#!/usr/bin/env python3
"""Build a standalone HTML timeline of patient care journeys.

Usage: python3 build_timeline.py <viz_data.json> <output.html> [--span 24]

viz_data.json: list of patients:
  {"idx": int, "name": str, "age": int, "gender": "male|female",
   "archetype": str, "v1_title": str, "v1_date": "YYYY-MM-DD",
   "fullDetail": bool,
   "visits": [{"m": float, "date": str, "label": str,
               "cat": "routine|acute|hospitalization|procedure|obstetric|eol",
               "highlight": str|null}]}

Use categorize() to auto-assign cat from labels, then review its output.
"""
import json, sys

CATS = {
  "routine":         {"label": "Routine / preventive", "color": "#2C7A72"},
  "acute":           {"label": "Acute / urgent",       "color": "#A6472B"},
  "hospitalization": {"label": "Hospitalization",      "color": "#8C6A2E"},
  "procedure":       {"label": "Procedure / surgery",  "color": "#4A5A9E"},
  "obstetric":       {"label": "Obstetric",            "color": "#6B4C6E"},
  "eol":             {"label": "End of life",          "color": "#3A3630"},
}

def categorize(label):
    l = label.lower()
    if "death" in l or "hospice" in l: return "eol"
    if any(k in l for k in ("delivery","prenatal","postpartum","obstetric","well-woman","c-section")): return "obstetric"
    if any(k in l for k in ("ed visit","emergency","urgent","flare")): return "acute"
    if any(k in l for k in ("hospital admission","snf","hospitalization","rehab")): return "hospitalization"
    if any(k in l for k in ("surgery","replacement","injection","catheterization")): return "procedure"
    return "routine"

TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Care journeys</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600&family=IBM+Plex+Mono&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
:root{--paper:#F1ECDF;--paper-raised:#F8F4E9;--ink:#211D14;--ink-soft:#5B5548;--ink-faint:#8C8573;--rule:#D9D0B8;--rule-strong:#C2B896;}
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font-family:'Inter',sans-serif;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:40px 28px 80px}
h1{font-family:'Fraunces',serif;font-weight:600;font-size:32px;margin:0 0 4px}
.dataset{font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:var(--ink-soft);margin-bottom:18px}
.legend{display:flex;flex-wrap:wrap;gap:16px;align-items:center;padding:12px 16px;background:var(--paper-raised);border:1px solid var(--rule);margin-bottom:6px}
.legend-item{display:flex;align-items:center;gap:6px;font-size:12px;color:var(--ink-soft)}
.legend-dot{width:9px;height:9px;border-radius:50%;flex:none}
.legend-dot.eol{border-radius:2px;transform:rotate(45deg)}
.axis{position:relative;height:26px;margin:18px 0 4px;margin-left:236px}
.axis .tick{position:absolute;top:0;font-family:'IBM Plex Mono',monospace;font-size:10.5px;color:var(--ink-faint);transform:translateX(-50%)}
.axis .tick::after{content:'';position:absolute;top:16px;left:50%;width:1px;height:2000px;background:var(--rule);z-index:0}
.row{display:flex;align-items:center;min-height:40px;border-bottom:1px solid var(--rule);position:relative}
.row:hover{background:var(--paper-raised)}
.row-label{width:236px;flex:none;padding:6px 12px 6px 0}
.row-label .nm{font-size:12.5px;font-weight:500}
.row-label .meta{font-size:10.5px;color:var(--ink-soft);font-family:'IBM Plex Mono',monospace}
.row-label .arch{font-size:10.5px;color:var(--ink-faint);margin-top:1px}
.track-wrap{flex:1;position:relative;height:40px}
.track-line{position:absolute;top:50%;left:0;right:0;height:1.5px;background:var(--rule-strong)}
.marker{position:absolute;top:50%;width:11px;height:11px;border-radius:50%;transform:translate(-50%,-50%);cursor:pointer;border:1.5px solid var(--paper)}
.marker.eol{border-radius:2px;transform:translate(-50%,-50%) rotate(45deg)}
.marker.v1{width:9px;height:9px;background:var(--ink);border-radius:2px;transform:translate(-50%,-50%) rotate(45deg)}
.badge{display:inline-block;font-family:'IBM Plex Mono',monospace;font-size:9px;padding:1px 5px;border:1px solid var(--rule-strong);border-radius:2px;color:var(--ink-soft);margin-left:6px}
.tooltip{position:fixed;display:none;z-index:50;background:var(--ink);color:var(--paper);padding:8px 11px;border-radius:3px;font-size:12px;max-width:260px;line-height:1.45;pointer-events:none}
.tooltip .tt-title{font-weight:500;margin-bottom:2px}
.tooltip .tt-date{font-family:'IBM Plex Mono',monospace;font-size:10.5px;opacity:.7;margin-bottom:4px}
.tooltip .tt-highlight{font-style:italic;opacity:.92}
.footnote{margin-top:20px;font-size:12px;color:var(--ink-soft);line-height:1.6;max-width:760px}
@media (max-width:760px){.row-label{width:130px}.axis{margin-left:130px}.row-label .arch{display:none}}
</style></head><body>
<div class="wrap">
<h1>Care journeys</h1>
<div class="dataset">__SUBTITLE__</div>
<div class="legend" id="legend"></div>
<div class="axis" id="axis"></div>
<div class="rows" id="rows"></div>
<p class="footnote">Each row starts at the patient's index visit (diamond) and runs __SPAN__ months forward. Circles are follow-up visits colored by type. Hover any marker for details.</p>
</div>
<div class="tooltip" id="tooltip"></div>
<script>
const DATA=__DATA__;const CATS=__CATS__;const SPAN=__SPAN__;
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const legend=document.getElementById('legend');
Object.entries(CATS).forEach(([k,v])=>{const e=document.createElement('div');e.className='legend-item';
e.innerHTML='<span class="legend-dot'+(k==='eol'?' eol':'')+'" style="background:'+v.color+'"></span><span>'+v.label+'</span>';legend.appendChild(e);});
const v1l=document.createElement('div');v1l.className='legend-item';
v1l.innerHTML='<span class="legend-dot" style="background:var(--ink);border-radius:2px;transform:rotate(45deg);width:8px;height:8px"></span><span>Index visit</span>';legend.appendChild(v1l);
const axis=document.getElementById('axis');
const step=SPAN<=24?6:12;
for(let m=0;m<=SPAN;m+=step){const t=document.createElement('div');t.className='tick';t.style.left=(m/SPAN*100)+'%';t.textContent=m===0?'V1':'+'+m+'mo';axis.appendChild(t);}
const tooltip=document.getElementById('tooltip');
function show(e,h){tooltip.innerHTML=h;tooltip.style.display='block';
tooltip.style.left=Math.min(e.clientX+14,window.innerWidth-280)+'px';tooltip.style.top=(e.clientY+14)+'px';}
function hide(){tooltip.style.display='none';}
const rows=document.getElementById('rows');
DATA.forEach(p=>{const row=document.createElement('div');row.className='row';
const lb=document.createElement('div');lb.className='row-label';
lb.innerHTML='<div class="nm">'+esc(p.name)+(p.fullDetail?'<span class="badge">full detail</span>':'')+'</div>'+
'<div class="meta">'+p.age+p.gender[0].toUpperCase()+' &middot; '+p.v1_date+'</div>'+
'<div class="arch">'+esc(p.archetype||'')+'</div>';row.appendChild(lb);
const tw=document.createElement('div');tw.className='track-wrap';
const ln=document.createElement('div');ln.className='track-line';tw.appendChild(ln);
const v1=document.createElement('div');v1.className='marker v1';v1.style.left='0%';
const v1h='<div class="tt-title">'+esc(p.v1_title)+'</div><div class="tt-date">'+p.v1_date+' &middot; index visit</div>';
['mouseenter','mousemove'].forEach(ev=>v1.addEventListener(ev,e=>show(e,v1h)));
v1.addEventListener('mouseleave',hide);tw.appendChild(v1);
p.visits.forEach(v=>{const m=document.createElement('div');const c=CATS[v.cat]||CATS.routine;
m.className='marker'+(v.cat==='eol'?' eol':'');m.style.left=Math.min(v.m/SPAN*100,100)+'%';m.style.background=c.color;
const h='<div class="tt-title">'+esc(v.label)+'</div><div class="tt-date">'+v.date+' &middot; +'+v.m+'mo</div>'+(v.highlight?'<div class="tt-highlight">'+esc(v.highlight)+'</div>':'');
['mouseenter','mousemove'].forEach(ev=>m.addEventListener(ev,e=>show(e,h)));
m.addEventListener('mouseleave',hide);tw.appendChild(m);});
row.appendChild(tw);rows.appendChild(row);});
</script></body></html>"""

def main():
    src, out = sys.argv[1], sys.argv[2]
    span = 24
    if "--span" in sys.argv:
        span = int(sys.argv[sys.argv.index("--span") + 1])
    data = json.load(open(src))
    for p in data:
        for v in p["visits"]:
            v.setdefault("cat", categorize(v["label"]))
            v.setdefault("highlight", None)
    n_visits = sum(1 + len(p["visits"]) for p in data)
    subtitle = f"{len(data)} patients &middot; {n_visits} visits &middot; index visit through +{span} months"
    html = (TEMPLATE.replace("__DATA__", json.dumps(data, separators=(",", ":")))
                    .replace("__CATS__", json.dumps(CATS))
                    .replace("__SPAN__", str(span))
                    .replace("__SUBTITLE__", subtitle))
    open(out, "w").write(html)
    print(f"wrote {out} ({len(html)} bytes, {len(data)} patients, {n_visits} visits)")

if __name__ == "__main__":
    main()
