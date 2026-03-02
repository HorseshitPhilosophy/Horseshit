def R0(s):  # Distinguish
    return "[·]" if s == "·" else s

def R1(s):  # Quote / Re-enter
    return f"{s}:⟦{s}⟧"

def R2(s):  # Normalize nested quotes
    while "⟦⟦" in s and "⟧⟧" in s:
        s = s.replace("⟦⟦","⟦").replace("⟧⟧","⟧")
    return s

addr_counter = 0
def fresh_addr():
    global addr_counter
    a = f"a{addr_counter}"
    addr_counter += 1
    return a

def R3_R4(s):  # Polarize + Address on a trace x:⟦x⟧
    if ":⟦" not in s or not s.endswith("⟧"):
        return s
    x = s.split(":⟦")[0]
    xq = "⟦" + x + "⟧"
    # syntactic compare:
    bit = "0" if x == xq else "1"
    a = fresh_addr()
    return f"{bit},({x}⊣{xq})@{a}"

# Demo: first distinction
s = "·"
print("0:", s)
s = R0(s)       # Distinguish
print("1:", s)
s = R1(s)       # Re-enter
print("2:", s)
s = R2(s)       # Normalize
print("3:", s)
s = R3_R4(s)    # Polarize + Address
print("4:", s)
