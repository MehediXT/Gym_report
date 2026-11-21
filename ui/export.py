"""
CSV export. Files go to the project's exports/ folder (mounted into the Docker
container), or to GYM_EXPORT_DIR if set. UTF-8 with BOM so Excel opens them cleanly.
"""

import csv
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORT_DIR = os.environ.get("GYM_EXPORT_DIR") or os.path.join(BASE_DIR, "exports")

_MARKERS = ("● ", "○ ")


def _clean(value):
    text = "" if value is None else str(value)
    for marker in _MARKERS:
        if text.startswith(marker):
            return text[len(marker):]
    return text


def export_rows(name, headers, rows):
    """Write rows to exports/<name>_<timestamp>.csv. Returns (path, row_count)."""
    os.makedirs(EXPORT_DIR, exist_ok=True)
    path = os.path.join(EXPORT_DIR, f"{name}_{datetime.now().strftime('%Y%m%d-%H%M%S')}.csv")
    rows = list(rows)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([_clean(v) for v in row])
    return path, len(rows)


def export_tree(tree, name):
    """Export exactly what a Treeview currently shows (respects search and filters)."""
    columns = tree["columns"]
    headers = [tree.heading(c)["text"] for c in columns]
    raw = getattr(tree, "raw_rows", {})
    rows = [raw.get(iid, tree.item(iid)["values"]) for iid in tree.get_children()]
    return export_rows(name, headers, rows)


def display_path(path):
    """Path relative to the project folder, for messages."""
    try:
        return os.path.relpath(path, BASE_DIR)
    except ValueError:
        return path
