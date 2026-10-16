"""ClinicalTrials.gov API v2 에서 파킨슨·알츠하이머 초기 중재 임상을 받아 JSONL.gz 스냅샷으로 저장한다.

사용: python -m moduleA.fetch OUT_DIR
- 질환별로 받고(조건 검색), 같은 NCT 번호는 하나로 합친다.
- 받은 날짜를 파일 이름에 넣어 매달 갱신분을 비교할 수 있게 한다.
"""
import gzip, json, sys, time, datetime as dt, pathlib, urllib.parse, urllib.request

API = "https://clinicaltrials.gov/api/v2/studies"
CONDITIONS = {"PD": "Parkinson Disease", "AD": "Alzheimer Disease"}
ADVANCED = ("AREA[StudyType]INTERVENTIONAL AND "
            "AREA[Phase](EARLY_PHASE1 OR PHASE1 OR PHASE2)")


def get(params, tries=5):
    url = API + "?" + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # 네트워크 일시 오류는 재시도
            if k == tries - 1:
                raise
            print(f"  retry {k+1}: {e}", file=sys.stderr)
            time.sleep(5 * (k + 1))


def fetch_condition(term):
    params = {"query.cond": term, "filter.advanced": ADVANCED,
              "pageSize": 200, "countTotal": "true", "format": "json"}
    out, total, token = [], None, None
    while True:
        if token:
            params["pageToken"] = token
        page = get(params)
        total = page.get("totalCount", total)
        out += page["studies"]
        token = page.get("nextPageToken")
        if not token:
            break
        time.sleep(0.3)
    return total, out


def main(out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    merged = {}
    for tag, term in CONDITIONS.items():
        total, studies = fetch_condition(term)
        print(f"  {tag} '{term}': totalCount={total} received={len(studies)}")
        assert total == len(studies), "받은 수가 totalCount와 다름"
        for s in studies:
            nct = s["protocolSection"]["identificationModule"]["nctId"]
            rec = merged.setdefault(nct, {"query_tags": [], "study": s})
            rec["query_tags"].append(tag)
    path = out_dir / f"ctgov_{today}.jsonl.gz"
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for nct in sorted(merged):
            f.write(json.dumps({"nct": nct, **merged[nct]}, ensure_ascii=False) + "\n")
    print(f"  unique trials: {len(merged)} -> {path} ({path.stat().st_size/1e6:.1f} MB)")
    return path


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data")
