"""Turn ClinicalTrials.gov study records into one row per trial with the fields the site uses.

In scope = interventional study + at least one autoimmune disease in its conditions or title + an immune-reset modality
(CAR or other engineered immune cell therapy, or a T-cell engager) in its interventions or title.
Rules are plain regular expressions so anyone can audit them; RULES_VERSION goes up whenever they change."""
import re
import pandas as pd

RULES_VERSION = "1.1"

DISEASES = [  # code, label, pattern (matched against conditions and titles)
    ("LN", "Lupus nephritis", r"lupus nephritis|\bLN\b|LN class|nephritis.{0,20}lupus"),
    ("SLE", "Systemic lupus erythematosus", r"systemic lupus|\bSLE\b|lupus erythematosus|\blupus\b"),
    ("SSC", "Systemic sclerosis", r"systemic sclerosis|scleroderma|\bSSc\b"),
    ("IIM", "Myositis", r"myositis|dermatomyositis|polymyositis|antisynthetase|anti-synthetase|\bIIM\b|inflammatory myopath|necrotizing myopath"),
    ("MG", "Myasthenia gravis", r"myasthenia"),
    ("MS", "Multiple sclerosis", r"multiple sclerosis|\bRRMS\b|\bPPMS\b|\bSPMS\b"),
    ("NMOSD", "NMOSD / MOGAD", r"neuromyelitis|\bNMOSD\b|\bNMO\b|\bMOGAD\b|MOG antibody"),
    ("CIDP", "CIDP and autoimmune neuropathy", r"\bCIDP\b|chronic inflammatory demyelinating|autoimmune (?:neuropathy|nodopathy)"),
    ("NEURO", "Other autoimmune neurological", r"autoimmune encephalitis|NMDA|stiff[- ]person|LGI1|autoimmune neurolog"),
    ("RA", "Rheumatoid arthritis", r"rheumatoid arthritis|\bRA\b(?=.*arthritis)"),
    ("AAV", "ANCA-associated vasculitis", r"\bANCA\b|vasculitis|granulomatosis with polyangiitis|microscopic polyangiitis|\bGPA\b"),
    ("SJD", "Sjögren's disease", r"sj[öo]gren"),
    ("IGG4", "IgG4-related disease", r"IgG4"),
    ("RENAL", "Immune kidney disease", r"membranous nephropathy|\bMN\b|nephrotic syndrome|IgA nephropathy|anti-GBM|glomerulonephritis|focal segmental"),
    ("HEME", "Immune blood disorders", r"immune thrombocytopeni|\bITP\b|autoimmune hem[oa]lytic|\bAIHA\b|thrombotic thrombocytopenic purpura|\bTTP\b|cold agglutinin"),
    ("SKIN", "Pemphigus / pemphigoid", r"pemphig|autoimmune bullous|bullous pemphigoid"),
    ("T1D", "Type 1 diabetes", r"type 1 diabetes|T1D\b"),
    ("OTHER", "Autoimmune, disease not named", r"autoimmun|immune[- ]mediated|antiphospholipid|still'?s disease|uveitis|psoriatic|ankylosing|spondyloarthritis|crohn|ulcerative colitis|myocarditis"),
]
DISEASE_LABEL = {c: l for c, l, _ in DISEASES} | {"MULTI": "Basket (several autoimmune diseases)"}
_DX = [(c, re.compile(p, re.I)) for c, _, p in DISEASES]
ONCO = re.compile(r"lymphoma|leuk[ae]mia|myeloma|cancer|carcinoma|tumou?r|neoplas|malignan|sarcoma|glioma|blastoma|melanoma", re.I)

TCE = re.compile(r"T[- ]cell[- ]engag|\bTCE\b|blinatumomab|teclistamab|mosunetuzumab|glofitamab|imvotamab|cevostamab|odronextamab|"
                 r"epcoritamab|elranatamab|linvoseltamab|talquetamab|CD19\s*[x×/]\s*CD3|CD20\s*[x×/]\s*CD3|BCMA\s*[x×/]\s*CD3|"
                 r"CD3\s*[x×/]\s*(?:CD19|CD20|BCMA)|bispecific.{0,40}CD3|CD3.{0,40}bispecific", re.I)
CAAR = re.compile(r"\bCAAR", re.I)
TREG = re.compile(r"CAR[- ]?Treg|regulatory T.{0,30}chimeric|chimeric.{0,60}regulatory T", re.I)
CARNK = re.compile(r"CAR[- ]?NK|NK[- ]cell.{0,40}(?:CAR\b|chimeric)|(?:CAR\b|chimeric).{0,40}NK[- ]cell|CNTY-?101|NKX019", re.I)
CART = re.compile(r"CAR[- ]?T\b|CAR[- ]T[- ]cell|chimeric antigen receptor|\bCAR\b.{0,15}T[- ]cell|KYV-?101|CABA-?201|rese-?cel|obe-?cel|"
                  r"obecabtagene|\bCAR-?19\b|zamto-?cel|azer-?cel|Descartes-?08|MB-?CART|FT819|YTB323|rapcabtagene|GC012F|BMS-?986353|"
                  r"\bCD19[- ]CAR|BCMA[- ]CAR|CD19[- ]directed.{0,20}T[- ]cell", re.I)
ALLO = re.compile(r"allogene|off[- ]the[- ]shelf|universal CAR|\bUCAR|donor[- ]derived|iPSC|induced pluripotent|healthy donor|"
                  r"FT819|CNTY-?101|azer-?cel|NKX019", re.I)
INVIVO = re.compile(r"in[- ]vivo CAR|in vivo.{0,40}(?:CAR|chimeric)|lipid nanoparticle|\bLNP\b|mRNA[- ]CAR|Descartes-?08|mRNA.{0,30}CAR", re.I)

# antigen, pattern (product names map to their published targets)
ANTIGENS = [("CD19", r"\bCD19\b|KYV-?101|CABA-?201|rese-?cel|obe-?cel|obecabtagene|azer-?cel|CNTY-?101|FT819|YTB323|rapcabtagene|"
                     r"BMS-?986353|blinatumomab|NKX019|CNCT19|inaticabtagene|relma-?cel|relmacabtagene|zamto-?cel|MB-?CART2019|GC012F|IMPT-?514"),
            ("BCMA", r"\bBCMA\b|Descartes-?08|teclistamab|elranatamab|linvoseltamab|CT103A|equecabtagene|eque-?cel|GC012F"),
            ("CD20", r"\bCD20\b|mosunetuzumab|glofitamab|imvotamab|odronextamab|epcoritamab|zamto-?cel|MB-?CART2019|IMPT-?514"),
            ("BAFF-R", r"\bBAFF"), ("CD7", r"\bCD7\b"), ("CD70", r"\bCD70\b"), ("CD38", r"\bCD38\b"),
            ("FcRH5 / GPRC5D", r"cevostamab|talquetamab|FcRH5|GPRC5D")]
_AG = [(c, re.compile(p, re.I)) for c, p in ANTIGENS]
ACTIVE = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING"}
PHASES = {"EARLY_PHASE1": "Early 1", "PHASE1": "1", "PHASE2": "2", "PHASE3": "3", "PHASE4": "4"}


def diseases(text):
    return [c for c, rx in _DX if rx.search(text)]


def modality(text):
    if TCE.search(text):
        return "T-cell engager"
    if CAAR.search(text):
        return "CAAR-T"
    if TREG.search(text):
        return "CAR-Treg"
    if CARNK.search(text):
        return "CAR-NK"
    if CART.search(text):
        return "CAR-T"
    return None


def target(names, full, desc=""):
    """Antigens named in the title or intervention names; then arm/intervention descriptions; then the summary and keywords
    (descriptions often mention other antigens, e.g. prior therapies, so earlier levels win)."""
    if CAAR.search(names):
        hit = [c for c, rx in _AG if rx.search(names)]
        return "Autoantigen (CAAR)" + ("+" + "+".join(hit) if hit else "")
    for text in (names, full, desc):
        hit = [c for c, rx in _AG if rx.search(text)]
        if hit:
            return "+".join(hit)
    return "Other / not stated"


def age(s):
    m = re.match(r"([\d.]+)\s*(Year|Month|Week|Day)", s or "", re.I)
    return None if not m else round(float(m.group(1)) / {"year": 1, "month": 12, "week": 52.18, "day": 365.25}[m.group(2).lower()], 1)


def row(s):
    p = s["protocolSection"]
    idm, st, des = p.get("identificationModule", {}), p.get("statusModule", {}), p.get("designModule", {})
    cond = p.get("conditionsModule", {}).get("conditions", [])
    ivs = p.get("armsInterventionsModule", {}).get("interventions", [])
    sp = p.get("sponsorCollaboratorsModule", {})
    el = p.get("eligibilityModule", {})
    locs = p.get("contactsLocationsModule", {}).get("locations", [])
    title, otitle = idm.get("briefTitle", ""), idm.get("officialTitle", "") or ""
    iv_text = " ".join(f"{i.get('name', '')} {' '.join(i.get('otherNames', []))} {i.get('description', '')}" for i in ivs)
    arm_text = " ".join(f"{a.get('label', '')} {a.get('description', '')}" for a in p.get("armsInterventionsModule", {}).get("armGroups", []))
    prod = f"{title} {otitle} {iv_text} {arm_text}"
    names = f"{title} {otitle} " + " ".join(f"{i.get('name', '')} {' '.join(i.get('otherNames', []))}" for i in ivs)
    cond_text = " ; ".join(cond) + " ; " + title + " ; " + otitle
    dx = diseases(cond_text)
    if len(dx) > 1 and "OTHER" in dx:
        dx.remove("OTHER")  # generic wording ("refractory autoimmune disease") only counts when no disease is named
    onco_only = bool(ONCO.search(" ".join(cond))) and not diseases(" ; ".join(cond))
    dm = p.get("descriptionModule", {})
    desc = f"{dm.get('briefSummary', '')} {dm.get('detailedDescription', '')} {' '.join(p.get('conditionsModule', {}).get('keywords', []))}"
    mod = modality(prod) or modality(desc)
    phases = des.get("phases", []) or []
    ph = "/".join(PHASES.get(x, "") for x in phases if x in PHASES) or ("Not applicable" if phases else "")
    countries = sorted({l.get("country") for l in locs if l.get("country")})
    plat = None
    if mod in ("CAR-T", "CAR-NK", "CAAR-T", "CAR-Treg"):
        plat = "In vivo / mRNA" if INVIVO.search(prod) else "Allogeneic" if ALLO.search(prod) or mod == "CAR-NK" and not re.search(r"autologous", prod, re.I) else "Autologous"
    in_scope = des.get("studyType") == "INTERVENTIONAL" and bool(dx) and mod is not None and not onco_only
    spec = [d for d in dx if d != "OTHER" and not (d == "SLE" and "LN" in dx)]
    primary = None if not dx else "OTHER" if not spec else spec[0] if len(spec) == 1 else "MULTI"
    return {
        "nct": idm["nctId"], "title": title, "in_scope": in_scope, "diseases": ";".join(dx), "disease": primary,
        "modality": mod, "platform": plat, "target": target(names, prod, desc) if mod else None,
        "phase": ph, "status": st.get("overallStatus"), "active": st.get("overallStatus") in ACTIVE,
        "start": st.get("startDateStruct", {}).get("date"), "primary_completion": st.get("primaryCompletionDateStruct", {}).get("date"),
        "first_posted": st.get("studyFirstPostDateStruct", {}).get("date"), "last_update": st.get("lastUpdatePostDateStruct", {}).get("date"),
        "has_results": bool(s.get("hasResults")), "sponsor": sp.get("leadSponsor", {}).get("name"), "sponsor_class": sp.get("leadSponsor", {}).get("class"),
        "collaborators": "; ".join(c.get("name", "") for c in sp.get("collaborators", [])),
        "enrollment": des.get("enrollmentInfo", {}).get("count"), "conditions": "; ".join(cond),
        "interventions": "; ".join(f"{i.get('type', '').title()}: {i.get('name', '')}" for i in ivs),
        "countries": ";".join(countries), "n_sites": len(locs), "age_min": age(el.get("minimumAge")), "age_max": age(el.get("maximumAge")),
        "summary": (p.get("descriptionModule", {}).get("briefSummary") or "")[:1500],
    }


def build(snapshot_rows):
    return pd.DataFrame([row(s) for s in snapshot_rows]).sort_values("nct").reset_index(drop=True)
