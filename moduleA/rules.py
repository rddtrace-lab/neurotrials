"""모듈 A의 분류 규칙. 사람이 읽고 고칠 수 있게 코드와 분리해 둔다.

기전(MECHANISMS): 중재 이름·제목·요약에 나오는 약 이름이나 표적 단어로 정한다.
위에 있는 기전이 우선한다(한 임상이 여러 기전에 걸리면 모두 기록하고, 첫 번째를 주 기전으로 쓴다).
"""
import re

# (코드, 한국어 이름, 계열, 정규식) — 계열: DMT(질환 조절) / SYM(증상 조절) / DX(진단)
MECHANISMS = [
    ("DUB", "DUB·유비퀴틴 경로", "DMT",
     r"\busp ?30\b|\busp ?14\b|deubiquitin|\bdub\b|mtx ?325|mtx ?115325|ubiquitin[- ]specific"),
    ("MITO", "미토파지·미토콘드리아", "DMT",
     r"mitophag|\bpink1\b|parkin activat|mitochondri|urolithin|ursodeoxychol|\budca\b|coenzyme q|\bcoq10\b|mitoq|"
     r"nicotinamide riboside|\bnad\+?\b|\bnr\b supplement|ept?i-?589|\bcreatine\b|terazosin|\bpgk1\b"),
    ("ASYN", "알파시누클레인", "DMT",
     r"ly3962681|synuclein(?!opath)|prasinezumab|cinpanemab|\bbiib054\b|lu ?af82422|amlenetug|minzasolmin|ucb0599|anle138b|"
     r"\bpd01\b|affitope|ub-?312|aci-?7104|medi1341|tak-?341|npt200|bion?-?1|\bbiib101\b|ion464|emrusolmin"),
    ("LRRK2", "LRRK2", "DMT", r"lrrk2|\bbiib122\b|dnl ?151|dnl ?201|neu-?411|\bbiib094\b|ion859"),
    ("GBA", "GBA·리소좀", "DMT",
     r"gt-?02287|\bgba1?\b|gcase|glucocerebrosid|ambroxol|venglustat|lti-?291|bia ?28-?6156|\bpr001\b|ly3884961|lysosom"),
    ("INFLAM", "신경염증·면역", "DMT",
     r"vhb937|tb006|galectin|bhv-?8000|tyk2|ec5026|soluble epoxide|lbt-?3627|cpg1018|tlr9|\bad04\b|dimethyl fumarate|ozanimod|s1p|niacin|nicotinic acid|dasatinib|quercetin|senolytic|nlrp3|inflammasome|dapansutrile|selnoflast|ventyx|vent-?02|nt-?0796|zyil1|\btrem2\b|\bal002\b|vg-?3927|"
     r"microglia|csf1r|sargramostim|gm-csf|xpro1595|\btnf\b|masitinib|verdiperstat|azd3241|myeloperoxidase|"
     r"baricitinib|daratumumab|complement|anx005|minocycline|neuroinflam|anti-inflammat|\bil-?\d+\b|interleukin|"
     r"montelukast|canakinumab|anakinra|rapamycin|sirolimus|azathioprine|immunomod|treg|regulatory t"),
    ("GLP1", "GLP-1·대사", "DMT",
     r"sitagliptin|gliptin|dpp-?4|benfotiamine|t3d-?959|obicetrapib|cetp|ketone|exenatide|lixisenatide|liraglutide|semaglutide|tirzepatide|nly01|pt320|\bglp-?1\b|intranasal insulin|"
     r"\binsulin\b|metformin|pioglitazone|empagliflozin|dapagliflozin"),
    ("KINASE", "c-Abl 등 키나제", "DMT", r"radotinib|fasudil|rock inhibitor|nilotinib|bosutinib|c-abl|risvodetinib|ikt-?148009|vodobatinib|k0706"),
    ("IRON", "철·산화 스트레스", "DMT", r"npi-?001|2-hydroxybenzylamine|2-hoba|tocotrienol|tocovid|antioxidant|edaravone|deferiprone|iron chelat|inosine|\burate\b|uric acid|glutathione|n[- ]?acetyl[- ]?cysteine|\bnac\b"),
    ("AMYLOID", "아밀로이드", "DMT",
     r"ct1812|sabirnetug|acu193|pmn310|aci-?24|aln-?app|mivelsiran|dnl921|gsm-?\d|gamma[- ]secretase|\bapp\b|amyloid|lecanemab|donanemab|aducanumab|gantenerumab|solanezumab|crenezumab|remternetug|trontinemab|"
     r"\bbace\b|valiltramiprosate|alz-?801|tramiprosate|verubecestat|lanabecestat|elenbecestat|ab ?vac|abeta|a-?beta|\baβ\b"),
    ("TAU", "타우", "DMT",
     r"aro-?mapt|\bmapt\b|nio752|vy1706|bms-?986446|\btau\b|anti-tau|biib080|bepranemab|e2814|semorinemab|gosuranemab|tilavonemab|zagotenemab|"
     r"hydromethylthionine|\blmtm\b|posdinemab|jnj-?63733657|aadvac|o-glcnac|osmotic"),
    ("GUT", "장내 미생물", "DMT", r"probiotic|microbio|f(?:a)?ecal microbiota|f(?:a)?ecal transplant|\bfmt\b|rifaximin|gut-?x|tributyrin|butyrate"),
    ("GENECELL", "유전자·세포 치료", "DMT",
     r"vgn-?r09b|ab-?1005|dsp-?1083|nouvneu|\bidap\b|cord blood|umbilical|neural precursor|progenitor cell|snk01|natural killer|chemogenetic|\baav\b|gene therap|\bgdnf\b|\baadc\b|cell therap|stem cell|dopaminergic neuron|bemdaneprocel|transplant|"
     r"\bipsc\b|mesenchymal|fibroblast|exosome|antisense|\baso\b|sirna"),
    ("SYM_PD", "PD 증상 조절", "SYM",
     r"lu ?af28996|mucuna|ipx ?203|varenicline|falls|gait|adenosine a2a|a2a antagonist|levodopa|carbidopa|apomorphine|rotigotine|ropinirole|pramipexole|opicapone|entacapone|safinamide|rasagiline|"
     r"selegiline|istradefylline|amantadine|tavapadon|nd0612|foslevodopa|p2b001|ipx203|mesdopetam|pimavanserin|"
     r"droxidopa|dyskinesi|\boff\b episode|off[- ]time|motor fluctuation|wearing[- ]off|freezing of gait|tremor"),
    ("SYM_COG", "인지 증상 조절", "SYM", r"donepezil|e2020|aricept|galantamine|memantine|rivastigmine|cholinesterase|huperzine"),
    ("SYM_NP", "비운동·정신 증상", "SYM",
     r"cannabidiol|\bcbd\b|xanomeline|trospium|karxt|brexpiprazole|suvorexant|lemborexant|pimavanserin|agitation|axs-?05|masupirdine|methylphenidate|apathy|"
     r"psychosis|hallucinat|insomnia|\bsleep|depressi|anxiety|constipation|orthostatic|hypotension|\bpain\b|fatigue"),
    ("DX", "진단·영상", "DX", r"\bpet\b tracer|radioligand|radiotracer|[\[(]\s*1[18][cf]\s*[\])]|[\[(]\s*123i\s*[\])]|\b123i\b|i-?123\b|datscan|\[1[18][cf]\]|\b[cf]-?1[18]\b|\b1[18][cf]-|\bf ?18\b|18f-|11c-|"
     r"\bspect\b|imaging agent|pet (?:imaging agent|ligand)|ioflupane|florbetapir|florbetaben|flutemetamol|flortaucipir|mk-?6240|florquinitau|"
     r"pi-?2620|nav4694|\bpib\b|pbr28|ucb-j|f-?dopa|fdopa|lumason|microbubble|gadolinium|dotarem|amyvid"),
]
# 정규식 안의 백슬래시가 두 번 들어가면(\\\\b) 단어 경계가 아니라 글자 '\\b'를 찾게 되어 조용히 안 맞는다. 미리 막는다.
assert not any("\\\\" in p for c, n, g, p in MECHANISMS), "규칙 정규식에 백슬래시가 두 번 들어갔습니다"
MECH_RE = [(c, n, g, re.compile(p, re.I)) for c, n, g, p in MECHANISMS]

# 증상 조절 계열을 중재 설명·제목에서 찾을 때는 적응증 단어만 쓴다.
# 레보도파·도네페질 같은 약 이름은 '안정 용량 유지' 같은 동반 약물로 자주 나오기 때문이다. 요약에서는 증상 계열을 찾지 않는다.
SYM_INDICATION = {
    "SYM_PD": re.compile(r"\btremor|dyskinesi|\boff\b[- ](?:episode|time|period|state)|motor fluctuation|wearing[- ]off|freezing of gait|\bfalls?\b", re.I),
    "SYM_COG": re.compile(r"symptomatic (?:treatment|relief) of cognit", re.I),
    "SYM_NP": re.compile(r"psychosis|hallucinat|agitation|insomnia|depressi|apathy|anxiety|constipation|orthostatic hypotension|\bpain\b|fatigue", re.I),
}
# 승인된 항아밀로이드 항체는 '배경 치료'로 함께 적히는 일이 많다. 다른 시험 중재가 있으면 기전 판단에서 뺀다.
BACKGROUND_DRUG = re.compile(r"lecanemab|leqembi|donanemab|kisunla|aducanumab|standard (?:of )?care|standard (?:treatment|therapy)|usual care|background therapy", re.I)
# 모회사·자회사처럼 이름은 달라도 같은 조직(기관 겹침에서 '관련 조직'으로 본다). 아는 것만 적은 부분 목록이다.
ORG_ALIASES = {"prevail therapeutics": "eli lilly and company", "loxo oncology": "eli lilly and company",
               "genentech inc": "hoffmann la roche", "chugai pharmaceutical": "hoffmann la roche",
               "janssen research development llc": "johnson johnson", "acadia pharmaceuticals inc": "acadia pharmaceuticals"}
MECH_NAME = {c: n for c, n, g, p in MECHANISMS}
MECH_GROUP = {c: g for c, n, g, p in MECHANISMS}
MECH_NAME["OTHER"] = "기타·미분류"
MECH_GROUP["OTHER"] = "UNK"   # 미분류: 질환 조절로도 증상 조절로도 세지 않는다

DRUG_TYPES = {"DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT"}
ACTIVE_STATUS = {"RECRUITING", "NOT_YET_RECRUITING", "ENROLLING_BY_INVITATION", "ACTIVE_NOT_RECRUITING"}
