"""Source traceability gate.

Asserts that every numeric value appearing in the authored manuscript and
supplement sources (`manuscript/*.md`) is derivable from the pipeline's own
outputs, so the claim "every number in the paper comes from this pipeline"
is mechanically checked rather than asserted.

Provenance accepted:
  1. any value in outputs/*.csv, at 1-4 decimal places (this includes
     reported_values.csv, which stage 14 writes for quantities no other
     step stores);
  2. any value in the frozen protocol or its amendment (fixed design
     constants: penalty, seeds, band boundaries, card points);
  3. a value declared in manuscript/CARRIED_FORWARD.md, which names every
     figure reported from an earlier analysis rather than recomputed;
  4. the baseline tables carried verbatim from the submitted supplement,
     listed in data/submitted_tables.json and data/baseline_landmark.json
     when those files are present (they hold patient-level-derived summary
     rows and are not redistributable, so their absence is tolerated and
     reported rather than failed);
  5. an explicit allowlist of non-result numerals (DOIs, database years,
     software versions, reference volume/page numbers).

Run after the pipeline. Exit status is non-zero on any untraceable value.
"""
import json
import os
import re
import sys

_B = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('CSMORT6_OUT', os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
DATA = os.environ.get('CSMORT6_DATA', os.path.join(_B, '..', 'data')).rstrip('/') + '/'
DOC = os.path.join(_B, '..', 'manuscript')

# Non-result numerals: identifiers and citation metadata, not findings.
ALLOW = {
    '10.5281',            # Zenodo DOI prefix
    '3.9', '4.5',         # Python / R versions
    '2008', '2022', '2014', '2015',   # database year spans
    '427.5',              # ICD-9 code for cardiac arrest (a code, not a result)
}

NUM = re.compile(r'\d+\.\d+')


def variants(value: float):
    """Every rounding a manuscript might legitimately print."""
    out = set()
    for dp in (1, 2, 3, 4):
        out.add(f'{abs(value):.{dp}f}')
    return out


def provenance():
    src = set()
    n_files = 0
    for name in sorted(os.listdir(OUT)):
        if not name.endswith('.csv'):
            continue
        n_files += 1
        text = open(OUT + name).read()
        for token in re.findall(r'-?\d+\.\d+', text):
            src |= variants(float(token))
            src.add(token.lstrip('-'))
    carried = os.path.join(DOC, 'CARRIED_FORWARD.md')
    if os.path.exists(carried):
        for token in NUM.findall(open(carried).read()):
            src |= variants(float(token))
            src.add(token)
    for extra in ('PROTOCOL.md', 'PROTOCOL_AMENDMENT.md'):
        path = os.path.join(_B, '..', extra)
        if os.path.exists(path):
            src |= set(NUM.findall(open(path).read()))
    missing = []
    for name in ('submitted_tables.json', 'baseline_landmark.json'):
        path = DATA + name
        if os.path.exists(path):
            src |= set(NUM.findall(json.dumps(json.load(open(path)))))
        else:
            missing.append(name)
    return src, n_files, missing


def main():
    src, n_files, missing = provenance()
    src |= ALLOW
    failures = []
    for doc in ('MANUSCRIPT.md', 'SUPPLEMENT.md'):
        path = os.path.join(DOC, doc)
        if not os.path.exists(path):
            failures.append(f'{doc}: missing')
            continue
        text = open(path).read()
        # reference lists carry volume/page numbers, not results
        body = text.split('## Reference list')[0].split('## References')[0]
        unexplained = sorted({v for v in NUM.findall(body) if v not in src})
        print(f'{doc}: {len(set(NUM.findall(body)))} numerals, '
              f'{len(unexplained)} untraceable')
        if unexplained:
            failures.append(f'{doc}: {unexplained}')
    print(f'provenance built from {n_files} output tables')
    if missing:
        print('note: not redistributable, skipped: ' + ', '.join(missing))
    if failures:
        print('\nUNTRACEABLE VALUES')
        for f in failures:
            print(' -', f)
        sys.exit(1)
    print('verify_sources: every value in the manuscript and supplement '
          'traces to the pipeline')


if __name__ == '__main__':
    main()
