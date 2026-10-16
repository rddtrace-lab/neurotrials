# NeuroTrials Watch

Parkinson's and Alzheimer's early-phase drug trials (phase 1 to 2/3), rebuilt every day from the public ClinicalTrials.gov API,
classified by mechanism, with a daily change log, a primary completion calendar and one page per trial.

- **This week**: detected changes (status, phase, mechanism label, enrollment, primary completion date, posted results, new registrations)
- **Explore**: filterable table of every trial in scope
- **Completion calendar**: primary completion dates, plus trials still listed as active more than a year after primary completion
- **Mechanisms**: active trials by mechanism, disease and phase
- **RSS** feed of changes and CSV downloads

## How it works
`tracker/update.py` downloads a snapshot (`moduleA/fetch.py`), classifies it (`moduleA/build.py`, rule dictionary in `moduleA/rules.py`),
compares it with the previous day's table (`data/trials_prev.csv`) and appends changes to `data/events.csv`. `tracker/generate.py` writes the static site.
A GitHub Actions workflow (`.github/workflows/neurotrials.yml`) runs both every day and deploys to GitHub Pages.
The site URL defaults to `https://OWNER.github.io/REPO`; set the repository variable `SITE_URL`
to override it (the RSS feed and sitemap need absolute links).

```bash
pip install pandas
python -m tracker.update data raw      # fetch + classify + log changes
python -m tracker.generate data site   # build the static site into ./site
```

## Classification accuracy
Measured against blinded manual reading of 40 randomly sampled active trials not used to write the rules (rules v2.5): class
(disease-modifying / symptomatic / unclassified) 82.5% (95% CI 68.0–91.3%), primary mechanism 75.0% (59.8–85.8%). Current rules are v2.8.
Wrongly excluded: 7 of 169 (4.1%, 2.0–8.3%) active trials excluded by rules v2.4, 6 since fixed.
Please report misclassifications through Issues.

## Data and license
Source data: ClinicalTrials.gov (U.S. National Library of Medicine). Code: MIT License. Derived tables may be reused with attribution.
Not medical advice.
