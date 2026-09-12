"""Gate: the authored supplement must carry every regenerated table value.

This runs in the opposite direction to verify_sources.py. That gate checks
document -> outputs: every numeral printed in the documents is derivable from
the pipeline. It cannot detect a value that has gone stale, because a stale
number usually still exists somewhere in outputs and so still traces.

This gate checks outputs -> document: every value in the regenerated table
blocks must appear in manuscript/SUPPLEMENT.md. A number that changes in the
analysis and is not carried into the supplement fails here.

Rationale: no supplementary table has a generator that writes into the
document, so every one is hand-maintained and can drift. Two values did drift
this way before this gate existed.
"""
import os
import re
import sys

_B = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('CSMORT6_OUT', os.path.join(_B, '..', 'outputs')).rstrip('/') + '/'
DOC = os.path.join(_B, '..', 'manuscript', 'SUPPLEMENT.md')


def variants(v):
    """Roundings the supplement may legitimately print.

    Deliberately conservative. An earlier version generated a one-decimal
    rounding, so -0.427892 matched inside the unrelated -0.412 and the gate
    reported a false pass. Only the exact value and roundings that keep at
    least two decimals are accepted.
    """
    out = {v}
    try:
        f = float(v)
    except ValueError:
        return out
    if f == 0:                       # -0.0 and 0.0 are the same number
        out |= {'0', '0.0', '0.00', '-0.0'}
        return out
    dec = len(v.split('.')[1]) if '.' in v else 0
    for dp in range(2, max(dec, 2) + 1):
        out.add(f"{f:.{dp}f}")
    if f == int(f):                  # 6.0 may legitimately print as 6
        out.add(str(int(f)))
        out.add(f"{int(f):.1f}")
        if abs(f) >= 1000:
            out.add(f"{int(f):,d}")
    return {x for x in out if x}


def present(value, doc):
    """Token match: the number must not be a fragment of a longer number."""
    return any(re.search(r'(?<![\d.])' + re.escape(v) + r'(?![\d])', doc)
               for v in variants(value))


def table_blocks(text):
    blocks, cur = [], []
    for ln in text.split('\n'):
        if ln.strip().startswith('|'):
            cur.append(ln)
        elif cur:
            blocks.append(cur)
            cur = []
    if cur:
        blocks.append(cur)
    return blocks


def main():
    gen_path = OUT + 'SUPPLEMENT_TABLES.md'
    if not os.path.exists(gen_path):
        sys.exit(f'verify_tables: {gen_path} missing; run pipeline/09_supplement_tables.py')
    doc = ' '.join(open(DOC).read().split())
    checked = 0
    failures = []
    for i, block in enumerate(table_blocks(open(gen_path).read()), 1):
        header = ' '.join(c.strip() for c in block[0].strip('|').split('|'))[:48]
        for row in block[2:]:
            for cell in row.strip('|').split('|'):
                cell = cell.strip()
                # 0 and 1 are too common to be informative
                if not re.fullmatch(r'-?\d+\.?\d*', cell) or cell in ('0', '1'):
                    continue
                checked += 1
                if not present(cell, doc):
                    failures.append(f'block {i} ({header}): {cell!r} not in SUPPLEMENT.md')
    if failures:
        print('verify_tables: FAIL')
        for f in failures[:25]:
            print('  ' + f)
        if len(failures) > 25:
            print(f'  ... and {len(failures) - 25} more')
        sys.exit(1)
    print(f'verify_tables: {checked} regenerated table values all present in the supplement')


if __name__ == '__main__':
    main()
