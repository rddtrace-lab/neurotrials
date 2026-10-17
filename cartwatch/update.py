"""Daily data update.
1. Download a ClinicalTrials.gov snapshot (tracker.fetch) or reuse a given one.
2. Classify it (tracker.classify) and keep the in-scope trials.
3. Compare with the last table from an earlier day and append detected changes to data/events.csv.
Re-running on the same day compares against the same base, so it gives the same events. The raw snapshot is not stored.
Usage: python -m tracker.update DATA_DIR RAW_DIR [SNAPSHOT.jsonl.gz [DATE]]"""
import sys, json, gzip, hashlib, pathlib, datetime as dt
import pandas as pd
from . import fetch, classify

TRACKED = ["status", "phase", "enrollment", "primary_completion", "modality", "target"]
EV_COLS = ["date", "nct", "kind", "before", "after", "disease", "title"]


def _same(x, y):
    return (x.isna() & y.isna()) | (x.astype(str) == y.astype(str))


def diff(a, b, date, rules_changed=False):
    """Changes between two in-scope tables. rules_changed: skip new/removed/modality/target events that our own rule update caused."""
    a, b = a.set_index("nct"), b.set_index("nct")
    ev = []

    def add(n, kind, before, after, row):
        ev.append({"date": date, "nct": n, "kind": kind, "before": "" if pd.isna(before) else before,
                   "after": "" if pd.isna(after) else after, "disease": row["disease"], "title": row["title"]})
    if not rules_changed:
        for n in b.index.difference(a.index):
            add(n, "new", "", b.loc[n, "status"], b.loc[n])
        for n in a.index.difference(b.index):
            add(n, "removed", a.loc[n, "status"], "", a.loc[n])
    both = a.index.intersection(b.index)
    for f in TRACKED:
        if rules_changed and f in ("modality", "target"):
            continue
        same = _same(a.loc[both, f], b.loc[both, f])
        for n in both[(~same).values]:
            add(n, f, a.loc[n, f], b.loc[n, f], b.loc[n])
    for n in both[(~a.loc[both, "has_results"].astype(bool) & b.loc[both, "has_results"].astype(bool)).values]:
        add(n, "results", "", "posted", b.loc[n])
    return pd.DataFrame(ev, columns=EV_COLS)


def main(data_dir, raw_dir, snapshot=None, date=None):
    data, raw = pathlib.Path(data_dir), pathlib.Path(raw_dir)
    data.mkdir(parents=True, exist_ok=True)
    snap = pathlib.Path(snapshot) if snapshot else fetch.main(raw)
    date = date or dt.date.today().isoformat()
    t = classify.build(json.loads(l) for l in gzip.open(snap, "rt"))
    t = t[t.in_scope].drop(columns=["in_scope"]).reset_index(drop=True)
    latest, base, events = data / "trials_latest.csv", data / "trials_prev.csv", data / "events.csv"
    meta_p = data / "meta.json"
    prev = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    if latest.exists() and prev.get("snapshot_date") != date:
        base.write_bytes(latest.read_bytes())
        prev["base_rules"] = prev.get("rules")
    if base.exists():
        rules_changed = (prev.get("base_rules") or classify.RULES_VERSION) != classify.RULES_VERSION
        t.to_csv(latest, index=False)  # compare CSV to CSV so blanks and numbers read back the same way on both sides
        ev = diff(pd.read_csv(base), pd.read_csv(latest), date, rules_changed)
        if events.exists():
            old = pd.read_csv(events)
            ev = pd.concat([old[old.date != date], ev], ignore_index=True)
        ev.to_csv(events, index=False)
        print(f"  {date}: {len(ev[ev.date == date])} changes" + (" (rules changed: re-labels not logged)" if rules_changed else ""))
    else:
        pd.DataFrame(columns=EV_COLS).to_csv(events, index=False)
        print("  first run: baseline only")
    t.to_csv(latest, index=False)
    meta = {"snapshot_date": date, "tracking_started": prev.get("tracking_started", date), "base_rules": prev.get("base_rules"),
            "rules": classify.RULES_VERSION, "n_trials": int(len(t)), "n_active": int(t.active.sum()),
            "snapshot_md5": hashlib.md5(snap.read_bytes()).hexdigest()}
    meta_p.write_text(json.dumps(meta, indent=1))
    print(" ", meta)


if __name__ == "__main__":
    main(*sys.argv[1:5])
