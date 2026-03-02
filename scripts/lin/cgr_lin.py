import numpy as np

def trace_schur(A,B,C,D):
    I = np.eye(D.shape[0])
    return A + B @ np.linalg.inv(I - D) @ C   # Tr_X([A B; C D])

def spectral_radius(M):
    return max(abs(np.linalg.eigvals(M)))

def guarded(D, tol=1.0-1e-6):
    return spectral_radius(D) < tol

def holonomy(blocks):
    H = np.eye(blocks[0].shape[0])
    for M in blocks: H = M @ H
    return H

def curvature(H):
    # log near identity (use scipy.linalg.logm later)
    w,V = np.linalg.eig(H)
    L = np.diag(np.log(w))
    return V @ L @ np.linalg.inv(V)

def phi_bias(D):
    # toy φ-bias: reward mildly-irrational planar rotations, penalize damping & near-rational locking
    w = np.linalg.eigvals(D)
    # angle penalty (wrap to [0,π])
    ang = np.angle(w)
    irr_pen = np.prod(1.0 / (1.0 + (np.round(ang/np.pi*10)-ang/np.pi*10)**2 + 1e-6))
    # damping penalty
    damp = np.prod(1.0 - np.minimum(0.99, np.abs(w)))
    return irr_pen * (0.1 + damp)

def spawn_rate(B,C,D, κ=1.0):
    margin = max(0.0, 1.0 - spectral_radius(D))
    return κ * phi_bias(D) * margin

class LinLoop:
    def __init__(self, A,B,C,D):  # blocks
        self.A,self.B,self.C,self.D = A,B,C,D
    def trace(self): return trace_schur(self.A,self.B,self.C,self.D)
    def viable(self): return guarded(self.D)
    def K(self): return curvature(self.D)   # curvature proxy on loop block
    def rate(self): return spawn_rate(self.B,self.C,self.D)

def random_loop(dimA=1, dimX=2, scale=0.2, rng=None):
    r = np.random.default_rng() if rng is None else rng
    A = r.normal(scale=scale, size=(dimA,dimA))
    B = r.normal(scale=scale, size=(dimA,dimX))
    C = r.normal(scale=scale, size=(dimX,dimA))
    # keep D contractive-ish
    U,_ = np.linalg.qr(r.normal(size=(dimX,dimX)))
    vals = np.diag(r.uniform(-0.6, 0.6, size=dimX))
    D = U @ vals @ np.linalg.inv(U)
    return LinLoop(A,B,C,D)
