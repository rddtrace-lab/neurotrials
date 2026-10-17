from .classify import DISEASE_LABEL

STATUS_EN = {"RECRUITING": "Recruiting", "NOT_YET_RECRUITING": "Not yet recruiting", "ENROLLING_BY_INVITATION": "Enrolling by invitation",
             "ACTIVE_NOT_RECRUITING": "Active, not recruiting", "COMPLETED": "Completed", "TERMINATED": "Terminated", "WITHDRAWN": "Withdrawn",
             "SUSPENDED": "Suspended", "UNKNOWN": "Unknown status"}
PHASE_EN = {"Early 1": "Early phase 1", "1": "Phase 1", "1/2": "Phase 1/2", "2": "Phase 2", "2/3": "Phase 2/3", "3": "Phase 3", "4": "Phase 4",
            "Not applicable": "Not applicable", "": "Not stated"}
CHANGE_EN = {"new": "New trial", "removed": "Left the tracker", "status": "Status change", "phase": "Phase change",
             "enrollment": "Enrollment target change", "primary_completion": "Primary completion date change",
             "modality": "Modality re-labelled", "target": "Target change", "results": "Results posted"}
MODALITIES = ["CAR-T", "CAR-NK", "T-cell engager", "CAAR-T", "CAR-Treg"]
MOD_CLS = {"CAR-T": "s1", "T-cell engager": "s2", "CAR-NK": "s3", "CAAR-T": "s0", "CAR-Treg": "s0"}
PLATFORMS = ["Autologous", "Allogeneic", "In vivo / mRNA"]
