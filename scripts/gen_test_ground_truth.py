#!/usr/bin/env python3
"""
Generate ground truth solutions for the Solo 401(k) S-Corp Optimizer LP test cases.

Mirrors the LP in DESIGN.md §2 (v2 + TI_pre fix) and solves each test case
listed in §9 via scipy.optimize.linprog (HiGHS backend).

Output: tests/ground_truth.json  (consumed by index.html?test=1)

Run:
    python3 scripts/gen_test_ground_truth.py

If scipy is not installed:
    pip install scipy>=1.6
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from scipy.optimize import linprog

YEAR = 2026

ED_MAX = 24_500            # §402(g)(1)
SEC415_CAP = 72_000        # §415(c)(1)(A)
COMP_CAP_401A17 = 360_000  # §401(a)(17), not binding in stated X range
PS_RATE = 0.25             # S-Corp owner-employee employer PS rate
FICA_RATE = 0.0765
SE_TAX_RATE = 0.153
SE_INCOME_FACTOR = 0.9235
SS_WAGE_BASE = 184_500     # OASDI taxable max; informational only (DESIGN §7)
QBI_RATE = 0.20            # §199A(a)(1)

STD_DED: dict[str, int] = {
    "MFJ": 32_200,
    "QW": 32_200,
    "HoH": 24_150,
    "Single": 16_100,
}

BRACKET_TOPS: dict[str, list[int]] = {
    "MFJ":    [24_800, 100_800, 211_400, 403_550],
    "Single": [12_400,  50_400, 105_700, 201_775],
    "HoH":    [17_700,  67_450, 108_950, 201_775],
}
BRACKET_TOPS["QW"] = BRACKET_TOPS["MFJ"]

BRACKET_RATES = [0.10, 0.12, 0.22, 0.24]


def bracket_widths(filing_status: str) -> list[int]:
    tops = BRACKET_TOPS[filing_status]
    widths = [tops[0]]
    for i in range(1, len(tops)):
        widths.append(tops[i] - tops[i - 1])
    return widths


W_IDX, ED_IDX, PS_IDX, K1_IDX, QBI_IDX, TI_IDX = 0, 1, 2, 3, 4, 5
T1_IDX, T2_IDX, T3_IDX, T4_IDX = 6, 7, 8, 9
TI_PRE_IDX = 10
N_VARS = 11

VAR_NAMES = ["W", "ED", "PS", "K1", "QBI", "TI", "t1", "t2", "t3", "t4", "TI_pre"]


@dataclass
class LPInputs:
    X: float = 100_000
    other_passive: float = 0
    sched_c: float = 0
    filing_status: str = "MFJ"
    w_min: float = 30_000
    clean_paycheck: bool = True


@dataclass
class LPResult:
    status: str
    message: str = ""
    vars: dict[str, float] = field(default_factory=dict)
    derived: dict[str, float] = field(default_factory=dict)


def solve_lp(inp: LPInputs) -> LPResult:
    se_base = SE_INCOME_FACTOR * inp.sched_c
    se_tax = SE_TAX_RATE * se_base
    se_ded = 0.5 * se_tax
    std_ded = STD_DED[inp.filing_status]
    widths = bracket_widths(inp.filing_status)

    # Objective: min 0.10·t1 + 0.12·t2 + 0.22·t3 + 0.24·t4 + 2·0.0765·W
    # SE_tax is parameter-derived constant; omitted from LP, added to displayed total.
    c = np.zeros(N_VARS)
    c[W_IDX] = 2 * FICA_RATE
    for i, rate in enumerate(BRACKET_RATES):
        c[T1_IDX + i] = rate

    # Equality: budget (1.0765·W + PS + K1 = X) and bracket sum (Σt_i - TI = 0)
    A_eq = np.zeros((2, N_VARS))
    b_eq = np.zeros(2)
    A_eq[0, W_IDX] = 1 + FICA_RATE
    A_eq[0, PS_IDX] = 1
    A_eq[0, K1_IDX] = 1
    b_eq[0] = inp.X
    A_eq[1, T1_IDX:T4_IDX + 1] = 1
    A_eq[1, TI_IDX] = -1

    A_ub_rows: list[list[float]] = []
    b_ub_list: list[float] = []

    def add(coeffs: dict[int, float], rhs: float) -> None:
        row = [0.0] * N_VARS
        for idx, val in coeffs.items():
            row[idx] = val
        A_ub_rows.append(row)
        b_ub_list.append(rhs)

    add({ED_IDX: 1}, ED_MAX)                                            # §402(g)(1) dollar
    add({ED_IDX: 1, W_IDX: -1}, 0)                                      # §402(g) 100%-of-comp: ED ≤ W
    if inp.clean_paycheck:
        add({ED_IDX: 1, W_IDX: -SE_INCOME_FACTOR}, 0)                   # clean-paycheck: ED ≤ 0.9235·W
    add({PS_IDX: 1, W_IDX: -PS_RATE}, 0)                                # §404(a): PS ≤ 0.25·W
    add({ED_IDX: 1, PS_IDX: 1}, SEC415_CAP)                             # §415(c)(1)(A) dollar
    add({ED_IDX: 1, PS_IDX: 1, W_IDX: -1}, 0)                           # §415(c)(1)(B) 100%-of-comp: ED+PS ≤ W
    # QBI ≤ 0.20·(K1 + SchedC - SE_ded)  →  QBI - 0.20·K1 ≤ 0.20·(SchedC - SE_ded)
    add({QBI_IDX: 1, K1_IDX: -QBI_RATE}, QBI_RATE * (inp.sched_c - se_ded))
    # QBI ≤ 0.20·TI_pre  →  QBI - 0.20·TI_pre ≤ 0
    add({QBI_IDX: 1, TI_PRE_IDX: -QBI_RATE}, 0)
    # TI_pre ≥ AGI - StdDed, where AGI = (W-ED) + K1 + other_passive + SchedC - SE_ded
    # →  W - ED + K1 - TI_pre  ≤  StdDed + SE_ded - other_passive - SchedC
    add(
        {W_IDX: 1, ED_IDX: -1, K1_IDX: 1, TI_PRE_IDX: -1},
        std_ded + se_ded - inp.other_passive - inp.sched_c,
    )
    # TI ≥ TI_pre - QBI  →  TI_pre - QBI - TI ≤ 0
    add({TI_PRE_IDX: 1, QBI_IDX: -1, TI_IDX: -1}, 0)
    for i in range(4):
        add({T1_IDX + i: 1}, widths[i])
    add({W_IDX: -1}, -inp.w_min)

    A_ub = np.array(A_ub_rows)
    b_ub = np.array(b_ub_list)
    bounds = [(0, None)] * N_VARS

    result = linprog(
        c,
        A_ub=A_ub,
        b_ub=b_ub,
        A_eq=A_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not result.success:
        msg = (result.message or "").lower()
        if "infeasible" in msg or result.status == 2:
            return LPResult(status="infeasible", message=result.message)
        if result.status == 3:
            return LPResult(status="unbounded", message=result.message)
        return LPResult(status="error", message=result.message)

    x = result.x
    W, ED, PS, K1, QBI, TI = x[:6]
    t1, t2, t3, t4 = x[6:10]
    TI_pre = x[10]

    box1 = W - ED
    er_fica = FICA_RATE * W
    ee_fica = FICA_RATE * W
    agi = box1 + K1 + inp.other_passive + inp.sched_c - se_ded
    fed_tax = sum(t * r for t, r in zip([t1, t2, t3, t4], BRACKET_RATES))
    total_tax = fed_tax + 2 * FICA_RATE * W + se_tax

    def r(v: float, ndigits: int = 2) -> float:
        rounded = round(float(v), ndigits)
        return rounded + 0.0  # collapse IEEE-754 -0.0 to 0.0 for clean output

    return LPResult(
        status="optimal",
        vars={
            "W": r(W), "ED": r(ED), "PS": r(PS), "K1": r(K1),
            "QBI": r(QBI), "TI": r(TI),
            "t1": r(t1), "t2": r(t2), "t3": r(t3), "t4": r(t4),
            "TI_pre": r(TI_pre),
        },
        derived={
            "box1": r(box1),
            "agi": r(agi),
            "std_ded": std_ded,
            "se_base": r(se_base),
            "se_tax": r(se_tax),
            "se_ded": r(se_ded),
            "fed_tax": r(fed_tax),
            "ee_fica": r(ee_fica),
            "er_fica": r(er_fica),
            "total_tax": r(total_tax),
            "etr_vs_gross": r(total_tax / max(inp.X + inp.other_passive + inp.sched_c, 1), 4),
            "etr_vs_ti": r(total_tax / max(TI, 1), 4),
            "retirement_total": r(ED + PS),
        },
    )


TEST_CASES: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "X=0 boundary",
        "inputs": {"X": 0, "filing_status": "MFJ", "w_min": 0},
        "expected_behavior": "All decision vars = 0, total tax = 0",
    },
    {
        "id": 2,
        "name": "X=50k MFJ W_min=0",
        "inputs": {"X": 50_000, "filing_status": "MFJ", "w_min": 0},
        "expected_behavior": "Standard optimum (free choice of W)",
    },
    {
        "id": 3,
        "name": "X=100k MFJ W_min=30k (default)",
        "inputs": {"X": 100_000, "filing_status": "MFJ", "w_min": 30_000},
        "expected_behavior": "Reasonable comp binds at W=30k or W>30k optimal",
    },
    {
        "id": 4,
        "name": "X=200k MFJ W_min=0 (§415 saturates)",
        "inputs": {"X": 200_000, "filing_status": "MFJ", "w_min": 0},
        "expected_behavior": "§415(c) dollar cap saturates: ED + PS approaches 72k",
    },
    {
        "id": 5,
        "name": "X=100k W_min=50k binding",
        "inputs": {"X": 100_000, "filing_status": "MFJ", "w_min": 50_000},
        "expected_behavior": "W = 50000 (W_min binding)",
    },
    {
        "id": 6,
        "name": "OtherIncome_passive=50k X=50k",
        "inputs": {"X": 50_000, "other_passive": 50_000, "filing_status": "MFJ", "w_min": 0},
        "expected_behavior": "Joint AGI pushes brackets up",
    },
    {
        "id": 7,
        "name": "§415(c) dollar binding (X=200k, W_min forces big W)",
        "inputs": {"X": 200_000, "filing_status": "MFJ", "w_min": 100_000},
        "expected_behavior": "ED + PS = $72k (dollar cap saturates with high W)",
    },
    {
        "id": 8,
        "name": "§415(c) comp binding (low W)",
        "inputs": {"X": 30_000, "filing_status": "MFJ", "w_min": 15_000},
        "expected_behavior": "ED + PS ≤ W binds (low W → comp cap tighter than dollar cap)",
    },
    {
        "id": 9,
        "name": "Clean-paycheck off, X=50k W_min=25k",
        "inputs": {"X": 50_000, "filing_status": "MFJ", "w_min": 25_000, "clean_paycheck": False},
        "expected_behavior": "ED may reach W (Box 1 → 0)",
    },
    {
        "id": 10,
        "name": "QBI TI cap binding (X=150k, W_min=0)",
        "inputs": {"X": 150_000, "filing_status": "MFJ", "w_min": 0},
        "expected_behavior": "QBI capped by 0.20*TI_pre, not by 0.20*K1",
    },
    {
        "id": 11,
        "name": "SchedC=30k, X=0 (no S-Corp)",
        "inputs": {"X": 0, "sched_c": 30_000, "filing_status": "MFJ", "w_min": 0},
        "expected_behavior": "SE tax fires; AGI < StdDed → TI_pre=0, QBI=0",
    },
    {
        "id": 12,
        "name": "Infeasible: W_min=80k X=30k",
        "inputs": {"X": 30_000, "filing_status": "MFJ", "w_min": 80_000},
        "expected_behavior": "INFEASIBLE (W_min > X/1.0765)",
    },
    {
        "id": 13,
        "name": "FilingStatus=Single, X=100k",
        "inputs": {"X": 100_000, "filing_status": "Single", "w_min": 30_000},
        "expected_behavior": "Narrower brackets + smaller std ded → higher tax than MFJ case 3",
    },
]


def main() -> None:
    output: dict[str, Any] = {
        "year": YEAR,
        "generated_at": "2026-05-14",
        "lp_version": "v2.1 (post-audit, with TI_pre fix)",
        "constants_verified": True,
        "cases": [],
    }

    print(f"Solo 401(k) Optimizer — Ground Truth Generation ({YEAR})")
    print("=" * 100)
    print(f"{'#':>3} {'Scenario':<55} {'Status':<12} {'W':>9} {'ED':>8} {'PS':>8} {'K1':>10} {'Tax':>10}")
    print("-" * 100)

    for tc in TEST_CASES:
        inp = LPInputs(**tc["inputs"])
        result = solve_lp(inp)

        case_record = {
            **tc,
            "result": {
                "status": result.status,
                "message": result.message,
                "vars": result.vars,
                "derived": result.derived,
            },
        }
        output["cases"].append(case_record)

        if result.status == "optimal":
            v = result.vars
            d = result.derived
            print(
                f"{tc['id']:>3} {tc['name'][:55]:<55} {'optimal':<12} "
                f"{v['W']:>9,.0f} {v['ED']:>8,.0f} {v['PS']:>8,.0f} "
                f"{v['K1']:>10,.0f} {d['total_tax']:>10,.0f}"
            )
        else:
            print(
                f"{tc['id']:>3} {tc['name'][:55]:<55} {result.status.upper():<12} "
                f"({result.message[:30]})"
            )

    out_dir = os.path.join(os.path.dirname(__file__), "..", "tests")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "ground_truth.json")
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print("-" * 100)
    print(f"\n✅ Wrote {len(TEST_CASES)} test cases to {os.path.relpath(out_path)}")


if __name__ == "__main__":
    main()
