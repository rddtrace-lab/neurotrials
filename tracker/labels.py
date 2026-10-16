"""Display labels (English) for the public tracker. Codes come from moduleA.rules."""
MECH_EN = {
    "DUB": "Deubiquitinase / ubiquitin pathway", "MITO": "Mitophagy / mitochondria", "ASYN": "Alpha-synuclein",
    "LRRK2": "LRRK2", "GBA": "GBA / lysosome", "INFLAM": "Neuroinflammation / immune", "GLP1": "GLP-1 / metabolic",
    "KINASE": "c-Abl and other kinases", "IRON": "Iron / oxidative stress", "AMYLOID": "Amyloid", "TAU": "Tau",
    "GUT": "Gut microbiome", "GENECELL": "Gene / cell therapy", "SYM_PD": "PD symptomatic", "SYM_COG": "Cognitive symptomatic",
    "SYM_NP": "Non-motor / neuropsychiatric symptoms", "DX": "Diagnostic / imaging", "OTHER": "Other / unclassified",
}
GROUP_EN = {"DMT": "Disease-modifying", "SYM": "Symptomatic", "UNK": "Unclassified", "DX": "Diagnostic"}
DISEASE_EN = {"PD": "Parkinson's", "AD": "Alzheimer's", "PD+AD": "Parkinson's + Alzheimer's"}
STATUS_EN = {
    "RECRUITING": "Recruiting", "NOT_YET_RECRUITING": "Not yet recruiting", "ENROLLING_BY_INVITATION": "Enrolling by invitation",
    "ACTIVE_NOT_RECRUITING": "Active, not recruiting", "COMPLETED": "Completed", "TERMINATED": "Terminated",
    "WITHDRAWN": "Withdrawn", "SUSPENDED": "Suspended", "UNKNOWN": "Unknown status",
}
PHASE_EN = {"0/1 (초기 1상)": "Early phase 1", "1": "Phase 1", "1/2": "Phase 1/2", "2": "Phase 2", "2/3": "Phase 2/3"}
CHANGE_EN = {
    "new": "New registration", "removed": "Removed from registry query", "scope": "Scope change", "status": "Status change",
    "phase": "Phase change", "mech_primary": "Mechanism re-classified", "enrollment": "Enrollment change",
    "primary_completion": "Primary completion date change", "results": "Results posted",
}
