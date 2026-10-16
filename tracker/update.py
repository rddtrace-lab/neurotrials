"""Daily data update for the public trial tracker.

1. Download a ClinicalTrials.gov snapshot (moduleA.fetch) or reuse a given one.
2. Build the classified trial table (moduleA.build, same rules as the validated module A).
3. Compare with data/trials_latest.csv and append detected changes to data/events.csv.
4. Replace data/trials_latest.csv and write data/meta.json.

Only the compact table, the previous day's table (comparison base, so re-running on the same day gives the same events) and the
append-only change log are kept (the raw snapshot is ~12 MB and is not stored).
Usage: python -m tracker.update DATA_DIR RAW_DIR [SNAPSHOT.jsonl.gz [DATE]]
"""
import sys, json, hashlib, pathlib, tempfile, datetime as dt
import pandas as pd
from moduleA import fetch, build

KEEP = ["nct", "disease", "in_scope", "title", "phase", "status", "active", "start", "primary_completion", "last_update",
        "first_posted", "has_results", "sponsor", "sponsor_class", "collaborators", "enrollment", "mech_primary", "mechs",
        "interventions", "age_min", "age_max", "n_sites", "countries", "hy_max", "dur_max_y", "untreated", "dat_req",
        "saa_req", "lrrk2", "gba", "mmse_lo", "mmse_hi", "cdr", "amyloid_req", "tau_pet_req", "ad_stages"]
TRACKED = ["status", "phase", "mech_primary", "enrollment", "primary_completion"]
# 분류 규칙 판. 규칙을 고치면 올린다. 판이 바뀐 날에는 규칙 때문에 생긴 기전·범위 변화를 등록 정보 변화로 기록하지 않는다.
RULES_VERSION = "moduleA v2.8"


def _same(x, y):
    return (x.isna() & y.isna()) | (x.astype(str) == y.astype(str))


def diff(a, b, date, rules_changed=False):
    """Events between two trial tables. Only trials that are in scope in either table are reported.
    rules_changed=True: skip scope and mechanism events, because they would reflect our rule update rather than a registry change."""
    a, b = a.set_index("nct"), b.set_index("nct")
    ev = []

    def add(n, kind, before, after, row):
        ev.append({"date": date, "nct": n, "kind": kind, "before": "" if pd.isna(before) else before,
                   "after": "" if pd.isna(after) else after, "disease": row["disease"], "title": row["title"]})
    for n in b.index.difference(a.index):
        if b.loc[n, "in_scope"]:
            add(n, "new", "", b.loc[n, "status"], b.loc[n])
    for n in a.index.difference(b.index):
        if a.loc[n, "in_scope"]:
            add(n, "removed", a.loc[n, "status"], "", a.loc[n])
    both = a.index.intersection(b.index)
    rel = both[(a.loc[both, "in_scope"].astype(bool) | b.loc[both, "in_scope"].astype(bool)).values]
    if not rules_changed:
        for n in rel[(a.loc[rel, "in_scope"].astype(bool) != b.loc[rel, "in_scope"].astype(bool)).values]:
            add(n, "scope", a.loc[n, "in_scope"], b.loc[n, "in_scope"], b.loc[n])
    for f in TRACKED:
        if rules_changed and f == "mech_primary":
            continue
        same = _same(a.loc[rel, f], b.loc[rel, f])
        for n in rel[(~same).values]:
            add(n, f, a.loc[n, f], b.loc[n, f], b.loc[n])
    hr = rel[(~a.loc[rel, "has_results"].astype(bool) & b.loc[rel, "has_results"].astype(bool)).values]
    for n in hr:
        add(n, "results", "", "posted", b.loc[n])
    return pd.DataFrame(ev, columns=["date", "nct", "kind", "before", "after", "disease", "title"])


def main(data_dir, raw_dir, snapshot=None, date=None):
    data, raw = pathlib.Path(data_dir), pathlib.Path(raw_dir)
    data.mkdir(parents=True, exist_ok=True)
    snap = pathlib.Path(snapshot) if snapshot else fetch.main(raw)
    date = date or dt.date.today().isoformat()
    with tempfile.TemporaryDirectory() as tmp:
        t, _ = build.main(snap, tmp)
    t = t[t.disease.notna()][KEEP].sort_values("nct").reset_index(drop=True)
    latest, base = data / "trials_latest.csv", data / "trials_prev.csv"
    events_path = data / "events.csv"
    prev_meta = json.loads((data / "meta.json").read_text()) if (data / "meta.json").exists() else {}
    # 비교 기준은 '오늘 이전의 마지막 표'. 같은 날 다시 돌리면 latest가 이미 오늘 표이므로 보관해 둔 prev와 비교한다.
    if latest.exists() and prev_meta.get("snapshot_date") != date:
        base.write_bytes(latest.read_bytes())
        prev_meta["base_rules"] = prev_meta.get("rules")
    elif base.exists():
        prev_meta["base_rules"] = prev_meta.get("base_rules", prev_meta.get("rules"))
    if base.exists():
        old = pd.read_csv(base)
        rules_changed = (prev_meta.get("base_rules") or RULES_VERSION) != RULES_VERSION
        if rules_changed:
            print(f"  rules changed {prev_meta.get('base_rules')} → {RULES_VERSION}: scope/mechanism re-labels not logged as changes")
        ev = diff(old, t, date, rules_changed)
        if events_path.exists():
            prev = pd.read_csv(events_path)
            prev = prev[prev.date != date]  # re-running the same day replaces that day's events
            ev = pd.concat([prev, ev], ignore_index=True)
        ev.to_csv(events_path, index=False)
        print(f"  {date}: {len(ev[ev.date == date])} events")
    else:
        pd.DataFrame(columns=["date", "nct", "kind", "before", "after", "disease", "title"]).to_csv(events_path, index=False)
        print("  first run: baseline only")
    t.to_csv(latest, index=False)
    meta = {"snapshot_date": date, "base_rules": prev_meta.get("base_rules"), "n_trials": int(len(t)), "n_in_scope": int(t.in_scope.sum()),
            "n_active_in_scope": int((t.in_scope & t.active).sum()), "snapshot_md5": hashlib.md5(snap.read_bytes()).hexdigest(),
            "rules": RULES_VERSION}
    (data / "meta.json").write_text(json.dumps(meta, indent=1))
    print(" ", meta)


if __name__ == "__main__":
    main(*sys.argv[1:5])
