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

    body = (f"<h1>Dashboard</h1><p class='muted'>Parkinson's and Alzheimer's phase 1–2/3 drug trials on ClinicalTrials.gov, snapshot of {today:%B %d, %Y}. "
            "Hover or focus a bar for its values; every chart has a data table below it.</p><div class='cards'>" + "".join(cards) + "</div>")
    return body
