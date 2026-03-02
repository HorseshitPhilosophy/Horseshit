
import numpy as np
import math
from numpy.linalg import eigvals, eig, inv, norm
import matplotlib.pyplot as plt

# -------------------------
# Core linear backend (Lin)
# -------------------------

def trace_schur(A,B,C,D):
    I = np.eye(D.shape[0])
    return A + B @ inv(I - D) @ C   # Tr_X([A B; C D])

def spectral_radius(M):
    return float(np.max(np.abs(eigvals(M))))

def guarded(D, tol=1.0-1e-9):
    return spectral_radius(D) < tol

def curvature_matrix_log(H):
    w,V = eig(H)
    L = np.diag(np.log(w))
    return V @ L @ inv(V)

def curvature_norm(D):
    try:
        K = curvature_matrix_log(D)
        return float(norm(K, 'fro'))
    except Exception:
        return float('inf')

def phi_bias(D):
    """
    Toy φ-like bias:
    - prefer mildly irrational rotation angles (avoid small-denominator rationals),
    - avoid eigen-moduli that are too close to 0 (over-damped) or 1 (too rigid).
    """
    w = eigvals(D)
    ang = np.mod(np.angle(w), math.pi)
    penalty = 1.0
    for a in ang:
        if not np.isfinite(a): 
            continue
        frac = a / math.pi
        best = min(abs(frac - round(frac * q)/q) for q in range(1, 11))
        penalty *= 1.0 / (1.0 + 200.0 * best)
    mod = np.abs(w)
    band_center, band_width = 0.78, 0.25
    band_pen = np.prod(np.exp(-((mod - band_center)**2) / (2*(band_width**2) + 1e-9)))
    return float(penalty * band_pen)

def spawn_rate(B,C,D, kappa=1.0):
    margin = max(0.0, 1.0 - spectral_radius(D))
    return float(kappa * phi_bias(D) * margin)

class LinLoop:
    def __init__(self, A,B,C,D, name=None):
        self.A,self.B,self.C,self.D = A,B,C,D
        self.name = name or "loop"
    def trace(self): 
        return trace_schur(self.A,self.B,self.C,self.D)
    def viable(self): 
        return guarded(self.D)
    def K_norm(self): 
        return curvature_norm(self.D)
    def rate(self): 
        return spawn_rate(self.B,self.C,self.D)

def random_loop(dimA=1, dimX=2, scale=0.25, rng=None, name=None):
    r = np.random.default_rng() if rng is None else rng
    A = r.normal(scale=scale, size=(dimA,dimA))
    B = r.normal(scale=scale, size=(dimA,dimX))
    C = r.normal(scale=scale, size=(dimX,dimA))
    # contractive-ish D with some rotation
    Q,_ = np.linalg.qr(r.normal(size=(dimX,dimX)))
    vals = r.uniform(0.5, 0.95, size=dimX)
    phase = r.uniform(-0.6, 0.6, size=dimX)
    lam = vals * np.exp(1j*phase)
    D = Q @ np.diag(lam) @ np.linalg.inv(Q)
    return LinLoop(A,B,C,D, name=name)

# -------------------------
# Learning / emergence
# -------------------------

def gentle_update_D(D, shrink=0.98, jitter=0.02, rng=None):
    r = np.random.default_rng() if rng is None else rng
    w,V = eig(D)
    w_new = shrink*w + (jitter * r.normal(size=w.shape))
    return V @ np.diag(w_new) @ inv(V)

def learn(loop, steps=30, rng=None):
    hist = {'rate': [], 'curv': []}
    for _ in range(steps):
        if not loop.viable(): break
        hist['rate'].append(loop.rate())
        hist['curv'].append(loop.K_norm())
        loop.D = gentle_update_D(loop.D, rng=rng)
    return hist

def lift_feedback(loop: LinLoop, lift_dim=1, scale_new=0.7):
    D = loop.D
    dX = D.shape[0]
    Bp = np.concatenate([loop.B, np.zeros((loop.B.shape[0], lift_dim))], axis=1)
    Cp = np.concatenate([loop.C, np.zeros((lift_dim, loop.C.shape[1]))], axis=0)
    Dp = np.block([
        [D,                          np.zeros((dX, lift_dim))],
        [np.zeros((lift_dim, dX)),   scale_new*np.eye(lift_dim)]
    ])
    return LinLoop(loop.A, Bp, Cp, Dp, name=(loop.name + "_lift"))

# -------------------------
# Visualizations
# -------------------------

def plot_rate_vs_curvature(N=1000, dimA=1, dimX=2, seed=0):
    rng = np.random.default_rng(seed)
    rates, curvs = [], []
    for i in range(N):
        L = random_loop(dimA=dimA, dimX=dimX, rng=rng)
        if L.viable():
            rates.append(L.rate())
            curvs.append(L.K_norm())
    plt.figure(figsize=(7,5))
    plt.scatter(curvs, rates, s=10)
    plt.xlabel("curvature_norm (‖log D‖_F)")
    plt.ylabel("spawn rate (toy score)")
    plt.title(f"Viable loops: rate vs curvature (N={len(rates)}, dimX={dimX})")
    plt.grid(True, linestyle='--', linewidth=0.5)
    plt.show()

def plot_learning_curve(dimA=1, dimX=2, seed=1, steps=40):
    rng = np.random.default_rng(seed)
    L = random_loop(dimA=dimA, dimX=dimX, rng=rng, name="learn_demo")
    hist = learn(L, steps=steps, rng=rng)
    plt.figure(figsize=(7,4))
    plt.plot(hist['rate'])
    plt.xlabel("step")
    plt.ylabel("spawn rate")
    plt.title("Self-modification: spawn rate over steps")
    plt.grid(True, linestyle='--', linewidth=0.5)
    plt.show()

    plt.figure(figsize=(7,4))
    plt.plot(hist['curv'])
    plt.xlabel("step")
    plt.ylabel("curvature_norm")
    plt.title("Self-modification: curvature norm over steps")
    plt.grid(True, linestyle='--', linewidth=0.5)
    plt.show()

def plot_emergence(seed=2):
    rng = np.random.default_rng(seed)
    base = random_loop(dimA=1, dimX=2, rng=rng, name="emg_base")
    # push to marginal regime
    w,V = eig(base.D)
    base.D = V @ np.diag(0.995 * w / np.maximum(1e-6, np.abs(w))) @ inv(V)
    L2 = lift_feedback(base, lift_dim=1, scale_new=0.7)

    labels = ["base (dimX=2)", "lifted (dimX=3)"]
    rates = [base.rate(), L2.rate()]
    curvs = [base.K_norm(), L2.K_norm()]
    rhos  = [spectral_radius(base.D), spectral_radius(L2.D)]

    # bar plot: rate
    plt.figure(figsize=(6,4))
    plt.bar(labels, rates)
    plt.title("Emergence demo: spawn rate (lifted dimension)")
    plt.ylabel("spawn rate")
    plt.grid(True, axis='y', linestyle='--', linewidth=0.5)
    plt.show()

    # bar plot: curvature norm
    plt.figure(figsize=(6,4))
    plt.bar(labels, curvs)
    plt.title("Emergence demo: curvature norm")
    plt.ylabel("‖log D‖_F")
    plt.grid(True, axis='y', linestyle='--', linewidth=0.5)
    plt.show()

    # bar plot: spectral radius
    plt.figure(figsize=(6,4))
    plt.bar(labels, rhos)
    plt.title("Emergence demo: spectral radius of D")
    plt.ylabel("rho(D)")
    plt.grid(True, axis='y', linestyle='--', linewidth=0.5)
    plt.show()

# -------------------------
# Quick CLI entry
# -------------------------

def main():
    plot_rate_vs_curvature(N=1200, dimA=1, dimX=2, seed=42)
    plot_learning_curve(dimA=1, dimX=2, seed=7, steps=40)
    plot_emergence(seed=11)

if __name__ == "__main__":
    main()




# from cgr_lin_viz import (
#     plot_rate_vs_curvature, plot_learning_curve, plot_emergence
# )

# plot_rate_vs_curvature(N=2000, dimA=1, dimX=3, seed=1)
# plot_learning_curve(dimA=1, dimX=2, seed=7, steps=60)
# plot_emergence(seed=11)

#--------------------------

# from cgr_lin_viz import random_loop, learn, spectral_radius

# L = random_loop(dimA=1, dimX=4, seed=0)
# print("viable:", L.viable(), "rate:", L.rate(), "curvature:", L.K_norm(), "rho:", spectral_radius(L.D))

# hist = learn(L, steps=50)

