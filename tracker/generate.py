"""Static site generator for the Parkinson's & Alzheimer's trial tracker.

Reads data/trials_latest.csv, data/events.csv, data/meta.json (written by tracker.update) and writes a static site:
  index.html        this week's changes, upcoming readouts, new registrations, headline counts
  explore.html      filterable table of every in-scope trial (client-side, data/trials.json)
  changes.html      detected changes by date + registrations updated in the last 14 days
  readouts.html     primary-completion calendar (past 90 days to next 12 months)
  mechanisms.html   active trials by mechanism, disease and phase
  trials/NCT*.html  one page per in-scope trial (details, eligibility signals, change history, same-mechanism trials)
  about.html        methods, classification accuracy, disclaimer, data source
  feed.xml, sitemap.xml, robots.txt, data/*.csv, data/trials.json
Usage: python -m tracker.generate DATA_DIR OUT_DIR   (env SITE_URL, REPO_URL optional)
"""
import os, sys, json, shutil, pathlib, datetime as dt
from html import escape
import pandas as pd
from moduleA import rules
from .labels import MECH_EN, GROUP_EN, DISEASE_EN, STATUS_EN, PHASE_EN, CHANGE_EN

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
REPO_URL = os.environ.get("REPO_URL", "").rstrip("/")
SITE_NAME = "NeuroTrials Watch"
TAGLINE = "Parkinson's and Alzheimer's drug trials, updated daily from ClinicalTrials.gov"
ASSETS = pathlib.Path(__file__).with_name("assets")


def e(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else escape(str(x))


def pdate(s):
    """ClinicalTrials.gov dates are YYYY-MM or YYYY-MM-DD. Month precision maps to the LAST day of the month, so a trial
    registered as due "2026-10" still counts as due (not past) during October."""
    if not isinstance(s, str) or not s:
        return None
    try:
        if len(s) == 10:
            return dt.date.fromisoformat(s)
        first = dt.date.fromisoformat(s + "-01")
        return (first.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    except ValueError:
        return None


def phase(p):
    return PHASE_EN.get(str(p), f"Phase {p}")


def num(x):
    return "" if pd.isna(x) else f"{int(x):,}"


def page(title, body, rel="", desc=TAGLINE, canonical=""):
    nav = [("index.html", "This week"), ("explore.html", "Explore"), ("readouts.html", "Completion calendar"),
           ("mechanisms.html", "Mechanisms"), ("changes.html", "All changes"), ("about.html", "About")]
    links = "".join(f'<a href="{rel}{h}">{t}</a>' for h, t in nav)
    canon = f'<link rel="canonical" href="{SITE_URL}/{canonical}">' if SITE_URL and canonical else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} · {SITE_NAME}</title><meta name="description" content="{e(desc)}">{canon}
<link rel="stylesheet" href="{rel}assets/style.css"><link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{rel}feed.xml">
</head><body><header class="top"><div class="wrap"><a class="brand" href="{rel}index.html">{SITE_NAME}</a><nav>{links}</nav></div></header>
<main class="wrap">{body}</main>
<footer class="wrap foot">Data: <a href="https://clinicaltrials.gov">ClinicalTrials.gov</a> (U.S. National Library of Medicine), retrieved daily.
Mechanism labels are assigned automatically and can be wrong (see <a href="{rel}about.html">About</a>). Not medical advice.
<a href="{rel}feed.xml">RSS</a> · <a href="{rel}data/trials.csv">Download data</a>{f' · <a href="{REPO_URL}">Source code</a>' if REPO_URL else ''}</footer>
<script src="{rel}assets/app.js" defer></script></body></html>"""


def badge(text, cls=""):
    return f'<span class="badge {cls}">{e(text)}</span>'


def trial_row(r, rel="", extra=""):
    grp = rules.MECH_GROUP.get(r.mech_primary, "UNK")
    return (f'<li><a href="{rel}trials/{r.nct}.html">{e(r.title)}</a>'
            f'<div class="meta">{r.nct} · {DISEASE_EN.get(r.disease, r.disease)} · {phase(r.phase)} · '
            f'{badge(MECH_EN.get(r.mech_primary, r.mech_primary), grp.lower())} · {e(r.sponsor)}{extra}</div></li>')


def main(data_dir, out_dir):
    data, out = pathlib.Path(data_dir), pathlib.Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "trials").mkdir(parents=True)
    (out / "data").mkdir()
    shutil.copytree(ASSETS, out / "assets")
    t = pd.read_csv(data / "trials_latest.csv")
    ev = pd.read_csv(data / "events.csv")
    meta = json.loads((data / "meta.json").read_text())
    today = dt.date.fromisoformat(meta["snapshot_date"])
    t["group"] = t.mech_primary.map(rules.MECH_GROUP).fillna("UNK")
    t["pc_date"] = t.primary_completion.map(pdate)
    t["fp_date"] = t.first_posted.map(pdate)
    t["lu_date"] = t.last_update.map(pdate)
    s = t[t.in_scope.astype(bool)].copy()
    act = s[s.active.astype(bool)]
    ev = ev[ev.nct.isin(t.nct) | (ev.kind == "removed")]  # 범위에서 빠진 임상의 '범위 변화'도 남긴다(페이지 링크는 범위 안일 때만)
    by_nct = s.set_index("nct")

    # ---------- data downloads ----------
    s.drop(columns=["pc_date", "fp_date", "lu_date"]).to_csv(out / "data" / "trials.csv", index=False)
    ev.to_csv(out / "data" / "events.csv", index=False)
    js = [{"n": r.nct, "t": r.title, "d": r.disease, "p": phase(r.phase), "s": STATUS_EN.get(r.status, r.status), "a": bool(r.active),
           "m": MECH_EN.get(r.mech_primary, r.mech_primary), "g": GROUP_EN.get(r.group, r.group), "sp": r.sponsor if isinstance(r.sponsor, str) else "",
           "e": None if pd.isna(r.enrollment) else int(r.enrollment), "st": r.start if isinstance(r.start, str) else "",
           "pc": r.primary_completion if isinstance(r.primary_completion, str) else "", "r": bool(r.has_results)} for r in s.itertuples()]
    (out / "data" / "trials.json").write_text(json.dumps(js, separators=(",", ":")))

    # ---------- shared lists ----------
    week = ev[pd.to_datetime(ev.date).dt.date > today - dt.timedelta(days=7)]
    up = act[(act.pc_date >= today) & (act.pc_date <= today + dt.timedelta(days=90))].sort_values("pc_date")
    new30 = s[s.fp_date >= today - dt.timedelta(days=30)].sort_values("fp_date", ascending=False)
    upd14 = s[s.lu_date >= today - dt.timedelta(days=14)].sort_values("lu_date", ascending=False)

    def ev_item(x, rel=""):
        k = CHANGE_EN.get(x.kind, x.kind)
        if x.kind in ("status",):
            ch = f"{STATUS_EN.get(x.before, x.before)} → {STATUS_EN.get(x.after, x.after)}"
        elif x.kind == "mech_primary":
            ch = f"{MECH_EN.get(x.before, x.before)} → {MECH_EN.get(x.after, x.after)}"
        elif x.kind == "phase":
            ch = f"{phase(x.before)} → {phase(x.after)}"
        elif x.kind == "new":
            ch = STATUS_EN.get(x.after, x.after)
        elif x.kind == "results":
            ch = "results now on ClinicalTrials.gov"
        elif x.kind == "scope":
            ch = "now in scope" if str(x.after) in ("True", "1", "1.0") else "no longer in scope"
        elif x.kind == "enrollment":
            f = lambda v: f"{int(float(v)):,}" if str(v) not in ("", "nan") else "—"
            ch = f"{f(x.before)} → {f(x.after)}"
        else:
            ch = f"{e(x.before)} → {e(x.after)}"
        link = f'<a href="{rel}trials/{x.nct}.html">{e(x.title)}</a>' if x.nct in by_nct.index else e(x.title)
        return f'<li>{badge(k, "chg")} {link}<div class="meta">{x.nct} · {DISEASE_EN.get(x.disease, x.disease)} · {e(ch)} · {x.date}</div></li>'

    # ---------- index ----------
    def tile(label, value, sub=""):
        return f'<div class="tile"><div class="v">{value}</div><div class="l">{label}</div><div class="s">{sub}</div></div>'
    pd_dmt = int(((act.disease.str.contains("PD")) & (act.group == "DMT")).sum())
    ad_dmt = int(((act.disease.str.contains("AD")) & (act.group == "DMT")).sum())
    tiles = (tile("Active disease-modifying trials · Parkinson's", pd_dmt, "trials listing both diseases count in each") + tile("Active disease-modifying trials · Alzheimer's", ad_dmt, "mechanism labels are automated")
             + tile("Primary completions due in the next 90 days", len(up)) + tile("New registrations, last 30 days", len(new30)))
    week_html = ("<ul class='list'>" + "".join(ev_item(x) for x in week.sort_values("date", ascending=False).itertuples()) + "</ul>") if len(week) else \
        "<p class='muted'>No tracked field changed in the last 7 days. Registrations updated recently are listed below.</p>"
    body = f"""<section class="hero"><h1>{SITE_NAME}</h1><p>{TAGLINE}. Interventional drug, biologic and gene/cell trials from early phase 1 to phase 2/3, selected and
classified by mechanism. Last update: <b>{today:%B %d, %Y}</b>.</p></section>
<section class="tiles">{tiles}</section>
<section><h2>This week</h2>{week_html}</section>
<section><h2>Primary completions due in the next 90 days</h2><ul class="list">{''.join(trial_row(r, extra=f' · due {e(r.primary_completion)}') for r in up.head(15).itertuples())}</ul>
<p><a href="readouts.html">Full primary completion calendar →</a></p></section>
<section><h2>Newly registered (last 30 days)</h2><ul class="list">{''.join(trial_row(r, extra=f' · posted {e(r.first_posted)}') for r in new30.head(15).itertuples()) or "<li class='muted'>None</li>"}</ul></section>
<section><h2>Registrations updated in the last 14 days</h2><ul class="list">{''.join(trial_row(r, extra=f' · updated {e(r.last_update)}') for r in upd14.head(15).itertuples())}</ul>
<p><a href="changes.html">All changes →</a></p></section>
<section class="cta"><p>Follow along: <a href="feed.xml">RSS feed</a> · <a href="data/trials.csv">download the full table</a>.</p></section>"""
    (out / "index.html").write_text(page("This week", body, canonical="index.html"))

    # ---------- explore ----------
    opts = lambda vals: "".join(f"<option>{e(v)}</option>" for v in vals)
    body = f"""<h1>Explore trials</h1><p class="muted">{len(s):,} trials in scope ({len(act):,} active). Filter and sort; click a title for details.</p>
<div class="filters" id="filters">
<input id="q" type="search" placeholder="Search title, sponsor, NCT…">
<select id="fd"><option value="">All diseases</option><option value="PD">Parkinson's</option><option value="AD">Alzheimer's</option></select>
<select id="fg"><option value="">All classes</option>{opts(GROUP_EN[g] for g in ["DMT", "SYM", "UNK"])}</select>
<select id="fm"><option value="">All mechanisms</option>{opts(sorted({MECH_EN.get(m, m) for m in s.mech_primary}))}</select>
<select id="fp"><option value="">All phases</option>{opts(phase(p) for p in ["0/1 (초기 1상)", "1", "1/2", "2", "2/3"])}</select>
<label class="chk"><input id="fa" type="checkbox" checked> Active only</label></div>
<p id="count" class="muted"></p><div class="tablewrap"><table id="tbl"><thead><tr>
<th data-k="t">Trial</th><th data-k="d">Disease</th><th data-k="p">Phase</th><th data-k="m">Mechanism</th><th data-k="s">Status</th><th data-k="e">N</th><th data-k="pc">Primary completion</th></tr></thead><tbody></tbody></table></div>"""
    (out / "explore.html").write_text(page("Explore trials", body, canonical="explore.html"))

    # ---------- changes ----------
    parts = []
    for d, g in ev.sort_values("date", ascending=False).groupby("date", sort=False):
        parts.append(f"<h3>{d}</h3><ul class='list'>{''.join(ev_item(x) for x in g.itertuples())}</ul>")
    body = f"""<h1>All detected changes</h1><p class="muted">For trials in scope, each daily snapshot is compared with the previous one:
new registrations, status, phase, mechanism label, enrollment, primary completion date, posted results. A change is dated when it was first detected,
which can be a day or more after the sponsor's update. Mechanism re-labels caused by changes to this site's own rules are not logged.
Tracking started {ev.date.min() if len(ev) else meta['snapshot_date']}.</p>
{''.join(parts) or "<p class='muted'>No changes detected yet.</p>"}
<h2>Registrations updated in the last 14 days</h2><ul class="list">{''.join(trial_row(r, extra=f' · updated {e(r.last_update)}') for r in upd14.itertuples())}</ul>"""
    (out / "changes.html").write_text(page("All changes", body, canonical="changes.html"))

    # ---------- readouts ----------
    win = s[(s.pc_date >= today - dt.timedelta(days=90)) & (s.pc_date <= today + dt.timedelta(days=365))
            & (s.active.astype(bool) | s.status.eq("COMPLETED"))].sort_values("pc_date")
    parts = []
    for m, g in win.groupby(win.pc_date.map(lambda x: x.strftime("%Y-%m")), sort=True):
        label = dt.date.fromisoformat(m + "-01").strftime("%B %Y")
        items = "".join(trial_row(r, extra=(" · " + badge("results posted", "ok") if r.has_results else "") + f" · {STATUS_EN.get(r.status, r.status)}")
                        for r in g.itertuples())
        parts.append(f"<h3>{label} <span class='muted'>({len(g)})</span></h3><ul class='list'>{items}</ul>")
    overdue = act[act.pc_date < today - dt.timedelta(days=365)].sort_values("pc_date")
    od = "".join(trial_row(r, extra=f" · primary completion {e(r.primary_completion)} · {STATUS_EN.get(r.status, r.status)}") for r in overdue.itertuples())
    body = f"""<h1>Primary completion calendar</h1><p class="muted">Active or completed trials whose primary completion date falls between {today - dt.timedelta(days=90):%b %d, %Y}
and {today + dt.timedelta(days=365):%b %d, %Y}, as registered by the sponsor. Primary completion is when the last participant is assessed for the
primary outcome; public results usually follow later, and dates often slip.</p>{''.join(parts)}
<h2 id="overdue">Still listed as active more than a year after primary completion <span class='muted'>({len(overdue)})</span></h2>
<p class="muted">Registrations whose primary completion date passed over a year ago and whose status is still recruiting, not yet recruiting or active.
Possible reasons include an outdated record, a delayed trial, or legitimate follow-up or extension periods after the primary outcome (common for
"active, not recruiting"). Check the registry record before drawing conclusions.</p><ul class="list">{od}</ul>"""
    (out / "readouts.html").write_text(page("Primary completion calendar", body, canonical="readouts.html"))

    # ---------- mechanisms ----------
    rows = []
    for code in [c for c in MECH_EN if c not in ("DX",)]:
        g = act[act.mech_primary == code]
        if not len(g):
            continue
        cnt = lambda dis: int(g.disease.str.contains(dis).sum())
        ph = g.phase.astype(str).value_counts()
        rows.append((code, len(g), cnt("PD"), cnt("AD"), int(ph.get("1", 0) + ph.get("0/1 (초기 1상)", 0)), int(ph.get("1/2", 0) + ph.get("2", 0)), int(ph.get("2/3", 0))))
    rows.sort(key=lambda x: -x[1])
    trs = "".join(f"<tr><td><a href='#m-{c}'>{MECH_EN[c]}</a></td><td>{GROUP_EN[rules.MECH_GROUP[c]]}</td><td>{n}</td><td>{p}</td><td>{a}</td><td>{p1}</td><td>{p2}</td><td>{p3}</td></tr>"
                  for c, n, p, a, p1, p2, p3 in rows)
    lists = "".join(f"<h3 id='m-{c}'>{MECH_EN[c]} <span class='muted'>({n})</span></h3><ul class='list'>"
                    + "".join(trial_row(r) for r in act[act.mech_primary == c].sort_values("phase", ascending=False).itertuples()) + "</ul>"
                    for c, n, *_ in rows)
    body = f"""<h1>Active trials by mechanism</h1><p class="muted">{len(act):,} active trials (recruiting, not yet recruiting, enrolling by invitation,
or active and not recruiting). A trial listing both diseases counts under each.</p>
<div class="tablewrap"><table><thead><tr><th>Mechanism</th><th>Class</th><th>Active</th><th>PD</th><th>AD</th><th>Ph 1</th><th>Ph 1/2–2</th><th>Ph 2/3</th></tr></thead>
<tbody>{trs}</tbody></table></div>{lists}"""
    (out / "mechanisms.html").write_text(page("Mechanisms", body, canonical="mechanisms.html"))

    # ---------- trial pages ----------
    elig_fields = [("hy_max", "Max Hoehn & Yahr stage"), ("dur_max_y", "Max years since diagnosis"), ("untreated", "Requires untreated (de novo) PD"),
                   ("dat_req", "Requires abnormal DaT scan"), ("saa_req", "Requires α-synuclein seed amplification assay"), ("lrrk2", "LRRK2 carriers"),
                   ("gba", "GBA carriers"), ("mmse_lo", "MMSE minimum"), ("mmse_hi", "MMSE maximum"), ("cdr", "CDR"), ("amyloid_req", "Requires amyloid biomarker"),
                   ("tau_pet_req", "Requires tau PET"), ("ad_stages", "AD stages accepted")]
    hist = {n: g for n, g in ev.groupby("nct")}
    urls = ["index.html", "explore.html", "readouts.html", "mechanisms.html", "changes.html", "about.html"]
    for r in s.itertuples():
        grp = r.group
        el = "".join(f"<tr><th>{lab}</th><td>{e(getattr(r, f))}</td></tr>" for f, lab in elig_fields
                     if not pd.isna(getattr(r, f, None)) and getattr(r, f) not in (False, "False", ""))
        h = hist.get(r.nct)
        hh = "<ul class='list'>" + "".join(ev_item(x, "../") for x in h.sort_values("date", ascending=False).itertuples()) + "</ul>" if h is not None else \
            "<p class='muted'>No tracked changes since tracking began.</p>"
        same = act[(act.mech_primary == r.mech_primary) & (act.nct != r.nct)].head(8) if r.mech_primary != "OTHER" else act.iloc[0:0]
        mechs = ", ".join(MECH_EN.get(m, m) for m in str(r.mechs).split(";") if m)
        report = f' · <a href="{REPO_URL}/issues/new?title=Classification%20issue%20{r.nct}">Report a classification error</a>' if REPO_URL else ""
        body = f"""<p class="crumb"><a href="../explore.html">Explore</a> › {r.nct}</p><h1>{e(r.title)}</h1>
<p>{badge(DISEASE_EN.get(r.disease, r.disease))} {badge(phase(r.phase))} {badge(STATUS_EN.get(r.status, r.status))} {badge(GROUP_EN.get(grp, grp), grp.lower())}
{badge('Results posted', 'ok') if r.has_results else ''}</p>
<div class="grid2"><table class="kv">
<tr><th>Mechanism (primary)</th><td>{MECH_EN.get(r.mech_primary, r.mech_primary)}</td></tr><tr><th>All mechanisms</th><td>{e(mechs)}</td></tr>
<tr><th>Interventions</th><td>{e(r.interventions)}</td></tr><tr><th>Sponsor</th><td>{e(r.sponsor)}</td></tr>
<tr><th>Collaborators</th><td>{e(r.collaborators)}</td></tr><tr><th>Enrollment</th><td>{num(r.enrollment)}</td></tr>
<tr><th>Start</th><td>{e(r.start)}</td></tr><tr><th>Primary completion</th><td>{e(r.primary_completion)}</td></tr>
<tr><th>First posted</th><td>{e(r.first_posted)}</td></tr><tr><th>Last update</th><td>{e(r.last_update)}</td></tr>
<tr><th>Sites</th><td>{num(r.n_sites) or '—'}{(' · ' + e(r.countries.replace(';', ', '))) if isinstance(r.countries, str) and r.countries else ''}</td></tr></table>
<div><h2>Eligibility signals</h2>{'<table class="kv">' + el + '</table>' if el else "<p class='muted'>None extracted.</p>"}
<p class="muted small">Extracted automatically from the eligibility text; check the registry record.</p></div></div>
<p><a class="button" href="https://clinicaltrials.gov/study/{r.nct}">View on ClinicalTrials.gov</a>{report}</p>
<h2>Change history</h2>{hh}
{('<h2>Other active trials with the same mechanism</h2><ul class="list">' + ''.join(trial_row(x, '../') for x in same.itertuples()) + '</ul>') if len(same) else ''}"""
        (out / "trials" / f"{r.nct}.html").write_text(page(f"{r.nct}: {r.title}"[:120], body, rel="../",
                                                           desc=f"{r.nct} — {DISEASE_EN.get(r.disease, r.disease)} {phase(r.phase)} trial, {MECH_EN.get(r.mech_primary, r.mech_primary)}. Status, eligibility and change history.",
                                                           canonical=f"trials/{r.nct}.html"))
        urls.append(f"trials/{r.nct}.html")

    # ---------- about ----------
    body = f"""<h1>About</h1>
<p>{SITE_NAME} tracks interventional phase 1 to phase 2/3 trials registered on ClinicalTrials.gov for Parkinson's disease and Alzheimer's disease
that test a drug, biologic, gene or cell therapy. It is rebuilt every day from the public ClinicalTrials.gov API (v2).</p>
<h2>What is in scope</h2><ul><li>Condition lists Parkinson's disease (not atypical parkinsonism alone) or Alzheimer's disease.</li>
<li>Experimental arm includes a drug, biological, genetic or combination product. Imaging tracers and contrast agents do not count; diagnostic, screening and health-services studies are excluded.</li>
<li>Phases: early phase 1, 1, 1/2, 2, 2/3.</li></ul>
<h2>Mechanism classification</h2><p>Each trial gets a primary mechanism from a rule dictionary (drug names and target words, searched in intervention names, then descriptions and titles, then summaries)
and a class: disease-modifying, symptomatic, or unclassified. Accuracy was measured against blinded manual reading of 40 randomly sampled active trials that had not been
used to write the rules (rules version 2.5): class 82.5% (95% CI 68.0–91.3%), primary mechanism 75.0% (59.8–85.8%). Labels assigned as disease-modifying or symptomatic
were all correct in that sample; errors concentrated in "unclassified". The current rules (2.8) later fixed some of those errors, so re-scoring the same sample
(87.5% and 80.0%) is optimistic and is not used as the headline figure. Among 169 active trials the rules (version 2.4) excluded, 7 (4.1%, 2.0–8.3%) should have been included;
6 were fixed. Treat labels as a starting point and check the registry record.</p>
<h2>Changes</h2><p>For trials in scope, each day's table is compared with the previous day's. Changes in status, phase, mechanism label, enrollment,
primary completion date, newly posted results, and new or removed registrations are logged and dated when first detected. When this site's
classification rules are updated, the resulting re-labels are not logged as changes. Registered dates are set by sponsors and often change.</p>
<h2>Use and citation</h2><p>Data are derived from ClinicalTrials.gov. The derived table is free to reuse with attribution. Not medical advice; for trial participation,
contact the study team listed on ClinicalTrials.gov.</p>
<p class="muted">Snapshot {meta['snapshot_date']} · {meta['n_in_scope']:,} trials in scope · {meta['n_active_in_scope']:,} active · rules {meta['rules']}</p>"""
    (out / "about.html").write_text(page("About", body, canonical="about.html"))

    # ---------- feed, sitemap, robots ----------
    def rfc822(d):
        return dt.datetime.combine(dt.date.fromisoformat(d), dt.time(12)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for x in ev.sort_values("date", ascending=False).head(200).itertuples():
        link = f"{SITE_URL}/trials/{x.nct}.html" if SITE_URL else f"trials/{x.nct}.html"
        items.append(f"<item><title>{e(CHANGE_EN.get(x.kind, x.kind))}: {e(x.title)}</title><link>{link}</link>"
                     f"<guid isPermaLink=\"false\">{x.nct}-{x.kind}-{x.date}</guid><pubDate>{rfc822(x.date)}</pubDate>"
                     f"<description>{e(x.nct)} · {e(x.before)} → {e(x.after)}</description></item>")
    (out / "feed.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE_NAME}</title>
<link>{SITE_URL or ''}/</link><description>{TAGLINE}</description><lastBuildDate>{rfc822(meta['snapshot_date'])}</lastBuildDate>{''.join(items)}</channel></rss>""")
    if SITE_URL:
        (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                         + "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{meta['snapshot_date']}</lastmod></url>" for u in urls) + "</urlset>")
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    (out / ".nojekyll").write_text("")
    print(f"  site: {len(urls)} pages → {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
