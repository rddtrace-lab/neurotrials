"""참가 조건(eligibilityCriteria) 글에서 핵심 조건을 뽑는다. 규칙 기반이라 정확도는 validate.py로 잰다.

글을 포함 조건(inclusion)과 제외 조건(exclusion)으로 나누고, 항목마다 어느 쪽에서 찾을지 정한다.
값을 못 찾으면 None(조건 없음 또는 못 읽음)으로 둔다.
"""
import re

ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5}
NUM = r"(\d+(?:\.\d+)?)"


def clean(text):
    """등록부 글의 마크다운 이스케이프(\\&, \\~, \\<, \\>, \\*)를 푼다."""
    t = re.sub(r"\\([&~<>*_\-\[\]().])", r"\1", text or "")
    return t.replace("</=", "≤").replace("=<", "≤").replace(">/=", "≥").replace("=>", "≥")


def split_sections(text):
    """'Inclusion Criteria' / 'Exclusion Criteria' 머리말로 나눈다. 머리말이 없으면 전부 포함 조건으로 본다."""
    t = clean(text)
    m = re.search(r"exclusion criteria|key exclusion|exclusion:|\bexclusions?\b\s*:", t, re.I)
    if m:
        return t[:m.start()], t[m.start():]
    return t, ""


def _num(x):
    x = x.lower()
    return float(ROMAN[x]) if x in ROMAN else float(x)


def hoehn_yahr_max(inc):
    """포함 조건의 Hoehn & Yahr 상한. 예: 'H&Y stage ≤ 2', 'stage 1-2.5', 'stage I to III'."""
    HY = r"(?:hoehn[-\s]*(?:and|&)?[-\s]*yahr|\bh\s*&\s*y\b|\bh&y\b|\bhy\b|\bh-y\b)"
    pat = re.compile(r"(?:stage[^.\n;]{0,15}?(?:\d(?:\.\d)?|i{1,3}|iv)\s*(?:-|–|~|to)\s*(?:\d(?:\.\d)?|i{1,3}|iv)[^.\n;]{0,30}?)?" + HY + r"(?:[^.\n;]|(?<=\d)\.(?=\d)){0,80}", re.I)
    best = None
    for m in pat.finditer(inc):
        seg = m.group(0)
        seg2 = re.sub(HY, " ", seg, flags=re.I)
        r = re.search(r"(\d(?:\.\d)?|i{1,3}v?|iv|v)\s*(?:-|–|~|to|through|and|or)\s*(\d(?:\.\d)?|i{1,3}v?|iv|v)\b", seg2, re.I)
        if r:
            v = _num(r.group(2))
        else:
            r = re.search(r"(?:≤|<=|=<|less than or equal to|no (?:greater|more|higher) than|not (?:greater|more|higher) than|up to|maximum of|at most|of\s*<)\s*(?:stage\s*)?(\d(?:\.\d)?|i{1,3}v?|iv)\b", seg2, re.I)
            if r:
                v = _num(r.group(1))
            else:
                r = re.search(r"(?:<|below|less than|lower than)\s*(?:stage\s*)?(\d(?:\.\d)?)", seg2, re.I)
                if r:
                    v = float(r.group(1)) - 0.5
                else:
                    r = re.search(r"stage\s*(?:of\s*)?(\d(?:\.\d)?|i{1,3}|iv)\b(?!\s*(?:or (?:more|higher|greater)|\+|and above))", seg2, re.I)
                    lo_only = re.search(r"(?:≥|>=|>|at least|or (?:more|higher|greater)|and above)", seg2, re.I)
                    v = _num(r.group(1)) if (r and not lo_only) else None
        if v is not None and 0 < v <= 5:
            best = v if best is None else max(best, v)
    return best


def disease_duration_max_years(inc):
    """진단 후 기간 상한(년). 예: 'diagnosed within 3 years', 'disease duration ≤ 5 years', '< 2 years since diagnosis'."""
    pats = [
        r"(?:diagnos\w*|disease duration|duration of (?:the )?disease|since (?:the )?diagnosis|symptom onset|onset of (?:motor )?symptoms|duration of pd)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,100}?"
        r"(?:within|≤|<=|<|less than|no (?:more|longer) than|not (?:be )?(?:of )?(?:more|longer) than|not exceeding|maximum of|up to|of|in the (?:past|last)|between|range of)\s*(?:the (?:past|last)\s*)?(?:\d+(?:\.\d+)?\s*(?:-|–|to|and)\s*)?"
        r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|ten)\s*(years?|months?)",
        r"(?:within|≤|<=|<|less than|no more than)\s*(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|ten)\s*(years?|months?)"
        r"(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}?(?:diagnos\w*|onset|disease duration)",
        r"(?:diagnos\w*|disease duration|duration of (?:the )?disease|since (?:the )?diagnosis)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,60}?"
        r"(\d+(?:\.\d+)?|one|two|three|four|five|six|seven|eight|ten)\s*(years?|months?)\s*or (?:less|fewer|shorter)",
    ]
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "ten": 10}
    vals = []
    for p in pats:
        for m in re.finditer(p, inc, re.I):
            n = m.group(1).lower()
            n = float(words.get(n, n))
            if m.group(2).lower().startswith("month"):
                n = n / 12
            if 0 < n <= 30:
                vals.append(n)
    return max(vals) if vals else None


RX = {
    "untreated_inc": re.compile(r"untreated (?:pd|parkinson|patients|participants|subjects|early)|(?:pd|parkinson'?s? disease)[^.\n;]{0,20}untreated|de ?novo|drug[- ]na[iï]ve|treatment[- ]na[iï]ve|not (?:currently )?(?:be )?(?:receiving|taking|on) (?:any )?(?:dopaminergic|symptomatic|parkinson|pd|levodopa)|"
                                r"without (?:dopaminergic|symptomatic) (?:therapy|treatment)|no (?:prior |current )?(?:dopaminergic|symptomatic|pd) (?:therapy|treatment|medication)|"
                                r"not expected to require (?:dopaminergic|symptomatic)", re.I),
    "untreated_exc": re.compile(r"(?:current|prior|previous|any)\s+(?:use|treatment|therapy)\s+(?:of|with)\s+(?:levodopa|dopamine agonists?|dopaminergic|any (?:pd|parkinson))|"
                                r"(?:use|treatment) (?:of|with) (?:levodopa|dopaminergic (?:medication|therapy|drugs?)|pd medications?)\s+(?:within|for more than|> ?\d|at (?:any time|screening|baseline))|"
                                r"(?:has|have) (?:received|taken|used) (?:levodopa|dopaminergic|any (?:pd|parkinson'?s?) medication)", re.I),
    "dat": re.compile(r"\bdat\b|dat-?spect|datscan|dopamine transporter|ioflupane|\[123i\]|fp-?cit|\bvmat2\b pet|18f-?dopa|f-?dopa pet", re.I),
    "saa": re.compile(r"seed(?:ing)? amplification|\bsaa\b|rt-?quic|α-?syn(?:uclein)?(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}(?:positive|seed)|alpha[- ]synuclein(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}(?:positive|seed|assay)|synuclein biomarker", re.I),
    "lrrk2": re.compile(r"lrrk2", re.I),
    "gba": re.compile(r"\bgba1?\b|glucocerebrosidase", re.I),
    "updrs": re.compile(r"mds-?updrs|\bupdrs\b", re.I),
    "amyloid": re.compile(r"amyloid[- ](?:pet|positiv|positron)|amyloid(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}(?:pet|positive|confirm|elevat|evidence|scan|csf)|"
                          r"(?:csf|cerebrospinal)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,60}(?:aβ|abeta|a-?beta|amyloid|tau)|p-?tau\s?-?(?:181|217|231)|\bptau|plasma (?:biomarker|p-?tau)|"
                          r"biomarkers?(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}(?:alzheimer|\bad\b|evidence|consistent|suggestive|positive|confirm)|(?:amyloid|tau)(?: and tau)? pathology|(?:aβ|abeta)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,30}(?:positive|pathology)", re.I),
    "tau_pet": re.compile(r"tau[- ]pet|tau positron|flortaucipir|mk-?6240|pi-?2620|tau(?: positivity| deposition| burden| pathology)?\s*(?:on|by|via|using)\s*(?:brain\s*)?(?:pet|positron)", re.I),
}

STAGE_AD = [
    ("preclinical", r"preclinical|cognitively (?:normal|unimpaired)|asymptomatic"),
    ("MCI·초기", r"mild cognitive impairment|\bmci\b|prodromal|early (?:symptomatic )?(?:alzheimer|ad)\b|early-stage"),
    ("경도", r"\bmild (?:alzheimer|ad|dementia)|mild[- ]stage"),
    ("경도~중등도", r"mild[- ]to[- ]moderate|mild or moderate|mild\s*[-–/]\s*moderate"),
    ("중등도~중증", r"moderate[- ]to[- ]severe|severe (?:alzheimer|ad|dementia)|moderate(?:ly)? severe|moderate stage|moderate (?:alzheimer|ad\b|dementia)"),
]


def mmse_range(inc):
    m = None
    for p in [r"(?:mmse|mini[- ]mental state(?: examination)?)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,60}?(?:≥|>=|>)\s*(\d{1,2})\s*(?:and|,)?\s*(?:≤|<=|<)\s*(\d{1,2})\b",
              r"(?:mmse|mini[- ]mental state(?: examination)?)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,60}?(\d{1,2})\s*(?:-|–|to|and)\s*(\d{1,2})\b",
              r"(?:mmse|mini[- ]mental state(?: examination)?)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}?(?:≥|>=|of at least|at least|greater than or equal to)\s*(\d{1,2})",
              r"(?:mmse|mini[- ]mental state(?: examination)?)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}?(\d{1,2})\s*(?:or (?:higher|more|above|greater)|\+|and above)",
              r"(?:mmse|mini[- ]mental state(?: examination)?)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}?(?:>|greater than|above)\s*(\d{1,2})"]:
        m = re.search(p, inc, re.I)
        if m:
            g0 = m.group(0)
            lo = int(m.group(1)) + (1 if re.search(r"(?:>|greater than|above)\s*\d+\s*$", g0) or re.search(r"(?<![≥=])>\s*" + m.group(1) + r"\b", g0) else 0)
            hi = int(m.group(2)) if m.lastindex and m.lastindex >= 2 else None
            if hi is not None and re.search(r"<\s*" + m.group(2) + r"\b", g0) and not re.search(r"(?:≤|<=)\s*" + m.group(2) + r"\b", g0):
                hi -= 1  # '< 28'은 27까지
            if hi is not None and hi < lo:
                lo, hi = hi, lo  # 'MMSE 26 to 15'처럼 거꾸로 적은 범위
            if lo <= 30 and (hi is None or hi <= 30):
                return lo, hi
    return None, None


def cdr_global(inc):
    inc = re.sub(r"(?:cdr|clinical dementia rating)[-\s]*(?:\(?\s*)?(?:sum of boxes|sb)\b[^.\n;]*", " ", inc, flags=re.I)
    m = re.search(r"(?:cdr|clinical dementia rating)(?:[^.\n;]|(?<=\d)\.(?=\d)){0,40}?(?:global|gs|-gs)?(?:[^.\n;]|(?<=\d)\.(?=\d)){0,20}?(<\s*1|0\.5|0|1(?:\.0)?|2|3)(?:\s*(?:-|–|to|or|and)\s*(0\.5|0|1(?:\.0)?|2|3))?(?!\.\d|\d)", inc, re.I)
    if not m:
        return None
    first = m.group(1).replace(" ", "")
    v = sorted(({0.0, 0.5} if first == "<1" else {float(first)}) | ({float(m.group(2))} if m.group(2) else set()))
    f = lambda x: ("%g" % x)
    return f(v[0]) + ("–" + f(v[-1]) if len(v) > 1 else "")


EITHER_OR = re.compile(r"(?:na[iï]ve|untreated|de ?novo|not (?:on|taking|receiving) (?:any )?(?:pd|parkinson|dopaminergic|symptomatic))[^.\n;]{0,80}\(?\bor\b\)?[^.\n;]{0,80}(?:receiv|stable|treated|on )|"
                       r"(?:with or without|either)[^.\n;]{0,40}(?:treatment|therapy|medication)|"
                       r"for (?:participants|patients|subjects) (?:who are )?not (?:taking|on|receiving)", re.I)
GENE_OPTIONAL = re.compile(r"for (?:participants|patients|subjects) (?:with|who have|carrying) (?:an? )?(?:known )?(?:gba|lrrk2)|with or without[^.\n;]{0,40}(?:gba|lrrk2|mutation|variant)|(?:gba|lrrk2)[^.\n;]{0,40}(?:mutation|variant)?[^.\n;]{0,20}(?:or not|not required|regardless)", re.I)


OPTIONAL_LINE = re.compile(r"\boptional\b|if available|not required", re.I)


def required(rx, inc):
    """포함 조건의 각 줄에서 찾되, 그 줄이 명시적으로 선택 조건(optional, if available, not required)이면 필수로 세지 않는다.
    "and/or"·"supportive evidence"처럼 필수 조건에도 흔히 쓰는 표현은 선택으로 보지 않는다."""
    return any(rx.search(line) and not OPTIONAL_LINE.search(line) for line in re.split(r"\n|(?<=;)", inc))


def extract(text, disease):
    inc, exc = split_sections(text)
    out = {}
    if disease in ("PD", "PD+AD"):
        out["hy_max"] = hoehn_yahr_max(inc)
        out["dur_max_y"] = disease_duration_max_years(inc)
        out["untreated"] = bool((RX["untreated_inc"].search(inc) and not EITHER_OR.search(inc)) or RX["untreated_exc"].search(exc))
        out["dat_req"] = required(RX["dat"], inc)
        out["saa_req"] = bool(RX["saa"].search(inc))
        opt = GENE_OPTIONAL.search(inc)
        out["lrrk2"] = bool(RX["lrrk2"].search(inc)) and not opt
        out["gba"] = bool(RX["gba"].search(inc)) and not opt
    if disease in ("AD", "PD+AD"):
        lo, hi = mmse_range(inc)
        out["mmse_lo"], out["mmse_hi"] = lo, hi
        out["cdr"] = cdr_global(inc)
        out["amyloid_req"] = required(RX["amyloid"], inc)
        out["tau_pet_req"] = bool(RX["tau_pet"].search(inc))
        st = [lab for lab, p in STAGE_AD if re.search(p, inc + " ", re.I)]
        out["ad_stage"] = st[0] if st else None          # 가장 이른 병기(검증용, 판독 기준과 같음)
        out["ad_stages"] = ";".join(st) if st else None  # 포함 조건이 받는 병기 전부(현황판용)
    return out
