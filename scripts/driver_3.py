# Re-running the full CGR-1 pipeline.
# (See inline comments in the previous cell for an overview.)

from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List
import re
import math
import matplotlib.pyplot as plt
import pandas as pd
from collections import Counter, defaultdict

def R0(s: str) -> str:
    return "[·]" if s == "·" else s

def R1(s: str) -> str:
    return f"{s}:⟦{s}⟧"

def R2(s: str) -> str:
    prev = None
    cur = s
    while prev != cur:
        prev = cur
        cur = cur.replace("⟦⟦","⟦").replace("⟧⟧","⟧")
    return cur

def R3_R4_on_trace(trace: str, addr_str: str) -> str:
    if ":⟦" not in trace or not trace.endswith("⟧"):
        if "@a[" not in trace:
            return f"{trace}@{addr_str}"
        return trace
    idx = trace.rfind(":⟦")
    x = trace[:idx]
    xq = "⟦" + trace[:idx] + "⟧"
    bit = "0" if x == xq else "1"
    return f"{bit},({x}⊣{xq})@{addr_str}"

def T_op(U: str, i: int, j: int) -> str:
    trace = R1(U)
    trace = R2(trace)
    return R3_R4_on_trace(trace, addr_str=f"a[{i},{j}]")

def X_op(U: str, B: str, i: int, j: int) -> str:
    content = f"1,({U}⊣⟦{B}⟧)@a[{i},{j}]"
    return R2(content)

def alpha_normalize(s: str) -> str:
    s2 = R2(s)
    s2 = re.sub(r"@a\[[^\]]*\]", "", s2)
    s2 = re.sub(r"@b[0-9]+", "", s2)
    s2 = re.sub(r"\s+", "", s2)
    return s2

def seed_T_chain(steps: int) -> List[str]:
    forms = []
    U = "·"
    U = R0(U)
    U = R1(U)
    U = R2(U)
    U = R3_R4_on_trace(U, addr_str="a[0,0]")
    forms.append(U)
    for k in range(1, steps):
        U = T_op(U, i=k, j=0)
        forms.append(U)
    return forms

def candidate_motifs(window: List[str], min_len=6, max_len=14) -> Counter:
    cnt = Counter()
    banned = {",","(",")","[","]","⟦","⟧","⊣","1","0",":","@"}
    for s in window:
        s0 = re.sub(r"@a\[[^\]]*\]","", s)
        n = len(s0)
        for L in range(min_len, min(max_len, n)+1):
            for i in range(0, n-L+1):
                sub = s0[i:i+L]
                if any(ch in banned for ch in sub):
                    if all(ch in banned for ch in sub):
                        continue
                cnt[sub] += 1
    return cnt

def extract_promote_basis(forms: List[str], window_size=8, min_len=8, max_len=20, min_count=3) -> Optional[str]:
    window = forms[-window_size:] if window_size <= len(forms) else forms
    cnt = candidate_motifs(window, min_len=min_len, max_len=max_len)
    if not cnt:
        return None
    for motif, c in cnt.most_common():
        if c < min_count:
            break
        appear = sum(1 for s in window if motif in s)
        if appear >= 2:
            return motif
    return None

def build_grid(forms_seed: List[str], B: str, I: int, J: int) -> Dict[Tuple[int,int], str]:
    grid: Dict[Tuple[int,int], str] = {}
    grid[(0,0)] = forms_seed[0]
    for i in range(1, I):
        if i < len(forms_seed):
            grid[(i,0)] = forms_seed[i]
        else:
            grid[(i,0)] = T_op(grid[(i-1,0)], i=i, j=0)
    for j in range(1, J):
        grid[(0,j)] = X_op(grid[(0,j-1)], B=B, i=0, j=j)
    for i in range(1, I):
        for j in range(1, J):
            south = grid[(i-1,j)]
            via_T = T_op(south, i=i, j=j)
            east = X_op(via_T, B=B, i=i, j=j)
            grid[(i,j)] = east
    return grid

def plaquette_closure(grid: Dict[Tuple[int,int], str], B: str, I: int, J: int) -> pd.DataFrame:
    rows = []
    for i in range(I-1):
        for j in range(J-1):
            U = grid[(i,j)]
            path1 = T_op(X_op(U, B=B, i=i, j=j+1), i=i+1, j=j+1)  # T∘X
            path2 = X_op(T_op(U, i=i+1, j=j), B=B, i=i+1, j=j+1)  # X∘T
            closed = (alpha_normalize(path1) == alpha_normalize(path2))
            rows.append({
                "i": i, "j": j,
                "alpha_equal": closed,
                "len_path1": len(path1),
                "len_path2": len(path2),
            })
    return pd.DataFrame(rows)

SEED_STEPS = 10
GRID_I, GRID_J = 8, 8

seed_forms = seed_T_chain(SEED_STEPS)
B = extract_promote_basis(seed_forms, window_size=8, min_len=8, max_len=22, min_count=3)
if B is None:
    B = seed_forms[0]

basis_info_df = pd.DataFrame([{
    "basis_B": B,
    "seed_steps": SEED_STEPS,
    "grid_I": GRID_I,
    "grid_J": GRID_J
}])

grid = build_grid(seed_forms, B=B, I=GRID_I, J=GRID_J)
plaq_df = plaquette_closure(grid, B=B, I=GRID_I, J=GRID_J)

open_cells = {(r.i, r.j) for r in plaq_df.itertuples() if not r.alpha_equal}

plt.figure(figsize=(6,6))
ii = [i for (i,j) in grid.keys()]
jj = [j for (i,j) in grid.keys()]
plt.scatter(jj, ii, marker="o", label="nodes")
if open_cells:
    cj = [j+0.5 for (i,j) in open_cells]
    ci = [i+0.5 for (i,j) in open_cells]
    plt.scatter(cj, ci, marker="x", label="open plaquette(s)")
plt.gca().invert_yaxis()
plt.xlabel("j (X_B steps)")
plt.ylabel("i (T steps)")
plt.title("CGR-1 Grid and Plaquette Diagnostics")
plt.grid(True, linestyle="--", linewidth=0.5)
plt.legend()
plt.show()

from caas_jupyter_tools import display_dataframe_to_user
display_dataframe_to_user("CGR-1: Promoted basis (and settings)", basis_info_df)
display_dataframe_to_user("CGR-1: Plaquette closure (T∘X vs X∘T)", plaq_df)
