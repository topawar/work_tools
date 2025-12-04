def chunk_list(seq, size):
    res = []
    cur = []
    for x in seq:
        cur.append(x)
        if len(cur) >= size:
            res.append(cur)
            cur = []
    if cur:
        res.append(cur)
    return res

def to_literal(v):
    if v is None:
        return None
    s = str(v).strip()
    return "'" + s.replace("'", "''") + "'"

def format_in(values):
    vals = []
    for v in values:
        lit = to_literal(v)
        if lit and (lit not in vals):
            vals.append(lit)
    return ", ".join(vals)

def merge_by_key(records, key_fn):
    groups = {}
    for r in records:
        k = key_fn(r)
        groups.setdefault(k, []).append(r)
    return groups

def compose_or(conds, columns):
    parts = []
    for c in conds:
        segs = []
        ok = True
        for col in columns:
            v = c.get(col)
            lit = to_literal(v)
            if lit is None:
                ok = False
                break
            segs.append(f"{col}={lit}")
        if ok:
            parts.append("(" + " AND ".join(segs) + ")")
    return " OR ".join(parts)
