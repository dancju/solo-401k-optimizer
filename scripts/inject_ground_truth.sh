#!/bin/bash
# Re-inject tests/ground_truth.json into index.html, replacing the previous embedded copy.
# Idempotent: run after regenerating ground_truth.json via gen_test_ground_truth.py.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 - <<'PY'
import json, re
gt = json.load(open("tests/ground_truth.json"))
html = open("index.html").read()
replacement = "const GROUND_TRUTH = " + json.dumps(gt) + ";\n"
new, n = re.subn(
    r"const GROUND_TRUTH = .*?;\n",
    lambda _m: replacement,
    html,
    count=1,
    flags=re.DOTALL,
)
assert n == 1, "GROUND_TRUTH marker not found in index.html (0 substitutions)"
open("index.html", "w").write(new)
print(f"injected {len(json.dumps(gt))} bytes of ground truth into index.html")
PY
