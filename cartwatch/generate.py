"""Static site generator. Usage: python -m tracker.generate DATA_DIR OUT_DIR
Environment: SITE_URL (absolute base, for canonical links, sitemap, feed), REPO_URL (source link and error reports)."""
import os, re, sys, json, shutil, pathlib, hashlib, datetime as dt
import pandas as pd
from . import dashboard
from .common import e, clean, pdate, show_date, months_between, num, short_title
from .labels import DISEASE_LABEL, STATUS_EN, PHASE_EN, CHANGE_EN, MODALITIES, PLATFORMS
from .classify import RULES_VERSION, DISEASES

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
REPO_URL = os.environ.get("REPO_URL", "").rstrip("/")
SITE_NAME = "Autoimmune CAR-T Watch"
TAGLINE = "CAR-T, CAR-NK and T-cell engager trials in autoimmune disease, updated daily from ClinicalTrials.gov"
ASSETS = pathlib.Path(__file__).with_name("assets")
ASSET_V = hashlib.md5(b"".join((ASSETS / f).read_bytes() for f in ("style.css", "app.js"))).hexdigest()[:8]
STAMP = ""
NAV = [("index.html", "This week"), ("dashboard.html", "Dashboard"), ("explore.html", "Explore"), ("readouts.html", "Completion calendar"),
       ("diseases.html", "By disease"), ("changes.html", "All changes"), ("about.html", "About")]


def phase(p):
    return PHASE_EN.get("" if p is None or (isinstance(p, float) and pd.isna(p)) else str(p), f"Phase {p}")


def badge(text, cls=""):
    return f'<span class="badge {cls}">{e(text)}</span>'


def page(title, body, rel="", desc=TAGLINE, canonical="", jsonld=None, og_type="website"):
    cur = canonical or "index.html"
    links = "".join(f'<a href="{rel}{h}"{" aria-current=\"page\"" if h == cur else ""}>{t}</a>' for h, t in NAV)
    url = f"{SITE_URL}/{canonical}" if SITE_URL else ""
    og = (f'<meta property="og:site_name" content="{SITE_NAME}"><meta property="og:type" content="{og_type}">'
          f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">' + (f'<meta property="og:url" content="{url}">' if url else "")
          + f'<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}">')
    ld = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">{f'<link rel="canonical" href="{url}">' if url else ''}{og}{ld}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap">
<meta name="theme-color" content="#f6f7f9" media="(prefers-color-scheme: light)"><meta name="theme-color" content="#0c1015" media="(prefers-color-scheme: dark)">
<link rel="stylesheet" href="{rel}assets/style.css?v={ASSET_V}"><link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{rel}feed.xml">
</head><body><header class="top"><div class="wrap"><a class="brand" href="{rel}index.html"><svg class="mark" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><rect width="24" height="24" rx="7" fill="currentColor"/><circle cx="12" cy="12" r="4.2" fill="none" stroke="var(--panel)" stroke-width="2"/><path d="M12 3.5v3M12 17.5v3M3.5 12h3M17.5 12h3M6 6l2.1 2.1M15.9 15.9 18 18M18 6l-2.1 2.1M8.1 15.9 6 18" stroke="var(--panel)" stroke-width="1.8" stroke-linecap="round"/></svg>{SITE_NAME}</a><nav>{links}</nav><a class="btn sm ghost hdr" href="{rel}feed.xml">Subscribe</a></div></header>
<main class="wrap">{body}</main>
<footer class="foot"><div class="wrap"><div class="fgrid">
<div class="fbrand"><span class="brand">{SITE_NAME}</span><p>{TAGLINE}. Independent, open data, no login.</p></div>
<div><h4>Product</h4><a href="{rel}dashboard.html">Dashboard</a><a href="{rel}explore.html">Explore trials</a><a href="{rel}readouts.html">Completion calendar</a><a href="{rel}changes.html">Change log</a></div>
<div><h4>Data</h4><a href="{rel}data/trials.csv">Download CSV</a><a href="{rel}feed.xml">RSS feed</a><a href="{rel}about.html">Methods</a>{f'<a href="{REPO_URL}">Source code</a>' if REPO_URL else ''}</div>
<div><h4>Source</h4><p>Registry data from <a href="https://clinicaltrials.gov">ClinicalTrials.gov</a> (U.S. National Library of Medicine), retrieved daily. Labels are assigned automatically by published rules and can be wrong. Not medical advice; talk to your doctor about trial participation.</p></div>
</div><div class="fbar"><span>© {dt.date.today().year} {SITE_NAME}</span><span>Data snapshot {STAMP}</span></div></div></footer>
<script src="{rel}assets/app.js?v={ASSET_V}" defer></script></body></html>"""


def main(data_dir, out_dir):
    global STAMP
    data, out = pathlib.Path(data_dir), pathlib.Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    (out / "trials").mkdir(parents=True)
    (out / "data").mkdir()
    shutil.copytree(ASSETS, out / "assets")
    t = pd.read_csv(data / "trials_latest.csv", dtype={"phase": str})
    ev = pd.read_csv(data / "events.csv", dtype=str).fillna("")
    meta = json.loads((data / "meta.json").read_text())
    today = dt.date.fromisoformat(meta["snapshot_date"])
    STAMP = f"{today:%B %d, %Y}"
    track_start = meta.get("tracking_started", meta["snapshot_date"])
    for c in ("title", "sponsor", "collaborators", "interventions", "conditions", "summary"):
        t[c] = t[c].map(clean)
    ev["title"] = ev["title"].map(clean)
    t["phase"] = t.phase.fillna("")
    t["diseases"] = t.diseases.fillna("")
    t["active"] = t.active.astype(bool)
    t["has_results"] = t.has_results.astype(bool)
    t["pc_date"] = t.primary_completion.map(pdate)
    t["fp_date"] = t.first_posted.map(pdate)
    t["lu_date"] = t.last_update.map(pdate)
    t["fy"] = t.fp_date.map(lambda d: d.year if d else None)
    t["stale"] = t.active & t.pc_date.map(lambda d: bool(d) and d < today)
    t["industry"] = t.sponsor_class.eq("INDUSTRY")
    act = t[t.active]
    by_nct = t.set_index("nct")

    # ---------- downloads ----------
    csv = t.drop(columns=["pc_date", "fp_date", "lu_date", "fy", "summary"]).copy()
    csv["disease_labels"] = csv.diseases.map(lambda v: "; ".join(DISEASE_LABEL.get(x, x) for x in v.split(";") if x))
    csv["phase"] = csv.phase.map(phase)
    csv.to_csv(out / "data" / "trials.csv", index=False)
    ev.to_csv(out / "data" / "events.csv", index=False)
    dlabel = lambda r: DISEASE_LABEL.get(r.disease, r.disease or "")
    js = [{"n": r.nct, "t": r.title, "d": dlabel(r), "ds": [DISEASE_LABEL[x] for x in r.diseases.split(";") if x], "p": phase(r.phase),
           "s": STATUS_EN.get(r.status, r.status), "a": bool(r.active), "m": r.modality, "tg": r.target, "pl": r.platform if isinstance(r.platform, str) else "",
           "sp": r.sponsor if isinstance(r.sponsor, str) else "", "e": None if pd.isna(r.enrollment) else int(r.enrollment),
           "st": r.start if isinstance(r.start, str) else "", "pc": r.primary_completion if isinstance(r.primary_completion, str) else "",
           "c": r.countries if isinstance(r.countries, str) else "", "r": bool(r.has_results), "x": bool(r.stale)} for r in t.itertuples()]
    (out / "data" / "trials.json").write_text(json.dumps(js, separators=(",", ":")))

    # ---------- shared ----------
    week = ev[pd.to_datetime(ev.date).dt.date > today - dt.timedelta(days=7)]
    up = act[act.pc_date.map(lambda d: bool(d) and today <= d <= today + dt.timedelta(days=90))].sort_values("pc_date")
    new30 = t[t.fp_date.map(lambda d: bool(d) and d >= today - dt.timedelta(days=30))].sort_values("fp_date", ascending=False)
    upd14 = t[t.lu_date.map(lambda d: bool(d) and d >= today - dt.timedelta(days=14))].sort_values("lu_date", ascending=False)

    def flags(r):
        return (" · " + badge("completion date passed, status not updated", "warn")) if r.stale else ""

    def trial_row(r, rel="", extra=""):
        return (f'<li><a href="{rel}trials/{r.nct}.html">{e(r.title)}</a><div class="meta">{r.nct} · {e(dlabel(r))} · {phase(r.phase)} · '
                f'{badge(r.modality, "dmt")} · {e(r.target)} · {e(r.sponsor)}{extra}{flags(r)}</div></li>')

    def ev_change(x):
        if x.kind == "status":
            return f"{STATUS_EN.get(x.before, x.before)} → {STATUS_EN.get(x.after, x.after)}"
        if x.kind == "phase":
            return f"{phase(x.before)} → {phase(x.after)}"
        if x.kind == "new":
            return STATUS_EN.get(x.after, x.after)
        if x.kind == "removed":
            return "no longer listed or no longer in scope"
        if x.kind == "results":
            return "results now on ClinicalTrials.gov"
        if x.kind == "enrollment":
            f = lambda v: f"{int(float(v)):,}" if str(v) not in ("", "nan") else "—"
            try:
                return f"{f(x.before)} → {f(x.after)} ({int(float(x.after)) - int(float(x.before)):+,})"
            except (ValueError, TypeError):
                return f"{f(x.before)} → {f(x.after)}"
        if x.kind == "primary_completion":
            m = months_between(x.before, x.after)
            tail = "" if m is None else (f" (+{m} mo)" if m > 0 else f" ({m} mo)" if m < 0 else "")
            return f"{show_date(x.before)} → {show_date(x.after)}{tail}"
        return f"{x.before} → {x.after}"

    def ev_item(x, rel="", link=True):
        ttl = f'<a href="{rel}trials/{x.nct}.html">{e(x.title)}</a>' if (link and x.nct in by_nct.index) else e(x.title)
        return (f'<li>{badge(CHANGE_EN.get(x.kind, x.kind), "chg")} {ttl}<div class="meta">{x.nct} · {e(DISEASE_LABEL.get(x.disease, x.disease))} · '
                f'{e(ev_change(x))} · detected {x.date}</div></li>')

    def ul(items, empty="None"):
        return f"<ul class='list'>{items}</ul>" if items else f"<p class='muted'>{empty}</p>"

    def due_row(r):
        d = r.pc_date
        return (f'<li class="dated"><span class="date"><b>{d:%b}</b>{d:%d}</span><div><a href="trials/{r.nct}.html">{e(short_title(r.title, 110))}</a>'
                f'<div class="meta">{e(dlabel(r))} · {phase(r.phase)} · {badge(r.modality, "dmt")} · {e(r.sponsor)}'
                f'{" · approx. month" if isinstance(r.primary_completion, str) and len(r.primary_completion) == 7 else ""}</div></div></li>')

    # ---------- home ----------
    def tile(label, value, sub=""):
        return f'<div class="tile"><div class="v">{value}</div><div class="l">{label}</div><div class="s">{sub}</div></div>'
    lup = len(act[act.diseases.str.contains("SLE|LN")])
    tiles = (tile("Active trials", f"{len(act):,}", f"of {len(t):,} tracked since registration")
             + tile("Active lupus trials", lup, "SLE or lupus nephritis")
             + tile("Primary completions due in the next 90 days", len(up), "dates as registered")
             + tile("New registrations, last 30 days", len(new30), "by first-posted date"))
    week_html = ul("".join(ev_item(x) for x in week.sort_values("date", ascending=False).itertuples()),
                   f"No tracked field changed in the last 7 days. Change tracking started on {track_start}; history accumulates daily.")
    body = f"""<section class="hero2"><span class="live"><i></i>Live · updated {today:%b %d, %Y}</span>
<h1>Every CAR-T and T-cell engager trial in autoimmune disease, <span class="hl2">tracked daily.</span></h1>
<p class="sub">{len(t):,} interventional trials of CAR-T, CAR-NK, CAAR-T and T-cell engager therapies in lupus, myositis, systemic sclerosis, myasthenia gravis,
MS and other autoimmune diseases, checked against ClinicalTrials.gov every day: new entrants, status changes, delays and upcoming results in one place.</p>
<div class="ctas"><a class="btn" href="dashboard.html">Open the dashboard</a><a class="btn ghost" href="explore.html">Explore {len(t):,} trials</a></div></section>
<section class="tiles">{tiles}</section>
<div class="panels"><div class="col">
<section class="panel"><div class="ph"><h2>This week</h2><a href="changes.html">All changes →</a></div>{week_html}</section>
<section class="panel"><div class="ph"><h2>Newly registered</h2><span class="muted small">last 30 days</span></div>{ul(''.join(trial_row(r, extra=f' · posted {e(r.first_posted)}') for r in new30.head(8).itertuples()))}</section>
</div><div class="col">
<section class="panel"><div class="ph"><h2>Results due, next 90 days</h2><a href="readouts.html">Calendar →</a></div>
<p class="muted small">Primary completion as registered; results usually follow later. {len(up)} trials in the window.</p>
{ul(''.join(due_row(r) for r in up.head(10).itertuples()))}</section>
<section class="panel"><div class="ph"><h2>Recently updated</h2><span class="muted small">last 14 days</span></div>
<p class="muted small">The sponsor edited the record; the edit may be to any field.</p>{ul(''.join(trial_row(r, extra=f' · updated {e(r.last_update)}') for r in upd14.head(8).itertuples()))}</section>
</div></div>
<section class="cta2"><div><h2>Get the daily changes</h2><p>New trials, status changes and delays as they are detected. No account needed.</p></div>
<div class="ctas"><a class="btn" href="feed.xml">Subscribe via RSS</a><a class="btn ghost" href="data/trials.csv">Download CSV</a></div></section>"""
    jl = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "description": TAGLINE, **({"url": SITE_URL + "/"} if SITE_URL else {})}
    (out / "index.html").write_text(page(f"CAR-T & T-cell engager trials in autoimmune disease · {SITE_NAME}", body,
                                         desc=f"Daily-updated tracker of {len(t):,} CAR-T, CAR-NK and T-cell engager trials in lupus, myositis, systemic sclerosis, myasthenia gravis, MS and other autoimmune diseases.", jsonld=jl))
    (out / "dashboard.html").write_text(page(f"Dashboard · CAR-T in autoimmune disease · {SITE_NAME}", dashboard.build(t, today), canonical="dashboard.html",
                                             desc="Charts of CAR-T, CAR-NK and T-cell engager trials in autoimmune disease by disease, target, platform, phase, sponsor and country."))

    # ---------- explore ----------
    opts = lambda vals: "".join(f"<option>{e(v)}</option>" for v in vals)
    dz = [DISEASE_LABEL[c] for c, _, _ in DISEASES]
    body = f"""<h1>Explore trials</h1><p class="muted">{len(t):,} trials ({len(act):,} active). Click a column header to sort; click a title for details.
Filters are kept in the page address so a view can be bookmarked or shared.</p>
<div class="filters" id="filters"><input id="q" type="search" placeholder="Search title, sponsor, product, NCT…" aria-label="Search">
<select id="fd" aria-label="Disease"><option value="">All diseases</option>{opts(dz)}</select>
<select id="fm" aria-label="Modality"><option value="">All modalities</option>{opts(MODALITIES)}</select>
<select id="ft" aria-label="Target"><option value="">All targets</option>{opts(sorted(t.target.dropna().unique()))}</select>
<select id="fl" aria-label="Platform"><option value="">All platforms</option>{opts(PLATFORMS)}</select>
<select id="fp" aria-label="Phase"><option value="">All phases</option>{opts(phase(p) for p in ["Early 1", "1", "1/2", "2", "2/3", "3"])}</select>
<select id="fc" aria-label="Country"><option value="">All countries</option>{opts(sorted({c for s_ in t.countries.dropna() for c in s_.split(';')}))}</select>
<label class="chk"><input id="fa" type="checkbox" checked> Active only</label></div>
<p id="count" class="muted">Loading trial data…</p><noscript><p>This table needs JavaScript. <a href="data/trials.csv">Download the CSV</a> instead.</p></noscript>
<div class="tablewrap"><table id="tbl"><thead><tr><th data-k="t">Trial</th><th data-k="d">Disease</th><th data-k="p">Phase</th><th data-k="m">Modality · target</th>
<th data-k="s">Status</th><th data-k="e">N</th><th data-k="st">Start</th><th data-k="pc">Primary completion</th></tr></thead><tbody></tbody></table></div>"""
    (out / "explore.html").write_text(page(f"Explore CAR-T trials in autoimmune disease · {SITE_NAME}", body, canonical="explore.html",
                                           desc=f"Filter {len(t):,} CAR-T, CAR-NK and T-cell engager trials in autoimmune disease by disease, target, platform, phase, country and status."))

    # ---------- changes ----------
    parts = [f"<h3>{d}</h3>{ul(''.join(ev_item(x) for x in g.itertuples()))}" for d, g in ev.sort_values("date", ascending=False).groupby("date", sort=False)]
    body = f"""<h1>All detected changes</h1><p class="muted">Each daily snapshot is compared with the previous one: new trials, trials leaving the tracker,
status, phase, enrollment target, primary completion date, modality and target labels, and posted results. A change is dated when first detected.
Re-labels caused by updates to this site's own rules are not logged. Tracking started {track_start}; there is no history before that date.</p>
{''.join(parts) or "<p class='muted'>No changes detected yet.</p>"}
<h2>Registrations updated in the last 14 days</h2><p class="muted small">The sponsor edited the record; the edit may be to any field.</p>
{ul(''.join(trial_row(r, extra=f' · updated {e(r.last_update)}') for r in upd14.itertuples()))}"""
    (out / "changes.html").write_text(page(f"Detected changes · {SITE_NAME}", body, canonical="changes.html",
                                           desc="Day-by-day log of new trials, status, enrollment and completion-date changes in CAR-T and T-cell engager trials for autoimmune disease."))

    # ---------- completion calendar ----------
    def month_groups(df):
        out_ = []
        for m, g in df.groupby(df.pc_date.map(lambda x: x.strftime("%Y-%m")), sort=True):
            out_.append(f"<h3>{dt.date.fromisoformat(m + '-01'):%B %Y} <span class='muted'>({len(g)})</span></h3>"
                        + ul("".join(trial_row(r, extra=f" · {e(show_date(r.primary_completion))} · {STATUS_EN.get(r.status, r.status)}") for r in g.itertuples())))
        return "".join(out_)
    upcoming = act[act.pc_date.map(lambda d: bool(d) and today <= d <= today + dt.timedelta(days=365))].sort_values("pc_date")
    recent = t[t.pc_date.map(lambda d: bool(d) and today - dt.timedelta(days=90) <= d < today) & (t.active | t.status.eq("COMPLETED"))].sort_values("pc_date")
    body = f"""<h1>Primary completion calendar</h1><p class="muted">Primary completion is when the last participant is assessed for the primary outcome, as registered
by the sponsor. Results usually follow later and registered dates often slip. Month-only dates are shown as "~Mon YYYY".</p>
<p class="toc"><a href="#upcoming">Next 12 months ({len(upcoming)})</a> · <a href="#recent">Past 90 days ({len(recent)})</a></p>
<h2 id="upcoming">Next 12 months</h2>{month_groups(upcoming) or "<p class='muted'>None</p>"}
<h2 id="recent">Past 90 days</h2><p class="muted small">Active trials here have passed their registered date without a status update.</p>{month_groups(recent) or "<p class='muted'>None</p>"}"""
    (out / "readouts.html").write_text(page(f"Primary completion calendar · {SITE_NAME}", body, canonical="readouts.html",
                                            desc="Upcoming and recent primary completion dates of CAR-T and T-cell engager trials in autoimmune disease, by month."))

    # ---------- by disease ----------
    rows, lists = [], []
    for code, lab, _ in DISEASES:
        g = act[act.diseases.str.contains(rf"\b{code}\b")]
        if not len(g):
            continue
        mc = g.modality.value_counts()
        rows.append(f"<tr><td><a href='#d-{code}'>{e(lab)}</a></td><td class='num'>{len(g)}</td><td class='num'>{int(mc.get('CAR-T', 0))}</td>"
                    f"<td class='num'>{int(mc.get('CAR-NK', 0))}</td><td class='num'>{int(mc.get('T-cell engager', 0))}</td>"
                    f"<td class='num'>{int(g.target.str.contains('CD19').sum())}</td><td class='num'>{int(g.target.str.contains('BCMA').sum())}</td></tr>")
        lists.append(f"<h3 id='d-{code}'>{e(lab)} <span class='muted'>({len(g)})</span></h3>" + ul("".join(trial_row(r) for r in g.sort_values("phase", ascending=False).itertuples())))
    body = f"""<h1>Active trials by disease</h1><p class="muted">{len(act):,} active trials. A trial that enrolls several diseases is listed under each.</p>
<div class="tablewrap"><table><thead><tr><th>Disease</th><th>Active</th><th>CAR-T</th><th>CAR-NK</th><th>T-cell engager</th><th>CD19</th><th>BCMA</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>{''.join(lists)}"""
    (out / "diseases.html").write_text(page(f"CAR-T trials by autoimmune disease · {SITE_NAME}", body, canonical="diseases.html",
                                            desc="Active CAR-T, CAR-NK and T-cell engager trials grouped by autoimmune disease: lupus, lupus nephritis, myositis, systemic sclerosis, myasthenia gravis, MS and more."))

    # ---------- trial pages ----------
    hist = {n: g for n, g in ev.groupby("nct")}
    sm = [(u, meta["snapshot_date"]) for u in ("", "dashboard.html", "explore.html", "readouts.html", "diseases.html", "changes.html", "about.html")]

    def kvrow(label, value):
        return f"<tr><th>{label}</th><td>{value}</td></tr>" if value not in ("", None) else ""
    for r in t.itertuples():
        h = hist.get(r.nct)
        hh = ul("".join(ev_item(x, "../", link=False) for x in h.sort_values("date", ascending=False).itertuples())) if h is not None else \
            f"<p class='muted'>No tracked changes since tracking began ({track_start}).</p>"
        same = act[(act.target == r.target) & (act.modality == r.modality) & (act.nct != r.nct)].head(8)
        sites = f"{num(r.n_sites)}" + (f" · {e(r.countries.replace(';', ', '))}" if isinstance(r.countries, str) else "") if r.n_sites else ""
        ages = f"{'' if pd.isna(r.age_min) else f'{r.age_min:g}'}–{'' if pd.isna(r.age_max) else f'{r.age_max:g}'} years" if not (pd.isna(r.age_min) and pd.isna(r.age_max)) else ""
        kv = (kvrow("Diseases", e(", ".join(DISEASE_LABEL[x] for x in r.diseases.split(";") if x))) + kvrow("Modality", e(r.modality))
              + kvrow("Target", e(r.target)) + kvrow("Platform", e(r.platform) if isinstance(r.platform, str) else "")
              + kvrow("Conditions listed", e(r.conditions)) + kvrow("Interventions", e(r.interventions)) + kvrow("Sponsor", e(r.sponsor))
              + kvrow("Collaborators", e(r.collaborators) if isinstance(r.collaborators, str) else "") + kvrow("Enrollment", num(r.enrollment))
              + kvrow("Ages", ages) + kvrow("Start", e(show_date(r.start))) + kvrow("Primary completion", e(show_date(r.primary_completion)))
              + kvrow("First posted", e(r.first_posted)) + kvrow("Last update", e(r.last_update)) + kvrow("Sites", sites))
        warn = (f"<p class='note'>{badge('completion date passed, status not updated', 'warn')} The registered primary completion date "
                f"({e(show_date(r.primary_completion))}) has passed but the status is still “{STATUS_EN.get(r.status, r.status)}”.</p>") if r.stale else ""
        report = f' · <a href="{REPO_URL}/issues/new?title=Label%20issue%20{r.nct}">Report a labelling error</a>' if REPO_URL else ""
        summ = f"<h2>Summary (from the registry)</h2><p>{e(r.summary)}</p>" if isinstance(r.summary, str) and r.summary else ""
        body = f"""<p class="crumb"><a href="../explore.html">Explore</a> › {r.nct}</p><h1>{e(r.title)}</h1>
<p>{badge(dlabel(r))} {badge(phase(r.phase))} {badge(STATUS_EN.get(r.status, r.status))} {badge(r.modality, 'dmt')} {badge(r.target)}
{badge('Results posted', 'ok') if r.has_results else ''}</p>{warn}
<table class="kv">{kv}</table>{summ}
<p><a class="btn" href="https://clinicaltrials.gov/study/{r.nct}">View on ClinicalTrials.gov</a>{report}</p>
<h2>Change history</h2>{hh}
{('<h2>Other active trials with the same modality and target</h2>' + ul(''.join(trial_row(x, '../') for x in same.itertuples()))) if len(same) else ''}"""
        desc = (f"{r.nct}: {r.modality} ({r.target}) {phase(r.phase)} trial in {dlabel(r)}, {STATUS_EN.get(r.status, r.status).lower()}"
                f"{', sponsor ' + r.sponsor if isinstance(r.sponsor, str) else ''}. Status, details and change history.")
        jl = {"@context": "https://schema.org", "@type": "MedicalTrial", "name": r.title, "identifier": r.nct, "url": f"https://clinicaltrials.gov/study/{r.nct}",
              "trialDesign": phase(r.phase), "status": STATUS_EN.get(r.status, r.status), **({"sponsor": {"@type": "Organization", "name": r.sponsor}} if isinstance(r.sponsor, str) else {})}
        (out / "trials" / f"{r.nct}.html").write_text(page(f"{short_title(r.title)} ({r.nct}) · {SITE_NAME}", body, rel="../", desc=desc,
                                                           canonical=f"trials/{r.nct}.html", jsonld=jl, og_type="article"))
        lm = max([d for d in (r.lu_date, pdate(h.date.max()) if h is not None else None) if d] or [today])
        sm.append((f"trials/{r.nct}.html", lm.isoformat()))

    # ---------- about ----------
    drows = "".join(f"<tr><td>{e(l)}</td><td><code>{e(p)}</code></td></tr>" for _, l, p in DISEASES)
    body = f"""<h1>About and methods</h1>
<p>{SITE_NAME} follows every interventional trial of an immune-reset therapy in autoimmune disease registered on ClinicalTrials.gov, and records what changes each day.</p>
<h2>What is in scope</h2><ul>
<li><b>Therapy</b>: CAR-T (autologous, allogeneic, or engineered in vivo / with mRNA), CAR-NK, CAAR-T, CAR-Treg, and T-cell engagers (CD3 bispecifics)
against B-cell or plasma-cell targets, recognised from the title, intervention names and descriptions.</li>
<li><b>Disease</b>: at least one autoimmune or immune-mediated disease in the listed conditions or the title. Trials whose conditions are only cancers are excluded,
even if they mention autoimmunity elsewhere.</li><li><b>Study type</b>: interventional. Observational follow-up studies are excluded.</li></ul>
<h2>How labels are assigned</h2><p>Plain, published rules (regular expressions) in <code>tracker/classify.py</code>, version {RULES_VERSION}. Targets come from the title and intervention names;
descriptions are used only when those name none, because descriptions often mention other antigens. Products whose target is not disclosed are labelled "Other / not stated".
Platform is read from words such as allogeneic, off-the-shelf, donor-derived, iPSC, in vivo or mRNA; everything else is treated as autologous.</p>
<div class="tablewrap"><table><thead><tr><th>Disease group</th><th>Matched in conditions or title</th></tr></thead><tbody>{drows}</tbody></table></div>
<h2>Limits</h2><ul><li>Only ClinicalTrials.gov. Trials registered only in ChiCTR, EU CTR/CTIS or other registries are missing, which matters because many early
CAR-T studies in autoimmunity are run in China.</li><li>Registry fields are written by sponsors and are often out of date; "active" records past their completion
date are flagged.</li><li>Labels can be wrong. Each trial page links to the registry record{', and errors can be reported on GitHub' if REPO_URL else ''}.</li>
<li>Not medical advice. To ask about joining a trial, contact the study site listed on ClinicalTrials.gov together with your doctor.</li></ul>
<h2>Data</h2><p><a href="data/trials.csv">trials.csv</a> (all tracked trials with labels) and <a href="data/events.csv">events.csv</a> (every detected change) are updated daily.
<a href="feed.xml">RSS feed</a> of changes.</p>
<p class="muted">Snapshot {meta['snapshot_date']} · {len(t):,} trials · {len(act):,} active · rules {RULES_VERSION} · tracking since {track_start}</p>"""
    (out / "about.html").write_text(page(f"About and methods · {SITE_NAME}", body, canonical="about.html",
                                         desc="How Autoimmune CAR-T Watch selects and labels CAR-T, CAR-NK and T-cell engager trials in autoimmune disease, and its limits."))
    root = (SITE_URL + "/") if SITE_URL else ""
    (out / "404.html").write_text(page(f"Page not found · {SITE_NAME}", f"<h1>Page not found</h1><p>The trial may no longer be in scope. Try <a href='{root}explore.html'>Explore</a> "
                                       f"or the <a href='{root}index.html'>home page</a>.</p>", rel=root))

    # ---------- feed, sitemap ----------
    rfc = lambda d: dt.datetime.combine(dt.date.fromisoformat(d), dt.time(12)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = "".join(f"<item><title>{e(CHANGE_EN.get(x.kind, x.kind))}: {e(x.title)}</title><link>{SITE_URL + '/' if SITE_URL else ''}trials/{x.nct}.html</link>"
                    f"<guid isPermaLink=\"false\">{x.nct}-{x.kind}-{x.date}</guid><pubDate>{rfc(x.date)}</pubDate><description>{e(x.nct)} · {e(ev_change(x))}</description></item>"
                    for x in ev.sort_values("date", ascending=False).head(200).itertuples())
    (out / "feed.xml").write_text(f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE_NAME}</title><link>{SITE_URL}/</link>'
                                  f"<description>{TAGLINE}</description><lastBuildDate>{rfc(meta['snapshot_date'])}</lastBuildDate>{items}</channel></rss>")
    if SITE_URL:
        (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                         + "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{lm}</lastmod></url>" for u, lm in sm) + "</urlset>")
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    (out / ".nojekyll").write_text("")
    print(f"  site: {len(sm)} pages → {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
