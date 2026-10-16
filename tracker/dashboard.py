"""Dashboard page: inline SVG charts generated at build time (no chart library), with hover/focus tooltips (assets/app.js)
and a data table under every chart.

Charts
  1. Active trials by mechanism, Parkinson's vs Alzheimer's (horizontal paired bars)
  2. Active trials by phase, stacked by class (columns)
  3. New registrations per year by class (stacked columns; current year is partial)
  4. Primary completions due per month, next 12 months (columns)
  5. Active trials by recruitment status, with stale records shown separately (horizontal bars)
Colors: series slot 1 (blue) and slot 2 (orange) from the validated reference palette, plus a neutral gray for "unclassified".
"""
import datetime as dt
from html import escape
from .labels import MECH_EN, GROUP_EN, STATUS_EN, PHASE_EN

W = 520  # viewBox width of column charts (sized for a half-width card; the SVG scales to the card)


def e(x):
    return escape(str(x))


def nice_max(v):
    if v <= 5:
        return 5
    for step in (5, 10, 20, 25, 50, 100, 200, 250, 500):
        if v <= step * 5:
            return -(-v // step) * step
    return v


def ticks(vmax):
    step = vmax / 5
    return [round(step * i) for i in range(6)]


def legend(items):
    return "<div class='legend'>" + "".join(f"<span><i class='sw {cls}'></i>{e(lab)}</span>" for cls, lab in items) + "</div>"


def table(head, rows):
    th = "".join(f"<th>{e(h)}</th>" for h in head)
    tr = "".join("<tr>" + "".join(f"<td{' class=num' if isinstance(c, (int, float)) else ''}>{e(c)}</td>" for c in r) + "</tr>" for r in rows)
    return f"<details class='tbl'><summary>Show data table</summary><div class='tablewrap'><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div></details>"


def card(title, sub, svg, leg, tbl, cls=""):
    return f"<section class='card {cls}'><h2>{e(title)}</h2><p class='muted small'>{sub}</p>{leg}{svg}{tbl}</section>"


def bar_end(x, y, w, h, r=4, horizontal=True):
    """Bar with a 4px rounded data-end and a square baseline end (path)."""
    r = min(r, (h if horizontal else w) / 2, (w if horizontal else h))
    if w <= 0 or h <= 0:
        return ""
    if horizontal:
        return f"M{x},{y}H{x + w - r}Q{x + w},{y} {x + w},{y + r}V{y + h - r}Q{x + w},{y + h} {x + w - r},{y + h}H{x}Z"
    return f"M{x},{y + h}V{y + r}Q{x},{y} {x + r},{y}H{x + w - r}Q{x + w},{y} {x + w},{y + r}V{y + h}Z"


def hbars_paired(rows, a_lab, b_lab, a_cls, b_cls):
    """rows: [(label, a, b)]. HTML bars (text stays readable at any width): two thin bars per row, value at each tip."""
    vmax = max([max(a, b) for _, a, b in rows] + [1])
    out = [f"<div class='chart hbars' role='img' aria-label='{e(a_lab)} and {e(b_lab)} by category'>"]
    for lab, a, b in rows:
        bars = "".join(f"<div class='hb'><i class='bar {cls}' style='width:{100 * v / vmax:.1f}%'></i><span class='hv'>{v}</span></div>"
                       for v, cls in ((a, a_cls), (b, b_cls)))
        tip = f"{lab}|{a_lab}: {a}|{b_lab}: {b}"
        out.append(f"<div class='hrow hit' tabindex='0' data-tip='{e(tip)}'><div class='hl'>{e(lab)}</div><div class='hbs'>{bars}</div></div>")
    out.append("</div>")
    return "".join(out)


def columns_stacked(cats, series, classes, labels, partial=None):
    """cats: x labels; series: list of value lists (bottom→top); 2px surface gap between segments."""
    left, top, bottom = 34, 10, 26
    n = len(cats)
    tot = [sum(s[i] for s in series) for i in range(n)]
    vmax = nice_max(max(tot + [1]))
    ph = 220
    h = top + ph + bottom
    band = (W - left - 8) / n
    bw = min(24, band * 0.6)
    sy = lambda v: ph * v / vmax
    out = [f"<svg viewBox='0 0 {W} {h}' role='img' class='chart'><title>{e(', '.join(labels))} by {e('category')}</title>"]
    for tv in ticks(vmax):
        y = top + ph - sy(tv)
        out.append(f"<line class='grid' x1='{left}' x2='{W - 8}' y1='{y:.1f}' y2='{y:.1f}'/><text class='tick' x='{left - 6}' y='{y:.1f}' text-anchor='end' dominant-baseline='middle'>{tv}</text>")
    for i, c in enumerate(cats):
        x = left + band * i + (band - bw) / 2
        base = top + ph
        parts = []
        for k, s in enumerate(series):
            v = s[i]
            if not v:
                continue
            hgt = sy(v)
            last = all(series[m][i] == 0 for m in range(k + 1, len(series)))
            y0 = base - hgt
            gap = 2 if k > 0 else 0
            if last:
                out.append(f"<path class='mark {classes[k]}' d='{bar_end(x, y0, bw, hgt - gap, horizontal=False)}'/>")
            else:
                out.append(f"<rect class='mark {classes[k]}' x='{x:.1f}' y='{y0:.1f}' width='{bw:.1f}' height='{max(hgt - gap, 0):.1f}'/>")
            parts.append(f"{labels[k]}: {v}")
            base = y0
        star = "*" if partial is not None and i == partial else ""
        tip = f"{c}{star} · total {tot[i]}|" + "|".join(parts)
        out.append(f"<rect class='hit' x='{left + band * i:.1f}' y='{top}' width='{band:.1f}' height='{ph}' tabindex='0' data-tip='{e(tip)}'/>")
        if n <= 16 or i % 2 == 0:
            out.append(f"<text class='tick' x='{x + bw / 2:.1f}' y='{top + ph + 16}' text-anchor='middle'>{e(c)}{star}</text>")
    out.append(f"<line class='axis' x1='{left}' x2='{W - 8}' y1='{top + ph}' y2='{top + ph}'/></svg>")
    return "".join(out)


def hbars_single(rows, cls="s1", unit="", vmax=None):
    """rows: [(label, value, tip_extra)] single-series HTML bars."""
    vmax = vmax or max([v for _, v, _ in rows] + [1])
    out = ["<div class='chart hbars' role='img'>"]
    for lab, v, extra in rows:
        tip = f"{lab}|{v}{unit}" + (f"|{extra}" if extra else "")
        out.append(f"<div class='hrow hit' tabindex='0' data-tip='{e(tip)}'><div class='hl'>{e(lab)}</div><div class='hbs'><div class='hb'>"
                   f"<i class='bar {cls}' style='width:{100 * v / vmax:.1f}%'></i><span class='hv'>{v}{unit}</span></div></div></div>")
    out.append("</div>")
    return "".join(out)


def stacked100(rows, labels, classes):
    """rows: [(label, [counts…])] → 100% stacked HTML bars with 2px surface gaps."""
    out = ["<div class='chart hbars' role='img'>"]
    for lab, vals in rows:
        tot = sum(vals) or 1
        segs = "".join(f"<i class='seg {c}' style='width:{100 * v / tot:.2f}%'></i>" for v, c in zip(vals, classes) if v)
        tip = f"{lab} (n={sum(vals)})|" + "|".join(f"{l}: {v} ({100 * v / tot:.0f}%)" for l, v in zip(labels, vals))
        out.append(f"<div class='hrow hit' tabindex='0' data-tip='{e(tip)}'><div class='hl'>{e(lab)}</div><div class='stack'>{segs}</div></div>")
    out.append("</div>")
    return "".join(out)


RAMP = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281"]


def heatmap(row_labels, col_labels, m, corner=""):
    """Sequential one-hue (blue) heatmap as an HTML table; zero cells stay blank; ink chosen by fill lightness."""
    vmax = max([v for r in m for v in r] + [1])
    th = f"<th>{e(corner)}</th>" + "".join(f"<th class='num'>{e(c)}</th>" for c in col_labels)
    trs = []
    for lab, r in zip(row_labels, m):
        tds = []
        for c, v in zip(col_labels, r):
            if not v:
                tds.append("<td class='hm0'></td>")
                continue
            k = min(len(RAMP) - 1, int(round((len(RAMP) - 1) * v / vmax)))
            ink = "#0b0b0b" if k <= 5 else "#ffffff"
            tds.append(f"<td class='hm hit' tabindex='0' style='background:{RAMP[k]};color:{ink}' data-tip='{e(lab)} · {e(c)}|{v} trials'>{v}</td>")
        trs.append(f"<tr><th class='rl'>{e(lab)}</th>{''.join(tds)}</tr>")
    return f"<div class='tablewrap chart'><table class='heat'><thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table></div>"


def lines(xs, series, classes, labels, ymax=100, unit="%", notes=None, width=None):
    """SVG line chart (2px lines, 8px end markers with surface ring) with one hit column per x for the shared tooltip."""
    W = width or globals()["W"]
    left, top, ph, bottom = 34, 10, 200, 24
    h = top + ph + bottom
    n = len(xs)
    step = (W - left - 16) / max(n - 1, 1)
    sx = lambda i: left + step * i
    sy = lambda v: top + ph - ph * v / ymax
    out = [f"<svg viewBox='0 0 {W} {h}' role='img' class='chart'><title>{e(', '.join(labels))}</title>"]
    for tv in ticks(ymax):
        out.append(f"<line class='grid' x1='{left}' x2='{W - 8}' y1='{sy(tv):.1f}' y2='{sy(tv):.1f}'/><text class='tick' x='{left - 6}' y='{sy(tv):.1f}' text-anchor='end' dominant-baseline='middle'>{tv}</text>")
    for k, ser in enumerate(series):
        pts = [(sx(i), sy(v)) for i, v in enumerate(ser) if v is not None]
        if len(pts) > 1:
            out.append(f"<polyline class='ln {classes[k]}' points='{' '.join(f'{x:.1f},{y:.1f}' for x, y in pts)}'/>")
        if pts:
            x, y = pts[-1]
            out.append(f"<circle class='dot {classes[k]}' cx='{x:.1f}' cy='{y:.1f}' r='4'/>")
    for i, x in enumerate(xs):
        parts = [f"{labels[k]}: {'—' if series[k][i] is None else f'{series[k][i]:.0f}{unit}'}" + (f" ({notes[k][i]})" if notes else "") for k in range(len(series))]
        out.append(f"<rect class='hit' x='{sx(i) - step / 2:.1f}' y='{top}' width='{step:.1f}' height='{ph}' tabindex='0' data-tip='{e(str(x) + '|' + '|'.join(parts))}'/>")
        if n <= 14 or i % 2 == 0:
            out.append(f"<text class='tick' x='{sx(i):.1f}' y='{top + ph + 16}' text-anchor='middle'>{e(x)}</text>")
    out.append(f"<line class='axis' x1='{left}' x2='{W - 8}' y1='{top + ph}' y2='{top + ph}'/></svg>")
    return "".join(out)


def median(v):
    v = sorted(x for x in v if x == x)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def quart(v, q):
    v = sorted(x for x in v if x == x)
    if not v:
        return None
    i = (len(v) - 1) * q
    lo = int(i)
    return v[lo] + (v[min(lo + 1, len(v) - 1)] - v[lo]) * (i - lo)


def section(title, sub, cards):
    return f"<h2 class='sec'>{e(title)}</h2><p class='muted'>{sub}</p><div class='cards'>{''.join(cards)}</div>"


def build(s, act, today, group_en=GROUP_EN):
    """s: in-scope trials (with group, pc_date, fp_date, hv_study, stale); act: active subset. Returns (body_html, n_charts)."""
    cards = []
    core = act[~act.hv_study]

    # 1. mechanisms, PD vs AD (putative disease-modifying + symptomatic; unclassified last)
    mrows = []
    for code, lab in MECH_EN.items():
        if code == "DX":
            continue
        g = core[core.mech_primary == code]
        if len(g):
            mrows.append((lab, int(g.disease.str.contains("PD").sum()), int(g.disease.str.contains("AD").sum()), code))
    mrows.sort(key=lambda r: (r[3] == "OTHER", -(r[1] + r[2])))
    svg = hbars_paired([(l, a, b) for l, a, b, _ in mrows], "Parkinson's", "Alzheimer's", "s1", "s2")
    cards.append(card("Active trials by mechanism", f"{len(core):,} active trials, healthy-volunteer studies excluded. A trial listing both diseases counts in both bars. "
                      "Unclassified = drug not recognised by the rules, so other bars are lower bounds.",
                      svg, legend([("s1", "Parkinson's"), ("s2", "Alzheimer's")]),
                      table(["Mechanism", "Parkinson's", "Alzheimer's"], [(l, a, b) for l, a, b, _ in mrows]), "wide"))

    # 2. phase × class
    phases = ["0/1 (초기 1상)", "1", "1/2", "2", "2/3"]
    pl = [PHASE_EN.get(p, p).replace("Phase ", "Ph ").replace("Early phase 1", "Early Ph 1") for p in phases]
    ser = [[int(((core.phase.astype(str) == p) & (core.group == gcode)).sum()) for p in phases] for gcode in ("DMT", "SYM", "UNK")]
    labs = [group_en["DMT"], group_en["SYM"], group_en["UNK"]]
    svg = columns_stacked(pl, ser, ["s1", "s2", "s0"], labs)
    cards.append(card("Active trials by phase and class", "Class describes what the mechanism aims at, not evidence that the drug works.",
                      svg, legend([("s1", labs[0]), ("s2", labs[1]), ("s0", labs[2])]),
                      table(["Phase"] + labs, [(pl[i], ser[0][i], ser[1][i], ser[2][i]) for i in range(len(pl))])))

    # 3. registrations per year
    y0 = 2012
    years = list(range(y0, today.year + 1))
    fy = s.fp_date.map(lambda d: d.year if d else None)
    ser = [[int(((fy == y) & (s.group == gcode)).sum()) for y in years] for gcode in ("DMT", "SYM", "UNK")]
    svg = columns_stacked([str(y)[2:] if i else str(y) for i, y in enumerate(years)], ser, ["s1", "s2", "s0"], labs, partial=len(years) - 1)
    cards.append(card("New registrations per year", f"In-scope trials by year first posted on ClinicalTrials.gov, {y0}–{today.year}. "
                      f"* {today.year} is year to date (through {today:%b %d}).",
                      svg, legend([("s1", labs[0]), ("s2", labs[1]), ("s0", labs[2])]),
                      table(["Year"] + labs, [(str(y) + ("*" if y == today.year else ""), ser[0][i], ser[1][i], ser[2][i]) for i, y in enumerate(years)])))

    # 4. primary completions next 12 months
    months = []
    m0 = dt.date(today.year, today.month, 1)
    for k in range(12):
        y, m = divmod(m0.month - 1 + k, 12)
        months.append(dt.date(m0.year + y, m + 1, 1))
    keyed = act.pc_date.map(lambda d: d.strftime("%Y-%m") if d else None)
    vals = [int((keyed == d.strftime("%Y-%m")).sum()) for d in months]
    svg = columns_stacked([d.strftime("%b") + ("" if d.month != 1 and k else " " + d.strftime("%y")) for k, d in enumerate(months)], [vals], ["s1"], ["Trials"])
    cards.append(card("Primary completions due, next 12 months", f"Active trials by registered primary completion month, {months[0]:%b %Y}–{months[-1]:%b %Y}. "
                      "Dates are set by sponsors and often slip; see the <a href='readouts.html'>completion calendar</a> for the trials.",
                      svg, "", table(["Month", "Trials"], [(d.strftime("%b %Y"), v) for d, v in zip(months, vals)])))

    # 5. status, with stale shown separately
    order = ["RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING"]
    srows = [(STATUS_EN[st], int(((act.status == st) & ~act.stale).sum()), int(((act.status == st) & act.stale).sum())) for st in order]
    svg = hbars_paired(srows, "Primary completion still ahead", "Completion date passed, status not updated", "s1", "s2")
    cards.append(card("Active trials by recruitment status", f"{len(act):,} active trials (healthy-volunteer studies included). The second bar counts records whose "
                      "registered primary completion date has passed without a status update; they may be outdated or in follow-up.",
                      svg, legend([("s1", "Primary completion still ahead"), ("s2", "Completion date passed, status not updated")]),
                      table(["Status", "Completion ahead", "Completion passed"], srows)))

    import pandas as pd
    ind = s.sponsor_class.eq("INDUSTRY")
    s = s.assign(industry=ind, sy=s.start.map(lambda x: int(x[:4]) if isinstance(x, str) and x[:4].isdigit() else None))
    act = s[s.active.astype(bool)]
    core = act[~act.hv_study]
    is_pd = lambda d: d.disease.str.contains("PD")
    is_ad = lambda d: d.disease.str.contains("AD")
    pct = lambda a, b: 100 * a / b if b else 0
    ph_groups = [("Phase 1 (incl. early)", ["0/1 (초기 1상)", "1"]), ("Phase 1/2", ["1/2"]), ("Phase 2", ["2"]), ("Phase 2/3", ["2/3"])]

    # ---- sponsors & geography ----
    sp = []
    rows = []
    for lab, sub in [("Parkinson's · putative DMT", core[is_pd(core) & (core.group == "DMT")]), ("Alzheimer's · putative DMT", core[is_ad(core) & (core.group == "DMT")]),
                     ("Parkinson's · symptomatic", core[is_pd(core) & (core.group == "SYM")]), ("Alzheimer's · symptomatic", core[is_ad(core) & (core.group == "SYM")])]:
        rows.append((lab, [int(sub.industry.sum()), int((~sub.industry).sum())]))
    sp.append(card("Who sponsors active trials", "Lead sponsor registered as industry vs. academic, government or other. Healthy-volunteer studies excluded.",
                   stacked100(rows, ["Industry", "Academic / other"], ["s1", "s2"]), legend([("s1", "Industry"), ("s2", "Academic / other")]),
                   table(["Group", "Industry", "Academic / other"], [(l, v[0], v[1]) for l, v in rows])))
    top_sp = core.sponsor.value_counts().head(12)
    rows = [(n, int(c), "industry" if core[core.sponsor == n].industry.any() else "academic / other") for n, c in top_sp.items()]
    sp.append(card("Most active lead sponsors", "Lead sponsors with the most active trials (healthy-volunteer studies excluded). Subsidiaries are not merged.",
                   hbars_single(rows), "", table(["Sponsor", "Active trials", "Type"], rows)))
    cc = {}
    for r in core.itertuples():
        for c in set(str(r.countries).split(";")) if isinstance(r.countries, str) else []:
            if c:
                d = cc.setdefault(c, [0, 0])
                d[0] += "PD" in r.disease
                d[1] += "AD" in r.disease
    top_c = sorted(cc.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))[:15]
    n_nosite = int(core.countries.isna().sum())
    sp.append(card("Countries with sites in active trials", f"Number of active trials with at least one registered site in the country (a multinational trial counts in each). "
                   f"{n_nosite} active trials list no sites yet.", hbars_paired([(c, v[0], v[1]) for c, v in top_c], "Parkinson's", "Alzheimer's", "s1", "s2"),
                   legend([("s1", "Parkinson's"), ("s2", "Alzheimer's")]), table(["Country", "Parkinson's", "Alzheimer's"], [(c, v[0], v[1]) for c, v in top_c]), "wide"))

    # ---- pipeline structure ----
    pipe = []
    mcodes = [c for c in MECH_EN if c not in ("DX", "OTHER")] + ["OTHER"]
    mrows = [c for c in mcodes if (core.mech_primary == c).any()]
    phl = [l for l, _ in ph_groups]
    m = [[int(((core.mech_primary == c) & core.phase.astype(str).isin(ps)).sum()) for _, ps in ph_groups] for c in mrows]
    pipe.append(card("Pipeline: mechanism × phase", "Active trials, healthy-volunteer studies excluded. Darker = more trials.",
                     heatmap([MECH_EN[c] for c in mrows], phl, m, "Mechanism"), "", "", "wide"))
    yrs = list(range(today.year - 10, today.year + 1))
    started = s[s.sy.isin(yrs) & ~s.hv_study]
    m2 = [[int(((started.mech_primary == c) & (started.sy == y)).sum()) for y in yrs] for c in mrows]
    pipe.append(card("Trial starts by mechanism and year", f"In-scope trials by registered start year, {yrs[0]}–{yrs[-1]} ({yrs[-1]} includes planned starts later this year). "
                     "Shows which mechanisms are gaining or losing activity.", heatmap([MECH_EN[c] for c in mrows], [str(y) for y in yrs], m2, "Mechanism"), "", "", "wide"))

    # ---- design ----
    des = []
    med_rows, tbl = [], []
    for lab, ps in ph_groups:
        g = core[core.phase.astype(str).isin(ps)]
        a_, b_ = g[is_pd(g)].enrollment.dropna().tolist(), g[is_ad(g)].enrollment.dropna().tolist()
        ma, mb = median(a_), median(b_)
        med_rows.append((lab, int(ma or 0), int(mb or 0)))
        tbl.append((lab, int(ma or 0), f"{quart(a_, .25) or 0:.0f}–{quart(a_, .75) or 0:.0f}", len(a_), int(mb or 0), f"{quart(b_, .25) or 0:.0f}–{quart(b_, .75) or 0:.0f}", len(b_)))
    des.append(card("Planned enrollment by phase (median)", "Active trials, healthy-volunteer studies excluded. Registered target or actual enrollment; the table gives the interquartile range.",
                    hbars_paired(med_rows, "Parkinson's", "Alzheimer's", "s1", "s2"), legend([("s1", "Parkinson's"), ("s2", "Alzheimer's")]),
                    table(["Phase", "PD median", "PD IQR", "PD n", "AD median", "AD IQR", "AD n"], tbl)))
    from .generate import pdate
    def dur(r):
        a_, b_ = pdate(r.start), pdate(r.primary_completion)
        return (b_ - a_).days / 30.44 if a_ and b_ and b_ > a_ else None
    durs = core.apply(dur, axis=1)
    drows, dtbl = [], []
    for lab, ps in ph_groups:
        sel = core.phase.astype(str).isin(ps)
        a_, b_ = durs[sel & is_pd(core)].dropna().tolist(), durs[sel & is_ad(core)].dropna().tolist()
        drows.append((lab, round(median(a_) or 0), round(median(b_) or 0)))
        dtbl.append((lab, round(median(a_) or 0), len(a_), round(median(b_) or 0), len(b_)))
    des.append(card("Planned time to primary completion (median months)", "From registered start to registered primary completion, active trials. Includes recruitment time.",
                    hbars_paired(drows, "Parkinson's", "Alzheimer's", "s1", "s2"), legend([("s1", "Parkinson's"), ("s2", "Alzheimer's")]),
                    table(["Phase", "PD months", "PD n", "AD months", "AD n"], dtbl)))
    by = list(range(today.year - 12, today.year + 1))
    adp, pdd, pds, nad, npd = [], [], [], [], []
    for y in by:
        g = s[(s.sy == y) & ~s.hv_study]
        ga, gp = g[is_ad(g)], g[is_pd(g)]
        nad.append(len(ga)); npd.append(len(gp))
        adp.append(pct(ga.amyloid_req.map(lambda v: str(v) == "True").sum(), len(ga)) if len(ga) >= 5 else None)
        pdd.append(pct(gp.dat_req.map(lambda v: str(v) == "True").sum(), len(gp)) if len(gp) >= 5 else None)
        pds.append(pct(gp.saa_req.map(lambda v: str(v) == "True").sum(), len(gp)) if len(gp) >= 5 else None)
    ymax = nice_max(max([v for v in adp + pdd + pds if v is not None] + [10]))
    svg = lines([str(y) for y in by], [adp, pdd, pds], ["s1", "s2", "s3"], ["AD: amyloid biomarker required", "PD: abnormal DaT scan required", "PD: α-syn SAA required"],
                ymax=min(ymax, 100), notes=[[f"n={n}" for n in nad], [f"n={n}" for n in npd], [f"n={n}" for n in npd]], width=1000)
    des.append(card("Biomarker-based eligibility over time", "Share of in-scope trials, by start year, whose eligibility text requires the biomarker (automated text extraction; "
                    "under-detects, so read the trend rather than the level). Years with fewer than 5 trials are not plotted.",
                    svg, legend([("s1", "AD: amyloid biomarker required"), ("s2", "PD: abnormal DaT scan required"), ("s3", "PD: α-syn SAA required")]),
                    table(["Start year", "AD trials", "AD amyloid %", "PD trials", "PD DaT %", "PD SAA %"],
                          [(y, nad[i], "—" if adp[i] is None else round(adp[i]), npd[i], "—" if pdd[i] is None else round(pdd[i]), "—" if pds[i] is None else round(pds[i])) for i, y in enumerate(by)]), "wide"))

    # ---- execution & transparency ----
    exe = []
    ended = s[s.status.isin(["COMPLETED", "TERMINATED", "WITHDRAWN"]) & (s.sy >= 2010) & ~s.hv_study]
    rows = []
    for lab, g in [("Putative disease-modifying", ended[ended.group == "DMT"]), ("Symptomatic", ended[ended.group == "SYM"]), ("Unclassified", ended[ended.group == "UNK"]),
                   ("Industry sponsor", ended[ended.industry]), ("Academic / other sponsor", ended[~ended.industry])]:
        rows.append((lab, [int((g.status == "COMPLETED").sum()), int((g.status == "TERMINATED").sum()), int((g.status == "WITHDRAWN").sum())]))
    exe.append(card("How trials ended", "In-scope trials started 2010 or later that have ended. Terminated = stopped early; withdrawn = stopped before enrolling. "
                    "Reasons (safety, efficacy, business, enrollment) are not shown here.",
                    stacked100(rows, ["Completed", "Terminated", "Withdrawn"], ["s0", "s2", "s1"]),
                    legend([("s0", "Completed"), ("s2", "Terminated"), ("s1", "Withdrawn")]),
                    table(["Group", "Completed", "Terminated", "Withdrawn"], [(l, *v) for l, v in rows])))
    cutoff = dt.date(today.year - 1, today.month, 1)
    comp = s[(s.status == "COMPLETED") & s.pc_date.map(lambda d: d is not None and dt.date(2015, 1, 1) <= d < cutoff)]
    rows = []
    for lab, g in [("Industry · phase 2–2/3", comp[comp.industry & comp.phase.astype(str).isin(["1/2", "2", "2/3"])]),
                   ("Academic / other · phase 2–2/3", comp[~comp.industry & comp.phase.astype(str).isin(["1/2", "2", "2/3"])]),
                   ("Industry · phase 1", comp[comp.industry & comp.phase.astype(str).isin(["0/1 (초기 1상)", "1"])]),
                   ("Academic / other · phase 1", comp[~comp.industry & comp.phase.astype(str).isin(["0/1 (초기 1상)", "1"])])]:
        rows.append((lab, round(pct(g.has_results.astype(bool).sum(), len(g))), f"{int(g.has_results.astype(bool).sum())} of {len(g)}"))
    exe.append(card("Results posted on ClinicalTrials.gov", f"Completed trials with primary completion from Jan 2015 to {cutoff:%b %Y} (at least a year ago). "
                    "Phase 1 and many non-US trials have no legal duty to post here, and results may be published elsewhere, so a gap is not evidence of non-reporting.",
                    hbars_single(rows, unit="%", vmax=100), "", table(["Group", "% with results", "Count"], rows)))
    stl = act[act.stale]
    rows = [("Industry", round(pct(stl.industry.sum(), act.industry.sum())), f"{int(stl.industry.sum())} of {int(act.industry.sum())}"),
            ("Academic / other", round(pct((~stl.industry).sum(), (~act.industry).sum())), f"{int((~stl.industry).sum())} of {int((~act.industry).sum())}")]
    exe.append(card("Active records past their completion date", "Share of active trials whose registered primary completion date has passed without a status update, by sponsor type.",
                    hbars_single(rows, unit="%", vmax=100), "", table(["Sponsor type", "% past date", "Count"], rows)))

    # ---- key findings (computed) ----
    dmt = core[core.group == "DMT"]
    ph2 = core[core.phase.astype(str).isin(["2"])]
    def pooled(years):
        g = s[s.sy.isin(years) & ~s.hv_study]
        g = g[is_ad(g)]
        return (pct(g.amyloid_req.map(lambda v: str(v) == "True").sum(), len(g)), len(g))
    rec_ad, old_ad = pooled(by[-3:]), pooled(by[:3])
    allr = comp[comp.phase.astype(str).isin(["1/2", "2", "2/3"])]
    us = cc.get("United States", [0, 0])
    kf = [f"Industry is the lead sponsor of <b>{pct(dmt.industry.sum(), len(dmt)):.0f}%</b> of active putative disease-modifying trials "
          f"(Parkinson's {pct(dmt[is_pd(dmt)].industry.sum(), len(dmt[is_pd(dmt)])):.0f}%, Alzheimer's {pct(dmt[is_ad(dmt)].industry.sum(), len(dmt[is_ad(dmt)])):.0f}%).",
          f"Median planned enrollment of active phase 2 trials: <b>{int(median(ph2[is_pd(ph2)].enrollment.dropna().tolist()) or 0)}</b> (Parkinson's) and "
          f"<b>{int(median(ph2[is_ad(ph2)].enrollment.dropna().tolist()) or 0)}</b> (Alzheimer's) participants.",
          f"<b>{pct(allr.has_results.astype(bool).sum(), len(allr)):.0f}%</b> of completed phase 1/2–2/3 trials that reached primary completion in Jan 2015–{cutoff:%b %Y} have results posted on ClinicalTrials.gov.",
          f"<b>{len(act[act.stale])}</b> of {len(act)} active records ({pct(len(act[act.stale]), len(act)):.0f}%) are past their registered primary completion date without a status update.",
          f"The United States has sites in <b>{pct(sum(1 for r in core.itertuples() if isinstance(r.countries, str) and 'United States' in r.countries.split(';')), len(core)):.0f}%</b> of active trials."]
    if rec_ad[1] and old_ad[1]:
        kf.append(f"Alzheimer's trials requiring an amyloid biomarker: <b>{rec_ad[0]:.0f}%</b> of {rec_ad[1]} trials starting {by[-3]}–{by[-1]} vs "
                  f"{old_ad[0]:.0f}% of {old_ad[1]} starting {by[0]}–{by[2]} (automated text extraction under-detects; read as a trend).")
    kf_html = "<section class='card wide kf'><h2>Key findings</h2><ul>" + "".join(f"<li>{x}</li>" for x in kf) + "</ul><p class='muted small'>Computed automatically from today's snapshot.</p></section>"

    body = (f"<h1>Dashboard</h1><p class='muted'>Parkinson's and Alzheimer's phase 1–2/3 drug trials on ClinicalTrials.gov, snapshot of {today:%B %d, %Y}. "
            "Hover or focus a bar or cell for its values; every chart has a data table. Jump to: <a href='#landscape'>Landscape</a> · <a href='#pipeline'>Pipeline</a> · "
            "<a href='#sponsors'>Sponsors &amp; geography</a> · <a href='#design'>Trial design</a> · <a href='#execution'>Execution &amp; transparency</a></p>"
            f"<div class='cards'>{kf_html}</div>"
            + f"<div id='landscape'>{section('Landscape', 'What is active now, and how the field has grown.', cards)}</div>"
            + f"<div id='pipeline'>{section('Pipeline', 'Where activity sits by mechanism and phase, and how it is shifting.', pipe)}</div>"
            + f"<div id='sponsors'>{section('Sponsors & geography', 'Who runs the trials and where.', sp)}</div>"
            + f"<div id='design'>{section('Trial design', 'Size, duration and biomarker-based eligibility.', des)}</div>"
            + f"<div id='execution'>{section('Execution & transparency', 'How trials end, results posting, and record freshness.', exe)}</div>")
    return body
