"""Dashboard: every chart leads with a computed takeaway, a why-it-matters line, then the chart and a fold with method and data."""
import datetime as dt
from .charts import (e, legend, table, card, hbars_paired, columns_stacked, hbars_single, stacked100, heatmap, lines, spark,
                     median, section, nice_max)
from .labels import DISEASE_LABEL, MODALITIES, MOD_CLS, PLATFORMS, PHASE_EN

P = lambda a, b: round(100 * a / b) if b else 0


def build(t, today):
    act = t[t.active]
    cell = act[act.modality != "T-cell engager"]
    years = list(range(2019, today.year + 1))
    ly = today.year - 1

    # ---------- landscape ----------
    land = []
    dz = act.diseases.str.split(";").explode()
    dz = dz[dz.notna() & (dz != "")]
    cnt = dz.value_counts().to_dict()
    drows = sorted(cnt.items(), key=lambda kv: (kv[0] == "OTHER", -kv[1]))
    rows = [(DISEASE_LABEL[d], v, "") for d, v in drows]
    lup = len(set(act[act.diseases.str.contains("SLE|LN")].nct))
    second = next((r for r in rows if not r[0].startswith(("Systemic lupus", "Lupus"))), rows[0])
    land.append(card("Active trials by disease",
                     "Active = recruiting, not yet recruiting, enrolling by invitation, or active and not recruiting. A trial that enrolls several diseases "
                     "counts under each (for example a lupus trial that also enrolls lupus nephritis), so bars add up to more than the number of trials.",
                     hbars_single(rows), "", table(["Disease", "Active trials"], [(a, b) for a, b, _ in rows]), "wide",
                     f"Lupus leads: <b>{lup}</b> active trials include SLE or lupus nephritis; next is <b>{e(second[0])}</b> ({second[1]})",
                     "Shows where patients, investigators and sponsors are competing hardest, and which diseases are still early ground."))
    mrows = [(m, int((act.modality == m).sum()), "") for m in MODALITIES if (act.modality == m).any()]
    land.append(card("Active trials by modality", "Modality is read from the intervention names, titles and descriptions with published rules (see About).",
                     hbars_single(mrows), "", table(["Modality", "Active trials"], [(a, b) for a, b, _ in mrows]), "",
                     f"CAR-T is <b>{P(mrows[0][1], len(act))}%</b> of active trials; T-cell engagers <b>{P(int((act.modality == 'T-cell engager').sum()), len(act))}%</b>",
                     "Cell therapy needs apheresis, manufacturing and conditioning chemotherapy; engagers are off-the-shelf infusions. The mix shapes cost and access."))
    ser = [[int(((t.fy == y) & (t.modality == m)).sum()) for y in years] for m in ("CAR-T", "CAR-NK", "T-cell engager")]
    ser.append([int(((t.fy == y) & t.modality.isin(["CAAR-T", "CAR-Treg"])).sum()) for y in years])
    labs = ["CAR-T", "CAR-NK", "T-cell engager", "CAAR-T / CAR-Treg"]
    tot = [sum(s[i] for s in ser) for i in range(len(years))]
    a5, b5 = tot[years.index(ly)], tot[years.index(ly - 3)] if ly - 3 in years else 0
    land.append(card("New trials registered per year", f"In-scope trials by year first posted on ClinicalTrials.gov, {years[0]}–{today.year}. * {today.year} is year to date.",
                     columns_stacked([str(y) if i == 0 else str(y)[2:] for i, y in enumerate(years)], ser, ["s1", "s3", "s2", "s0"], labs, partial=len(years) - 1),
                     legend(list(zip(["s1", "s3", "s2", "s0"], labs))),
                     table(["Year"] + labs, [(str(y) + ("*" if y == today.year else ""), *[s[i] for s in ser]) for i, y in enumerate(years)]), "",
                     f"<b>{a5}</b> trials registered in {ly}, vs <b>{b5}</b> in {ly - 3}",
                     "The field went from case reports to a crowded pipeline in a few years; this is the pace of new entrants."))
    order = ["Early 1", "1", "1/2", "2", "2/3", "3", "Not applicable"]
    prow = [(PHASE_EN.get(p, p), int((act.phase.astype(str) == p).sum()), "") for p in order if (act.phase.astype(str) == p).any()]
    early = int(act.phase.astype(str).isin(["Early 1", "1", "1/2"]).sum())
    late = int(act.phase.astype(str).isin(["2/3", "3"]).sum())
    land.append(card("Active trials by phase", "Registered phase. Investigator-initiated studies in China are often registered as early phase 1.",
                     hbars_single(prow), "", table(["Phase", "Active trials"], [(a, b) for a, b, _ in prow]), "",
                     f"<b>{P(early, len(act))}%</b> of active trials are phase 1 or 1/2; only <b>{late}</b> are phase 2/3 or 3",
                     "Almost all evidence is still early and uncontrolled. Durable, randomized data will come from a handful of late trials."))

    # ---------- targets & platforms ----------
    tp = []
    trows = [(k, int(v), "") for k, v in act.target.value_counts().items()]
    trows.sort(key=lambda r: (r[0] == "Other / not stated", -r[1]))
    cd19 = int(act.target.str.contains("CD19").sum())
    tp.append(card("Targets of active trials", "Antigens named in the title or intervention names (descriptions only if those name none). "
                   "'Other / not stated' includes undisclosed targets.", hbars_single(trows), "", table(["Target", "Active trials"], [(a, b) for a, b, _ in trows]), "",
                   f"<b>{P(cd19, len(act))}%</b> of active trials hit CD19 (alone or with another target); <b>{int(act.target.str.contains('BCMA').sum())}</b> hit BCMA",
                   "CD19 removes B cells; BCMA reaches long-lived plasma cells that make autoantibodies. Dual targets try to do both."))
    yrs = list(range(2021, today.year + 1))
    c_all = t[t.modality.isin(["CAR-T", "CAR-NK", "CAAR-T", "CAR-Treg"])]
    shares = {p: [] for p in PLATFORMS}
    notes = {p: [] for p in PLATFORMS}
    for y in yrs:
        g = c_all[c_all.fy == y]
        for p in PLATFORMS:
            shares[p].append(P(int((g.platform == p).sum()), len(g)) if len(g) >= 10 else None)
            notes[p].append(f"n={len(g)}")
    ok = [i for i in range(len(yrs)) if shares["Autologous"][i] is not None]
    i0, i1 = (ok[0], ok[-1]) if ok else (0, len(yrs) - 1)
    off_then = sum(shares[p][i0] or 0 for p in ("Allogeneic", "In vivo / mRNA"))
    off_now = sum(shares[p][i1] or 0 for p in ("Allogeneic", "In vivo / mRNA"))
    y0, y1 = yrs[i0], yrs[i1]
    tp.append(card("Cell therapy platform by registration year", "Share of in-scope cell-therapy trials first posted each year. Allogeneic = donor or "
                   "cell-line derived (off the shelf); in vivo / mRNA = cells engineered inside the body or transiently with mRNA. Read from registry text.",
                   lines([str(y) for y in yrs], [shares[p] for p in PLATFORMS], ["s1", "s2", "s3"], PLATFORMS, ymax=100, notes=[notes[p] for p in PLATFORMS]),
                   legend(list(zip(["s1", "s2", "s3"], PLATFORMS))),
                   table(["Year"] + PLATFORMS + ["n"], [(y, *["—" if shares[p][i] is None else shares[p][i] for p in PLATFORMS], notes["Autologous"][i]) for i, y in enumerate(yrs)]), "",
                   f"Off-the-shelf and in vivo approaches: <b>{off_then}%</b> of cell-therapy trials registered in {y0} → <b>{off_now}%</b> in {y1}" + (" (year to date)" if y1 == today.year else ""),
                   "Autologous products need each patient's own cells; off-the-shelf and in vivo designs aim to cut cost and waiting time."))
    dcodes = [d for d, _ in drows]
    m = [[int((act.diseases.str.contains(rf"\b{d}\b") & (act.modality == mo)).sum()) for mo in MODALITIES] for d in dcodes]
    best = max(((m[i][j], dcodes[i], MODALITIES[j]) for i in range(len(dcodes)) for j in range(len(MODALITIES)) if dcodes[i] != "OTHER"), default=(0, "", ""))
    tp.append(card("Disease × modality", "Active trials. A trial counts once per disease it enrolls. 'Autoimmune, disease not named' = basket trials that do not list specific diseases. Darker = more trials.",
                   heatmap([DISEASE_LABEL[d] for d in dcodes], MODALITIES, m, "Disease"), "", "", "wide",
                   f"Most crowded: <b>{e(DISEASE_LABEL.get(best[1], ''))}</b> with {e(best[2])} ({best[0]} active trials)",
                   "Empty cells show diseases where a modality has not been tried yet in a registered trial."))

    # ---------- sponsors & geography ----------
    sp = []
    rows = [(mo, [int(((act.modality == mo) & act.industry).sum()), int(((act.modality == mo) & ~act.industry).sum())]) for mo in MODALITIES if (act.modality == mo).any()]
    ind = P(int(act.industry.sum()), len(act))
    sp.append(card("Who sponsors active trials", "Lead sponsor class on ClinicalTrials.gov: industry vs hospital, university, government or other.",
                   stacked100(rows, ["Industry", "Academic / other"], ["s1", "s2"]), legend([("s1", "Industry"), ("s2", "Academic / other")]),
                   table(["Modality", "Industry", "Academic / other"], [(a, *b) for a, b in rows]), "",
                   f"Industry leads <b>{ind}%</b> of active trials; the rest are investigator-initiated",
                   "Many early CAR-T studies in autoimmunity are hospital-run; industry trials are the ones built for approval."))
    top = act.sponsor.value_counts().head(12)
    rows = [(n, int(c), "") for n, c in top.items()]
    sp.append(card("Most active lead sponsors", "Lead sponsors with the most active trials. Subsidiaries are not merged.",
                   hbars_single(rows), "", table(["Sponsor", "Active trials"], [(a, b) for a, b, _ in rows]), "",
                   f"<b>{e(rows[0][0])}</b> leads with {rows[0][1]} active trials" if rows else "No sponsors",
                   "The busiest sponsors are the likeliest partners, competitors and sources of the next readouts."))
    cc = {}
    for s_ in act.countries.dropna():
        for c in set(s_.split(";")):
            cc[c] = cc.get(c, 0) + 1
    topc = sorted(cc.items(), key=lambda kv: -kv[1])[:12]
    nos = int(act.countries.isna().sum())
    china = P(cc.get("China", 0), len(act))
    us = P(cc.get("United States", 0), len(act))
    sp.append(card("Countries with sites in active trials", f"Active trials with at least one registered site in the country; multinational trials count in each. {nos} active trials list no sites yet.",
                   hbars_single([(c, v, "") for c, v in topc]), "", table(["Country", "Active trials"], topc), "wide",
                   f"China has sites in <b>{china}%</b> of active trials, the United States in <b>{us}%</b>",
                   "Where trials recruit is where patients can get access today, and where competition for referrals is stiffest."))

    # ---------- execution ----------
    ex = []
    m0 = dt.date(today.year, today.month, 1)
    months = []
    for k in range(12):
        y, mm = divmod(m0.month - 1 + k, 12)
        months.append(dt.date(m0.year + y, mm + 1, 1))
    key = act.pc_date.map(lambda d: d.strftime("%Y-%m") if d else None)
    vals = [int((key == d.strftime("%Y-%m")).sum()) for d in months]
    ex.append(card("Primary completions due, next 12 months", f"Active trials by registered primary completion month, {months[0]:%b %Y}–{months[-1]:%b %Y}. Dates often slip.",
                   columns_stacked([d.strftime("%b") + ("" if d.month != 1 and k else " " + d.strftime("%y")) for k, d in enumerate(months)], [vals], ["s1"], ["Trials"]),
                   "", table(["Month", "Trials"], [(d.strftime("%b %Y"), v) for d, v in zip(months, vals)]), "",
                   f"<b>{sum(vals)}</b> trials reach primary completion in the next 12 months",
                   "Primary completion usually comes months before results; this is the queue of upcoming data."))
    ph = [("Phase 1 (incl. early)", ["Early 1", "1"]), ("Phase 1/2", ["1/2"]), ("Phase 2 or later", ["2", "2/3", "3", "4"])]
    rows, tbl = [], []
    for lab, ps in ph:
        g = act[act.phase.astype(str).isin(ps)].enrollment.dropna().tolist()
        md = int(median(g) or 0)
        rows.append((lab, md, f"n={len(g)}"))
        tbl.append((lab, md, len(g)))
    ex.append(card("Planned enrollment by phase (median)", "Registered target or actual enrollment of active trials.",
                   hbars_single(rows), "", table(["Phase", "Median participants", "Trials"], tbl), "",
                   f"A typical phase 1 enrolls <b>{rows[0][1]}</b> people; phase 2 or later <b>{rows[2][1]}</b>",
                   "Small single-arm studies can show striking remissions but cannot rule out regression to the mean or estimate rare harms."))
    stale = act[act.stale]
    rows = [("Industry", P(int(stale.industry.sum()), int(act.industry.sum())), f"{int(stale.industry.sum())} of {int(act.industry.sum())}"),
            ("Academic / other", P(int((~stale.industry).sum()), int((~act.industry).sum())), f"{int((~stale.industry).sum())} of {int((~act.industry).sum())}")]
    ex.append(card("Active records past their completion date", "Active trials whose registered primary completion date has passed without a status update.",
                   hbars_single(rows, unit="%", vmax=100), "", table(["Sponsor", "% past date", "Count"], rows), "",
                   f"<b>{len(stale)}</b> of {len(act)} 'active' records ({P(len(stale), len(act))}%) are past their completion date",
                   "Registry status lags reality; treat those trials' dates as unconfirmed."))

    # ---------- KPI tiles ----------
    def tile(v, label, so, href, sp_=""):
        return (f"<a class='kpi' href='{href}'><span class='kt'><span class='v'>{v}</span>{sp_}</span><span class='l'>{label}</span>"
                f"<span class='so'>{so}</span></a>")
    last12 = int((t.fp_date >= today - dt.timedelta(days=365)).sum())
    prev12 = int(((t.fp_date < today - dt.timedelta(days=365)) & (t.fp_date >= today - dt.timedelta(days=730))).sum())
    reg_series = [tot[i] for i in range(len(years) - 1)]
    tiles = [tile(f"{len(act):,}", f"active trials, of {len(t):,} tracked", "CAR-T, CAR-NK and T-cell engagers in autoimmune disease.", "explore.html"),
             tile(f"{last12}", f"registered in the last 12 months (prior 12: {prev12})", "New entrants keep arriving.", "#landscape",
                  spark(reg_series, "Registrations per year")),
             tile(f"{P(cd19, len(act))}%", "of active trials target CD19", "The default target; BCMA and dual targets are rising.", "#targets"),
             tile(f"{off_then}% → {off_now}%", f"off-the-shelf or in vivo share of new cell-therapy trials ({y0} → {y1})",
                  "Platforms are moving beyond each patient's own cells.", "#targets"),
             tile(f"{int((act.modality == 'T-cell engager').sum())}", "active T-cell engager trials", "No cell manufacturing, no chemotherapy conditioning.", "#landscape"),
             tile(f"{P(early, len(act))}%", "of active trials are phase 1 or 1/2", "Controlled evidence is still scarce.", "#landscape"),
             tile(f"{china}% / {us}%", "of active trials with sites in China / the United States", "Access depends heavily on geography.", "#sponsors"),
             tile(f"{sum(vals)}", "primary completions due in the next 12 months", "Expect a steady flow of results.", "readouts.html")]
    intro = (f"<span class='live'><i></i>Live · updated {today:%b %d, %Y}</span><h1>Autoimmune immune-reset dashboard</h1>"
             "<p class='lede'>CAR-T, CAR-NK and T-cell engager trials in lupus, myositis, systemic sclerosis, myasthenia gravis, MS and other autoimmune diseases, "
             "recomputed every day from ClinicalTrials.gov. <span class='muted'>Each headline is the chart's conclusion; open “How it's counted” for the method and data.</span></p>")
    jump = ("<nav class='jump' aria-label='Dashboard sections'><a href='#landscape'>Landscape</a><a href='#targets'>Targets &amp; platforms</a>"
            "<a href='#sponsors'>Sponsors &amp; geography</a><a href='#execution'>Execution</a></nav>")
    return (f"<section class='hero2 dash'>{intro}</section><div class='kpis'>{''.join(tiles)}</div>{jump}"
            + f"<div id='landscape'>{section('Landscape', 'What is active now and how fast the field is growing.', land)}</div>"
            + f"<div id='targets'>{section('Targets & platforms', 'Which antigens and which kinds of product.', tp)}</div>"
            + f"<div id='sponsors'>{section('Sponsors & geography', 'Who runs the trials and where.', sp)}</div>"
            + f"<div id='execution'>{section('Execution', 'Upcoming completions, trial size and record freshness.', ex)}</div>")
