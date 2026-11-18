#!/usr/bin/env python3
"""Droplet motion system: Apple-style springs turned into Qt easing curves.

Apple describes its animations as springs (SwiftUI: response = period of the undamped spring,
dampingFraction = zeta). Qt Quick animations take a duration + an easing curve, so each spring
is simulated, cut where it has settled, and fitted with a piecewise cubic Bezier
(QEasingCurve::BezierSpline, overshoot allowed). The fit is exact in time (control points at
1/3 and 2/3 of each segment, Hermite tangents), so the curve *is* the spring.

    motion.py            -> prints the QML tokens (pasted into desktop/shell/qml/Theme.qml)
    motion.py --check    -> max error of each fit against the simulated spring
"""
import math
import sys

# name: (response s, damping fraction, settle tolerance, role)
SPRINGS = {
    "doux":   (0.42, 1.00, 0.004, "panneaux, tailles, mises en page (aucun dépassement)"),
    "vif":    (0.28, 0.86, 0.004, "pression, interrupteurs, survol, sélection"),
    "rebond": (0.48, 0.72, 0.004, "apparition de popovers, Dock, notifications (léger dépassement)"),
}
SEGMENTS = 10


def spring(response, zeta):
    w0 = 2 * math.pi / response
    if zeta >= 1:
        def x(t): return 1 - math.exp(-w0 * t) * (1 + w0 * t)
        def v(t): return w0 * w0 * t * math.exp(-w0 * t)
    else:
        wd = w0 * math.sqrt(1 - zeta * zeta)
        a = zeta * w0
        def x(t): return 1 - math.exp(-a * t) * (math.cos(wd * t) + a / wd * math.sin(wd * t))
        def v(t): return math.exp(-a * t) * (w0 * w0 / wd) * math.sin(wd * t)
    return x, v


def settle(x, tol):
    t, last_out = 0.0, 0.0
    while t < 5:
        if abs(1 - x(t)) > tol:
            last_out = t
        t += 0.001
    return last_out + 0.001


def fit(response, zeta, tol):
    x, v = spring(response, zeta)
    D = settle(x, tol)
    # segment boundaries denser at the start, where the curve bends most
    us = [((i / SEGMENTS) ** 1.6) for i in range(SEGMENTS + 1)]
    pts = []
    for u0, u1 in zip(us, us[1:]):
        t0, t1 = u0 * D, u1 * D
        y0, y1 = x(t0), (x(t1) if u1 < 1 else 1.0)
        d0, d1 = v(t0) * D, (v(t1) * D if u1 < 1 else 0.0)   # dy/du
        du = u1 - u0
        pts += [u0 + du / 3, y0 + d0 * du / 3, u1 - du / 3, y1 - d1 * du / 3, u1, y1]
    return D, pts


def bezier_eval(pts, u):
    # pts as Qt's list; find the segment then solve x(s) = u (x is linear in s here)
    p0 = (0.0, 0.0)
    for i in range(0, len(pts), 6):
        c1, c2, e = pts[i:i + 2], pts[i + 2:i + 4], pts[i + 4:i + 6]
        if u <= e[0] + 1e-12:
            s = (u - p0[0]) / (e[0] - p0[0])
            m = 1 - s
            return m ** 3 * p0[1] + 3 * m * m * s * c1[1] + 3 * m * s * s * c2[1] + s ** 3 * e[1]
        p0 = (e[0], e[1])
    return 1.0


def main():
    check = "--check" in sys.argv
    for name, (resp, zeta, tol, role) in SPRINGS.items():
        D, pts = fit(resp, zeta, tol)
        x, _ = spring(resp, zeta)
        peak = max(x(t / 1000) for t in range(int(D * 1000)))
        if check:
            err = max(abs(bezier_eval(pts, k / 2000) - (x(k / 2000 * D) if k < 2000 else 1)) for k in range(2001))
            print(f"{name}: duree {D * 1000:.0f} ms, depassement {max(0, peak - 1) * 100:.1f} %, erreur max {err:.4f}")
        else:
            curve = ", ".join(f"{p:.4f}" for p in pts)
            print(f"    // {name}: ressort réponse {resp} s, amortissement {zeta} — {role}"
                  f" (dépassement {max(0, peak - 1) * 100:.1f} %)")
            print(f"    readonly property int {name}Duree: {round(D * 1000)}")
            print(f"    readonly property var {name}Courbe: [{curve}]")


if __name__ == "__main__":
    main()
