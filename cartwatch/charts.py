"""Chart primitives: HTML bars and inline SVG built at generation time (no chart library), each with hover/focus
tooltips (assets/app.js) and a data table. Palette: validated reference slots s1 blue, s2 orange, s3 aqua, s0 neutral gray."""
import datetime as dt
from html import escape

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
    return f"<div class='tablewrap'><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>"


def card(title, sub, svg, leg, tbl, cls="", take="", why=""):
    """Takeaway first: chart name (eyebrow) → takeaway headline → why it matters → chart → what is shown (method) → data table."""
    head = f"<div class='eyebrow'>{e(title)}</div><h2>{take}</h2>" if take else f"<h2>{e(title)}</h2>"
    why = f"<p class='why'>{why}</p>" if why else ""
    fold = f"<details class='tbl'><summary>How it's counted{' · data table' if tbl else ''}</summary><p class='muted small'>{sub}</p>{tbl}</details>"
    return f"<section class='card {cls}'>{head}{why}{leg}{svg}{fold}</section>"


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
        bars = "".join(f"<div class='hb'><i class='bar {cls}' style='width:{88 * v / vmax:.1f}%'></i><span class='hv'>{v}</span></div>"
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
                   f"<i class='bar {cls}' style='width:{88 * v / vmax:.1f}%'></i><span class='hv'>{v}{unit}</span></div></div></div>")
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


def spark(vals, label=""):
    """Tiny trend line for a KPI tile (no axes; the tile's numbers carry the values). None = gap."""
    pts = [(i, v) for i, v in enumerate(vals) if v is not None]
    if len(pts) < 3:
        return ""
    w, h, n = 120, 30, len(vals)
    lo, hi = min(v for _, v in pts), max(v for _, v in pts)
    sx = lambda i: 2 + (w - 6) * i / max(n - 1, 1)
    sy = lambda v: h - 4 - (h - 8) * ((v - lo) / (hi - lo) if hi > lo else .5)
    d = " ".join(f"{sx(i):.1f},{sy(v):.1f}" for i, v in pts)
    x, y = sx(pts[-1][0]), sy(pts[-1][1])
    return (f"<svg class='spark' viewBox='0 0 {w} {h}' role='img' aria-label='{e(label)}'><polyline points='{d}'/>"
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='3'/></svg>")


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


