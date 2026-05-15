#!/bin/bash
# Build a self-contained dist/index.html with vendor scripts inlined.
# Used for single-file deployment per DESIGN.md §4.1.
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p dist

python3 - <<'PY'
import re, pathlib

html = pathlib.Path("index.html").read_text()
yalps = pathlib.Path("vendor/yalps.min.js").read_text()
d3 = pathlib.Path("vendor/d3-sankey-bundle.min.js").read_text()

html = html.replace(
    '<script src="vendor/d3-sankey-bundle.min.js"></script>',
    f"<script>\n{d3}\n</script>",
)
html = html.replace(
    '<script src="vendor/yalps.min.js"></script>',
    f"<script>\n{yalps}\n</script>",
)
pathlib.Path("dist/index.html").write_text(html)
print(f"wrote dist/index.html ({len(html)} bytes)")
PY
