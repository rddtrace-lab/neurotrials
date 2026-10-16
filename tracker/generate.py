"""Static site generator for the Parkinson's & Alzheimer's trial tracker.

Reads data/trials_latest.csv, data/events.csv, data/meta.json (written by tracker.update) and writes a static site:
  index.html        this week's changes, upcoming primary completions, new registrations, headline counts
  dashboard.html    charts: mechanisms, phase × class, registrations per year, completions per month, status
  explore.html      filterable table of every in-scope trial (client-side, data/trials.json)
  changes.html      detected changes by date + registrations updated in the last 14 days
  readouts.html     primary-completion calendar (upcoming 12 months, past 90 days, and stale "active" records)
  mechanisms.html   active trials by mechanism, disease and phase
  trials/NCT*.html  one page per in-scope trial (details, eligibility signals, change history, same-mechanism trials)
  about.html        methods, classification accuracy, disclaimer, data source
  404.html, feed.xml, sitemap.xml, robots.txt, data/*.csv, data/trials.json
Usage: python -m tracker.generate DATA_DIR OUT_DIR   (env SITE_URL, REPO_URL optional)
"""
import os, re, sys, json, html, shutil, pathlib, datetime as dt
from html import escape
import pandas as pd
from moduleA import rules
from .labels import MECH_EN, GROUP_EN, DISEASE_EN, STATUS_EN, PHASE_EN, CHANGE_EN, AD_STAGE_EN
from . import dashboard

SITE_URL = os.environ.get("SITE_URL", "").rstrip("/")
REPO_URL = os.environ.get("REPO_URL", "").rstrip("/")
SITE_NAME = "NeuroTrials Watch"
TAGLINE = "Parkinson's and Alzheimer's drug trials, updated daily from ClinicalTrials.gov"
ASSETS = pathlib.Path(__file__).with_name("assets")
HV_RX = re.compile(r"healthy", re.I)


def e(x):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else escape(str(x))


def clean(x):
    """Registry text sometimes arrives with HTML entities already encoded (e.g. &#39;). Decode once before we escape."""
    return html.unescape(x) if isinstance(x, str) else x


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


def show_date(s):
    """Registry date for display; month-only dates are marked as approximate."""
    if not isinstance(s, str) or not s:
        return ""
    if len(s) == 7:
        try:
            return "~" + dt.date.fromisoformat(s + "-01").strftime("%b %Y")
        except ValueError:
            return s
    return s


def months_between(a, b):
    da, db = pdate(a), pdate(b)
    if not da or not db:
        return None
    return (db.year - da.year) * 12 + (db.month - da.month)


def phase(p):
    return PHASE_EN.get(str(p), f"Phase {p}")


def num(x):
    return "" if pd.isna(x) else f"{int(x):,}"


def truthy(v):
    return str(v) in ("True", "true", "1", "1.0")


def short_title(t, n=70):
    t = clean(t) or ""
    if len(t) <= n:
        return t
    cut = t[:n].rsplit(" ", 1)[0].rstrip(",;:-–(")
    return cut + "…"


def page(title, body, rel="", desc=TAGLINE, canonical="", jsonld=None, og_type="website"):
    nav = [("index.html", "This week"), ("dashboard.html", "Dashboard"), ("explore.html", "Explore"), ("readouts.html", "Completion calendar"),
           ("mechanisms.html", "Mechanisms"), ("changes.html", "All changes"), ("about.html", "About")]
    links = "".join(f'<a href="{rel}{h}">{t}</a>' for h, t in nav)
    url = f"{SITE_URL}/{canonical}" if SITE_URL else ""
    canon = f'<link rel="canonical" href="{url}">' if SITE_URL else ""
    og = (f'<meta property="og:site_name" content="{SITE_NAME}"><meta property="og:type" content="{og_type}">'
          f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
          + (f'<meta property="og:url" content="{url}">' if url else "")
          + f'<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}">')
    ld = f'<script type="application/ld+json">{json.dumps(jsonld)}</script>' if jsonld else ""
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title><meta name="description" content="{e(desc)}">{canon}{og}{ld}
<link rel="stylesheet" href="{rel}assets/style.css"><link rel="alternate" type="application/rss+xml" title="{SITE_NAME}" href="{rel}feed.xml">
</head><body><header class="top"><div class="wrap"><a class="brand" href="{rel}index.html">{SITE_NAME}</a><nav>{links}</nav></div></header>
<main class="wrap">{body}</main>
<footer class="wrap foot">Data: <a href="https://clinicaltrials.gov">ClinicalTrials.gov</a> (U.S. National Library of Medicine), retrieved daily.
Mechanism labels are assigned automatically and can be wrong (see <a href="{rel}about.html">About</a>). Not medical advice.
<a href="{rel}feed.xml">RSS</a> · <a href="{rel}data/trials.csv">Download data</a>{f' · <a href="{REPO_URL}">Source code</a>' if REPO_URL else ''}</footer>
<script src="{rel}assets/app.js" defer></script></body></html>"""


def badge(text, cls=""):
    return f'<span class="badge {cls}">{e(text)}</span>'


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
    for c in ("conditions", "healthy_volunteers"):
        if c not in t:
            t[c] = None
    for c in ("title", "sponsor", "collaborators", "interventions", "conditions"):
        t[c] = t[c].map(clean)
    ev["title"] = ev["title"].map(clean)
    t["group"] = t.mech_primary.map(rules.MECH_GROUP).fillna("UNK")
    t["pc_date"] = t.primary_completion.map(pdate)
    t["fp_date"] = t.first_posted.map(pdate)
    t["lu_date"] = t.last_update.map(pdate)
    # 건강인 대상 연구: 건강인 참여를 받고 제목에 'healthy'가 있는 경우(환자 대상 임상이 건강인도 받는 경우를 빼려는 근사)
    t["hv_study"] = t.healthy_volunteers.map(truthy) & t.title.fillna("").str.contains(HV_RX)
    # 1차 완료 예정일이 지났는데 상태가 아직 '진행 중'인 기록
    t["stale"] = t.active.astype(bool) & t.pc_date.map(lambda d: d is not None and d < today)
    s = t[t.in_scope.astype(bool)].copy()
    act = s[s.active.astype(bool)]
    ev = ev[ev.nct.isin(t.nct) | (ev.kind == "removed")]
    by_nct = s.set_index("nct")
    track_start = meta.get("tracking_started") or (ev.date.min() if len(ev) else meta["snapshot_date"])

    # ---------- data downloads ----------
    csv = s.drop(columns=["pc_date", "fp_date", "lu_date"]).copy()
    csv["phase"] = csv.phase.map(phase)
    csv["ad_stages"] = csv.ad_stages.map(lambda v: ";".join(AD_STAGE_EN.get(x, x) for x in v.split(";")) if isinstance(v, str) else v)
    csv["mechanism_label"] = csv.mech_primary.map(MECH_EN)
    csv["class_label"] = csv.group.map(GROUP_EN)
    csv.to_csv(out / "data" / "trials.csv", index=False)
    ev.to_csv(out / "data" / "events.csv", index=False)
    js = [{"n": r.nct, "t": r.title, "d": DISEASE_EN.get(r.disease, r.disease), "p": phase(r.phase), "s": STATUS_EN.get(r.status, r.status),
           "a": bool(r.active), "m": MECH_EN.get(r.mech_primary, r.mech_primary), "g": GROUP_EN.get(r.group, r.group),
           "sp": r.sponsor if isinstance(r.sponsor, str) else "", "e": None if pd.isna(r.enrollment) else int(r.enrollment),
           "st": r.start if isinstance(r.start, str) else "", "pc": r.primary_completion if isinstance(r.primary_completion, str) else "",
           "r": bool(r.has_results), "hv": bool(r.hv_study), "x": bool(r.stale)} for r in s.itertuples()]
    (out / "data" / "trials.json").write_text(json.dumps(js, separators=(",", ":")))

    # ---------- shared ----------
    week = ev[pd.to_datetime(ev.date).dt.date > today - dt.timedelta(days=7)]
    up = act[(act.pc_date >= today) & (act.pc_date <= today + dt.timedelta(days=90))].sort_values("pc_date")
    new30 = s[s.fp_date >= today - dt.timedelta(days=30)].sort_values("fp_date", ascending=False)
    upd14 = s[s.lu_date >= today - dt.timedelta(days=14)].sort_values("lu_date", ascending=False)

    def flags(r):
        out_ = ""
        if r.hv_study:
            out_ += " · " + badge("healthy volunteers", "")
        if r.stale:
            out_ += " · " + badge("completion date passed, status not updated", "warn")
        return out_

    def trial_row(r, rel="", extra=""):
        grp = r.group
        return (f'<li><a href="{rel}trials/{r.nct}.html">{e(r.title)}</a>'
                f'<div class="meta">{r.nct} · {DISEASE_EN.get(r.disease, r.disease)} · {phase(r.phase)} · '
                f'{badge(MECH_EN.get(r.mech_primary, r.mech_primary), grp.lower())} · {e(r.sponsor)}{extra}{flags(r)}</div></li>')

    def ev_change(x):
        if x.kind == "status":
            return f"{STATUS_EN.get(x.before, x.before)} → {STATUS_EN.get(x.after, x.after)}"
        if x.kind == "mech_primary":
            return f"{MECH_EN.get(x.before, x.before)} → {MECH_EN.get(x.after, x.after)}"
        if x.kind == "phase":
            return f"{phase(x.before)} → {phase(x.after)}"
        if x.kind == "new":
            return STATUS_EN.get(x.after, x.after)
        if x.kind == "results":
            return "results now on ClinicalTrials.gov"
        if x.kind == "scope":
            return "now in scope" if truthy(x.after) else "no longer in scope"
        if x.kind == "enrollment":
            f = lambda v: f"{int(float(v)):,}" if str(v) not in ("", "nan") else "—"
            try:
                d = int(float(x.after)) - int(float(x.before))
                return f"{f(x.before)} → {f(x.after)} ({d:+,})"
            except (ValueError, TypeError):
                return f"{f(x.before)} → {f(x.after)}"
        if x.kind == "primary_completion":
            m = months_between(x.before, x.after)
            tail = "" if m is None else (f" (+{m} mo)" if m > 0 else f" ({m} mo)" if m < 0 else "")
            return f"{show_date(x.before)} → {show_date(x.after)}{tail}"
        return f"{x.before} → {x.after}"

    def ev_item(x, rel="", link=True):
        k = CHANGE_EN.get(x.kind, x.kind)
        ttl = f'<a href="{rel}trials/{x.nct}.html">{e(x.title)}</a>' if (link and x.nct in by_nct.index) else e(x.title)
        return f'<li>{badge(k, "chg")} {ttl}<div class="meta">{x.nct} · {DISEASE_EN.get(x.disease, x.disease)} · {e(ev_change(x))} · detected {x.date}</div></li>'

    def ul(items, empty="None"):
        return f"<ul class='list'>{items}</ul>" if items else f"<p class='muted'>{empty}</p>"

    # ---------- index ----------
    def tile(label, value, sub=""):
        return f'<div class="tile"><div class="v">{value}</div><div class="l">{label}</div><div class="s">{sub}</div></div>'
    core = act[~act.hv_study]
    pd_dmt = int(((core.disease.str.contains("PD")) & (core.group == "DMT")).sum())
    ad_dmt = int(((core.disease.str.contains("AD")) & (core.group == "DMT")).sum())
    both_note = "excludes healthy-volunteer studies; trials listing both diseases count in each"
    tiles = (tile("Active putative disease-modifying trials · Parkinson's", pd_dmt, both_note)
             + tile("Active putative disease-modifying trials · Alzheimer's", ad_dmt, both_note)
             + tile("Primary completions due in the next 90 days", len(up), "active trials, dates as registered")
             + tile("New registrations, last 30 days", len(new30), "by first-posted date"))
    week_html = ul("".join(ev_item(x) for x in week.sort_values("date", ascending=False).itertuples()),
                   f"No tracked field changed in the last 7 days. Change tracking started on {track_start}; history accumulates daily.")
    shown = up.head(15)
    body = f"""<section class="hero"><h1>Parkinson's &amp; Alzheimer's drug trial tracker</h1><p>{TAGLINE}. Interventional drug, biologic and gene/cell trials from early phase 1 to phase 2/3,
selected and classified by mechanism with automated rules. "Putative disease-modifying" describes what a mechanism aims at, not evidence that a drug works.
Last update: <b>{today:%B %d, %Y}</b> · change tracking since {track_start}.</p></section>
<section class="tiles">{tiles}</section>
<p><a href="dashboard.html">See the charts on the dashboard →</a></p>
<section><h2>This week</h2>{week_html}</section>
<section><h2>Primary completions due in the next 90 days</h2>{ul(''.join(trial_row(r, extra=f' · due {e(show_date(r.primary_completion))}') for r in shown.itertuples()))}
<p>{f'Showing {len(shown)} of {len(up)}. ' if len(up) > len(shown) else ''}<a href="readouts.html">Full primary completion calendar →</a></p></section>
<section><h2>Newly registered (last 30 days)</h2>{ul(''.join(trial_row(r, extra=f' · posted {e(r.first_posted)}') for r in new30.head(15).itertuples()))}</section>
<section><h2>Registrations updated in the last 14 days</h2><p class="muted small">The sponsor edited the record; the edit may be to any field, not only those tracked above.</p>
{ul(''.join(trial_row(r, extra=f' · updated {e(r.last_update)}') for r in upd14.head(15).itertuples()))}
<p>{f'Showing 15 of {len(upd14)}. ' if len(upd14) > 15 else ''}<a href="changes.html">All changes →</a></p></section>
<section class="cta"><p>Follow along: <a href="feed.xml">RSS feed of detected changes</a> · <a href="data/trials.csv">download the full table (CSV)</a>.</p></section>"""
    jl = {"@context": "https://schema.org", "@type": "WebSite", "name": SITE_NAME, "description": TAGLINE, **({"url": SITE_URL + "/"} if SITE_URL else {})}
    (out / "index.html").write_text(page(f"Parkinson's & Alzheimer's Clinical Trial Tracker (Phase 1–2/3) · {SITE_NAME}", body, canonical="",
                                         desc=f"Daily-updated tracker of {len(s):,} Parkinson's and Alzheimer's phase 1–2/3 drug trials from ClinicalTrials.gov: status changes, upcoming primary completions, new registrations, mechanisms.",
                                         jsonld=jl))

    # ---------- dashboard ----------
    (out / "dashboard.html").write_text(page(f"Dashboard · Parkinson's & Alzheimer's trial landscape · {SITE_NAME}", dashboard.build(s, act, today),
                                             canonical="dashboard.html",
                                             desc="Charts of active Parkinson's and Alzheimer's drug trials by mechanism, phase, class, registration year, upcoming primary completions and status."))

    # ---------- explore ----------
    opts = lambda vals: "".join(f"<option>{e(v)}</option>" for v in vals)
    body = f"""<h1>Explore trials</h1><p class="muted">{len(s):,} trials in scope ({len(act):,} active). Click a column header to sort; click a title for details.
Filters are kept in the page address so a view can be bookmarked or shared.</p>
<div class="filters" id="filters">
<input id="q" type="search" placeholder="Search title, sponsor, NCT…" aria-label="Search">
<select id="fd" aria-label="Disease"><option value="">All diseases</option>{opts(DISEASE_EN.values())}</select>
<select id="fg" aria-label="Class"><option value="">All classes</option>{opts(GROUP_EN[g] for g in ["DMT", "SYM", "UNK"])}</select>
<select id="fm" aria-label="Mechanism"><option value="">All mechanisms</option>{opts(sorted({MECH_EN.get(m, m) for m in s.mech_primary}))}</select>
<select id="fp" aria-label="Phase"><option value="">All phases</option>{opts(phase(p) for p in ["0/1 (초기 1상)", "1", "1/2", "2", "2/3"])}</select>
<label class="chk"><input id="fa" type="checkbox" checked> Active only</label>
<label class="chk"><input id="fh" type="checkbox"> Hide healthy-volunteer studies</label></div>
<p id="count" class="muted">Loading trial data…</p><noscript><p>This table needs JavaScript. <a href="data/trials.csv">Download the CSV</a> instead.</p></noscript>
<div class="tablewrap"><table id="tbl"><thead><tr>
<th data-k="t">Trial</th><th data-k="d">Disease</th><th data-k="p">Phase</th><th data-k="m">Mechanism</th><th data-k="s">Status</th><th data-k="e">N</th><th data-k="st">Start</th><th data-k="pc">Primary completion</th></tr></thead><tbody></tbody></table></div>"""
    (out / "explore.html").write_text(page(f"Explore Parkinson's & Alzheimer's trials · {SITE_NAME}", body, canonical="explore.html",
                                           desc=f"Filter {len(s):,} Parkinson's and Alzheimer's phase 1–2/3 drug trials by disease, mechanism, phase and status."))

    # ---------- changes ----------
    parts = []
    for d, g in ev.sort_values("date", ascending=False).groupby("date", sort=False):
        parts.append(f"<h3>{d}</h3>{ul(''.join(ev_item(x) for x in g.itertuples()))}")
    body = f"""<h1>All detected changes</h1><p class="muted">For trials in scope, each daily snapshot is compared with the previous one:
new registrations, status, phase, mechanism label, enrollment, primary completion date, posted results. A change is dated when it was first detected,
which can be a day or more after the sponsor's update. Mechanism re-labels caused by changes to this site's own rules are not logged.
Tracking started {track_start}; there is no history before that date.</p>
{''.join(parts) or "<p class='muted'>No changes detected yet.</p>"}
<h2>Registrations updated in the last 14 days</h2><p class="muted small">The sponsor edited the record; the edit may be to any field.</p>
{ul(''.join(trial_row(r, extra=f' · updated {e(r.last_update)}') for r in upd14.itertuples()))}"""
    (out / "changes.html").write_text(page(f"Detected changes in Parkinson's & Alzheimer's trials · {SITE_NAME}", body, canonical="changes.html",
                                           desc="Day-by-day log of status, phase, enrollment and completion-date changes in Parkinson's and Alzheimer's drug trials."))

    # ---------- completion calendar ----------
    def month_groups(df, extra_fn):
        parts_ = []
        for m, g in df.groupby(df.pc_date.map(lambda x: x.strftime("%Y-%m")), sort=True):
            label = dt.date.fromisoformat(m + "-01").strftime("%B %Y")
            parts_.append(f"<h3>{label} <span class='muted'>({len(g)})</span></h3>{ul(''.join(trial_row(r, extra=extra_fn(r)) for r in g.itertuples()))}")
        return "".join(parts_)
    ext = lambda r: f" · {e(show_date(r.primary_completion))}" + (" · " + badge("results posted", "ok") if r.has_results else "") + f" · {STATUS_EN.get(r.status, r.status)}"
    upcoming = act[(act.pc_date >= today) & (act.pc_date <= today + dt.timedelta(days=365))].sort_values("pc_date")
    recent = s[(s.pc_date < today) & (s.pc_date >= today - dt.timedelta(days=90)) & (s.active.astype(bool) | s.status.eq("COMPLETED"))].sort_values("pc_date")
    overdue = act[act.pc_date < today - dt.timedelta(days=365)].sort_values("pc_date")
    body = f"""<h1>Primary completion calendar</h1><p class="muted">Primary completion is when the last participant is assessed for the primary outcome, as registered by the sponsor.
Public results usually follow later, and registered dates often slip. Dates given only as a month are shown as "~Mon YYYY".</p>
<p class="toc"><a href="#upcoming">Next 12 months ({len(upcoming)})</a> · <a href="#recent">Past 90 days ({len(recent)})</a> · <a href="#overdue">Passed over a year ago, still active ({len(overdue)})</a></p>
<h2 id="upcoming">Next 12 months <span class="muted">(active trials)</span></h2>{month_groups(upcoming, ext) or "<p class='muted'>None</p>"}
<h2 id="recent">Past 90 days <span class="muted">(active or completed)</span></h2>
<p class="muted small">Active trials here have passed their registered primary completion date without a status update.</p>{month_groups(recent, ext) or "<p class='muted'>None</p>"}
<h2 id="overdue">Still listed as active more than a year after primary completion <span class='muted'>({len(overdue)})</span></h2>
<p class="muted">Possible reasons include an outdated record, a delayed trial, or legitimate follow-up or extension periods after the primary outcome (common for
"active, not recruiting"). Check the registry record before drawing conclusions.</p>{ul(''.join(trial_row(r, extra=f' · primary completion {e(show_date(r.primary_completion))} · {STATUS_EN.get(r.status, r.status)}') for r in overdue.itertuples()))}"""
    (out / "readouts.html").write_text(page(f"Primary completion calendar · Parkinson's & Alzheimer's trials · {SITE_NAME}", body, canonical="readouts.html",
                                            desc="Upcoming and recent primary completion dates of Parkinson's and Alzheimer's phase 1–2/3 drug trials, by month."))

    # ---------- mechanisms ----------
    rows = []
    for code in [c for c in MECH_EN if c != "DX"]:
        g = act[act.mech_primary == code]
        if not len(g):
            continue
        cnt = lambda dis: int(g.disease.str.contains(dis).sum())
        ph = g.phase.astype(str).value_counts()
        rows.append((code, len(g), cnt("PD"), cnt("AD"), int(ph.get("1", 0) + ph.get("0/1 (초기 1상)", 0)), int(ph.get("1/2", 0) + ph.get("2", 0)), int(ph.get("2/3", 0))))
    rows.sort(key=lambda x: (x[0] == "OTHER", -x[1]))  # 미분류는 맨 뒤
    trs = "".join(f"<tr><td><a href='#m-{c}'>{MECH_EN[c]}</a></td><td>{GROUP_EN[rules.MECH_GROUP[c]]}</td><td class='num'>{n}</td><td class='num'>{p}</td><td class='num'>{a}</td><td class='num'>{p1}</td><td class='num'>{p2}</td><td class='num'>{p3}</td></tr>"
                  for c, n, p, a, p1, p2, p3 in rows)
    lists = "".join(f"<h3 id='m-{c}'>{MECH_EN[c]} <span class='muted'>({n})</span></h3>"
                    + ul("".join(trial_row(r) for r in act[act.mech_primary == c].sort_values("phase", ascending=False).itertuples()))
                    for c, n, *_ in rows)
    n_other = next((n for c, n, *_ in rows if c == "OTHER"), 0)
    body = f"""<h1>Active trials by mechanism</h1><p class="muted">{len(act):,} active trials (recruiting, not yet recruiting, enrolling by invitation,
or active and not recruiting). A trial listing both diseases counts under each disease column. {n_other} active trials ({n_other / max(len(act), 1):.0%}) are
"Other / unclassified" because the rules did not recognise the drug, so category counts are lower bounds. Class labels describe the mechanism's aim, not evidence.</p>
<div class="tablewrap"><table><thead><tr><th>Mechanism</th><th>Class</th><th>Active</th><th>PD</th><th>AD</th><th>Phase 1 (incl. early)</th><th>Phase 1/2 or 2</th><th>Phase 2/3</th></tr></thead>
<tbody>{trs}</tbody></table></div>{lists}"""
    (out / "mechanisms.html").write_text(page(f"Parkinson's & Alzheimer's trials by mechanism · {SITE_NAME}", body, canonical="mechanisms.html",
                                              desc="Active Parkinson's and Alzheimer's drug trials grouped by mechanism (alpha-synuclein, LRRK2, GBA, amyloid, tau, neuroinflammation and more) and phase."))

    # ---------- trial pages ----------
    bool_fields = [("untreated", "Requires untreated (de novo) PD"), ("dat_req", "Requires abnormal DaT scan"),
                   ("saa_req", "Requires α-synuclein seed amplification assay"), ("lrrk2", "LRRK2 variant carriers"), ("gba", "GBA variant carriers"),
                   ("amyloid_req", "Requires amyloid biomarker"), ("tau_pet_req", "Requires tau PET")]
    val_fields = [("hy_max", "Max Hoehn & Yahr stage"), ("dur_max_y", "Max years since diagnosis"), ("mmse_lo", "MMSE minimum"),
                  ("mmse_hi", "MMSE maximum"), ("cdr", "CDR")]
    hist = {n: g for n, g in ev.groupby("nct")}
    sm = [(u, meta["snapshot_date"]) for u in ("", "dashboard.html", "explore.html", "readouts.html", "mechanisms.html", "changes.html", "about.html")]

    def row(label, value):
        return f"<tr><th>{label}</th><td>{value}</td></tr>" if value not in ("", None) else ""

    def fmt(v):
        return f"{v:g}" if isinstance(v, float) else str(v)
    for r in s.itertuples():
        grp = r.group
        el = "".join(row(lab, e(fmt(getattr(r, f)))) for f, lab in val_fields if not pd.isna(getattr(r, f, None)))
        el += "".join(row(lab, "Yes") for f, lab in bool_fields if truthy(getattr(r, f, None)))
        if isinstance(r.ad_stages, str) and r.ad_stages:
            el += row("AD stages mentioned in criteria", e(", ".join(AD_STAGE_EN.get(x, x) for x in r.ad_stages.split(";"))))
        h = hist.get(r.nct)
        hh = ul("".join(ev_item(x, "../", link=False) for x in h.sort_values("date", ascending=False).itertuples())) if h is not None else \
            f"<p class='muted'>No tracked changes since tracking began ({track_start}).</p>"
        same = act[(act.mech_primary == r.mech_primary) & (act.nct != r.nct) & ~act.stale].head(8) if r.mech_primary != "OTHER" else act.iloc[0:0]
        mechs = ", ".join(MECH_EN.get(m, m) for m in str(r.mechs).split(";") if m)
        report = f' · <a href="{REPO_URL}/issues/new?title=Classification%20issue%20{r.nct}">Report a classification error</a>' if REPO_URL else ""
        conds = ", ".join(x for x in r.conditions.split(";") if x) if isinstance(r.conditions, str) else ""
        sites = (num(r.n_sites) + ((" · " + e(r.countries.replace(";", ", "))) if isinstance(r.countries, str) and r.countries else "")) \
            if not pd.isna(r.n_sites) and int(r.n_sites) > 0 else ""
        kv = (row("Mechanism (primary)", MECH_EN.get(r.mech_primary, r.mech_primary)) + row("All mechanisms", e(mechs))
              + row("Conditions listed", e(conds)) + row("Interventions", e(r.interventions)) + row("Sponsor", e(r.sponsor))
              + row("Collaborators", e(r.collaborators) if isinstance(r.collaborators, str) else "") + row("Enrollment", num(r.enrollment))
              + row("Start", e(show_date(r.start))) + row("Primary completion", e(show_date(r.primary_completion)))
              + row("First posted", e(r.first_posted)) + row("Last update", e(r.last_update)) + row("Sites", sites)
              + row("Healthy volunteers", "Accepted" if truthy(r.healthy_volunteers) else ""))
        warn = (f"<p class='note'>{badge('completion date passed, status not updated', 'warn')} The registered primary completion date "
                f"({e(show_date(r.primary_completion))}) has passed but the status is still “{STATUS_EN.get(r.status, r.status)}”. The record may be outdated.</p>") if r.stale else ""
        body = f"""<p class="crumb"><a href="../explore.html">Explore</a> › {r.nct}</p><h1>{e(r.title)}</h1>
<p>{badge(DISEASE_EN.get(r.disease, r.disease))} {badge(phase(r.phase))} {badge(STATUS_EN.get(r.status, r.status))} {badge(GROUP_EN.get(grp, grp), grp.lower())}
{badge('Results posted', 'ok') if r.has_results else ''} {badge('Healthy-volunteer study') if r.hv_study else ''}</p>{warn}
<div class="grid2"><table class="kv">{kv}</table>
<div><h2>Eligibility signals</h2>{'<table class="kv">' + el + '</table>' if el else "<p class='muted'>None extracted.</p>"}
<p class="muted small">Extracted automatically from the eligibility text; check the registry record.</p></div></div>
<p><a class="button" href="https://clinicaltrials.gov/study/{r.nct}">View on ClinicalTrials.gov</a>{report}</p>
<h2>Change history</h2>{hh}
{('<h2>Other active trials with the same mechanism</h2>' + ul(''.join(trial_row(x, '../') for x in same.itertuples()))) if len(same) else ''}"""
        desc = (f"{r.nct}: {DISEASE_EN.get(r.disease, r.disease)} {phase(r.phase)} trial ({MECH_EN.get(r.mech_primary, r.mech_primary)}), "
                f"{STATUS_EN.get(r.status, r.status).lower()}{', sponsor ' + r.sponsor if isinstance(r.sponsor, str) else ''}. Status, eligibility and change history.")
        jl = {"@context": "https://schema.org", "@type": "MedicalTrial", "name": r.title, "identifier": r.nct,
              "url": f"https://clinicaltrials.gov/study/{r.nct}", "trialDesign": phase(r.phase),
              "status": STATUS_EN.get(r.status, r.status), **({"sponsor": {"@type": "Organization", "name": r.sponsor}} if isinstance(r.sponsor, str) else {})}
        (out / "trials" / f"{r.nct}.html").write_text(page(f"{short_title(r.title)} ({r.nct}) · {SITE_NAME}", body, rel="../", desc=desc,
                                                           canonical=f"trials/{r.nct}.html", jsonld=jl, og_type="article"))
        lm = max([d for d in (r.lu_date, pdate(h.date.max()) if h is not None else None) if d] or [today])
        sm.append((f"trials/{r.nct}.html", lm.isoformat()))

    # ---------- about ----------
    body = f"""<h1>About</h1>
<p>{SITE_NAME} tracks interventional early phase 1 to phase 2/3 trials registered on ClinicalTrials.gov for Parkinson's disease and Alzheimer's disease
that test a drug, biologic, gene or cell therapy. It is rebuilt every day from the public ClinicalTrials.gov API (v2).</p>
<h2>What is in scope</h2><ul><li>The condition list names Parkinson's disease or Alzheimer's disease. A trial listing only atypical parkinsonism (e.g. PSP, MSA)
is excluded, but a trial that lists Parkinson's disease alongside them is included.</li>
<li>The experimental arm includes an intervention registered as a drug, biological, genetic or combination product. Imaging tracers and contrast agents do not count;
diagnostic, screening and health-services studies are excluded. Because this relies on how sponsors register interventions, some device or procedure trials
that register medication states as "drugs" slip through.</li>
<li>Phases: early phase 1, 1, 1/2, 2, 2/3. Healthy-volunteer studies of drugs developed for these diseases are included and flagged; headline counts exclude them.</li></ul>
<h2>Mechanism classification</h2><p>Each trial gets a primary mechanism from a rule dictionary (drug names and target words, searched in intervention names, then descriptions and titles, then summaries)
and a class: putative disease-modifying, symptomatic, or unclassified. "Putative disease-modifying" means the mechanism aims at disease biology; it says nothing about whether
the drug works. Accuracy was measured against blinded manual reading of 40 randomly sampled active trials that had not been
used to write the rules (rules version 2.5): class 82.5% (95% CI 68.0–91.3%), primary mechanism 75.0% (59.8–85.8%). Labels assigned as disease-modifying or symptomatic
were all correct in that sample; errors concentrated in "unclassified". The current rules (2.8) later fixed some of those errors, so re-scoring the same sample
(87.5% and 80.0%) is optimistic and is not used as the headline figure. Among 169 active trials the rules (version 2.4) excluded, 7 (4.1%, 2.0–8.3%) should have been included;
6 were fixed. Drugs the dictionary does not know end up "unclassified", so category counts are lower bounds. Treat labels as a starting point and check the registry record.</p>
<h2>Changes</h2><p>For trials in scope, each day's table is compared with the previous day's. Changes in status, phase, mechanism label, enrollment,
primary completion date, newly posted results, and new or removed registrations are logged and dated when first detected. Tracking started on {track_start}.
When this site's classification rules are updated, the resulting re-labels are not logged as changes. Registered dates are set by sponsors and often change.</p>
<h2>Use and citation</h2><p>Data are derived from ClinicalTrials.gov. The derived table is free to reuse with attribution. Not medical advice; for trial participation,
contact the study team listed on ClinicalTrials.gov.</p>
<p class="muted">Snapshot {meta['snapshot_date']} · {meta['n_in_scope']:,} trials in scope · {meta['n_active_in_scope']:,} active · classification rules {str(meta['rules']).replace('moduleA ', '')}</p>"""
    jl = {"@context": "https://schema.org", "@type": "Dataset", "name": f"{SITE_NAME}: Parkinson's and Alzheimer's phase 1–2/3 drug trials",
          "description": "Daily snapshot of Parkinson's and Alzheimer's early-phase drug trials from ClinicalTrials.gov, classified by mechanism, with a change log.",
          "isBasedOn": "https://clinicaltrials.gov", "dateModified": meta["snapshot_date"],
          **({"distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": f"{SITE_URL}/data/trials.csv"}]} if SITE_URL else {})}
    (out / "about.html").write_text(page(f"About and methods · {SITE_NAME}", body, canonical="about.html", jsonld=jl,
                                         desc="How NeuroTrials Watch selects, classifies and tracks Parkinson's and Alzheimer's trials, and how accurate the labels are."))

    # ---------- 404 (served for any missing path, so links must be absolute) ----------
    root = (SITE_URL + "/") if SITE_URL else ""
    (out / "404.html").write_text(page(f"Page not found · {SITE_NAME}", f"<h1>Page not found</h1><p>The trial or page may no longer be in scope. "
                                       f"Try <a href='{root}explore.html'>Explore</a> or the <a href='{root}index.html'>home page</a>.</p>", rel=root))

    # ---------- feed, sitemap, robots ----------
    def rfc822(d):
        return dt.datetime.combine(dt.date.fromisoformat(d), dt.time(12)).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for x in ev.sort_values("date", ascending=False).head(200).itertuples():
        link = f"{SITE_URL}/trials/{x.nct}.html" if SITE_URL else f"trials/{x.nct}.html"
        items.append(f"<item><title>{e(CHANGE_EN.get(x.kind, x.kind))}: {e(x.title)}</title><link>{link}</link>"
                     f"<guid isPermaLink=\"false\">{x.nct}-{x.kind}-{x.date}</guid><pubDate>{rfc822(x.date)}</pubDate>"
                     f"<description>{e(x.nct)} · {e(ev_change(x))}</description></item>")
    (out / "feed.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{SITE_NAME}</title>
<link>{SITE_URL or ''}/</link><description>{TAGLINE}</description><lastBuildDate>{rfc822(meta['snapshot_date'])}</lastBuildDate>{''.join(items)}</channel></rss>""")
    if SITE_URL:
        (out / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
                                         + "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{lm}</lastmod></url>" for u, lm in sm) + "</urlset>")
        (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    (out / ".nojekyll").write_text("")
    print(f"  site: {len(sm)} pages → {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
