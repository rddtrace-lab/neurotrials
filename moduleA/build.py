"""스냅샷(JSONL.gz)을 분석용 표로 바꾼다.

사용: python -m moduleA.build SNAPSHOT OUT_DIR
만드는 표 (모두 공개 자료에서 나온 임상 단위 정보):
  trials.csv     임상 1건 1줄: 질환, 단계, 상태, 시작일, 후원사, 기전, 분석 대상 여부, 참가 조건 추출값
  sites.csv      임상×기관 1줄: 기관명(정규화), 도시, 나라, 기관별 모집 상태
분석 대상(in_scope): 질환이 PD/AD로 명시 + 진단·선별 목적이 아님 + 약물·생물학적·유전자 중재 + 주 기전이 진단 영상이 아님.
"""
import gzip, json, re, sys, pathlib, unicodedata
import pandas as pd
from .rules import MECH_RE, MECH_GROUP, DRUG_TYPES, ACTIVE_STATUS, SYM_INDICATION, BACKGROUND_DRUG
from .criteria import extract

PD_RE = re.compile(r"parkinson(?!ism)(?!ian)|^\s*pd\s*$", re.I)
PD_NAMED = re.compile(r"parkinson'?s? disease|^\s*pd\s*$", re.I)
PD_EXCL = re.compile(r"multiple system atrophy|progressive supranuclear|corticobasal|parkinsonism|wolff", re.I)
AD_RE = re.compile(r"alzheimer", re.I)


def disease_of(ps):
    conds = ps.get("conditionsModule", {}).get("conditions", [])
    # 비정형 파킨슨증 등은 빼되, 같은 칸에 '파킨슨병'이 함께 적혀 있으면 넣는다(예: "Parkinsonism or Parkinson's Disease")
    pd_hit = any(PD_RE.search(c) and (not PD_EXCL.search(c) or PD_NAMED.search(c)) for c in conds)
    ad_hit = any(AD_RE.search(c) for c in conds)
    if pd_hit and ad_hit:
        return "PD+AD"
    if pd_hit:
        return "PD"
    if ad_hit:
        return "AD"
    return None


def phase_label(phases):
    p = set(phases or [])
    if p == {"EARLY_PHASE1"}:
        return "0/1 (초기 1상)"
    if p == {"PHASE1"}:
        return "1"
    if p == {"PHASE1", "PHASE2"}:
        return "1/2"
    if p == {"PHASE2"}:
        return "2"
    if p == {"PHASE2", "PHASE3"}:
        return "2/3"
    return "/".join(sorted(p)) or "?"


SITE_TAG = re.compile(r"\(?\s*(?:site|study site)\s*[-#]?\s*(?:no\.?|number)?\s*[-#]?\s*[a-z]?\d+\s*\)?", re.I)
GENERIC_WORD = re.compile(r"^(?:research|investigational|investigative|investigator|clinical|study|local|trial|clinical trial|clinical research)$", re.I)
GENERIC_SITE = re.compile(r"^(?:[\w&.-]+\s+)?(?:clinical (?:trial|research|study)|research|investigational|investigative|investigator|study|clinical|local)?\s*(?:site|institution)(?:s|\(s\))?\s*$", re.I)


def norm(s):
    raw = s or ""
    s = SITE_TAG.sub(" ", raw).strip(" ,-")
    if s and GENERIC_WORD.search(s):
        return ""  # 'Research Site 1', 'Investigational Site Number 840041'
    if s and len(s.split()) < 2 and SITE_TAG.search(raw):
        s = raw  # 'Vima Site #101'처럼 남는 이름이 한 단어(상호)면 번호가 곳을 구분하므로 번호를 남긴다
    elif not s or GENERIC_SITE.search(s):
        return ""  # 'Novartis Investigative Site', 'Research Site', 'Site 0012'처럼 이름 없는 자리표시 기관은 같은 곳인지 알 수 없다
    if GENERIC_SITE.search(s):
        return ""
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    s = re.sub(r"\b(the|inc|llc|ltd|gmbh|of|at|and)\b", " ", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


BACKGROUND = {"AMYLOID", "TAU", "ASYN"}
DX_RX = next(rx for c, n, g, rx in MECH_RE if c == "DX")
ADDON = re.compile(r"along with|in addition|add-?on|adjunct|background|continu|stable dose|concomitant|on top of|standard (?:therapy|treatment|of care)|usual care", re.I)


def classify(ps):
    """기전을 3단계로 찾는다: ① 중재 이름·다른 이름 ② 중재 설명·제목(증상 계열은 적응증 단어만) ③ 요약(배경·증상·진단 단어 제외).
    앞 단계에서 찾으면 멈춘다. 약 이름이 제목·요약의 배경 설명보다 앞서게 하려는 것이다."""
    ivs = [i for i in ps.get("armsInterventionsModule", {}).get("interventions", [])
           if not re.search(r"placebo|sham|vehicle", i.get("name", ""), re.I)]
    # 배경 치료(승인 항체·표준 치료)는 다른 시험 중재가 있을 때 기전 판단에서 뺀다
    arms = [set(n.split(": ", 1)[-1] for n in g.get("interventionNames", []))
            for g in ps.get("armsInterventionsModule", {}).get("armGroups", [])]
    def is_background(i):
        if not BACKGROUND_DRUG.search(i.get("name", "")):
            return False
        in_all_arms = len(arms) > 1 and all(i.get("name") in a for a in arms)
        return in_all_arms or bool(ADDON.search(i.get("description", "")))
    # 대조군(ACTIVE_COMPARATOR 등) 팔에만 쓰이고 시험군 팔에 단독으로 나오지 않는 약도 시험약이 아니다
    groups = ps.get("armsInterventionsModule", {}).get("armGroups", [])
    comp = {n.split(": ", 1)[-1] for g in groups if g.get("type") in ("ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR")
            for n in g.get("interventionNames", [])}
    solo_exp = {list(a)[0] for g, a in zip(groups, arms) if g.get("type") not in ("ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR") and len(a) == 1}
    for drop in (is_background, lambda i: i.get("name") in comp and i.get("name") not in solo_exp):
        fg = [i for i in ivs if not drop(i)]
        if fg:  # 거르고 나서 남는 것이 있을 때만 적용(따로 적용해, 한 기준이 전부를 지워도 다른 기준은 적용된다)
            ivs = fg
    # 제목이 영상 연구이고 진단 약(추적자)이 들어 있으면 영상 연구로 본다(약은 영상 비교용 자극제인 경우가 많다)
    title = ps["identificationModule"].get("officialTitle", "") + " " + ps["identificationModule"].get("briefTitle", "")
    therapy_named = any(MECH_GROUP[c] == "DMT" and rx.search(i.get("name", "")) for i in ivs if not DX_RX.search(i.get("name", "")) for c, n, g, rx in MECH_RE)
    if (not therapy_named and re.search(r"\bimaging\b|\bpet\b|positron|tracer|radioligand", title, re.I)
            and any(DX_RX.search(i.get("name", "")) for i in ivs)):
        return ["DX"], "영상 연구", ivs
    # ① 중재 이름: 증상 조절 약(레보도파·도네페질 등)은 '모든' 시험 중재가 분류될 때만 인정한다.
    #    시험약 + 표준 치료(예: '셀레콕시브' 팔과 '레보도파' 팔)라면 시험약을 모르는 것이지 증상 조절 임상이 아니다.
    per_iv = [{c for c, n, g, rx in MECH_RE if rx.search(i.get("name", "") + " " + " ".join(i.get("otherNames", [])))} for i in ivs]
    t1 = [c for c, n, g, rx in MECH_RE if any(c in h for h in per_iv)]
    if t1:
        # 진단 영상 약(PET 추적자 등)은 모든 시험 중재가 진단 약일 때만 주 기전이 된다(신약 시험에 PET를 곁들인 경우는 신약 기준)
        if "DX" in t1 and not all(h and h <= {"DX"} for h in per_iv):
            t1 = [c for c in t1 if c != "DX"]
            per_iv = [h - {"DX"} for h in per_iv]
        non_sym = [c for c in t1 if MECH_GROUP[c] not in ("SYM", "DX")]
        if non_sym:
            return non_sym, "중재 이름", ivs
        if t1 and all(per_iv):
            return t1, "중재 이름", ivs
    # ①' 이름으로 분류되지 않은 시험 중재의 설명에 약 이름이 있으면(예: 'IVL3003 — 도네페질 장기 지속 주사') 그 설명으로 정한다
    # 설명 첫머리(약이 무엇인지 말하는 부분)만 보고, '…와 함께/추가로/안정 용량' 같은 병용 표현이 있으면 그 문장은 쓰지 않는다
    unk = [i for i, h in zip(ivs, per_iv) if not h]
    head_hits = [set() if ADDON.search(i.get("description", "")) else
                 {c for c, n, g, rx in MECH_RE if c not in BACKGROUND and g != "DX" and rx.search(i.get("description", "")[:100])} for i in unk]
    t1b = [c for c, n, g, rx in MECH_RE if any(c in h for h in head_hits)]
    if t1b:
        non_sym = [c for c in t1b if MECH_GROUP[c] != "SYM"]
        if non_sym:
            return non_sym, "시험 중재 설명", ivs
        if all(head_hits):  # 증상 계열은 이름으로 모르던 시험 중재가 모두 증상 약으로 설명될 때만
            return t1b, "시험 중재 설명", ivs
    tiers = [
        ("중재 설명·제목", " | ".join([i.get("description", "") for i in ivs]
                                    + [ps["identificationModule"].get("officialTitle", ""), ps["identificationModule"].get("briefTitle", "")])),
        ("요약", ps.get("descriptionModule", {}).get("briefSummary", "")),
    ]
    conds_text = " | ".join(ps.get("conditionsModule", {}).get("conditions", []))
    for src, text in tiers:
        hits = []
        for c, n, g, rx in MECH_RE:
            if src == "요약" and (c in BACKGROUND or g in ("SYM", "DX")):
                continue  # 요약은 질환 배경(아밀로이드 축적, 떨림·초조 같은 증상)을 늘 설명하므로 이 계열은 요약으로 정하지 않는다
            if src == "중재 설명·제목" and g == "DX":
                continue  # 설명의 'DAT 스캔' 같은 평가 수단 언급으로 진단 임상이 되지 않게 한다
            if src == "중재 설명·제목" and g == "SYM":
                # 증상 적응증은 조건 칸(예: 'Parkinson Disease Psychosis')에서도 찾는다. 다른 계열은 조건 칸을 쓰지 않는다(예: 심장 '아밀로이드증')
                if SYM_INDICATION[c].search(text + " | " + conds_text):
                    hits.append(c)
                continue  # 약 이름(레보도파 등)은 동반 약물일 때가 많아 적응증 단어만 본다
            if rx.search(text):
                hits.append(c)
        if hits:
            return hits, src, ivs
    return ["OTHER"], "없음", ivs


def _nfkc(o):
    """윗첨자(¹⁸F)·전각 문자를 보통 글자로 바꿔 규칙이 같은 표기로 보게 한다."""
    if isinstance(o, str):
        return unicodedata.normalize("NFKC", o)
    if isinstance(o, list):
        return [_nfkc(x) for x in o]
    if isinstance(o, dict):
        return {k: _nfkc(v) for k, v in o.items()}
    return o


def main(snapshot, out_dir):
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, sites = [], []
    for line in gzip.open(snapshot, "rt", encoding="utf-8"):
        rec = json.loads(line)
        ps = _nfkc(rec["study"]["protocolSection"])
        st, dm, el = ps["statusModule"], ps["designModule"], ps.get("eligibilityModule", {})
        disease = disease_of(ps)
        mechs, src, ivs = classify(ps)
        aim = ps.get("armsInterventionsModule", {})
        iv_types = {i.get("type") for i in aim.get("interventions", [])}
        # 대조군에만 약이 있는 시술·기기 임상을 빼기 위해, 팔 정보가 있으면 시험군(EXPERIMENTAL·대조군이 아닌 팔)의 중재 형식을 본다
        exp_names = {n.split(": ", 1)[-1] for g in aim.get("armGroups", []) if g.get("type") not in ("ACTIVE_COMPARATOR", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR", "NO_INTERVENTION")
                     for n in g.get("interventionNames", [])}
        if exp_names:
            iv_types = {i.get("type") for i in aim.get("interventions", []) if i.get("name") in exp_names} or iv_types
        # 영상 추적자·조영제는 '약물 중재'로 치지 않는다(기기·시술 임상이 추적자 때문에 들어오지 않게)
        drug_like = {i.get("type") for i in aim.get("interventions", [])
                     if (not exp_names or i.get("name") in exp_names) and not DX_RX.search(i.get("name", ""))}
        iv_types = iv_types & drug_like if drug_like else set()
        purpose = dm.get("designInfo", {}).get("primaryPurpose")
        # 목적 칸은 후원사마다 다르게 적는다(치료제 1상을 BASIC_SCIENCE·OTHER로 적기도 함). 진단·선별·의료서비스 연구만 뺀다.
        in_scope = (bool(disease) and purpose not in ("DIAGNOSTIC", "SCREENING", "HEALTH_SERVICES_RESEARCH")
                    and bool(iv_types & DRUG_TYPES) and mechs[0] != "DX")
        crit = extract(el.get("eligibilityCriteria", ""), disease) if disease else {}
        locs = ps.get("contactsLocationsModule", {}).get("locations", [])
        row = {
            "nct": rec["nct"], "disease": disease, "in_scope": in_scope,
            "title": ps["identificationModule"].get("briefTitle"),
            "phase": phase_label(dm.get("phases")), "status": st["overallStatus"],
            "active": st["overallStatus"] in ACTIVE_STATUS,
            "start": st.get("startDateStruct", {}).get("date"),
            "primary_completion": st.get("primaryCompletionDateStruct", {}).get("date"),
            "last_update": st.get("lastUpdatePostDateStruct", {}).get("date"),
            "first_posted": st.get("studyFirstPostDateStruct", {}).get("date"),
            "has_results": bool(rec["study"].get("hasResults", False)),
            "sponsor": ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("name"),
            "sponsor_class": ps.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("class"),
            "collaborators": ";".join(c.get("name", "") for c in ps.get("sponsorCollaboratorsModule", {}).get("collaborators", [])),
            "purpose": purpose, "enrollment": dm.get("enrollmentInfo", {}).get("count"),
            "mech_primary": mechs[0], "mechs": ";".join(mechs), "mech_source": src,
            "interventions": "; ".join(sorted({i.get("name", "") for i in ivs})),
            "age_min": el.get("minimumAge"), "age_max": el.get("maximumAge"),
            "healthy_volunteers": el.get("healthyVolunteers"),
            "n_sites": len(locs), "countries": ";".join(sorted({l.get("country", "") for l in locs})),
            **crit,
        }
        rows.append(row)
        for l in locs:
            fk = norm(l.get("facility"))
            sites.append({"nct": rec["nct"], "sponsor": row["sponsor"], "orgs": ";".join(filter(None, [row["sponsor"], row["collaborators"]])), "facility": l.get("facility"), "facility_key": (fk + "|" + norm(l.get("city"))) if fk else None,
                          "city": l.get("city"), "country": l.get("country"), "site_status": l.get("status")})
    t = pd.DataFrame(rows)
    s = pd.DataFrame(sites)
    t.to_csv(out_dir / "trials.csv", index=False)
    s.to_csv(out_dir / "sites.csv", index=False)
    print(f"  trials: {len(t)}  in_scope: {int(t.in_scope.sum())}  in_scope&active: {int((t.in_scope & t.active).sum())}  site rows: {len(s)}")
    return t, s


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
