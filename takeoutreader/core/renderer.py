# ============================================
# takeoutreader/core/renderer.py
# Generation du dossier de sortie HTML
# (index.html + mails.js + bodies.js + PJ)
# ============================================

import os
import json
import html as html_mod
from datetime import datetime
from collections import Counter

from takeoutreader.core.extractor import extract_pj_to_disk

def generate_output(mails, output_dir):
    """Cree un dossier avec index.html + mails.js + bodies.js.
    Retourne la taille totale en Mo."""

    os.makedirs(output_dir, exist_ok=True)

    all_labels = Counter()
    for m in mails:
        for lb in m["labels"]:
            all_labels[lb] += 1
    total_pj = sum(m["p"] for m in mails)
    nb = len(mails)
    now = datetime.now().strftime("%d/%m/%Y %H:%M")

    dates = [m["ds"] for m in mails if m["ds"] != "0000-00-00"]
    date_min = dates[-1][:4] if dates else "?"
    date_max = dates[0][:4] if dates else "?"

    # === EXTRACT PJ TO DISK ===
    print("  [PJ] Extraction des pieces jointes...", flush=True)
    extract_pj_to_disk(mails, output_dir)

    # === MAILS.JS — headers + snippet, PAS de body ===
    mails_light = []
    bodies = []
    for m in mails:
        light = {k: m[k] for k in ("ds", "d", "f", "ff", "to", "cc", "s",
                                     "labels", "l", "p", "pj", "cat", "tid", "sn",
                                     "spam", "trash", "sent")}
        # Ajouter chemins PJ si extraites
        if "pjp" in m:
            light["pjp"] = m["pjp"]
        mails_light.append(light)
        bodies.append(m.get("b", ""))

    mails_json = json.dumps(mails_light, ensure_ascii=True, separators=(',', ':'))
    mails_json = mails_json.replace("<", "\\u003C")

    mails_js_path = os.path.join(output_dir, "mails.js")
    with open(mails_js_path, "w", encoding="utf-8") as f:
        f.write("var D=")
        f.write(mails_json)
        f.write(";\n")

    mails_size = os.path.getsize(mails_js_path) / (1024 * 1024)
    print(f"    mails.js  : {mails_size:.1f} Mo ({nb:,} mails)", flush=True)

    # === BODIES.JS — full body array, same index as D ===
    bodies_json = json.dumps(bodies, ensure_ascii=True, separators=(',', ':'))
    bodies_json = bodies_json.replace("<", "\\u003C")

    bodies_js_path = os.path.join(output_dir, "bodies.js")
    with open(bodies_js_path, "w", encoding="utf-8") as f:
        f.write("var B=")
        f.write(bodies_json)
        f.write(";\n")

    bodies_size = os.path.getsize(bodies_js_path) / (1024 * 1024)
    print(f"    bodies.js : {bodies_size:.1f} Mo", flush=True)

    # === DASHBOARD DATA (dans le HTML, pas dans le JSON) ===
    cat_stats = Counter(m["cat"] for m in mails)
    year_stats = Counter()
    sender_stats = Counter()
    for m in mails:
        y = m["ds"][:4]
        if y != "0000":
            year_stats[y] += 1
        sender_stats[m["f"]] += 1
    top_senders = sender_stats.most_common(8)
    years_sorted = sorted(year_stats.items(), reverse=True)

    # Thread count
    tid_count = Counter(m["tid"] for m in mails if m.get("tid"))
    threads_multi = sum(1 for c in tid_count.values() if c > 1)

    cat_order = ["Perso", "Achats", "Banque", "Newsletter", "Notif", "Social"]
    cat_emoji = {"Perso": "&#9993;", "Achats": "&#128230;", "Banque": "&#127974;",
                 "Newsletter": "&#128240;", "Notif": "&#128276;", "Social": "&#128172;"}
    cat_colors = {"Perso": "#4FC3F7", "Achats": "#FFB74D", "Banque": "#81C784",
                  "Newsletter": "#BA68C8", "Notif": "#90A4AE", "Social": "#F06292"}

    max_yr = max(year_stats.values()) if year_stats else 1
    dash_cats = ""
    for cat in cat_order:
        cnt = cat_stats.get(cat, 0)
        if cnt == 0:
            continue
        pct = cnt * 100 // nb if nb else 0
        col = cat_colors.get(cat, "#888")
        emo = cat_emoji.get(cat, "")
        dash_cats += (f'<div class="dc" onclick="dCat(\'{cat}\')" style="border-color:{col}">'
                      f'<div class="dcn">{emo} {cat}</div>'
                      f'<div class="dcc" style="color:{col}">{cnt:,}</div>'
                      f'<div class="dcp">{pct}%</div></div>')

    dash_years = ""
    for yr, cnt in years_sorted:
        w = max(8, cnt * 100 // max_yr)
        dash_years += (f'<div class="dy" onclick="dYr(\'{yr}\')">'
                       f'<span class="dyl">{yr}</span>'
                       f'<div class="dyb"><div class="dyf" style="width:{w}%"></div></div>'
                       f'<span class="dyc">{cnt:,}</span></div>')

    dash_snd = ""
    for snd, cnt in top_senders:
        snd_esc = snd.replace("'", "\\'").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        snd_disp = html_mod.escape(snd[:25] + ("..." if len(snd) > 25 else ""))
        dash_snd += (f'<div class="dse" onclick="dSnd(\'{snd_esc}\')">'
                     f'<span class="dsn">{snd_disp}</span>'
                     f'<span class="dsc">{cnt:,}</span></div>')

    # === INDEX.HTML ===
    index_html = f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gmail Archive - {nb:,} mails</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{--bg:#0D0D10;--bg1:#16161D;--bg2:#1E1E28;--bg3:#2A2A38;--brd:#3A3A4A;--t:#E8E8F0;--t2:#B8B8C8;--t3:#8888A0;--ac:#B388FF;--ac2:#9C64FF;--gn:#A5D6A7;--gnbg:#1B2E1E;--hover:#1E1B2E;--act:#251E3E;--actbrd:#B388FF;--dbg:#181820;--shadow:0 1px 4px rgba(80,40,120,.25);--glow:0 0 0 2px rgba(179,136,255,.2)}}
body.light{{--bg:#FDF5F7;--bg1:#FFFFFF;--bg2:#F5EAEE;--bg3:#EADFDF;--brd:#DDD0D5;--t:#2A1A20;--t2:#5A3A45;--t3:#8A6A75;--ac:#E91E63;--ac2:#C2185B;--gn:#2E7D32;--gnbg:#E8F5E9;--hover:#FDE8EE;--act:#FCE4EC;--actbrd:#E91E63;--dbg:#FFFFFF;--shadow:0 1px 4px rgba(120,40,60,.08);--glow:0 0 0 2px rgba(233,30,99,.15)}}
body{{background:var(--bg);color:var(--t);font-family:'Segoe UI',system-ui,-apple-system,sans-serif;font-size:14px;height:100vh;overflow:hidden;display:flex;flex-direction:column;transition:background .3s,color .3s}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(8px)}}to{{opacity:1;transform:translateY(0)}}}}
@keyframes fadeIn{{from{{opacity:0}}to{{opacity:1}}}}
::-webkit-scrollbar{{width:7px}}::-webkit-scrollbar-track{{background:transparent}}::-webkit-scrollbar-thumb{{background:var(--bg3);border-radius:4px}}::-webkit-scrollbar-thumb:hover{{background:var(--t3)}}
.hdr{{background:var(--bg1);border-bottom:1px solid var(--brd);padding:12px 20px;display:flex;align-items:center;gap:12px;flex-shrink:0;flex-wrap:wrap;box-shadow:var(--shadow);animation:fadeIn .4s}}
.hdr h1{{font-size:18px;font-weight:700;color:var(--t);white-space:nowrap;letter-spacing:-.3px;cursor:pointer}}
.stats{{display:flex;gap:12px;font-size:12px;color:var(--t3)}}.stats b{{color:var(--t2);font-weight:600}}
.hdr-r{{display:flex;gap:8px;margin-left:auto;align-items:center}}
.thb,.cmdb{{background:transparent;border:1px solid var(--brd);border-radius:8px;padding:5px 11px;font-size:14px;cursor:pointer;color:var(--t2);transition:all .2s}}
.thb:hover,.cmdb:hover{{border-color:var(--ac);color:var(--ac);box-shadow:var(--glow)}}
.ctl{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 16px;border-bottom:1px solid var(--brd);background:var(--bg1);flex-shrink:0;box-shadow:var(--shadow);animation:fadeIn .5s}}
.sbw{{position:relative;display:flex;align-items:center}}.sbw::before{{content:"\\1F50D";position:absolute;left:10px;font-size:11px;pointer-events:none;opacity:.45}}
.sb{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:8px 14px 8px 32px;color:var(--t);font-size:13px;width:220px;outline:none;transition:border-color .2s,box-shadow .2s}}
.sb:focus{{border-color:var(--ac);box-shadow:var(--glow)}}.sb::placeholder{{color:var(--t3)}}
select{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:7px 10px;color:var(--t);font-size:12px;outline:none;cursor:pointer;max-width:160px;transition:border-color .2s,box-shadow .2s}}
select:focus{{border-color:var(--ac);box-shadow:var(--glow)}}
.tgl{{display:flex;align-items:center;gap:4px;font-size:11px;color:var(--t3);cursor:pointer;user-select:none}}.tgl input{{accent-color:var(--ac)}}
.tgl.dis{{opacity:.4;pointer-events:none}}
.cnt{{color:var(--t3);font-size:12px;margin-left:auto;white-space:nowrap}}
.bld{{font-size:10px;color:var(--gn);margin-left:4px}}

/* DASHBOARD = MODAL OVERLAY */
.dash-ov{{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:998;display:none;align-items:center;justify-content:center}}
.dash-ov.on{{display:flex}}
.dash{{background:var(--bg1);border:1px solid var(--brd);border-radius:16px;width:680px;max-height:80vh;overflow-y:auto;display:flex;flex-direction:column;align-items:center;padding:32px 28px;gap:24px;box-shadow:0 20px 60px rgba(80,40,120,.3);position:relative;animation:fadeUp .3s}}
.dash-t{{font-size:22px;font-weight:700;color:var(--t);text-align:center}}
.dash-t small{{display:block;font-size:13px;font-weight:400;color:var(--t3);margin-top:4px}}
.dash-s{{display:flex;gap:20px;font-size:12px;color:var(--t2);flex-wrap:wrap;justify-content:center}}
.dash-s b{{font-size:18px;display:block;color:var(--t);font-weight:700}}
.dash-x{{position:absolute;top:12px;right:16px;background:none;border:none;color:var(--t3);font-size:20px;cursor:pointer;padding:4px 8px;border-radius:4px}}
.dash-x:hover{{color:var(--t);background:var(--bg3)}}
.dcs{{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;max-width:700px}}
.dc{{background:var(--bg1);border:1px solid var(--brd);border-left:3px solid;border-radius:10px;padding:14px 18px;min-width:100px;cursor:pointer;transition:transform .15s,box-shadow .15s;text-align:center}}
.dc:hover{{transform:translateY(-2px);box-shadow:0 6px 16px rgba(0,0,0,.3)}}
.dcn{{font-size:12px;color:var(--t2);margin-bottom:4px}}.dcc{{font-size:22px;font-weight:700}}.dcp{{font-size:11px;color:var(--t3)}}
.dyr{{max-width:500px;width:100%}}.dyr-t{{font-size:13px;font-weight:600;color:var(--t2);margin-bottom:8px}}
.dy{{display:flex;align-items:center;gap:8px;padding:3px 0;cursor:pointer;border-radius:4px;transition:background .1s}}.dy:hover{{background:var(--hover)}}
.dyl{{width:40px;text-align:right;font-size:12px;color:var(--t3);font-variant-numeric:tabular-nums}}
.dyb{{flex:1;height:16px;background:var(--bg3);border-radius:3px;overflow:hidden}}.dyf{{height:100%;background:var(--ac);border-radius:3px;transition:width .3s}}
.dyc{{width:45px;font-size:12px;color:var(--t2);font-variant-numeric:tabular-nums}}
.dss{{max-width:500px;width:100%}}.dss-t{{font-size:13px;font-weight:600;color:var(--t2);margin-bottom:8px}}
.dse{{display:flex;justify-content:space-between;padding:4px 8px;cursor:pointer;border-radius:4px;transition:background .1s;font-size:12px}}.dse:hover{{background:var(--hover)}}
.dsn{{color:var(--t2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}.dsc{{color:var(--t3);flex-shrink:0;margin-left:8px;font-variant-numeric:tabular-nums}}

/* COMMAND PALETTE */
.cpo{{position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:999;display:none;align-items:flex-start;justify-content:center;padding-top:15vh}}
.cpo.on{{display:flex}}
.cpb{{background:var(--bg1);border:1px solid var(--brd);border-radius:14px;width:520px;max-height:400px;overflow:hidden;box-shadow:0 20px 60px rgba(80,40,120,.3);animation:fadeUp .2s}}
.cpi{{width:100%;padding:14px 18px;border:none;border-bottom:1px solid var(--brd);background:transparent;color:var(--t);font-size:15px;outline:none}}.cpi::placeholder{{color:var(--t3)}}
.cpr{{overflow-y:auto;max-height:340px}}
.cpri{{padding:10px 18px;cursor:pointer;display:flex;align-items:center;gap:10px;font-size:13px;color:var(--t2);transition:background .1s}}
.cpri:hover,.cpri.sel{{background:var(--hover);color:var(--t)}}
.cpri .ck{{color:var(--t3);font-size:11px;margin-left:auto}}.cpri .ce{{font-size:16px;width:22px;text-align:center}}

/* MAIN SPLIT */
.main{{flex:1;display:flex;overflow:hidden}}
.lp{{width:44%;min-width:320px;border-right:1px solid var(--brd);display:flex;flex-direction:column;overflow:hidden}}
.ls{{flex:1;overflow-y:auto}}
.mr{{padding:10px 14px;border-bottom:1px solid var(--bg3);cursor:pointer;transition:background .15s,transform .1s;display:flex;gap:10px;align-items:flex-start;animation:fadeUp .25s backwards}}
.mr:hover{{background:var(--hover);transform:translateX(2px)}}
.mr.act{{background:var(--act);border-left:3px solid var(--actbrd);padding-left:11px;transform:translateX(0)}}
.av{{width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;color:#fff;flex-shrink:0;margin-top:1px;letter-spacing:-.5px;box-shadow:0 1px 3px rgba(0,0,0,.3)}}
.mc{{flex:1;min-width:0}}
.mc .top{{display:flex;justify-content:space-between;gap:8px}}
.mc .frm{{font-weight:600;font-size:13px;color:var(--t);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;flex:1}}
.mc .dt{{font-size:11px;color:var(--t3);white-space:nowrap;font-variant-numeric:tabular-nums}}
.mc .su{{font-size:13px;color:var(--t2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:1px}}
.mc .sn{{font-size:12px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px;line-height:1.3}}
.mc .mt{{display:flex;gap:4px;margin-top:3px;flex-wrap:wrap;align-items:center}}
.lb{{background:var(--bg3);border:1px solid var(--brd);border-radius:4px;padding:2px 7px;font-size:10px;color:var(--t3);letter-spacing:.2px}}
.lb2{{background:var(--bg3);border:1px solid var(--brd);border-radius:4px;padding:2px 6px;font-size:9px;color:var(--t3);opacity:.7}}
.pt{{background:var(--gnbg);color:var(--gn);border-radius:4px;padding:2px 7px;font-size:10px;font-weight:600}}
.ct{{border-radius:4px;padding:2px 7px;font-size:10px;font-weight:500;border:1px solid}}
.pgn{{display:flex;justify-content:center;align-items:center;gap:10px;padding:8px;border-top:1px solid var(--brd);flex-shrink:0;background:var(--bg1)}}
.pgn button{{background:var(--bg2);border:1px solid var(--brd);border-radius:8px;padding:6px 16px;color:var(--t);cursor:pointer;font-size:13px;transition:all .2s}}
.pgn button:hover:not(:disabled){{border-color:var(--ac);color:var(--ac);box-shadow:var(--glow)}}.pgn button:disabled{{opacity:.3;cursor:default}}.pgn .pi{{color:var(--t3);font-size:11px}}
.rp{{flex:1;display:flex;flex-direction:column;overflow:hidden}}
.re{{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;color:var(--t3);font-size:14px;text-align:center;line-height:2.2}}
.rh{{padding:18px 24px;border-bottom:1px solid var(--brd);flex-shrink:0;animation:fadeUp .25s}}
.rs{{font-size:18px;font-weight:700;color:var(--t);margin-bottom:12px;line-height:1.35}}
.rm{{display:grid;grid-template-columns:55px 1fr;gap:3px 10px;font-size:12px}}
.rm .k{{color:var(--t3);text-align:right}}.rm .v{{color:var(--t2);word-break:break-all}}
.rlbs{{padding:6px 20px;border-bottom:1px solid var(--brd);display:flex;flex-wrap:wrap;gap:4px;flex-shrink:0}}
.rlbs .rlb{{padding:2px 8px;background:var(--bg3);border:1px solid var(--brd);border-radius:4px;font-size:11px;color:var(--t2)}}
.rpj{{padding:10px 20px;border-bottom:1px solid var(--brd);display:flex;flex-wrap:wrap;gap:6px;flex-shrink:0}}
.rpj .pjit{{display:flex;align-items:center;gap:6px;padding:6px 12px;background:var(--bg2);border:1px solid var(--brd);border-radius:8px;color:var(--t);font-size:12px;transition:all .2s;text-decoration:none}}
.rpj a.pjit{{cursor:pointer}}
.rpj a.pjit:hover{{border-color:var(--ac);box-shadow:var(--glow);color:var(--ac)}}
.rpj span.pjit:hover{{border-color:var(--brd)}}
.rb{{flex:1;overflow-y:auto;padding:20px 24px}}
.rb pre{{color:var(--t2);font-size:13px;line-height:1.7;white-space:pre-wrap;word-wrap:break-word;font-family:'Segoe UI',system-ui,sans-serif}}
.rb .emp{{color:var(--t3);font-style:italic}}
.kh{{position:fixed;bottom:6px;left:8px;color:var(--t3);font-size:10px;opacity:.35}}
.foot{{position:fixed;bottom:6px;right:8px;color:var(--t3);font-size:10px;opacity:.35}}

/* THREAD */
.thb2{{background:#2A1F3E;color:#CE93D8;border-radius:3px;padding:1px 6px;font-size:10px;font-weight:600;cursor:pointer}}
body.light .thb2{{background:#F3E5F5;color:#8E24AA}}
.tv{{flex:1;overflow-y:auto;padding:12px 20px}}
.tm{{background:var(--bg2);border:1px solid var(--brd);border-radius:10px;margin-bottom:8px;overflow:hidden;transition:all .2s;box-shadow:var(--shadow);animation:fadeUp .3s backwards}}
.tm:hover{{box-shadow:var(--glow)}}
.tm.cur{{border-color:var(--ac)}}
.tmh{{display:flex;align-items:center;gap:10px;padding:10px 14px;cursor:pointer;transition:background .15s}}
.tmh:hover{{background:var(--bg3)}}
.tmh .tma{{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;flex-shrink:0}}
.tmh .tmi{{flex:1;min-width:0}}
.tmh .tmf{{font-size:12px;font-weight:600;color:var(--t)}}
.tmh .tmd{{font-size:11px;color:var(--t3);margin-left:auto;white-space:nowrap;font-variant-numeric:tabular-nums}}
.tmh .tms{{font-size:11px;color:var(--t3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.tmh .arr{{color:var(--t3);font-size:10px;transition:transform .15s;margin-left:6px}}
.tm.exp .tmh .arr{{transform:rotate(90deg)}}
.tmb{{display:none;padding:0 14px 12px 52px;border-top:1px solid var(--brd)}}
.tm.exp .tmb{{display:block}}
.tmb pre{{color:var(--t2);font-size:13px;line-height:1.6;white-space:pre-wrap;word-wrap:break-word;font-family:'Segoe UI',system-ui,sans-serif;margin-top:8px}}
.tmb .tmpj{{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px}}
.tmb .tmpji{{padding:3px 8px;background:var(--bg3);border:1px solid var(--brd);border-radius:4px;font-size:11px;color:var(--t2)}}

/* SELECTION */
.stb{{display:none;gap:8px;align-items:center;padding:6px 16px;background:#1A237E;border-bottom:1px solid #283593;flex-shrink:0}}
body.light .stb{{background:#E8EAF6;border-color:#C5CAE9}}
.stb.on{{display:flex}}
.stb .sc{{color:#90CAF9;font-size:13px;font-weight:600}}
body.light .stb .sc{{color:#1565C0}}
.stb button{{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);border-radius:6px;padding:4px 12px;color:#fff;font-size:12px;cursor:pointer;transition:background .15s}}
body.light .stb button{{background:var(--bg2);border-color:var(--brd);color:var(--t)}}
.stb button:hover{{background:rgba(255,255,255,.2)}}
.stb .sep{{flex:1}}
.stb .exp{{background:#2E7D32;border-color:#388E3C}}
.stb .exp:hover{{background:#388E3C}}
.stb .hid{{background:#B71C1C;border-color:#C62828}}
.stb .hid:hover{{background:#C62828}}
.mr .ck{{width:16px;height:16px;accent-color:var(--ac);flex-shrink:0;margin-top:2px;cursor:pointer}}
.mr.sel{{background:#1A237E20}}
body.light .mr.sel{{background:#E8EAF630}}
</style>
</head>
<body>
<div class="hdr">
  <h1 id="logo">&#9993; Gmail Archive</h1>
  <div class="stats">
    <span><b>{nb:,}</b> mails</span>
    <span><b>{total_pj:,}</b> PJ</span>
    <span><b>{len(all_labels)}</b> labels</span>
    <span><b>{date_min}-{date_max}</b></span>
  </div>
  <div class="hdr-r">
    <button class="cmdb" id="stB" title="Statistiques">&#128202;</button>
    <button class="cmdb" id="cmdB" title="Ctrl+K">&#8984; K</button>
    <button class="thb" id="thB" title="Theme">&#9788;</button>
  </div>
</div>
<div class="ctl">
  <div class="sbw"><input type="text" class="sb" id="sI" placeholder="Rechercher..."></div>
  <select id="cF"><option value="">&#128193; Categorie</option></select>
  <select id="yF"><option value="">&#128197; Annee</option></select>
  <select id="lF"><option value="">&#127991; Labels</option></select>
  <select id="fF"><option value="">&#128100; Expediteur</option></select>
  <select id="pF"><option value="">&#128206; PJ</option><option value="y">Avec PJ</option><option value="n">Sans PJ</option></select>
  <select id="dF"><option value="">&#128229; Boite</option><option value="inbox">Recus</option><option value="sent">Envoyes</option><option value="spam">Spam</option><option value="trash">Corbeille</option></select>
  <label class="tgl" id="bsL"><input type="checkbox" id="bS"> &#128196; corps</label>
  <span class="bld" id="bld"></span>
  <span class="cnt" id="cE"></span>
</div>
<div class="stb" id="stbar">
  <span class="sc" id="sCnt">0 selectionne(s)</span>
  <button onclick="selPage()">&#9745; Page</button>
  <button onclick="selAll()">&#9745; Tous (filtre)</button>
  <button onclick="selNone()">&#9746; Aucun</button>
  <span class="sep"></span>
  <button onclick="hideSelected()" class="hid">&#128683; Masquer</button>
  <button class="exp" onclick="exportSel()">&#128190; Exporter HTML</button>
</div>
<div class="dash-ov" id="dashOv">
<div class="dash" id="dash">
  <button class="dash-x" onclick="closeStats()">&times;</button>
  <div class="dash-t">&#128202; Ton archive Gmail<small>{nb:,} mails &middot; {date_min} a {date_max}</small></div>
  <div class="dash-s"><div><b>{nb:,}</b> mails</div><div><b>{total_pj:,}</b> pieces jointes</div><div><b>{len(all_labels)}</b> labels</div><div><b>{threads_multi:,}</b> conversations</div></div>
  <div class="dcs">{dash_cats}</div>
  <div class="dyr"><div class="dyr-t">Mails par annee</div>{dash_years}</div>
  <div class="dss"><div class="dss-t">Top expediteurs</div>{dash_snd}</div>
</div>
</div>
<div class="main" id="mainP">
  <div class="lp"><div class="ls" id="ls"></div><div class="pgn" id="pg"></div></div>
  <div class="rp" id="rp"><div class="re"><div style="font-size:48px;opacity:.3;margin-bottom:12px">&#9993;</div>Selectionne un mail<br><small style="color:var(--t3)">j/k naviguer &middot; / recherche &middot; Ctrl+K commandes &middot; Esc reset</small></div></div>
</div>
<div class="cpo" id="cpo"><div class="cpb"><input class="cpi" id="cpI" placeholder="&#128269; Rechercher label, expediteur, annee, categorie..."><div class="cpr" id="cpR"></div></div></div>
<div class="kh">j/k &middot; / recherche &middot; Ctrl+K commandes &middot; Esc reset</div>
<div class="foot">Genere {now} &middot; TakeoutReader</div>
<script src="mails.js"></script>
<script>
"use strict";
var B=null,BL=false;
var F=[].concat(D),pg=0,pp=100,si=-1;

// === THREAD MAP: tid → [indices in D] sorted by date asc ===
var TH={{}};
(function(){{
for(var i=0;i<D.length;i++){{
  var t=D[i].tid;
  if(!t)continue;
  if(!TH[t])TH[t]=[];
  TH[t].push(i);
}}
// Sort each thread by date ascending (oldest first)
for(var t in TH){{
  if(TH[t].length>1){{
    TH[t].sort(function(a,b){{return D[a].ds<D[b].ds?-1:D[a].ds>D[b].ds?1:0;}});
  }}
}}
}})();
function thLen(m){{var t=m.tid;return(t&&TH[t])?TH[t].length:1;}}

// Pre-index: chaque D[i] porte son index (O(1) au lieu de indexOf O(n))
for(var _i=0;_i<D.length;_i++)D[_i]._di=_i;
function gDi(m){{return(m&&m._di!==undefined)?m._di:-1;}}

// === SELECTION STATE ===
var sel={{}};  // D-index → true (selected)
var hidden={{}}; // D-index → true (hidden)
function updSelBar(){{
var n=Object.keys(sel).length;
sCnt.textContent=n+" selectionne"+(n>1?"s":"");
if(n>0)stbar.classList.add("on");else stbar.classList.remove("on");
}}
function tgSel(fi,ev){{
if(ev)ev.stopPropagation();
var m=F[fi];var di=gDi(m);if(di<0)return;
if(sel[di])delete sel[di];else sel[di]=true;
var row=document.querySelector("[data-i=\\""+fi+"\\"]");
if(row){{var cb=row.querySelector(".ck");if(cb)cb.checked=!!sel[di];row.classList.toggle("sel",!!sel[di]);}}
updSelBar();
}}
function selPage(){{
var s=pg*pp,en=Math.min(s+pp,F.length);
for(var j=s;j<en;j++){{var di=gDi(F[j]);if(di>=0)sel[di]=true;}}
rl();updSelBar();
}}
function selAll(){{
for(var j=0;j<F.length;j++){{var di=gDi(F[j]);if(di>=0)sel[di]=true;}}
rl();updSelBar();
}}
function selNone(){{sel={{}};rl();updSelBar();}}

function hideSelected(){{
var keys=Object.keys(sel);
for(var i=0;i<keys.length;i++)hidden[keys[i]]=true;
sel={{}};af();updSelBar();
}}
function restoreHidden(){{hidden={{}};af();}}

// Export selection as standalone HTML download
function exportSel(){{
var keys=Object.keys(sel);if(!keys.length)return;
var h="<!DOCTYPE html><html lang=\\"fr\\"><head><meta charset=\\"UTF-8\\"><title>Gmail Export - "+keys.length+" mails</title>"
+"<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:#0A0A0A;color:#E0E0E0;font-family:'Segoe UI',system-ui,sans-serif;padding:20px;max-width:900px;margin:0 auto}}"
+"h1{{font-size:20px;margin-bottom:20px;color:#fff}}"
+".m{{border:1px solid #333;border-radius:8px;margin-bottom:12px;overflow:hidden}}"
+".mh{{background:#111;padding:12px 16px;display:flex;justify-content:space-between;cursor:pointer}}"
+".mh:hover{{background:#1A1A2E}}"
+".mf{{font-weight:600;color:#E0E0E0}}.md{{color:#666;font-size:12px}}"
+".ms{{color:#AAA;font-size:13px;padding:4px 16px 8px}}"
+".mb{{display:none;padding:12px 16px;border-top:1px solid #333;color:#AAA;font-size:13px;white-space:pre-wrap;line-height:1.6}}"
+".m.exp .mb{{display:block}}.m.exp .mh{{border-bottom:1px solid #222}}"
+"</style></head><body>"
+"<h1>Gmail Export &mdash; "+keys.length+" mails</h1>";
keys.sort(function(a,b){{return D[b].ds<D[a].ds?-1:D[b].ds>D[a].ds?1:0;}});
for(var i=0;i<keys.length;i++){{
var di=parseInt(keys[i]);var m=D[di];
var body=(BL&&B&&di>=0)?B[di]:"";
h+="<div class=\\"m\\" onclick=\\"this.classList.toggle('exp')\\">"
+"<div class=\\"mh\\"><span class=\\"mf\\">"+esc(m.f)+" &mdash; "+esc(m.s)+"</span><span class=\\"md\\">"+esc(m.d)+"</span></div>"
+"<div class=\\"ms\\">A: "+esc(m.to)+"</div>"
+"<div class=\\"mb\\">"+esc(body)+"</div></div>";
}}
h+="</body></html>";
var blob=new Blob([h],{{type:"text/html;charset=utf-8"}});
var url=URL.createObjectURL(blob);
var a=document.createElement("a");
a.href=url;a.download="gmail_export_"+keys.length+"_mails.html";
document.body.appendChild(a);a.click();document.body.removeChild(a);
URL.revokeObjectURL(url);
}}
var ls=document.getElementById("ls"),pgD=document.getElementById("pg"),
rp=document.getElementById("rp"),sI=document.getElementById("sI"),
lF=document.getElementById("lF"),pF=document.getElementById("pF"),
yF=document.getElementById("yF"),fF=document.getElementById("fF"),
cF=document.getElementById("cF"),
dF=document.getElementById("dF"),
bS=document.getElementById("bS"),bsL=document.getElementById("bsL"),
bld=document.getElementById("bld"),
cE=document.getElementById("cE"),
thB=document.getElementById("thB"),cmdB=document.getElementById("cmdB"),
stB=document.getElementById("stB"),
stbar=document.getElementById("stbar"),sCnt=document.getElementById("sCnt"),
dashOv=document.getElementById("dashOv"),
mainP=document.getElementById("mainP"),
cpo=document.getElementById("cpo"),cpI=document.getElementById("cpI"),
cpR=document.getElementById("cpR");

// === LAZY LOAD BODIES ===
bsL.classList.add("dis");
bld.textContent="chargement corps...";
var bScript=document.createElement("script");
bScript.src="bodies.js";
bScript.onload=function(){{BL=true;bsL.classList.remove("dis");bld.textContent="corps charge";setTimeout(function(){{bld.textContent="";}},3000);}};
bScript.onerror=function(){{bld.textContent="corps indisponible";}};
document.body.appendChild(bScript);

var catC={{"Perso":"#4FC3F7","Achats":"#FFB74D","Banque":"#81C784","Newsletter":"#BA68C8","Notif":"#90A4AE","Social":"#F06292"}};
thB.addEventListener("click",function(){{document.body.classList.toggle("light");thB.innerHTML=document.body.classList.contains("light")?"&#9789;":"&#9788;";}});
function avH(s){{var h=0;for(var i=0;i<s.length;i++){{h=s.charCodeAt(i)+((h<<5)-h);}}return Math.abs(h)%360;}}
function avI(n){{if(!n)return"?";var p=n.trim().split(/\\s+/);if(p.length>=2)return(p[0][0]+p[1][0]).toUpperCase();return n.substring(0,Math.min(2,n.length)).toUpperCase();}}

// Dropdowns
var ccnt={{}};D.forEach(function(m){{ccnt[m.cat]=(ccnt[m.cat]||0)+1;}});
["Perso","Achats","Banque","Newsletter","Notif","Social"].forEach(function(c){{if(!ccnt[c])return;var o=document.createElement("option");o.value=c;o.textContent=c+" ("+ccnt[c]+")";cF.appendChild(o);}});
var lc={{}};D.forEach(function(m){{var arr=m.labels||[m.l];for(var i=0;i<arr.length;i++){{lc[arr[i]]=(lc[arr[i]]||0)+1;}}}});
Object.keys(lc).sort().forEach(function(l){{var o=document.createElement("option");o.value=l;o.textContent=l+" ("+lc[l]+")";lF.appendChild(o);}});
var yrs={{}};D.forEach(function(m){{var y=m.ds.substring(0,4);if(y!=="0000")yrs[y]=(yrs[y]||0)+1;}});
Object.keys(yrs).sort().reverse().forEach(function(y){{var o=document.createElement("option");o.value=y;o.textContent=y+" ("+yrs[y]+")";yF.appendChild(o);}});
var sndC={{}};D.forEach(function(m){{sndC[m.f]=(sndC[m.f]||0)+1;}});
var top30=Object.keys(sndC).sort(function(a,b){{return sndC[b]-sndC[a];}}).slice(0,30);
top30.forEach(function(s){{var o=document.createElement("option");o.value=s;o.textContent=s+" ("+sndC[s]+")";fF.appendChild(o);}});

function esc(s){{var d=document.createElement("div");d.textContent=s;return d.innerHTML;}}
function cpTxt(text,btn){{if(navigator.clipboard&&navigator.clipboard.writeText){{navigator.clipboard.writeText(text).then(function(){{cpOk(btn);}}).catch(function(){{cpFb(text,btn);}});}}else{{cpFb(text,btn);}}}}
function cpFb(text,btn){{var ta=document.createElement("textarea");ta.value=text;ta.style.cssText="position:fixed;left:-9999px";document.body.appendChild(ta);ta.select();try{{document.execCommand("copy");cpOk(btn);}}catch(e){{btn.textContent="Echec";}}document.body.removeChild(ta);}}
function cpOk(btn){{var orig=btn.getAttribute("data-label")||btn.textContent;btn.textContent="Copie !";setTimeout(function(){{btn.textContent=orig;}},1500);}}

// Stats modal open/close
function openStats(){{dashOv.classList.add("on");}}
function closeStats(){{dashOv.classList.remove("on");}}
stB.addEventListener("click",openStats);
dashOv.addEventListener("click",function(ev){{if(ev.target===dashOv)closeStats();}});
function dCat(c){{closeStats();cF.value=c;af();sI.focus();}}
function dYr(y){{closeStats();yF.value=y;af();sI.focus();}}
function dSnd(s){{closeStats();fF.value=s;af();sI.focus();}}

// Command palette
var cpSel=0,cpItems=[];
function buildPaletteItems(){{
cpItems=[];
cpItems.push({{t:"&#128202; Statistiques",k:"dashboard stats statistiques",fn:function(){{closePalette();openStats();}}}});
cpItems.push({{t:"&#128270; Reset filtres",k:"reset filtres tous browse",fn:function(){{closePalette();cF.value="";yF.value="";fF.value="";lF.value="";pF.value="";dF.value="";sI.value="";bS.checked=false;af();}}}});
["Perso","Achats","Banque","Newsletter","Notif","Social"].forEach(function(c){{if(!ccnt[c])return;cpItems.push({{t:"&#128193; "+c+" ("+ccnt[c]+")",k:"categorie "+c.toLowerCase(),fn:function(){{closePalette();cF.value=c;yF.value="";fF.value="";lF.value="";pF.value="";sI.value="";af();}}}});}});
Object.keys(yrs).sort().reverse().forEach(function(y){{cpItems.push({{t:"&#128197; "+y+" ("+yrs[y]+")",k:"annee "+y,fn:function(){{closePalette();yF.value=y;af();}}}});}});
top30.slice(0,15).forEach(function(s){{cpItems.push({{t:"&#128100; "+s+" ("+sndC[s]+")",k:"expediteur "+s.toLowerCase(),fn:function(){{closePalette();fF.value=s;af();}}}});}});
Object.keys(lc).sort().forEach(function(l){{cpItems.push({{t:"&#127991; "+l+" ("+lc[l]+")",k:"label "+l.toLowerCase(),fn:function(){{closePalette();lF.value=l;af();}}}});}});
cpItems.push({{t:"&#9728; Theme clair",k:"theme light clair",fn:function(){{closePalette();document.body.classList.add("light");thB.innerHTML="&#9789;";}}}});
cpItems.push({{t:"&#9790; Theme sombre",k:"theme dark sombre",fn:function(){{closePalette();document.body.classList.remove("light");thB.innerHTML="&#9788;";}}}});
cpItems.push({{t:"&#128206; Avec PJ uniquement",k:"pieces jointes attachments",fn:function(){{closePalette();pF.value="y";af();}}}});
cpItems.push({{t:"&#9850; Restaurer masques",k:"restaurer masques hidden",fn:function(){{closePalette();restoreHidden();}}}});
cpItems.push({{t:"&#128229; Mails recus",k:"recus inbox boite reception",fn:function(){{closePalette();dF.value="inbox";af();}}}});
cpItems.push({{t:"&#128228; Mails envoyes",k:"envoyes sent",fn:function(){{closePalette();dF.value="sent";af();}}}});
cpItems.push({{t:"&#128165; Voir spam",k:"spam junk",fn:function(){{closePalette();dF.value="spam";af();}}}});
cpItems.push({{t:"&#128465; Voir corbeille",k:"corbeille trash poubelle",fn:function(){{closePalette();dF.value="trash";af();}}}});
}}
buildPaletteItems();
function openPalette(){{cpo.classList.add("on");cpI.value="";cpSel=0;renderPalette("");cpI.focus();}}
function closePalette(){{cpo.classList.remove("on");cpI.blur();}}
function renderPalette(q){{
var fl=cpItems;
if(q){{var ws=q.toLowerCase().split(/\\s+/);fl=cpItems.filter(function(it){{for(var i=0;i<ws.length;i++)if(it.k.indexOf(ws[i])===-1)return false;return true;}});}}
if(cpSel>=fl.length)cpSel=Math.max(0,fl.length-1);
var h="";for(var i=0;i<Math.min(fl.length,12);i++){{var cls=i===cpSel?"cpri sel":"cpri";h+="<div class=\\""+cls+"\\" data-pi=\\""+i+"\\">"+fl[i].t+"</div>";}}
if(!fl.length)h="<div class=\\"cpri\\" style=\\"color:var(--t3)\\">Aucun resultat</div>";
cpR.innerHTML=h;
var els=cpR.querySelectorAll("[data-pi]");for(var i=0;i<els.length;i++){{(function(idx){{els[idx].addEventListener("click",function(){{
var f2=cpItems;if(cpI.value){{var ws2=cpI.value.toLowerCase().split(/\\s+/);f2=cpItems.filter(function(it){{for(var j=0;j<ws2.length;j++)if(it.k.indexOf(ws2[j])===-1)return false;return true;}});}}
if(f2[idx])f2[idx].fn();}});}})( i);}}
return fl;}}
cpI.addEventListener("input",function(){{cpSel=0;renderPalette(cpI.value);}});
cpI.addEventListener("keydown",function(ev){{
var q=cpI.value;var fl=cpItems;
if(q){{var ws=q.toLowerCase().split(/\\s+/);fl=cpItems.filter(function(it){{for(var i=0;i<ws.length;i++)if(it.k.indexOf(ws[i])===-1)return false;return true;}});}}
if(ev.key==="ArrowDown"){{ev.preventDefault();cpSel=Math.min(cpSel+1,Math.min(fl.length-1,11));renderPalette(q);}}
else if(ev.key==="ArrowUp"){{ev.preventDefault();cpSel=Math.max(cpSel-1,0);renderPalette(q);}}
else if(ev.key==="Enter"){{ev.preventDefault();if(fl[cpSel])fl[cpSel].fn();}}
else if(ev.key==="Escape"){{ev.preventDefault();closePalette();}}}});
cpo.addEventListener("click",function(ev){{if(ev.target===cpo)closePalette();}});
cmdB.addEventListener("click",openPalette);

// Filter
function af(){{
sel={{}};updSelBar();
var q=sI.value.toLowerCase().trim(),lb=lF.value,pj=pF.value,yr=yF.value,sn=fF.value,ct=cF.value,dr=dF.value,deep=bS.checked&&BL;
var ws=q?q.split(/\\s+/):[];
F=D.filter(function(m){{
var di=m._di;if(hidden[di])return false;
// Direction filter: inbox=hide spam+trash, sent/spam/trash=show only that
if(dr==="inbox"&&(m.spam||m.trash))return false;
if(dr==="sent"&&!m.sent)return false;
if(dr==="spam"&&!m.spam)return false;
if(dr==="trash"&&!m.trash)return false;
// Default (no filter): hide spam+trash
if(!dr&&(m.spam||m.trash))return false;
if(yr&&m.ds.substring(0,4)!==yr)return false;
if(ct&&m.cat!==ct)return false;
if(lb){{var arr=m.labels||[m.l];var found=false;for(var i=0;i<arr.length;i++){{if(arr[i]===lb){{found=true;break;}}}}if(!found)return false;}}
if(sn&&m.f!==sn)return false;
if(pj==="y"&&m.p===0)return false;
if(pj==="n"&&m.p>0)return false;
if(q){{
var labs=(m.labels||[m.l]).join(" ");
var h=(m.d+" "+m.f+" "+m.s+" "+labs+" "+(m.cat||"")).toLowerCase();
if(deep){{if(di>=0&&B&&B[di])h+=" "+B[di].toLowerCase();}}
for(var i=0;i<ws.length;i++)if(h.indexOf(ws[i])===-1)return false;}}
return true;}});
pg=0;si=-1;rl();}}

// Render list
function rl(){{
var s=pg*pp,en=Math.min(s+pp,F.length),sl=F.slice(s,en);
var h="";
for(var j=0;j<sl.length;j++){{
var m=sl[j],idx=s+j;
var di=gDi(m);var isSel=!!sel[di];
var cls=(idx===si?"mr act":"mr")+(isSel?" sel":"");
var chk=isSel?" checked":"";
var pjt=m.p>0?"<span class=\\"pt\\">"+m.p+" PJ</span>":"";
var thn=thLen(m);var tht=thn>1?"<span class=\\"thb2\\">"+thn+" msgs</span>":"";
var arr=m.labels||[m.l];var lbh="<span class=\\"lb\\">"+esc(arr[0])+"</span>";
if(arr.length>1)lbh+="<span class=\\"lb2\\">+"+String(arr.length-1)+"</span>";
var cc=catC[m.cat]||"#888";var cbt="<span class=\\"ct\\" style=\\"color:"+cc+";border-color:"+cc+"\\">"+esc(m.cat||"")+"</span>";
var hue=avH(m.f);var ini=avI(m.f);
h+="<div class=\\""+cls+"\\" data-i=\\""+idx+"\\" onclick=\\"sm("+idx+")\\">"
+"<input type=\\"checkbox\\" class=\\"ck\\""+chk+" onclick=\\"tgSel("+idx+",event)\\">"
+"<div class=\\"av\\" style=\\"background:hsl("+hue+",42%,55%)\\">"+esc(ini)+"</div>"
+"<div class=\\"mc\\">"
+"<div class=\\"top\\"><span class=\\"frm\\">"+esc(m.f)+"</span><span class=\\"dt\\">"+esc(m.d)+"</span></div>"
+"<div class=\\"su\\">"+esc(m.s)+"</div>"
+(m.sn?"<div class=\\"sn\\">"+esc(m.sn)+"</div>":"")
+"<div class=\\"mt\\">"+cbt+lbh+pjt+tht+"</div>"
+"</div></div>";}}
ls.innerHTML=h;
var hn=Object.keys(hidden).length;
var htxt=hn>0?" <span style=\\"color:var(--ac);cursor:pointer\\" onclick=\\"restoreHidden()\\">"+hn+" masque"+(hn>1?"s":"")+", restaurer</span>":"";
cE.innerHTML=F.length.toLocaleString()+" mail"+(F.length>1?"s":"")+htxt;
var tp=Math.ceil(F.length/pp);
pgD.innerHTML="<button onclick=\\"gp("+(pg-1)+")\\""+( pg<1?" disabled":"")+">&#8592;</button><span class=\\"pi\\">"+(pg+1)+"/"+Math.max(tp,1)+"</span><button onclick=\\"gp("+(pg+1)+")\\""+( pg>=tp-1?" disabled":"")+">&#8594;</button>";}}

function gp(p){{var tp=Math.ceil(F.length/pp);if(p<0||p>=tp)return;pg=p;si=-1;rl();ls.scrollTop=0;}}

// Show mail — thread-aware
function sm(i){{
si=i;
var rows=document.querySelectorAll(".mr");for(var r=0;r<rows.length;r++)rows[r].classList.toggle("act",parseInt(rows[r].dataset.i)===i);
var m=F[i];
var gIdx=m._di;
var tids=(m.tid&&TH[m.tid])?TH[m.tid]:[];
var isThread=tids.length>1;

if(!isThread){{
  // === SINGLE MAIL VIEW ===
  var cc=catC[m.cat]||"#888";
  var h="<div class=\\"rh\\"><div class=\\"rs\\">"+esc(m.s)+"</div><div class=\\"rm\\">"
  +"<span class=\\"k\\">De</span><span class=\\"v\\">"+esc(m.ff)+"</span>"
  +"<span class=\\"k\\">A</span><span class=\\"v\\">"+esc(m.to)+"</span>";
  if(m.cc)h+="<span class=\\"k\\">Cc</span><span class=\\"v\\">"+esc(m.cc)+"</span>";
  h+="<span class=\\"k\\">Date</span><span class=\\"v\\">"+esc(m.d)+"</span>"
  +"<span class=\\"k\\">Cat.</span><span class=\\"v\\" style=\\"color:"+cc+"\\">"+esc(m.cat||"")+"</span>"
  +"</div></div>";
  var arr=m.labels||[m.l];
  if(arr.length>0){{h+="<div class=\\"rlbs\\">";for(var g=0;g<arr.length;g++){{h+="<span class=\\"rlb\\">"+esc(arr[g])+"</span>";}}h+="</div>";}}
  if(m.pj&&m.pj.length>0){{h+="<div class=\\"rpj\\">";for(var p=0;p<m.pj.length;p++){{if(m.pjp&&m.pjp[p]){{h+="<a class=\\"pjit\\" href=\\""+esc(m.pjp[p])+"\\" target=\\"_blank\\">&#128206; "+esc(m.pj[p])+"</a>";}}else{{h+="<span class=\\"pjit\\">&#128206; "+esc(m.pj[p])+"</span>";}}}}h+="</div>";}}
  h+="<div class=\\"rb\\">";
  var body=(BL&&B&&gIdx>=0)?B[gIdx]:"";
  if(body){{h+="<pre>"+esc(body)+"</pre>";}}
  else if(!BL){{h+="<div class=\\"emp\\">Chargement du corps en cours...</div>";}}
  else{{h+="<div class=\\"emp\\">Aucun contenu texte extrait.</div>";}}
  h+="</div>";
  rp.innerHTML=h;
}} else {{
  // === THREAD VIEW (conversation) ===
  var h="<div class=\\"rh\\"><div class=\\"rs\\">"+esc(m.s)+"</div>"
  +"<div style=\\"font-size:12px;color:var(--t3);margin-top:4px\\">"+tids.length+" messages dans cette conversation</div></div>";
  h+="<div class=\\"tv\\">";
  for(var t=0;t<tids.length;t++){{
    var ti=tids[t];var tm=D[ti];
    var isCur=ti===gIdx;
    var cls2=isCur?"tm exp cur":"tm";
    var hue2=avH(tm.f);var ini2=avI(tm.f);
    h+="<div class=\\""+cls2+"\\" data-tm=\\""+t+"\\">"
    +"<div class=\\"tmh\\" onclick=\\"tgTm(this)\\">"
    +"<div class=\\"tma\\" style=\\"background:hsl("+hue2+",42%,55%)\\">"+esc(ini2)+"</div>"
    +"<div class=\\"tmi\\"><div class=\\"tmf\\">"+esc(tm.f)+"</div>"
    +"<div class=\\"tms\\">"+esc(tm.s)+"</div></div>"
    +"<span class=\\"tmd\\">"+esc(tm.d)+"</span>"
    +"<span class=\\"arr\\">&#9654;</span>"
    +"</div>";
    h+="<div class=\\"tmb\\">";
    if(tm.to)h+="<div style=\\"font-size:11px;color:var(--t3);margin-top:6px\\">A: "+esc(tm.to)+"</div>";
    if(tm.pj&&tm.pj.length>0){{
      h+="<div class=\\"tmpj\\">";
      for(var p2=0;p2<tm.pj.length;p2++){{if(tm.pjp&&tm.pjp[p2]){{h+="<a class=\\"tmpji\\" href=\\""+esc(tm.pjp[p2])+"\\" target=\\"_blank\\" style=\\"text-decoration:none;color:var(--t2)\\">&#128206; "+esc(tm.pj[p2])+"</a>";}}else{{h+="<span class=\\"tmpji\\">&#128206; "+esc(tm.pj[p2])+"</span>";}}}}
      h+="</div>";
    }}
    var tbody=(BL&&B&&ti>=0)?B[ti]:"";
    if(tbody){{h+="<pre>"+esc(tbody)+"</pre>";}}
    else if(!BL){{h+="<div class=\\"emp\\">Chargement...</div>";}}
    else{{h+="<div class=\\"emp\\">Aucun contenu texte.</div>";}}
    h+="</div></div>";
  }}
  h+="</div>";
  rp.innerHTML=h;
  // Scroll to current message
  var curEl=rp.querySelector(".tm.cur");
  if(curEl)setTimeout(function(){{curEl.scrollIntoView({{block:"nearest",behavior:"smooth"}});}},50);
}}
}}
// Toggle thread message expand/collapse
function tgTm(el){{
var card=el.parentElement;
card.classList.toggle("exp");
}}

// Keyboard
document.addEventListener("keydown",function(ev){{
if((ev.ctrlKey||ev.metaKey)&&ev.key==="k"){{ev.preventDefault();openPalette();return;}}
if(cpo.classList.contains("on"))return;
if(dashOv.classList.contains("on")){{if(ev.key==="Escape")closeStats();return;}}
if(ev.target.tagName==="INPUT"||ev.target.tagName==="SELECT"){{if(ev.key==="Escape"){{sI.blur();sI.value="";af();}}return;}}
if(ev.key==="ArrowDown"||ev.key==="j"){{ev.preventDefault();if(si<0){{sm(0);}}else if(si<F.length-1){{var np=Math.floor((si+1)/pp);if(np!==pg){{pg=np;rl();}}sm(si+1);}}var el=document.querySelector(".mr.act");if(el)el.scrollIntoView({{block:"nearest"}});}}
else if(ev.key==="ArrowUp"||ev.key==="k"){{ev.preventDefault();if(si>0){{var np2=Math.floor((si-1)/pp);if(np2!==pg){{pg=np2;rl();}}sm(si-1);}}var el2=document.querySelector(".mr.act");if(el2)el2.scrollIntoView({{block:"nearest"}});}}
else if(ev.key==="Escape"){{sI.value="";lF.value="";yF.value="";fF.value="";pF.value="";cF.value="";dF.value="";bS.checked=false;af();}}
else if(ev.key==="/"){{ev.preventDefault();sI.focus();sI.select();}}}});

var st;sI.addEventListener("input",function(){{clearTimeout(st);st=setTimeout(af,200);}});
lF.addEventListener("change",af);pF.addEventListener("change",af);
yF.addEventListener("change",af);fF.addEventListener("change",af);
cF.addEventListener("change",af);dF.addEventListener("change",af);bS.addEventListener("change",af);
af();
</script>
</body>
</html>'''

    index_path = os.path.join(output_dir, "index.html")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_html)

    index_size = os.path.getsize(index_path) / (1024 * 1024)
    print(f"    index.html: {index_size:.2f} Mo", flush=True)

    total_size = mails_size + bodies_size + index_size
    return total_size, index_path
