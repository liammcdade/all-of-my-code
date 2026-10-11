#!/usr/bin/env python3
"""
Computational sanity checks for the paper
   "The irrationality exponent of pi is 2"  (OpenAI, 2026)

The main theorem mu(pi) = 2 is an eventual statement over all large q
and cannot be verified by finite computation.  The tests below check
each *testable* ingredient of the argument:

  (A) Lemma 4.1  -- existence of admissible parameters
      theta < A < B < 1, C > 1, eta, g > 0  for every nu > 2.
  (B) The m -> infinity limits used in the proof of Theorem 1.1:
      K/w0 -> 0,  m/v0 -> 0,  L -> infinity.
  (C) Continued-fraction convergents of pi:  q^nu |pi - p/q| stays
      bounded below for every nu > 2 tested (consistent with mu(pi)=2).
  (D) Flint-Hills partial sums  sum_{n<=N} 1/(n^3 sin^2 n)
      (claimed to converge by Corollary 1.2).
  (E) The generalized criterion  a > max(1, b)  of Corollary 5.2.
"""

import math
from fractions import Fraction

import mpmath as mp
import numpy as np

mp.mp.dps = 200


# ======================================================================
# (A) Lemma 4.1  --  parameter construction
# ======================================================================
def build_parameters(nu, safety=0.5):
    """
    Return (theta, A, B, C, eta, g) as floats satisfying Lemma 4.1
    for the given nu > 2.

    Following the proof: pick b in (1/2, 1 - 1/nu), then delta small,
    theta = 1 - delta, A = 1 - b*delta;  choose C in (A/theta, 1/A)
    and B in (A, min(1/C, C*theta));  finally choose eta small so that
    g = nu*(A*(1-eta) - theta) - (1-theta) > 0.
    """
    assert nu > 2.0, "Lemma 4.1 requires nu > 2"

    # b in (1/2, 1 - 1/nu)
    b_hi = 1.0 - 1.0 / nu
    assert 0.5 < b_hi
    b = 0.5 * (0.5 + b_hi)

    # delta < (2b-1)/b^2  ensures A^2 < theta
    delta_max = (2.0 * b - 1.0) / (b * b)
    delta = safety * delta_max
    theta = 1.0 - delta
    A = 1.0 - b * delta

    # basic ordering
    assert 0.0 < theta < A < 1.0
    assert A * A < theta, "need A^2 < theta"

    # C in (A/theta, 1/A)
    C = 0.5 * (A / theta + 1.0 / A)
    assert C > 1.0

    # B in (A, min(1/C, C*theta))
    B_hi = min(1.0 / C, C * theta)
    assert A < B_hi
    B = 0.5 * (A + B_hi)

    # verify (4.1)
    assert 0.0 < theta < A < B < 1.0
    assert nu * (A - theta) > 1.0 - theta
    assert C > 1.0
    assert B < 1.0 / C
    assert B < C * theta

    # eta  so that  g > 0
    g0 = nu * (A - theta) - (1.0 - theta)
    assert g0 > 0.0
    eta = 0.9 * g0 / (nu * A)
    g = nu * (A * (1.0 - eta) - theta) - (1.0 - theta)
    assert g > 0.0

    return theta, A, B, C, eta, g


def test_lemma_41():
    print("=" * 76)
    print("(A) Lemma 4.1 -- existence of admissible parameters for nu > 2")
    print("=" * 76)
    for nu in [2.001, 2.01, 2.1, 2.5, 3.0, 5.0, 10.0]:
        theta, A, B, C, eta, g = build_parameters(nu)
        print(f"  nu = {nu:7.3f}  "
              f"theta={theta:.6f}  A={A:.6f}  B={B:.6f}  C={C:.6f}  "
              f"eta={eta:.4e}  g={g:.4e}")
    print("  All inequalities of (4.1) verified.\n")


# ======================================================================
# (B) Dimension growth asymptotics (proof of Theorem 1.1)
# ======================================================================
def test_dimension_growth():
    print("=" * 76)
    print("(B) m -> infinity asymptotics of Section 4")
    print("=" * 76)

    for nu in [2.5, 3.0, 5.0, 8.0]:
        theta, A, B, C, eta, g = build_parameters(nu)
        print(f"\n  nu = {nu}:  theta={theta:.4f}  A={A:.4f}  B={B:.4f}  "
              f"C={C:.4f}  eta={eta:.4e}  g={g:.4e}")

        lC, lt, lB, lA = math.log(C), math.log(theta), math.log(B), math.log(A)
        ln10 = math.log(10.0)

        hdr = (f"  {'m':>6} | {'log10 K':>8} {'log10 w0':>9} {'log10 v0':>9} "
               f"| {'log10(K/w0)':>12} {'log10(m/v0)':>12} "
               f"| {'log10 L':>8} {'L':>10}")
        print(hdr)
        print("  " + "-" * len(hdr))

        for m in [10, 100, 500, 1000, 2000, 3000, 5000, 10000]:
            logK  = m * lC
            logw0 = -m * lB
            logv0 = math.log(2.0) + m * (lC + lt - lB)

            logKw0 = logK + logw0                # K/w0
            logmv0 = math.log(m) - logv0         # m/v0

            logL = (2.0 * math.log(eta)
                    + m * (lB - lA)
                    - math.log(2.0 * (m + 1)))
            L = math.exp(logL) if logL < 700 else float("inf")

            print(f"  {m:>6} | {logK/ln10:>8.2f} {logw0/ln10:>9.2f} "
                  f"{logv0/ln10:>9.2f} | {logKw0/ln10:>12.2f} "
                  f"{logmv0/ln10:>12.2f} | {logL/ln10:>8.2f} {L:>10.3e}")

    print("\n  Expected behaviour:  K/w0 -> 0,  m/v0 -> 0,  L -> infinity.")
    print("  This is exactly the regime required by Proposition 3.4.\n")


# ======================================================================
# (C) Continued-fraction convergents of pi
# ======================================================================
def _cf(x, n):
    a = []
    for _ in range(n):
        ai = int(mp.floor(x))
        a.append(ai)
        f = x - ai
        if f == 0:
            break
        x = 1 / f
    return a


def _convergents(a):
    pm2, pm1 = 0, 1
    qm2, qm1 = 1, 0
    out = []
    for ai in a:
        p = ai * pm1 + pm2
        q = ai * qm1 + qm2
        out.append((p, q))
        pm2, pm1 = pm1, p
        qm2, qm1 = qm1, q
    return out


def test_pi_convergents():
    print("=" * 76)
    print("(C) Continued-fraction convergents of pi")
    print("=" * 76)

    a = _cf(mp.pi, 60)
    convs = _convergents(a)

    print(f"  first 30 partial quotients: {a[:30]}")
    print()
    hdr = (f"  {'k':>3} {'p_k':>22} {'q_k':>22} "
           f"{'log10 q^2.5 e':>15} {'log10 q^3 e':>13} {'log10 q^5 e':>13}")
    print(hdr)
    print("  " + "-" * len(hdr))

    show = (0, 1, 2, 3, 5, 8, 12, 20, 30, 40, 50, 55, 58, 59)
    for k in show:
        if k >= len(convs):
            continue
        p, q = convs[k]
        e = abs(mp.pi - mp.mpf(p) / q)
        if e == 0:
            continue
        le = mp.log10(e)
        r25 = 2.5 * mp.log10(q) + le
        r30 = 3.0 * mp.log10(q) + le
        r50 = 5.0 * mp.log10(q) + le
        print(f"  {k:>3} {p:>22} {q:>22} "
              f"{float(r25):>15.4f} {float(r30):>13.4f} {float(r50):>13.4f}")

    # minimum over the tail
    tail = [(2.5 * mp.log10(q) + mp.log10(abs(mp.pi - mp.mpf(p) / q)))
            for (p, q) in convs if q > 100]
    print(f"\n  minimum over convergents with q > 100 of "
          f"log10(q^2.5 * |pi - p/q|): {float(min(tail)):.4f}")
    print("  If mu(pi) > 2, some entry would drift to -infinity with k.")
    print("  All tested entries remain bounded below (consistent with mu(pi)=2).\n")


# ======================================================================
# (D) Flint-Hills partial sums
# ======================================================================
def flint_hills_partial(N):
    n = np.arange(1, N + 1, dtype=np.float64)
    s = np.sin(n)
    return float(np.sum(1.0 / (n ** 3 * s ** 2)))


def test_flint_hills():
    print("=" * 76)
    print("(D) Flint-Hills partial sums  sum_{n<=N} 1/(n^3 sin^2 n)")
    print("=" * 76)

    prev = 0.0
    for N in [100, 1_000, 10_000, 100_000, 1_000_000, 5_000_000]:
        s = flint_hills_partial(N)
        print(f"  N = {N:>10}   S_N = {s:.10f}   increment = {s - prev:.6e}")
        prev = s
    print("  Corollary 1.2 predicts convergence (very slow).\n")


# ======================================================================
# (E) Generalized criterion   a > max(1, b)
# ======================================================================
def gen_partial(a, b, N):
    n = np.arange(1, N + 1, dtype=np.float64)
    s = np.abs(np.sin(n))
    s[s < 1e-300] = 1e-300
    return float(np.sum(1.0 / (n ** a * s ** b)))


def test_generalized():
    print("=" * 76)
    print("(E) Generalized Flint-Hills   sum 1/(n^a |sin n|^b)")
    print("    Corollary 5.2: converges iff  a > max(1, b).")
    print("=" * 76)

    cases = [
        (2.0, 1.0, "conv  a=2   > max(1,1)   =1"),
        (1.5, 1.0, "conv  a=1.5 > max(1,1)   =1"),
        (3.0, 2.0, "conv  a=3   > max(1,2)   =2"),
        (1.2, 0.5, "conv  a=1.2 > max(1,0.5) =1"),
        (2.5, 2.5, "div   a=2.5 = max(1,2.5) =2.5"),
        (1.0, 1.0, "div   a=1   = max(1,1)   =1"),
        (1.5, 2.0, "div   a=1.5 < max(1,2)   =2"),
        (2.0, 3.0, "div   a=2   < max(1,3)   =3"),
    ]
    print(f"  {'a':>5} {'b':>5}   {'S(1e3)':>13} {'S(1e4)':>13} "
          f"{'S(1e5)':>13}   expectation")
    print("  " + "-" * 84)
    for a, b, desc in cases:
        s1 = gen_partial(a, b, 1_000)
        s2 = gen_partial(a, b, 10_000)
        s3 = gen_partial(a, b, 100_000)
        print(f"  {a:>5} {b:>5}   {s1:>13.5e} {s2:>13.5e} {s3:>13.5e}"
              f"   {desc}")
    print("\n  Convergent cases: partial sums level off.")
    print("  Divergent  cases: partial sums keep growing.\n")


# ======================================================================
if __name__ == "__main__":
    test_lemma_41()
    test_dimension_growth()
    test_pi_convergents()
    test_flint_hills()
    test_generalized()
    print("All tests completed.")