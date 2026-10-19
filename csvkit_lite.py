#!/usr/bin/env python3
"""csvkit-lite: a tiny, zero-dependency, single-file CSV swiss army knife.

Subcommands:
    view    Pretty-print a CSV as an aligned table
    tojson  Convert CSV to JSON (objects or arrays)
    merge   Merge multiple CSVs, aligning columns
    filter  Keep rows matching a condition, e.g. --where "age>30"
    stats   Column statistics: counts, non-empty, min/max/avg for numerics
"""
import argparse
import csv
import json
import re
import sys
import unicodedata
from io import StringIO

VERSION = "1.0.0"


# ---------- helpers ----------

def detect_encoding(path):
    """Try utf-8 (with BOM), then gbk."""
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, ValueError):
            continue
    return "utf-8"  # last resort; may produce mojibake


def detect_delimiter(sample):
    """Sniff delimiter among comma / semicolon / tab / pipe."""
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        if dialect.delimiter in (",", ";", "\t", "|"):
            return dialect.delimiter
    except csv.Error:
        pass
    # Fallback: pick the candidate with the most consistent column counts
    best, best_score = ",", -1
    lines = [ln for ln in sample.splitlines() if ln.strip()][:20]
    for cand in (",", ";", "\t", "|"):
        counts = [ln.count(cand) for ln in lines]
        if not counts or max(counts) == 0:
            continue
        score = sum(1 for c in counts if c == counts[0]) * 100 + max(counts)
        if score > best_score:
            best, best_score = cand, score
    return best


def read_csv(path):
    """Return (header, rows). header is a list, rows are lists of str."""
    enc = detect_encoding(path)
    with open(path, "r", encoding=enc, newline="") as f:
        sample = f.read(8192)
        f.seek(0)
        delim = detect_delimiter(sample)
        reader = csv.reader(f, delimiter=delim)
        data = [row for row in reader if row]
    if not data:
        return [], []
    return data[0], data[1:]


def disp_width(s):
    """Display width: CJK chars count as 2."""
    w = 0
    for ch in s:
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def pad(s, width):
    return s + " " * max(0, width - disp_width(s))


def format_table(header, rows):
    widths = [disp_width(h) for h in header]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(widths):
                widths[i] = max(widths[i], disp_width(cell))
    lines = []
    lines.append(" | ".join(pad(h, widths[i]) for i, h in enumerate(header)))
    lines.append("-+-".join("-" * w for w in widths))
    for row in rows:
        cells = [row[i] if i < len(row) else "" for i in range(len(header))]
        lines.append(" | ".join(pad(c, widths[i]) for i, c in enumerate(cells)))
    return "\n".join(lines)


def try_number(s):
    """Return int/float if s looks numeric, else None."""
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        return None


# ---------- view ----------

def cmd_view(args):
    header, rows = read_csv(args.file)
    if not header:
        print("empty file", file=sys.stderr)
        return 1
    total = len(rows)
    if args.tail is not None:
        rows = rows[-args.tail:]
    else:
        rows = rows[:args.head]
    print(format_table(header, rows))
    print(f"\n[{len(rows)} of {total} rows shown]", file=sys.stderr)
    return 0


# ---------- tojson ----------

def cmd_tojson(args):
    header, rows = read_csv(args.file)
    if args.arrays:
        out = [[row[i] if i < len(row) else "" for i in range(len(header))] for row in rows]
    else:
        out = []
        for row in rows:
            out.append({h: (row[i] if i < len(row) else "") for i, h in enumerate(header)})
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text + "\n")
        print(f"wrote {args.output} ({len(out)} records)", file=sys.stderr)
    else:
        print(text)
    return 0


# ---------- merge ----------

def cmd_merge(args):
    columns = []          # union of columns, in first-seen order
    all_rows = []         # list of dicts
    for path in args.files:
        header, rows = read_csv(path)
        for h in header:
            if h not in columns:
                columns.append(h)
        for row in rows:
            d = {h: (row[i] if i < len(row) else "") for i, h in enumerate(header)}
            all_rows.append(d)
    out_rows = [[d.get(c, "") for c in columns] for d in all_rows]
    buf = StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(columns)
    w.writerows(out_rows)
    text = buf.getvalue()
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"wrote {args.output} ({len(out_rows)} rows, {len(columns)} columns)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


# ---------- filter ----------

COND_RE = re.compile(r"^\s*([^<>=!]+?)\s*(>=|<=|==|!=|>|<)\s*(.+?)\s*$")


def parse_condition(where, header):
    m = COND_RE.match(where)
    if not m:
        raise ValueError(f"bad condition: {where!r} (expected like \"age>30\")")
    col, op, val = m.group(1).strip(), m.group(2), m.group(3).strip()
    # strip surrounding quotes from value
    if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
        val = val[1:-1]
    if col not in header:
        raise ValueError(f"unknown column: {col!r} (available: {', '.join(header)})")
    return header.index(col), op, val


def match(cell, op, val):
    n_cell, n_val = try_number(cell), try_number(val)
    if n_cell is not None and n_val is not None:
        a, b = n_cell, n_val
    else:
        a, b = cell, val
    if op == ">":
        return a > b
    if op == ">=":
        return a >= b
    if op == "<":
        return a < b
    if op == "<=":
        return a <= b
    if op == "==":
        return a == b
    if op == "!=":
        return a != b
    return False


def cmd_filter(args):
    header, rows = read_csv(args.file)
    try:
        idx, op, val = parse_condition(args.where, header)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    kept = [row for row in rows if idx < len(row) and match(row[idx], op, val)]
    buf = StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(kept)
    text = buf.getvalue()
    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        print(f"wrote {args.output} ({len(kept)}/{len(rows)} rows kept)", file=sys.stderr)
    else:
        sys.stdout.write(text)
    return 0


# ---------- stats ----------

def cmd_stats(args):
    header, rows = read_csv(args.file)
    if not header:
        print("empty file", file=sys.stderr)
        return 1
    print(f"rows: {len(rows)}")
    print(f"columns: {len(header)}")
    print()
    for i, h in enumerate(header):
        cells = [row[i] if i < len(row) else "" for row in rows]
        non_empty = sum(1 for c in cells if c.strip())
        nums = [try_number(c) for c in cells]
        nums = [n for n in nums if n is not None]
        line = f"  {h}: non-empty {non_empty}/{len(rows)}"
        if nums and len(nums) == non_empty:
            line += f" | min {min(nums)} | max {max(nums)} | avg {sum(nums)/len(nums):.2f}"
        print(line)
    return 0


# ---------- main ----------

def main(argv=None):
    p = argparse.ArgumentParser(
        prog="csvkit-lite",
        description="A tiny, zero-dependency, single-file CSV toolkit.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("view", help="Pretty-print CSV as an aligned table")
    v.add_argument("file")
    v.add_argument("--head", type=int, default=20, help="show first N rows (default 20)")
    v.add_argument("--tail", type=int, default=None, help="show last N rows")
    v.set_defaults(func=cmd_view)

    t = sub.add_parser("tojson", help="Convert CSV to JSON")
    t.add_argument("file")
    t.add_argument("-o", "--output", default=None)
    t.add_argument("--arrays", action="store_true", help="output array of arrays instead of array of objects")
    t.set_defaults(func=cmd_tojson)

    m = sub.add_parser("merge", help="Merge multiple CSVs, aligning columns")
    m.add_argument("files", nargs="+")
    m.add_argument("-o", "--output", default=None)
    m.set_defaults(func=cmd_merge)

    f = sub.add_parser("filter", help='Keep rows matching a condition, e.g. --where "age>30"')
    f.add_argument("file")
    f.add_argument("--where", required=True, help='condition like "age>30", "name==张三"')
    f.add_argument("-o", "--output", default=None)
    f.set_defaults(func=cmd_filter)

    s = sub.add_parser("stats", help="Column statistics")
    s.add_argument("file")
    s.set_defaults(func=cmd_stats)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
