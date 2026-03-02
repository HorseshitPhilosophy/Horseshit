# Re-run the CGR-0 simulator cell (see previous message for description).

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import re
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

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

class AddrGen:
    def __init__(self):
        self.n = 0
    def fresh(self) -> str:
        a = f"a{self.n}"
        self.n += 1
        return a

addr_gen = AddrGen()

def R3_R4_on_trace(trace: str) -> str:
    if ":⟦" not in trace or not trace.endswith("⟧"):
        return trace
    idx = trace.rfind(":⟦")
    x = trace[:idx]
    xq = "⟦" + trace[:idx] + "⟧"
    bit = "0" if x == xq else "1"
    a = addr_gen.fresh()
    return f"{bit},({x}⊣{xq})@{a}"

@dataclass
class Unit:
    addr: str
    form: str
    parent: Optional[str]
    step: int

class Ledger:
    def __init__(self):
        self.units: Dict[str, Unit] = {}
        self.edges: List[Tuple[str,str]] = []
        self.history: List[str] = []
    def add(self, u: Unit):
        self.units[u.addr] = u
        self.history.append(u.form)
        if u.parent is not None:
            self.edges.append((u.parent, u.addr))

def first_distinction(debug_print=True):
    led = Ledger()
    s = "·"
    if debug_print: print("0:", s)
    s = R0(s)
    if debug_print: print("1:", s)
    s = R1(s)
    if debug_print: print("2:", s)
    s = R2(s)
    if debug_print: print("3:", s)
    s = R3_R4_on_trace(s)
    if debug_print: print("4:", s)
    m = re.search(r"@([a-zA-Z0-9_]+)$", s)
    addr = m.group(1) if m else "a?"
    led.add(Unit(addr=addr, form=s, parent=None, step=1))
    return led, addr

def reenter_unit_form(unit_form: str) -> str:
    trace = R1(unit_form)
    trace = R2(trace)
    return R3_R4_on_trace(trace)

def run_sim(N=8, debug_print=True) -> Ledger:
    led, last_addr = first_distinction(debug_print=debug_print)
    last_form = led.units[last_addr].form
    for step in range(2, N+1):
        new_form = reenter_unit_form(last_form)
        if debug_print:
            print(f"{step+2}:", new_form)
        m = re.search(r"@([a-zA-Z0-9_]+)$", new_form)
        addr = m.group(1) if m else f"a?{step}"
        led.add(Unit(addr=addr, form=new_form, parent=last_addr, step=step))
        last_addr, last_form = addr, new_form
    return led

def ledger_dataframe(led: Ledger) -> pd.DataFrame:
    rows = []
    for a,u in led.units.items():
        rows.append({
            "addr": a,
            "step": u.step,
            "parent": u.parent,
            "form_len": len(u.form),
            "form": u.form
        })
    df = pd.DataFrame(rows).sort_values("step").reset_index(drop=True)
    return df

def plot_length_growth(df: pd.DataFrame):
    plt.figure(figsize=(7,4))
    plt.plot(df["step"].values, df["form_len"].values, marker="o")
    plt.xlabel("address index (step)")
    plt.ylabel("string length of addressed unit")
    plt.title("CGR-0 field growth: length vs. step")
    plt.grid(True, linestyle="--", linewidth=0.5)
    plt.show()

# Run a demo
led = run_sim(N=10, debug_print=True)
df = ledger_dataframe(led)

from caas_jupyter_tools import display_dataframe_to_user
display_dataframe_to_user("CGR-0 Ledger (first 10 distinctions)", df)

plot_length_growth(df)
