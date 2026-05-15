# Solo 401(k) S-Corp Optimizer (2026)

Browser-based optimizer for splitting S-Corp net profit between W-2 wages,
401(k) employee deferral, employer profit-sharing, and K-1 distribution to
minimize current-year federal tax burden. Solves an 11-variable LP via YALPS.

## Usage

Open `index.html` in any modern browser. No server required.

## Testing

Open `index.html?test=1` to run the 13 ground-truth cases. All must pass.

If your browser blocks `fetch` on `file://`, run `python3 -m http.server 8000`
and navigate to `http://localhost:8000/index.html?test=1`.

## Design

See [DESIGN.md](./DESIGN.md) — LP model, UI layout, 2026 tax constant verification.

## Regenerate ground truth

```bash
python3 scripts/gen_test_ground_truth.py
```

Requires `scipy>=1.6`.
