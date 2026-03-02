from cgr_lin import random_loop

loop = random_loop(dimA=1, dimX=2)
if loop.viable():
    T = loop.trace()
    r = loop.rate()
    K = loop.K()
    # Log the trio (viable?, spawn rate, curvature norm)
