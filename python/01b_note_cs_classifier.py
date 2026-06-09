#!/usr/bin/env python3
# ============================================================================
# 01b_note_cs_classifier.py
# Study:  CS-MORT Dynamic (CS-MORT-8 Rebuild)
# Purpose: Mention/sentence-level classification of "cardiogenic shock" in
#          MIMIC-IV discharge notes using medspaCy + the ConText algorithm,
#          to identify TRUE, CURRENT, AFFIRMED cardiogenic shock and to
#          recover genuine CS missed by whole-note regex (tamponade/PE/
#          post-arrest/post-cardiotomy phenotypes that lack an AMI/HF code).
#
# WHY: Whole-note SQL regex over-aggregates (one differential mention anywhere
#      kills an otherwise-affirmed note). ConText classifies EACH mention by
#      its local context (negated / historical / hypothetical / family /
#      uncertain), so a note is positive iff it has >=1 affirmed, current,
#      non-hypothetical, non-family mention.
#
# OUTPUT: table `YOUR_PROJECT_ID.3_UPDATED_CS_MORT_STUDY.note_cs_affirm`
#         with columns: hadm_id, has_cs_note_affirm (1/0), n_affirm_mentions,
#         n_total_mentions. Consumed by the rebuilt 01_cohort_generation.sql.
#
# REPRODUCIBILITY: pinned in r_requirements/requirements.txt; runs in Colab
#   (uses the BigQuery client) or locally (reads a JSON the bq CLI exported).
# ============================================================================
import sys, json, csv

PROJECT = "YOUR_PROJECT_ID"
DATASET = "3_UPDATED_CS_MORT_STUDY"
NOTES_JSON = "/tmp/cs_candidate_notes.json"      # local: bq-exported notes
OUT_CSV    = "/tmp/note_cs_affirm.csv"

# --- 1. Load candidate notes: every discharge note containing the phrase ----
# Columns expected: hadm_id (int), text (str). One row per note.
def load_notes():
    try:
        from google.cloud import bigquery   # Colab / authed-client path
        client = bigquery.Client(project=PROJECT)
        q = """
        SELECT hadm_id, text
        FROM `physionet-data.mimiciv_note.discharge`
        WHERE LOWER(text) LIKE '%cardiogenic shock%'
        """
        return [dict(r) for r in client.query(q).result()]
    except Exception as e:
        print(f"[info] BigQuery client unavailable ({e}); reading {NOTES_JSON}")
        with open(NOTES_JSON) as f:
            content = f.read().strip()
        try:
            data = json.loads(content)            # JSON array (bq --format=json)
            return data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            return [json.loads(line) for line in content.splitlines() if line.strip()]  # NDJSON

# --- 2. Build the medspaCy ConText pipeline ---------------------------------
def build_nlp():
    import medspacy
    from medspacy.ner import TargetRule
    from medspacy.context import ConTextRule
    nlp = medspacy.load(medspacy_enable=["medspacy_pyrush",
                                         "medspacy_target_matcher",
                                         "medspacy_context"])
    # Target: the phrase (text is lowercased before processing).
    nlp.get_pipe("medspacy_target_matcher").add([TargetRule("cardiogenic shock", "CS")])
    # Clinical context rules beyond ConText defaults, tuned to the false
    # positives found in the manual audit (differential / uncertainty / denial).
    ctx = nlp.get_pipe("medspacy_context")
    extra = [
        # differential / uncertainty -> treat as NON-affirmed (POSSIBLE)
        ConTextRule("vs",                 "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("vs.",                "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("v.",                 "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("+/-",                "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("versus",             "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("differential",       "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("on the differential","POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("ddx",                "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("considered",         "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("consideration",      "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("concern for",        "POSSIBLE_EXISTENCE", direction="FORWARD"),
        ConTextRule("concerning for",     "POSSIBLE_EXISTENCE", direction="FORWARD"),
        ConTextRule("c/f",                "POSSIBLE_EXISTENCE", direction="FORWARD"),
        ConTextRule("low c/f",            "NEGATED_EXISTENCE",  direction="FORWARD"),
        ConTextRule("suspicion for",      "POSSIBLE_EXISTENCE", direction="FORWARD"),
        ConTextRule("suspicion of",       "POSSIBLE_EXISTENCE", direction="FORWARD"),
        ConTextRule("low suspicion",      "NEGATED_EXISTENCE",  direction="FORWARD"),
        ConTextRule("possible",           "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("possibly",           "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("question of",        "POSSIBLE_EXISTENCE", direction="BIDIRECTIONAL"),
        ConTextRule("less likely",        "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("unlikely",           "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("improbable",         "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("argued against",     "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("argues against",     "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("not consistent with","NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("not consistent",     "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("inconsistent with",  "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("non-diagnostic",     "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("rather than",        "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("doubt",              "NEGATED_EXISTENCE",  direction="FORWARD"),
        ConTextRule("ruled out",          "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("ruling out",         "NEGATED_EXISTENCE",  direction="BIDIRECTIONAL"),
        ConTextRule("no evidence of",     "NEGATED_EXISTENCE",  direction="FORWARD"),
        ConTextRule("no signs of",        "NEGATED_EXISTENCE",  direction="FORWARD"),
    ]
    ctx.add(extra)
    return nlp

# --- 3. Classify ------------------------------------------------------------
def is_affirmed(ent):
    e = ent._
    return not (getattr(e, "is_negated", False) or getattr(e, "is_historical", False)
                or getattr(e, "is_hypothetical", False) or getattr(e, "is_family", False)
                or getattr(e, "is_uncertain", False))

def main():
    notes = load_notes()
    print(f"[info] loaded {len(notes)} candidate notes")
    nlp = build_nlp()
    from collections import defaultdict
    agg = defaultdict(lambda: [0, 0])     # hadm_id -> [n_affirm, n_total]
    texts = [(n["hadm_id"], (n["text"] or "").lower()) for n in notes]
    for i, (hadm_id, doc) in enumerate(zip([h for h, _ in texts],
                                           nlp.pipe([t for _, t in texts], batch_size=50))):
        cs = [e for e in doc.ents if e.label_ == "CS"]
        agg[hadm_id][1] += len(cs)
        agg[hadm_id][0] += sum(1 for e in cs if is_affirmed(e))
        if (i + 1) % 500 == 0:
            print(f"[info] processed {i+1}/{len(texts)}")
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hadm_id", "has_cs_note_affirm", "n_affirm_mentions", "n_total_mentions"])
        for hadm_id, (na, nt) in agg.items():
            w.writerow([hadm_id, 1 if na > 0 else 0, na, nt])
    print(f"[done] wrote {OUT_CSV}: {sum(1 for v in agg.values() if v[0]>0)} affirmed of {len(agg)} hadm")

if __name__ == "__main__":
    main()
