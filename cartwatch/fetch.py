"""Download the ClinicalTrials.gov studies that could be in scope: every study whose interventions mention a CAR / engineered
cell therapy or a T-cell engager, plus autoimmune-condition studies that mention such products by name. The classifier
(tracker.classify) decides what is actually in scope. Output: one gzipped JSON-lines snapshot.
Usage: python -m tracker.fetch RAW_DIR"""
import sys, json, gzip, time, pathlib, datetime as dt, urllib.parse, urllib.request

BASE = "https://clinicaltrials.gov/api/v2/studies"
CELL_TERMS = ("chimeric antigen receptor OR CAR-T OR \"CAR T\" OR CAR-NK OR \"CAR NK\" OR CAAR-T OR \"CAR-Treg\" OR "
              "KYV-101 OR CABA-201 OR rese-cel OR obe-cel OR obecabtagene OR zamto-cel OR azer-cel OR Descartes-08 OR "
              "MB-CART2019.1 OR CNTY-101 OR FT819 OR YTB323 OR GC012F OR BMS-986353 OR \"CD19 CAR\" OR \"BCMA CAR\"")
TCE_TERMS = ("\"T-cell engager\" OR \"T cell engager\" OR blinatumomab OR teclistamab OR mosunetuzumab OR glofitamab OR imvotamab OR "
             "cevostamab OR odronextamab OR epcoritamab OR elranatamab OR linvoseltamab OR talquetamab OR \"CD19xCD3\" OR \"CD20xCD3\" OR "
             "\"BCMAxCD3\" OR \"CD19 x CD3\" OR \"BCMA x CD3\" OR \"CD3 bispecific\"")
AUTOIMMUNE = ("lupus OR scleroderma OR \"systemic sclerosis\" OR myositis OR dermatomyositis OR myasthenia OR \"multiple sclerosis\" OR "
              "neuromyelitis OR CIDP OR \"rheumatoid arthritis\" OR vasculitis OR ANCA OR Sjogren OR IgG4 OR \"autoimmune\" OR pemphigus OR "
              "\"immune thrombocytopenia\" OR \"membranous nephropathy\" OR \"nephrotic syndrome\" OR \"stiff person\" OR \"type 1 diabetes\"")
QUERIES = [{"query.intr": CELL_TERMS}, {"query.intr": TCE_TERMS},
           {"query.cond": AUTOIMMUNE, "query.term": "CAR OR chimeric OR engager OR bispecific OR \"cell therapy\""}]


def get(params, tries=5):
    url = BASE + "?" + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "trial-tracker/1.0"}), timeout=120) as r:
                return json.load(r)
        except Exception:
            if k == tries - 1:
                raise
            time.sleep(10 * (k + 1))


def main(raw_dir):
    raw = pathlib.Path(raw_dir)
    raw.mkdir(parents=True, exist_ok=True)
    seen = {}
    for q in QUERIES:
        params = {**q, "pageSize": 1000, "format": "json"}
        n = 0
        while True:
            d = get(params)
            for s in d.get("studies", []):
                seen[s["protocolSection"]["identificationModule"]["nctId"]] = s
                n += 1
            if not d.get("nextPageToken"):
                break
            params["pageToken"] = d["nextPageToken"]
        print(f"  query {list(q.values())[0][:40]}…: {n} studies")
    out = raw / f"ctgov_{dt.date.today():%Y%m%d}.jsonl.gz"
    with gzip.open(out, "wt") as f:
        for s in seen.values():
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    print(f"  {len(seen)} unique studies → {out}")
    return out


if __name__ == "__main__":
    main(sys.argv[1])
