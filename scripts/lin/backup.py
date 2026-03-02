import numpy as np

def trace_schur(A,B,C,D):
    # Tr_X([A B; C D]) = A + B (I-D)^{-1} C
    I = np.eye(D.shape[0])
    return A + B @ np.linalg.inv(I - D) @ C

def guarded(D, tol=1.0-1e-6):
    # spectral radius < 1
    rho = max(abs(np.linalg.eigvals(D)))
    return rho < tol

def holonomy(loop_blocks):
    H = np.eye(loop_blocks[0].shape[0])
    for M in loop_blocks:
        H = M @ H
    return H

def curvature(H):
    # logm approximation near I
    eigvals, V = np.linalg.eig(H)
    if np.allclose(H, np.eye(H.shape[0]), atol=1e-6):
        return np.zeros_like(H)
    L = np.diag(np.log(eigvals))
    return V @ L @ np.linalg.inv(V)
