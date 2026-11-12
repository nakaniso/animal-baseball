# -*- coding: utf-8 -*-
"""Bake meshes into src/15-meshes.js.

The game ships as one HTML file, so geometry has to live in the source. This
writes each mesh as quantised binary in base64: positions as Int16 over the
mesh's own bounding box, normals as Int8, indices as Uint16. That is about a
third the size of writing the floats out as text, and it decodes into the same
vertex buffer the hand-written primitives already use.

Two sources of geometry:
  * an .obj dropped in tools/obj/  (Blockbench, Blender, anything)
  * the procedural builders below

The builders exist because a salmon and a rhinoceros beetle are exactly the
shapes you cannot fake by stacking spheres: a fish is a loft through elliptical
sections, and a Trypoxylus horn is a tube swept along a curve that forks. Both
are a few lines of maths and neither is a few lines of primitives.

    python tools/mesh2js.py
"""
import base64
import io
import math
import os
import struct

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# plain javascript the builders want shipped beside their meshes
DATA = []

# ----------------------------------------------------------------- mesh core


class Mesh(object):
    def __init__(self):
        self.v = []      # [x, y, z]
        self.f = []      # [i, j, k]
        self.t = []      # [u, v] or None — only face patches carry these

    def vert(self, x, y, z, u=None, w=None):
        self.v.append((x, y, z))
        self.t.append(None if u is None else (u, w))
        return len(self.v) - 1

    def has_uv(self):
        return any(t is not None for t in self.t)

    def tri(self, a, b, c):
        self.f.append((a, b, c))

    def quad(self, a, b, c, d):
        self.tri(a, b, c)
        self.tri(a, c, d)

    def merge(self, other):
        n = len(self.v)
        self.v.extend(other.v)
        self.t.extend(other.t)
        self.f.extend([(a + n, b + n, c + n) for a, b, c in other.f])
        return self

    def normals(self):
        """Area-weighted vertex normals, so the cel bands follow the form."""
        nn = [[0.0, 0.0, 0.0] for _ in self.v]
        for a, b, c in self.f:
            pa, pb, pc = self.v[a], self.v[b], self.v[c]
            ux, uy, uz = pb[0] - pa[0], pb[1] - pa[1], pb[2] - pa[2]
            vx, vy, vz = pc[0] - pa[0], pc[1] - pa[1], pc[2] - pa[2]
            cx = uy * vz - uz * vy
            cy = uz * vx - ux * vz
            cz = ux * vy - uy * vx
            for i in (a, b, c):
                nn[i][0] += cx
                nn[i][1] += cy
                nn[i][2] += cz
        out = []
        for n in nn:
            L = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
            out.append((n[0] / L, n[1] / L, n[2] / L))
        return out


def loft(rings, cap_start=True, cap_end=True, flip=False):
    """Stitch a stack of equal-length rings into a tube.

    Rings run counter-clockwise seen from outside looking back down the stack,
    which is the winding the renderer culls to.
    """
    m = Mesh()
    n = len(rings[0])
    idx = []
    for r in rings:
        idx.append([m.vert(*p) for p in r])
    for k in range(len(rings) - 1):
        a, b = idx[k], idx[k + 1]
        for i in range(n):
            j = (i + 1) % n
            if flip:
                m.quad(a[i], b[i], b[j], a[j])
            else:
                m.quad(a[i], a[j], b[j], b[i])
    for cap, ring, rev in ((cap_start, idx[0], not flip), (cap_end, idx[-1], flip)):
        if not cap:
            continue
        cx = sum(m.v[i][0] for i in ring) / n
        cy = sum(m.v[i][1] for i in ring) / n
        cz = sum(m.v[i][2] for i in ring) / n
        c = m.vert(cx, cy, cz)
        for i in range(n):
            j = (i + 1) % n
            if rev:
                m.tri(c, ring[j], ring[i])
            else:
                m.tri(c, ring[i], ring[j])
    return m


def section_pt(cx, cy, cz, half_w, half_d, a, e=2.2, back_flat=1.0):
    ca, sa = math.cos(a), math.sin(a)
    px = math.copysign(abs(ca) ** (2.0 / e), ca) * half_w
    pz = math.copysign(abs(sa) ** (2.0 / e), sa) * half_d
    if pz < 0:
        pz *= back_flat
    return (cx + px, cy, cz + pz)


def section(cx, cy, cz, half_w, half_d, n=16, e=2.2, back_flat=1.0):
    """One elliptical (slightly superelliptical) cross-section in the x/z plane.

    A fish is not a true ellipse: the back is flatter than the belly, which is
    what `back_flat` pinches.
    """
    pts = []
    for i in range(n):
        a = (i / float(n)) * math.tau
        ca, sa = math.cos(a), math.sin(a)
        # superellipse keeps the section from looking like a balloon
        px = math.copysign(abs(ca) ** (2.0 / e), ca) * half_w
        pz = math.copysign(abs(sa) ** (2.0 / e), sa) * half_d
        if pz < 0:
            pz *= back_flat
        pts.append((cx + px, cy, cz + pz))
    return pts


def lerp_profile(t, keys):
    """Piecewise-linear read of [(t, value), ...]."""
    if t <= keys[0][0]:
        return keys[0][1]
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]
        t1, v1 = keys[i + 1]
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return v0 + (v1 - v0) * k
    return keys[-1][1]


def blade(pts_a, pts_b, thick):
    """A fin or a wing case edge: a flat sheet given a little thickness."""
    m = Mesh()
    top = [m.vert(p[0] + thick, p[1], p[2]) for p in pts_a]
    bot = [m.vert(p[0] - thick, p[1], p[2]) for p in pts_a]
    top2 = [m.vert(p[0] + thick, p[1], p[2]) for p in pts_b]
    bot2 = [m.vert(p[0] - thick, p[1], p[2]) for p in pts_b]
    n = len(pts_a)
    for i in range(n - 1):
        m.quad(top[i], top[i + 1], top2[i + 1], top2[i])
        m.quad(bot2[i], bot2[i + 1], bot[i + 1], bot[i])
        m.quad(top[i], top2[i], bot2[i], bot[i])
        m.quad(top[i + 1], bot[i + 1], bot2[i + 1], top2[i + 1])
    m.quad(top[0], bot[0], bot2[0], top2[0])
    m.quad(top[n - 1], top2[n - 1], bot2[n - 1], bot[n - 1])
    return m


def sweep(path, radii, n=10):
    """A tube along a path — the beetle's horn, and its forks."""
    rings = []
    for i, (px, py, pz) in enumerate(path):
        if i == 0:
            dx, dy, dz = (path[1][0] - px, path[1][1] - py, path[1][2] - pz)
        elif i == len(path) - 1:
            dx, dy, dz = (px - path[-2][0], py - path[-2][1], pz - path[-2][2])
        else:
            dx = path[i + 1][0] - path[i - 1][0]
            dy = path[i + 1][1] - path[i - 1][1]
            dz = path[i + 1][2] - path[i - 1][2]
        L = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        dx, dy, dz = dx / L, dy / L, dz / L
        # A stable frame, square to the path. Taking x across the body and
        # leaving it at that skews the tube wherever the path runs sideways —
        # which is exactly what the horn's forks do, and a thick horn shows it.
        ux, uy, uz = 1.0, 0.0, 0.0
        d_u = dx * ux + dy * uy + dz * uz
        if abs(d_u) > 0.94:                       # path nearly along x: turn 90
            ux, uy, uz = 0.0, 1.0, 0.0
            d_u = dy
        ux, uy, uz = ux - dx * d_u, uy - dy * d_u, uz - dz * d_u
        Lu = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
        ux, uy, uz = ux / Lu, uy / Lu, uz / Lu
        vx = dy * uz - dz * uy
        vy = dz * ux - dx * uz
        vz = dx * uy - dy * ux
        Lv = math.sqrt(vx * vx + vy * vy + vz * vz) or 1.0
        vx, vy, vz = vx / Lv, vy / Lv, vz / Lv
        r = radii[i]
        ring = []
        for k in range(n):
            a = (k / float(n)) * math.tau
            ca, sa = math.cos(a) * r, math.sin(a) * r
            ring.append((px + ux * ca + vx * sa,
                         py + uy * ca + vy * sa,
                         pz + uz * ca + vz * sa))
        rings.append(ring)
    return loft(rings)


def ball(cx, cy, cz, r, n=10):
    rings = []
    for i in range(n + 1):
        a = math.pi * i / n
        rings.append(section(cx, cy + math.cos(a) * r, cz,
                             math.sin(a) * r, math.sin(a) * r, n, e=2.0))
    return loft(rings)


def bez(a, b, c, n):
    out = []
    for i in range(n):
        t = i / float(n - 1)
        u = 1.0 - t
        out.append(tuple(u * u * a[k] + 2 * u * t * b[k] + t * t * c[k] for k in range(3)))
    return out


# ------------------------------------------------------------------- salmon
# A male chum salmon (シロザケ) on the spawning run: the real fish, not a toy.
#
# Canonical frame: the spine runs along +Y with the snout up (y = SAL_L at the
# tip of the kype, 0 at the base of the tail), the back toward -Z, the belly
# toward +Z, and +X is the fish's left flank. `t` counts from the snout (0) to
# the base of the tail (1). Every marking, the eye, the gill cover and the fin
# roots are solved on the same (t, e) map of the body — e is the elevation
# round the section, +pi/2 the dorsal ridge, -pi/2 the keel — so nothing has to
# be placed by eye and nothing floats.
#
# The game curls the body in the vertex shader (R.bend), about local y = SAL_PIV
# and only behind it: the head is rigid, as a fish's is, so the jaw, the gill
# covers and the pectorals hang off fixed hinges.

SAL_L = 1.24
SAL_PIV_T = 0.30
SAL_E = 2.3            # superellipse exponent of the sections

# dorsal edge, ventral edge (z, metres) and half width, by t. The head front is
# only the upper jaw: its ventral edge is the mouth line, and the kype hooks
# down past it at the very tip. Depth at the dorsal is 26% of the length, width
# half the depth: deep, flat-sided, not a cigar.
SAL_TOP = [(0.0, 0.066), (0.010, 0.032), (0.025, -0.012), (0.05, -0.048),
           (0.08, -0.098), (0.12, -0.148), (0.17, -0.172), (0.23, -0.194),
           (0.30, -0.207), (0.37, -0.219), (0.43, -0.221), (0.50, -0.210),
           (0.60, -0.174), (0.70, -0.128), (0.80, -0.086), (0.87, -0.060),
           (0.93, -0.053), (1.0, -0.058)]
SAL_BOT = [(0.0, 0.084), (0.010, 0.090), (0.025, 0.070), (0.045, 0.052), (0.07, 0.045),
           (0.10, 0.043), (0.15, 0.042), (0.175, 0.050), (0.20, 0.086),
           (0.23, 0.114), (0.27, 0.133), (0.33, 0.155), (0.42, 0.174),
           (0.52, 0.171), (0.62, 0.146), (0.70, 0.112), (0.78, 0.082),
           (0.86, 0.058), (0.93, 0.050), (1.0, 0.056)]
SAL_W = [(0.0, 0.009), (0.012, 0.016), (0.03, 0.024), (0.06, 0.034),
         (0.10, 0.044), (0.15, 0.054), (0.21, 0.066), (0.28, 0.079),
         (0.36, 0.088), (0.44, 0.091), (0.52, 0.087), (0.62, 0.075),
         (0.72, 0.057), (0.82, 0.037), (0.90, 0.025), (0.96, 0.022),
         (1.0, 0.023)]


def sal_y(t):
    return SAL_L * (1.0 - t)


def sal_sec(t):
    top = smooth_profile(t, SAL_TOP)
    bot = smooth_profile(t, SAL_BOT)
    w = smooth_profile(t, SAL_W)
    return top, bot, w, top + 0.46 * (bot - top)


def sal_ring_pt(t, a):
    """The body surface at section angle a (0 = left flank, +pi/2 = keel)."""
    top, bot, w, mid = sal_sec(t)
    ca, sa = math.cos(a), math.sin(a)
    k = 2.0 / SAL_E
    x = math.copysign(abs(ca) ** k, ca) * w
    z = mid + ((top - mid) if sa < 0 else (bot - mid)) * abs(sa) ** k
    return (x, sal_y(t), z)


def sal_a(e, side):
    return -e if side > 0 else math.pi + e


def sal_nrm(t, a):
    h = 1e-4
    p = sal_ring_pt(t, a)
    pt = sal_ring_pt(min(1.0, t + h), a)
    pt0 = sal_ring_pt(max(0.0, t - h), a)
    pa = sal_ring_pt(t, a + h)
    pa0 = sal_ring_pt(t, a - h)
    u = [pt[i] - pt0[i] for i in range(3)]
    v = [pa[i] - pa0[i] for i in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    L = math.sqrt(sum(c * c for c in n)) or 1.0
    n = [c / L for c in n]
    mid = sal_sec(t)[3]
    if n[0] * p[0] + n[2] * (p[2] - mid) < 0:
        n = [-c for c in n]
    return n


def sal_pt(t, e, side, off=0.0):
    a = sal_a(e, side)
    p = sal_ring_pt(t, a)
    if not off:
        return p
    n = sal_nrm(t, a)
    return (p[0] + n[0] * off, p[1] + n[1] * off, p[2] + n[2] * off)


def jag(*k):
    """A repeatable scatter in [-1, 1]."""
    s = 0.0
    for i, q in enumerate(k):
        s += q * (12.9898 + 31.7 * i)
    v = math.sin(s) * 43758.5453
    return 2.0 * (v - math.floor(v)) - 1.0


def sal_grid(rows, inside):
    """Quads over a grid of points; faces turned away from `inside`, a function
    giving a point under each vertex (the spine at that height)."""
    m = Mesh()
    idx = [[m.vert(*p) for p in r] for r in rows]
    s = 0.0
    for k in range(len(rows) - 1):
        for i in range(len(rows[k]) - 1):
            a, b, c, d = idx[k][i], idx[k][i + 1], idx[k + 1][i + 1], idx[k + 1][i]
            m.quad(a, b, c, d)
            pa, pb, pc = m.v[a], m.v[b], m.v[c]
            u = [pb[j] - pa[j] for j in range(3)]
            v = [pc[j] - pa[j] for j in range(3)]
            n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            q = inside(pa)
            s += sum(n[j] * (pa[j] - q[j]) for j in range(3))
    if s < 0:
        m.f = [(a, c, b) for a, b, c in m.f]
    return m


def sal_axis(p):
    t = max(0.0, min(1.0, 1.0 - p[1] / SAL_L))
    return (0.0, p[1], sal_sec(t)[3])


def sal_patch(fn, nr, nc, off):
    """A skin patch: fn(r, c) -> (t, e, side) over r, c in [0, 1]."""
    rows = []
    for i in range(nr):
        row = []
        for j in range(nc):
            t, e, side = fn(i / float(nr - 1), j / float(nc - 1))
            row.append(sal_pt(t, e, side, off))
        rows.append(row)
    return sal_grid(rows, sal_axis)


def sal_dome(t, e, side, R, off, dome, nr=4, nt=14):
    """A round domed disc on the skin (an eye, a nostril), solved on the map so
    its rim follows the body's curve."""
    a = sal_a(e, side)
    p = sal_ring_pt(t, a)
    n = sal_nrm(t, a)
    h = 1e-3
    pt = sal_ring_pt(t + h, a)
    pe = sal_pt(t, e + h, side)
    Lt = math.dist(p, pt) / h
    Le = math.dist(p, pe) / h
    m = Mesh()
    c0 = m.vert(p[0] + n[0] * (off + dome), p[1] + n[1] * (off + dome), p[2] + n[2] * (off + dome))
    rings = []
    for i in range(1, nr + 1):
        rho = i / float(nr)
        ring = []
        for k in range(nt):
            th = math.tau * k / nt
            tt = t + R * rho * math.cos(th) / Lt
            ee = e + R * rho * math.sin(th) / Le
            q = sal_ring_pt(tt, sal_a(ee, side))
            nn = sal_nrm(tt, sal_a(ee, side))
            hh = off + dome * (1 - rho * rho)
            ring.append(m.vert(q[0] + nn[0] * hh, q[1] + nn[1] * hh, q[2] + nn[2] * hh))
        rings.append(ring)
    for k in range(nt):
        m.tri(c0, rings[0][k], rings[0][(k + 1) % nt])
    for i in range(nr - 1):
        a_, b_ = rings[i], rings[i + 1]
        for k in range(nt):
            j = (k + 1) % nt
            m.quad(a_[k], b_[k], b_[j], a_[j])
    return oriented_open(m, (0.0, p[1], sal_sec(t)[3]))


def sal_fin(base, dirs, lens, th0, th1, nrm, rows=5, ridge=0.0, droop=None, split=None):
    """A fin: rays fanned from points on the body, given a thickness that
    tapers to the edge (a thin wedge, not a slab) and ridged every other ray so
    the light picks the rays out. With `split`, returns (fin, margin) cut at
    that share of the ray length, so the edge can take its own colour."""
    nc = len(base)

    def P(i, s, sgn):
        b, d, L = base[i], dirs[i], lens[i]
        th = (th0 + (th1 - th0) * s) * 0.5
        if ridge and 0 < i < nc - 1:
            th *= 1.0 + (ridge if i % 2 else -ridge) * min(1.0, s * 3.0) * (1.0 - s) ** 2
        n = nrm[i] if isinstance(nrm[0], (list, tuple)) else nrm
        q = [b[k] + d[k] * L * s for k in range(3)]
        if droop:
            for k in range(3):
                q[k] += droop[k] * L * s * s
        return (q[0] + n[0] * th * sgn, q[1] + n[1] * th * sgn, q[2] + n[2] * th * sgn)

    def solid(s0, s1, nrow):
        m = Mesh()
        ss = [s0 + (s1 - s0) * r / float(nrow) for r in range(nrow + 1)]
        top = [[m.vert(*P(i, s, 1)) for i in range(nc)] for s in ss]
        bot = [[m.vert(*P(i, s, -1)) for i in range(nc)] for s in ss]
        for r in range(nrow):
            for i in range(nc - 1):
                m.quad(top[r][i], top[r][i + 1], top[r + 1][i + 1], top[r + 1][i])
                m.quad(bot[r][i], bot[r + 1][i], bot[r + 1][i + 1], bot[r][i + 1])
            m.quad(top[r][0], top[r + 1][0], bot[r + 1][0], bot[r][0])
            m.quad(top[r][-1], bot[r][-1], bot[r + 1][-1], top[r + 1][-1])
        for i in range(nc - 1):
            m.quad(top[0][i], bot[0][i], bot[0][i + 1], top[0][i + 1])
            m.quad(top[-1][i], top[-1][i + 1], bot[-1][i + 1], bot[-1][i])
        return oriented(m)

    if split is None:
        return solid(0.0, 1.0, rows)
    r0 = max(1, int(round(rows * split)))
    return solid(0.0, split, r0), solid(split, 1.0, max(1, rows - r0))


def _nz(v):
    L = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / L for c in v]


def _cross(u, v):
    return [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]


def sal_cone(b, d, L, r, n=5):
    """A tooth: a recurved cone from base b along d."""
    m = Mesh()
    d = _nz(d)
    u = _nz(_cross(d, [0.0, 1.0, 0.0] if abs(d[1]) < 0.9 else [1.0, 0.0, 0.0]))
    v = _cross(d, u)
    ring = []
    for k in range(n):
        a = math.tau * k / n
        ring.append(m.vert(*[b[i] + (u[i] * math.cos(a) + v[i] * math.sin(a)) * r for i in range(3)]))
    tip = m.vert(*[b[i] + d[i] * L + (-0.25 * L if i == 1 else 0.0) for i in range(3)])
    for k in range(n):
        m.tri(ring[k], ring[(k + 1) % n], tip)
    return oriented_open(m, b)


SAL_JAW_T = [(0.030, 0.056, 0.064, 0.009), (0.040, 0.054, 0.080, 0.015),
             (0.060, 0.057, 0.100, 0.023), (0.100, 0.052, 0.120, 0.033),
             (0.150, 0.047, 0.127, 0.042), (0.205, 0.046, 0.116, 0.048),
             (0.235, 0.048, 0.104, 0.044)]


def sal_jaw_sec(t):
    keys = SAL_JAW_T
    top = smooth_profile(t, [(k[0], k[1]) for k in keys])
    bot = smooth_profile(t, [(k[0], k[2]) for k in keys])
    w = smooth_profile(t, [(k[0], k[3]) for k in keys])
    return top, bot, w


def build_salmon():
    out = {}
    piv = sal_y(SAL_PIV_T)

    # --- the body: 56 sections, packed toward the head where the kype is
    rings = []
    for i in range(42):
        t = (i / 41.0) ** 1.25
        rings.append([sal_ring_pt(t, math.tau * k / 22.0) for k in range(22)])
    out['sal_body'] = oriented(loft(rings))

    # --- colour, as skin patches offset along the normal, stacked by height:
    # belly < bars < back < lines. The back is dark olive down to the eye and
    # well down the gill cover; its edge wanders a little, as a real one does.
    def back_e(t, side):
        h = smooth_profile(t, [(0.0, 2.4), (0.05, 2.0), (0.10, 1.40), (0.16, 1.08),
                               (0.22, 1.02), (0.30, 1.08), (0.45, 1.14), (0.65, 1.20),
                               (0.85, 1.30), (1.0, 1.36)])
        return (math.pi / 2 - h + 0.035 * math.sin(t * 41 + side)
                + 0.025 * math.sin(t * 97 + 2 * side))

    def back_fn(r, c):
        t = 0.002 + 0.996 * r ** 1.2
        side = 1 if c < 0.5 else -1
        k = abs(c - 0.5) * 2
        e0 = back_e(t, side)
        return t, math.pi / 2 - (math.pi / 2 - e0) * k, side
    out['sal_back'] = sal_patch(back_fn, 30, 7, 0.0075)

    def belly_e(t):
        return -math.pi / 2 + smooth_profile(t, [(0.185, 0.40), (0.23, 0.55), (0.30, 0.62),
                                                  (0.45, 0.64), (0.60, 0.58), (0.72, 0.46),
                                                  (0.82, 0.34), (0.90, 0.20)])

    def belly_fn(r, c):
        t = 0.185 + 0.715 * r
        side = 1 if c < 0.5 else -1
        k = abs(c - 0.5) * 2
        return t, -math.pi / 2 + (belly_e(t) + math.pi / 2) * k, side
    out['sal_belly'] = sal_patch(belly_fn, 26, 7, 0.0035)

    # the spawning bars (ブナ毛): ragged vertical flames of maroon from under the
    # dark back down the lower flank, with dusky green between them
    bars, dbars = Mesh(), Mesh()
    for side in (1, -1):
        for k in range(8):
            tc = 0.280 + k * 0.073 + 0.010 * jag(k, side)
            fade = 1.0 - 0.10 * max(0, k - 4)              # smaller toward the tail
            e_lo = (-0.80 - 0.18 * (0.5 + 0.5 * jag(k, 3, side))) * fade
            wk = 0.022 * (1.0 + 0.40 * jag(k, 11, side)) * fade

            def bar(r, c, tc=tc, e_lo=e_lo, k=k, side=side, wk=wk, r0=0.0, r1=1.0, dt=0.0, sc=1.0):
                r = r0 + (r1 - r0) * r
                e_hi = back_e(tc, side) + 0.14
                e = e_hi + (e_lo - e_hi) * r
                hw = wk * sc * (1.0 + 0.30 * r) * (1.0 + 0.45 * jag(k, int(r * 10), side, c))
                if r > 0.80:
                    hw *= max(0.15, 1.0 - (r - 0.80) * 4.0)
                mz = 0.010 * jag(k, int(r * 5), side, 9)    # the bar wanders
                return tc + 0.016 * e + mz + dt + (c * 2 - 1) * hw, e, side
            if k in (1, 6):                                # broken
                bars.merge(sal_patch(lambda r, c, f=bar: f(r, c, r0=0.0, r1=0.44), 5, 2, 0.0055))
                bars.merge(sal_patch(lambda r, c, f=bar: f(r, c, r0=0.54, r1=1.0), 4, 2, 0.0055))
            elif k in (2, 4):                              # forked at the foot
                bars.merge(sal_patch(lambda r, c, f=bar: f(r, c, r0=0.0, r1=0.62), 6, 2, 0.0055))
                for d in (-1, 1):
                    bars.merge(sal_patch(lambda r, c, f=bar, d=d: f(r, c, r0=0.58, r1=1.0,
                               dt=d * wk * (0.45 + 0.9 * r), sc=0.5), 3, 2, 0.0055))
            else:
                bars.merge(sal_patch(bar, 8, 2, 0.0055))
        for k in range(7):
            tc = 0.280 + k * 0.073 + 0.0365 + 0.006 * jag(k, 7, side)
            e_lo = -0.40 - 0.45 * (0.5 + 0.5 * jag(k, 5, side))
            wide = 1.9 if k == 3 else 1.0                   # two bars run together here

            def dbar(r, c, tc=tc, e_lo=e_lo, k=k, side=side, wide=wide):
                e_hi = back_e(tc, side) + 0.10
                e = e_hi + (e_lo - e_hi) * r
                hw = 0.0095 * (1.0 + 0.9 * r * wide) * (1.0 + 0.45 * jag(k, int(r * 9), side, c, 2))
                if r > 0.8:
                    hw *= 1.0 - (r - 0.8) * 4.0
                return tc + 0.016 * e + (c * 2 - 1) * hw, e, side
            dbars.merge(sal_patch(dbar, 7, 2, 0.006))
    out['sal_bars'] = bars
    out['sal_dbars'] = dbars

    # --- the gill cover: a plate hinged at the preopercle, with a rounded rear
    # edge. Under it a sliver of red gill, which shows when it flares.
    def oper_t(e):
        # the preopercle runs down behind the eye and sweeps forward under it
        tf = 0.162 - 0.022 * max(0.0, -(e + 0.35)) ** 1.4
        q = (e + 0.18) / 1.10
        tr = 0.170 + 0.068 * max(0.0, 1.0 - q * q) ** 0.55
        return tf, max(tr, tf + 0.008)
    E0, E1 = 0.56, -1.22
    for side, nm in ((1, 'l'), (-1, 'r')):
        def oper(r, c, side=side):
            e = E0 + (E1 - E0) * r
            tf, tr = oper_t(e)
            return tf + (tr - tf) * c, e, side
        out['sal_oper' + nm] = sal_patch(oper, 12, 5, 0.0070)
    gill, line = Mesh(), Mesh()
    for side in (1, -1):
        def gl_(r, c, side=side):
            e = E0 - 0.02 + (E1 + 0.04 - E0) * r
            tr = oper_t(e)[1]
            return tr - 0.024 + 0.022 * c, e, side
        gill.merge(sal_patch(gl_, 11, 2, 0.0045))

        def rim(r, c, side=side):
            e = E0 + (E1 - E0) * r
            tr = oper_t(e)[1]
            return tr - 0.003 + 0.008 * c, e, side
        line.merge(sal_patch(rim, 11, 2, 0.0080))

        def pre(r, c, side=side):
            e = 0.45 + (-1.15 - 0.45) * r
            tf = oper_t(e)[0]
            return tf - 0.003 + 0.006 * c, e, side
        line.merge(sal_patch(pre, 9, 2, 0.0098))

        # the lateral line, dark and straight from the gill to the tail
        def ll(r, c, side=side):
            t = 0.245 + 0.71 * r
            e = 0.06 + 0.10 * (1 - r) ** 3 + (c * 2 - 1) * 0.022
            return t, e, side
        line.merge(sal_patch(ll, 20, 2, 0.0095))
        for tn, en in ((0.036, 0.44), (0.050, 0.42)):
            line.merge(sal_dome(tn, en, side, 0.0062, 0.0095, 0.0, 2, 8))
    out['sal_gill'] = gill
    out['sal_line'] = line

    # --- the eye: small, set high over the long jaw, under a domed cornea
    eye, iris, pupil = Mesh(), Mesh(), Mesh()
    TE, EE = 0.115, 0.22
    for side in (1, -1):
        eye.merge(sal_dome(TE, EE, side, 0.0245, 0.0090, 0.004, 2, 12))
        iris.merge(sal_dome(TE, EE, side, 0.0178, 0.0105, 0.007, 3, 12))
        pupil.merge(sal_dome(TE, EE, side, 0.0100, 0.0160, 0.0040, 2, 12))
    out['sal_eye'] = eye
    out['sal_iris'] = iris
    out['sal_pupil'] = pupil

    # --- the mouth: dark roof under the upper jaw, the lower jaw on its hinge,
    # and teeth. A spawning male's are long at the front of both jaws.
    def palate(r, c):
        t = 0.010 + 0.18 * r
        side = 1 if c < 0.5 else -1
        k = abs(c - 0.5) * 2
        return t, -math.pi / 2 + 0.30 * k, side
    out['sal_mouth'] = sal_patch(palate, 11, 5, 0.0015)

    jr = []
    for i in range(16):
        t = 0.235 - (0.235 - 0.030) * (i / 15.0) ** 0.8
        top, bot, w = sal_jaw_sec(t)
        mid = 0.5 * (top + bot)
        ring = []
        for k in range(12):
            a = math.tau * k / 12.0
            ca, sa = math.cos(a), math.sin(a)
            ring.append((math.copysign(abs(ca) ** 0.8, ca) * w, sal_y(t),
                         mid + math.copysign(abs(sa) ** 0.8, sa) * (bot - top) * 0.5))
        jr.append(ring)
    out['sal_jaw'] = oriented(loft(jr))
    jaw_hinge = (sal_y(0.195), 0.048)

    teeth, lteeth = Mesh(), Mesh()
    for side in (1, -1):
        for t, L in ((0.012, 0.036), (0.026, 0.026), (0.052, 0.010), (0.079, 0.013),
                     (0.113, 0.008), (0.141, 0.010)):
            b = sal_pt(t, -1.26, side, -0.002)
            teeth.merge(sal_cone(b, (-side * 0.12, -0.10, 1.0), L, L * 0.30))
        for t, L in ((0.036, 0.032), (0.048, 0.020), (0.074, 0.011), (0.104, 0.012),
                     (0.133, 0.008)):
            top, bot, w = sal_jaw_sec(t)
            b = (side * w * 0.72, sal_y(t), top + 0.003)
            lteeth.merge(sal_cone(b, (side * 0.10, 0.10, -1.0), L, L * 0.30))
    out['sal_teeth'] = teeth
    out['sal_lteeth'] = lteeth

    # --- fins
    def ridge_pt(t, top=True, inset=0.006):
        a, b_, w, m_ = sal_sec(t)
        return (0.0, sal_y(t), (a + inset) if top else (b_ - inset))

    X = [1.0, 0.0, 0.0]
    # dorsal: a raked trapezoid of 12 rays, the second and third the longest
    n = 12
    base = [ridge_pt(0.405 + 0.125 * i / (n - 1)) for i in range(n)]
    dirs = []
    lens = []
    for i in range(n):
        r = 0.32 + 0.62 * i / (n - 1)
        dirs.append((0.0, -math.sin(r), -math.cos(r)))
        u = i / (n - 1.0)
        lens.append(1.25 * (0.118 if i == 0 else 0.140 - 0.085 * u ** 1.1) * (1 + 0.05 * jag(i, 1)))
    out['sal_dorsal'], out['sal_dorsal_m'] = sal_fin(
        base, dirs, lens, 0.026, 0.010, X, 5, 0.30, (0.0, -0.10, 0.0), split=0.84)

    # adipose: a small fleshy lobe, no rays — the salmonid signature
    n = 7
    base = [ridge_pt(0.785 + 0.055 * i / (n - 1), inset=0.005) for i in range(n)]
    dirs = [(0.0, -math.sin(0.85 + 0.5 * i / (n - 1)), -math.cos(0.85 + 0.5 * i / (n - 1)))
            for i in range(n)]
    lens = [0.012 + 0.032 * math.sin(math.pi * (i + 0.6) / (n + 0.2)) for i in range(n)]
    out['sal_adipose'] = sal_fin(base, dirs, lens, 0.022, 0.012, X, 3, 0.0, (0.0, -0.3, 0.0))

    # caudal: broad and shallowly forked, rays fanned from the end of the
    # peduncle, with a dark trailing edge
    n = 17
    tb = 0.985
    a_, b_, w, m_ = sal_sec(tb)
    base = [(0.0, sal_y(tb), (a_ + 0.006) + (b_ - a_ - 0.012) * i / (n - 1)) for i in range(n)]
    dirs, lens = [], []
    for i in range(n):
        ph = -0.62 + 1.24 * i / (n - 1)
        dirs.append((0.0, -math.cos(ph), math.sin(ph)))
        q = abs(ph) / 0.62
        L = 0.165 + 0.105 * q ** 1.6
        if i in (0, n - 1):
            L *= 0.90
        lens.append(L * (1 + 0.03 * jag(i, 4)))
    out['sal_caudal'], out['sal_caudal_m'] = sal_fin(
        base, dirs, lens, 0.036, 0.010, X, 5, 0.28, split=0.80)

    # anal: under the adipose, raked back, a white leading tip
    n = 9
    base = [ridge_pt(0.712 + 0.080 * i / (n - 1), top=False) for i in range(n)]
    dirs, lens = [], []
    for i in range(n):
        r = 0.45 + 0.55 * i / (n - 1)
        dirs.append((0.0, -math.sin(r), math.cos(r)))
        lens.append((0.105 - 0.062 * (i / (n - 1.0)) ** 0.9) * (1 + 0.05 * jag(i, 6)))
    out['sal_anal'], out['sal_anal_m'] = sal_fin(
        base, dirs, lens, 0.022, 0.009, X, 5, 0.28, (0.0, -0.08, 0.0), split=0.84)

    # pelvics (paired, under the dorsal) with the small axillary process
    pel, pel_m, axil = Mesh(), Mesh(), Mesh()
    for side in (1, -1):
        n = 7
        base = [sal_pt(0.492 + 0.042 * i / (n - 1), -1.18, side, -0.004) for i in range(n)]
        d = _nz((side * 0.38, -0.82, 0.46))
        nr = _nz(_cross([0.0, -1.0, 0.0], d))
        dirs = [d] * n
        lens = [(0.098 - 0.034 * i / (n - 1.0)) * (1 + 0.04 * jag(i, 8, side)) for i in range(n)]
        a1, a2 = sal_fin(base, dirs, lens, 0.020, 0.008, nr, 5, 0.28, split=0.84)
        pel.merge(a1)
        pel_m.merge(a2)
        base = [sal_pt(0.482 + 0.020 * i / 2.0, -1.02, side, -0.003) for i in range(3)]
        d = _nz((side * 0.16, -0.97, 0.12))
        nr = sal_nrm(0.50, sal_a(-1.02, side))
        axil.merge(sal_fin(base, [d] * 3, [0.040, 0.046, 0.036], 0.014, 0.006, nr, 3))
    out['sal_pelvic'] = pel
    out['sal_pelvic_m'] = pel_m
    out['sal_axil'] = axil

    # pectorals, low behind the gill cover, each its own mesh so it can flick
    pec_axis = None
    for side, nm in ((1, 'l'), (-1, 'r')):
        n = 8
        base = [sal_pt(0.242 + 0.016 * i / (n - 1), -0.60 - 0.26 * i / (n - 1), side, -0.004)
                for i in range(n)]
        d = _nz((side * 0.42, -0.86, 0.26))
        nr = _nz(_cross(_nz([base[-1][k] - base[0][k] for k in range(3)]), d))
        lens = [(0.150 - 0.075 * (i / (n - 1.0)) ** 0.8) * (1 + 0.04 * jag(i, 9, side))
                for i in range(n)]
        out['sal_pec' + nm] = sal_fin(base, [d] * n, lens, 0.022, 0.008, nr, 5, 0.28,
                                      (0.0, -0.10, 0.10))
        if side > 0:
            pec_axis = base[0] + base[-1]

    # the one piece of kit: a narrow ribbon round the peduncle, like a tag
    band = []
    for i in range(3):
        t = 0.905 + 0.026 * i / 2.0
        ring = []
        for k in range(24):
            a = math.tau * k / 24.0
            p, nn = sal_ring_pt(t, a), sal_nrm(t, a)
            ring.append((p[0] + nn[0] * 0.006, p[1] + nn[1] * 0.006, p[2] + nn[2] * 0.006))
        band.append(ring)
    out['sal_band'] = oriented(loft(band))

    # the spine, the hinges and the ground-contact table the game needs
    oa = sal_pt(oper_t(E0)[0], E0, 1, 0.009)
    ob = sal_pt(oper_t(E1)[0], E1, 1, 0.009)
    sec = []
    for t in (0.0, 0.08, 0.18, 0.30, 0.42, 0.55, 0.68, 0.80, 0.90, 1.0):
        top, bot, w, mid = sal_sec(t)
        sec.append('[%.3f,%.3f,%.3f,%.3f,%.3f]' % (sal_y(t), top, bot, w, mid))
    sec.append('[-0.200,-0.020,0.020,0.012,0.000]')
    sec.append('[-0.265,-0.010,0.010,0.006,0.000]')
    DATA.append('/* the salmon: bend pivot, hinges (jaw, gill cover, pectoral) and')
    DATA.append('   sections [y, top, bottom, half width, mid] for ground contact */')
    DATA.append('const SAL = { piv: %.4f, jaw: [%.4f, %.4f], oper: [%s], pec: [%s],'
                % (piv, jaw_hinge[0], jaw_hinge[1], ','.join('%.4f' % v for v in oa + ob),
                   ','.join('%.4f' % v for v in pec_axis)))
    DATA.append('  sec: [%s] };' % ','.join(sec))
    DATA.append('')
    return out


# --------------------------------------------------------------------- bear
# The first mammal with a baked shell. Unlike the salmon and the beetle it
# keeps the whole shared rig — arms, legs, cap, four expressions — so the mesh
# has to drop into the existing anchors: the head is authored about the head
# anchor (y+1.34 in the game) and the body about the torso anchor (y+0.74).
#
# The head is one surface, not a skull with a muzzle stuck on the front, and
# that is the whole point. It works because the surface is a map from
# (azimuth, elevation) to a point: the face decal patches are then just
# rectangles of that same domain, so they sit on the surface by construction
# instead of being fitted to it by hand. Any mammal can be baked this way.

# The owner's pencil sketch (2026-09-23) is the reference now, and it is read
# off the paper, not guessed at. In the standing figure the head is 46% of his
# height and very nearly square (1.03 wide to 1 tall); the muzzle is an oval
# 49% of the head wide that starts 57% of the way down and nearly reaches the
# chin; the eyes are 40% down, 0.43 of the half-width out, and a little under a
# fifth of the head wide; the brows are 27% down. SKETCH holds those numbers
# as fractions of the head — y from the top, x from the centre line — and the
# (az, el) that put each thing there are solved off the skull below, so the
# face moves with the head instead of being typed in twice.
HEAD_X, HEAD_Y, HEAD_Z = 0.420, 0.400, 0.350
HEAD_UP = 0.070                 # sits on the body, not in it; the rig's anchor stays
HEAD_FWD = 0.02                 # the head primitive sat this far forward
HEAD_N = 3.0                    # a rounded box: the sketch's face is broad and flat
SKETCH = {
    'muz_top': 0.55, 'muz_bot': 0.86, 'muz_w': 0.49,
    'eye_y': 0.40, 'eye_x': 0.43, 'eye_w': 0.19, 'brow_y': 0.27,
}


def _skull(az, el):
    """The bare rounded box, before any swelling is added to it."""
    dx = math.cos(el) * math.sin(az)
    dy = math.sin(el)
    dz = math.cos(el) * math.cos(az)
    k = (abs(dx) ** HEAD_N + abs(dy) ** HEAD_N + abs(dz) ** HEAD_N) ** (-1.0 / HEAD_N)
    return dx * k * HEAD_X, dy * k * HEAD_Y, dz * k * HEAD_Z


def _solve(f, target, lo, hi):
    """Bisection on a monotone f."""
    flo = f(lo) - target
    for _ in range(60):
        mid = (lo + hi) / 2
        fm = f(mid) - target
        if (fm < 0) == (flo < 0):
            lo, flo = mid, fm
        else:
            hi = mid
    return (lo + hi) / 2


def el_at(down):
    """Elevation of the front centre line `down` of the way from crown to chin."""
    return _solve(lambda e: _skull(0.0, e)[1] / HEAD_Y, 1 - 2 * down, -1.5, 1.5)


def az_at(across, el):
    """Azimuth `across` of the half-width out from the centre line, at `el`."""
    return _solve(lambda a: _skull(a, el)[0] / HEAD_X, across, 0.0, 1.5)


_mt, _mb = el_at(SKETCH['muz_top']), el_at(SKETCH['muz_bot'])
SNOUT_EL = (_mt + _mb) / 2      # a bear's muzzle points down as well as out
MUZ_EL_R = (_mt - _mb) / 2
MUZ_AZ_R = az_at(SKETCH['muz_w'], SNOUT_EL)
EYE_EL = el_at(SKETCH['eye_y'])
EYE_AZ = az_at(SKETCH['eye_x'], EYE_EL)
EYE_AZ_R = (az_at(SKETCH['eye_x'] + SKETCH['eye_w'], EYE_EL)
            - az_at(SKETCH['eye_x'] - SKETCH['eye_w'], EYE_EL)) / 2
BROW_EL = el_at(SKETCH['brow_y'])

# the two decal patches, in (az, el): the face over the eyes and brows, the
# snout a little larger than the pale oval so its outline and the nose on its
# top edge both land inside it
FACE_AZ_R, FACE_EL_R = 60 * math.pi / 180, 50 * math.pi / 180
SNOUT_AZ_R, SNOUT_EL_R = MUZ_AZ_R * 1.16, MUZ_EL_R * 1.34


def bump(q, amp):
    """A smooth blob over an elliptical footprint, zero outside it.

    The obvious `max(0, 1 - q) ** p` looks the same but its curvature blows up
    at the rim, which digs a crease the surface cannot be offset out of: the
    pale muzzle patch sat 6mm proud and the skull still bit a chunk out of it.
    Smoothstep is flat at both ends, so the rim is a valley with a radius.
    """
    u = max(0.0, min(1.0, 1.0 - q))
    return amp * u * u * (3 - 2 * u)


def bear_head_pt(az, el, out=0.0):
    """A point on the bear's skull. Star-shaped in (az, el) by construction."""
    x, y, z = _skull(az, el)

    # The muzzle: broad, shallow, and part of the same surface. Wider than it
    # is tall is what stops it reading as a ball glued to the front.
    #
    # It was once a mesa — flat on top with a steep flank, which is what a real
    # bear's muzzle does and which puts a proper stop in the profile. It was
    # also wrong for this game. Anatomy is not the target: a round face with a
    # soft swelling on it is, and the stop turned the face into a snout. Do not
    # reach for realism here again. `bump` is the decision, not the default.
    #
    # The sketch's muzzle is the biggest thing on the face — nearly half its
    # width and height — and it stands well out from it. Bigger and further
    # out, but still a bump: it is the size that changed, not the profile.
    #
    # In the sketch it is drawn as an outline on a flat face, but every
    # three-quarter figure shows it standing out, so it swells — and the
    # swelling reaches a little past the pale oval so the rim is a slope.
    d = bump((az / (MUZ_AZ_R * 1.22)) ** 2 + ((el - SNOUT_EL) / (MUZ_EL_R * 1.25)) ** 2, 0.105)

    # the brow ridge, kept light — enough to catch the light above the eyes
    d += bump((az / 0.95) ** 2 + ((el - BROW_EL) / 0.22) ** 2, 0.018)

    # jowls, low and wide, carrying the line from the muzzle back to the ears
    d += bump(((abs(az) - 1.00) / 0.58) ** 2 + ((el + 0.20) / 0.44) ** 2, 0.030)

    # the flat of the crown — no cap sits on it any more, but the sketch's
    # head is flat-topped between the ears
    d -= 0.020 * max(0.0, (el - 0.95) / 0.62) ** 2

    L = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x + x / L * d, y + y / L * d + HEAD_UP, z + z / L * d + HEAD_FWD)


def lifted(fn, az, el, out):
    """A point `out` clear of the surface, along its own normal."""
    p = fn(az, el)
    if not out:
        return p
    h = 2e-3
    pa, pb = fn(az + h, el), fn(az - h, el)
    pc, pd = fn(az, el + h), fn(az, el - h)
    u = [pa[i] - pb[i] for i in range(3)]
    v = [pc[i] - pd[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1],
         u[2] * v[0] - u[0] * v[2],
         u[0] * v[1] - u[1] * v[0]]
    L = math.sqrt(sum(q * q for q in n))
    if L < 1e-9:                      # a pole: fall back to the radial
        L = math.sqrt(sum(q * q for q in p)) or 1.0
        n = list(p)
    if n[0] * p[0] + n[1] * p[1] + n[2] * p[2] < 0:
        n = [-q for q in n]           # always outward
    return tuple(p[i] + n[i] / L * out for i in range(3))


def surface_of(fn, naz=28, nel=18):
    """Close a (az, el) surface map into a solid, poles and all."""
    m = Mesh()
    rows = []
    for i in range(nel + 1):
        el = -math.pi / 2 + math.pi * i / nel
        if i == 0 or i == nel:
            rows.append([m.vert(*fn(0.0, el))] * naz)
        else:
            rows.append([m.vert(*fn(-math.pi + math.tau * j / naz, el))
                         for j in range(naz)])
    for i in range(nel):
        a, b = rows[i], rows[i + 1]
        for j in range(naz):
            k = (j + 1) % naz
            if i == 0:
                m.tri(a[j], b[k], b[j])
            elif i == nel - 1:
                m.tri(a[j], a[k], b[j])
            else:
                m.quad(a[j], a[k], b[k], b[j])
    return m


def uv_patch(fn, az_c, az_r, el_c, el_r, out, n=12, mm=12):
    """A rectangle of the same surface, carrying the face cell's UVs.

    The mapping copies the `facep` primitive exactly — u across azimuth, v down
    elevation — so a cell drawn for the sphere patch lands the same way here.
    """
    m = Mesh()
    rows = []
    for i in range(mm + 1):
        el = el_c + ((i / float(mm)) * 2 - 1) * el_r
        row = []
        for j in range(n + 1):
            az = az_c + ((j / float(n)) * 2 - 1) * az_r
            x, y, z = lifted(fn, az, el, out)
            row.append(m.vert(x, y, z, j / float(n), 1 - i / float(mm)))
        rows.append(row)
    for i in range(mm):
        a, b = rows[i], rows[i + 1]
        for j in range(n):
            m.tri(a[j], a[j + 1], b[j])
            m.tri(a[j + 1], b[j + 1], b[j])
    return m


def oval_patch(fn, az_c, el_c, az_r, el_r, out, nr=6, nt=22):
    """An oval of the surface — the pale mask over the muzzle."""
    m = Mesh()
    rings = [[m.vert(*lifted(fn, az_c, el_c, out))] * nt]
    for r in range(1, nr + 1):
        rho = r / float(nr)
        rings.append([m.vert(*lifted(fn, az_c + rho * math.cos(th) * az_r,
                                     el_c + rho * math.sin(th) * el_r, out))
                      for th in [math.tau * j / nt for j in range(nt)]])
    for r in range(nr):
        a, b = rings[r], rings[r + 1]
        for j in range(nt):
            k = (j + 1) % nt
            if r == 0:
                m.tri(a[0], b[j], b[k])
            else:
                m.quad(a[j], b[j], b[k], a[k])
    return m


EAR_AZ, EAR_EL = 1.50, 0.86      # on the top corners, half off the outline
EAR_LIFT = 0.062                 # and how far out of it the disc's centre sits


def _ear_frame(side):
    # Two numbers decide the whole silhouette, and both were wrong.
    #
    # The axis is the ear's own normal. Splayed barely off forward
    # (0.42, 0.06, 0.90) the disc lay almost in the screen plane head-on and
    # went edge-on in profile, which put a fin on top of the skull from the
    # side — the same failure the rounded rim was meant to cure, one level up.
    # Halfway out costs the same foreshortening either way and reads round
    # from both.
    #
    # The centre was typed in as coordinates, so it drifted inside the skull
    # the moment the skull changed and left a sickle of rim showing. Solve it
    # off the head map instead, the way the beetle's legs are solved off the
    # shell: a point on the surface, lifted along the axis. Now the ear sits
    # on the head whatever the head does next.
    ax = (side * 0.720, 0.185, 0.668)
    L = math.sqrt(sum(q * q for q in ax))
    ax = tuple(q / L for q in ax)
    root = bear_head_pt(side * EAR_AZ, EAR_EL)
    c = tuple(root[i] + ax[i] * EAR_LIFT for i in range(3))
    u = (ax[2], 0.0, -ax[0])
    Lu = math.sqrt(u[0] ** 2 + u[2] ** 2) or 1.0
    u = (u[0] / Lu, 0.0, u[2] / Lu)
    v = (ax[1] * u[2] - ax[2] * u[1],
         ax[2] * u[0] - ax[0] * u[2],
         ax[0] * u[1] - ax[1] * u[0])
    return c, ax, u, v


EAR_R = 0.104                     # a quarter of the head's width, as drawn
EAR_IN = 0.54                     # the inner ear's share of the radius


def _ear_front(rho):
    """How far the front face stands off the disc plane, at radius `rho`.

    Not a plain dome: a rim ridge with a dish inside it. A convex front has
    nowhere to put the inner ear except on top of it, where it reads as a
    button stuck to the outside; a cupped one has a hollow that the pale
    patch sits down in while still standing clear of the surface.
    """
    return 0.074 * math.sqrt(max(0.0, 1 - rho * rho)) \
        - 0.040 * max(0.0, 1 - (rho / 0.74) ** 2)


def bear_ear(side):
    """A round flap with a rounded rim.

    A lens whose two faces meet at a sharp rim looks right head-on and turns
    into a fin in profile, which is what the first cut did. `sqrt(1 - rho^2)`
    brings both faces into the rim with a vertical tangent, so the edge is
    round from every angle. The fold goes in bear_ear_inner, not here.
    """
    c, ax, u, v = _ear_frame(side)

    def pt(rho, th, off):
        a = EAR_R * rho * math.cos(th)
        b = EAR_R * rho * math.sin(th) * 1.06
        return tuple(c[i] + u[i] * a + v[i] * b + ax[i] * off for i in range(3))

    m = Mesh()
    NT, NR = 18, 6
    for front in (True, False):
        rings = []
        for r in range(NR + 1):
            rho = r / float(NR)
            # the rim (rho = 1) is shared; the faces part company inside it
            off = _ear_front(rho) if front else \
                -0.086 * math.sqrt(max(0.0, 1 - rho * rho))
            rings.append([pt(rho, math.tau * j / NT, off) for j in range(NT)])
        idx = [[m.vert(*q) for q in ring] for ring in rings]
        for r in range(NR):
            a, b = idx[r], idx[r + 1]
            for j in range(NT):
                k = (j + 1) % NT
                if r == 0:
                    m.tri(a[0], b[j], b[k]) if front else m.tri(a[0], b[k], b[j])
                elif front:
                    m.quad(a[j], b[j], b[k], a[k])
                else:
                    m.quad(a[k], b[k], b[j], a[j])
    return m


def bear_ear_inner(side):
    """The pale patch that sits in the hollow of the ear.

    It has to stand *proud* of the outer ear, not follow it: laid on the same
    curve minus a few millimetres it ends up inside the flap, and the bear
    went a whole revision with an inner ear no camera ever saw. The clearance
    also has to beat A.ink (0.022) or the outline pass swallows it.
    """
    c, ax, u, v = _ear_frame(side)
    m = Mesh()
    NT, NR = 16, 5
    rings = []
    for r in range(NR + 1):
        rho = r / float(NR)
        off = _ear_front(rho * EAR_IN) + 0.028
        ring = []
        for j in range(NT):
            th = math.tau * j / NT
            a = EAR_R * EAR_IN * rho * math.cos(th)
            b = EAR_R * EAR_IN * rho * math.sin(th) * 1.06
            ring.append(tuple(c[i] + u[i] * a + v[i] * b + ax[i] * off for i in range(3)))
        rings.append(ring)
    idx = [[m.vert(*q) for q in ring] for ring in rings]
    for r in range(NR):
        a, b = idx[r], idx[r + 1]
        for j in range(NT):
            k = (j + 1) % NT
            if r == 0:
                m.tri(a[0], b[j], b[k])
            else:
                m.quad(a[j], b[j], b[k], a[k])
    return m


# ---- the body. A round one: this is a toy, not an animal. ------------------
# Three goes at this. A sphere first, then a barrel with real shoulders and a
# bear's shoulder hump, and now back to round on purpose.
#
# The middle one was anatomy, and anatomy was the wrong target. A hump over the
# shoulder blades is the thing that says "bear" on a nature programme; on a
# 1.5m toy with a head a third of its height it says "something is wrong with
# his back". The reference for this game is a stuffed bear, and a stuffed bear
# is an egg.
#
# So: widest low, a rounded bottom the legs come out from under, and nothing
# sticking out behind. Depth stays close to width, because the one thing worth
# keeping from the barrel is that he should not go flat when he turns.
# The sketch's shirt and trousers are one sack that comes down to 12% of his
# height, with only stubs of leg below it; the hips stay where the rig has them
BODY_LO, BODY_HI = -0.525, 0.300      # about the torso anchor, so y+0.22 .. y+1.04

# Widest low, and still wide at the top: a toy bear has no neck, the head sits
# straight on the body. Tapering to a collar left a ring of jersey trim showing
# under the chin like a bib.
BODY_W = [(0.00, 0.128), (0.05, 0.216), (0.11, 0.282), (0.19, 0.331),
          (0.28, 0.362), (0.36, 0.374), (0.48, 0.372), (0.60, 0.360),
          (0.70, 0.344), (0.80, 0.320), (0.88, 0.292), (0.94, 0.262),
          (1.00, 0.228)]
# depth about nine tenths of width all the way up — the one thing worth keeping
# from the barrel is that he should not go flat when he turns
BODY_D = [(0.00, 0.115), (0.05, 0.196), (0.11, 0.256), (0.19, 0.302),
          (0.28, 0.332), (0.36, 0.344), (0.48, 0.340), (0.60, 0.328),
          (0.70, 0.312), (0.80, 0.290), (0.88, 0.264), (0.94, 0.238),
          (1.00, 0.208)]
# the belly leads and the shoulders sit back a little, which is all the
# posture a shape like this needs
BODY_Z = [(0.00, 0.004), (0.34, 0.022), (0.62, 0.012), (0.85, -0.012),
          (1.00, -0.028)]


def bear_body_pt(a, t, out=0.0):
    """A point on the torso. `a` runs from the centre of the chest (0) round
    toward the character's left; `t` from the bottom (0) to the collar (1)."""
    y = BODY_LO + t * (BODY_HI - BODY_LO)
    hw = lerp_profile(t, BODY_W) + out
    hd = lerp_profile(t, BODY_D) + out
    cz = lerp_profile(t, BODY_Z)
    sa, ca = math.sin(a), math.cos(a)
    e = 2.02                            # round; anything squarer reads as a box
    x = math.copysign(abs(sa) ** (2.0 / e), sa) * hw
    z = math.copysign(abs(ca) ** (2.0 / e), ca) * hd

    # Shoulder caps. The sleeve is a capped cylinder hung at x = +/-0.33 with a
    # 0.112 radius, so its top is a flat disc reaching out to 0.44, and a round
    # body is narrower up there than a barrel was. The jersey comes out to meet
    # it; the rest of the join is the shoulder ball drawn over the joint.
    q = ((abs(x) - 0.300) / 0.185) ** 2 + ((y - 0.180) / 0.195) ** 2
    if q < 1.0:
        x += math.copysign(bump(q, 0.058), x)
    return (x, y, z + cz)


def bear_strip(a_c, a_r, t0, t1, out, na=7, nt=10):
    """A ribbon lying on the torso — a placket, a stripe."""
    m = Mesh()
    rows = []
    for i in range(nt + 1):
        t = t0 + (t1 - t0) * i / float(nt)
        rows.append([m.vert(*bear_body_pt(a_c + ((j / float(na)) * 2 - 1) * a_r, t, out))
                     for j in range(na + 1)])
    for i in range(nt):
        a, b = rows[i], rows[i + 1]
        for j in range(na):
            m.quad(a[j], a[j + 1], b[j + 1], b[j])
    return m


def bear_band(t0, t1, out, na=28, nt=4):
    """A full ring of the torso — the collar and the belt."""
    m = Mesh()
    rows = []
    for i in range(nt + 1):
        t = t0 + (t1 - t0) * i / float(nt)
        rows.append([m.vert(*bear_body_pt(math.tau * j / na, t, out)) for j in range(na)])
    for i in range(nt):
        a, b = rows[i], rows[i + 1]
        for j in range(na):
            k = (j + 1) % na
            m.quad(a[j], a[k], b[k], b[j])
    return m


def build_bear():
    out = {}

    head = surface_of(bear_head_pt)
    for side in (-1.0, 1.0):
        head.merge(bear_ear(side))
    out['bear_head'] = head

    inner = Mesh()
    for side in (-1.0, 1.0):
        inner.merge(bear_ear_inner(side))
    out['bear_earin'] = inner

    # the pale mask over the muzzle, and the two decal patches
    out['bear_muz'] = oval_patch(bear_head_pt, 0.0, SNOUT_EL, MUZ_AZ_R, MUZ_EL_R, 0.008)
    out['bear_face'] = uv_patch(bear_head_pt, 0.0, FACE_AZ_R, 0.0, FACE_EL_R, 0.009)
    out['bear_snout'] = uv_patch(bear_head_pt, 0.0, SNOUT_AZ_R, SNOUT_EL, SNOUT_EL_R, 0.011,
                                 n=16, mm=14)

    # Where the face art goes, in each patch's own 0..1 cell (y from the top),
    # so the atlas draws the eyes and the muzzle's outline where the skull put
    # them. A patch maps azimuth and elevation linearly, and the pale oval is
    # an ellipse in that same domain, so its outline is an ellipse in the cell.
    cu = lambda az, R: 0.5 + az / (2 * R)
    cv = lambda el, c, R: 0.5 - (el - c) / (2 * R)
    DATA.append('/* the bear\'s face layout, solved off the skull from the sketch */')
    DATA.append('const BEAR_FACE = { eyeX: %.4f, eyeY: %.4f, eyeR: %.4f, browY: %.4f,'
                % (cu(EYE_AZ, FACE_AZ_R) - 0.5, cv(EYE_EL, 0.0, FACE_EL_R),
                   EYE_AZ_R / (2 * FACE_AZ_R), cv(BROW_EL, 0.0, FACE_EL_R)))
    DATA.append('  muz: [0.5, 0.5, %.4f, %.4f] };' % (MUZ_AZ_R / (2 * SNOUT_AZ_R),
                                                      MUZ_EL_R / (2 * SNOUT_EL_R)))
    DATA.append('')

    body = Mesh()
    NA, NT = 28, 22
    idx = []
    for i in range(NT + 1):
        idx.append([body.vert(*bear_body_pt(math.tau * j / NA, i / float(NT)))
                    for j in range(NA)])
    for i in range(NT):
        a, b = idx[i], idx[i + 1]
        for j in range(NA):
            k = (j + 1) % NA
            body.quad(a[j], a[k], b[k], b[j])
    for ring, rev in ((idx[0], True), (idx[-1], False)):
        cx = sum(body.v[q][0] for q in ring) / NA
        cy = sum(body.v[q][1] for q in ring) / NA
        cz = sum(body.v[q][2] for q in ring) / NA
        c = body.vert(cx, cy, cz)
        for j in range(NA):
            k = (j + 1) % NA
            if rev:
                body.tri(c, ring[k], ring[j])
            else:
                body.tri(c, ring[j], ring[k])
    out['bear_body'] = body

    # The collar rides high enough that the head hides most of it. With no
    # neck to sit on there is nowhere for a jersey collar to go, and a full
    # ring of pale trim below the chin reads as a bib, not a collar.
    #
    # The belt sits below the widest point, where the top of the trousers
    # would be — on the waist of an egg it reads as a seam cutting him in half
    out['bear_collar'] = bear_band(0.935, 0.995, 0.008)
    out['bear_belt'] = bear_band(0.300, 0.350, 0.008)   # 69% down, as drawn
    # The sketch's jersey is a pinstripe: a dozen thin lines all the way
    # round, and one dark placket down the front. Four fat stripes in the
    # jersey's own colour read as corduroy.
    out['bear_placket'] = bear_strip(0.0, 0.036, 0.36, 0.93, 0.007)
    stripes = Mesh()
    for k in range(1, 16):
        stripes.merge(bear_strip(math.tau * k / 16, 0.017, 0.36, 0.93, 0.006, na=2))
    out['bear_stripe'] = stripes
    return out


# ---------------------------------------------------------------- headwear
# Shared by every species that wears one, which is why it was left alone for
# so long and why it ended up the weakest thing on the bear: a half-sphere
# 13cm tall with a rectangular slab for a bill. Head-on it was a dark bar
# across the brow; from the side, a plate with a plank nailed to it.
#
# A cap is two things the primitives cannot give. The crown has a lip where
# the sweatband is and a shoulder where the panels turn over, so it is not a
# dome. And the bill is curved twice — down along its length and up across
# its width — which is the whole reason a real one reads as a bill from any
# angle instead of disappearing edge-on.

CAP_RX, CAP_RZ, CAP_CZ = 0.378, 0.336, 0.012      # the crown at the sweatband
CAP_RIM = 0.222                                   # and where that sits
# t -> (height, how much of the base radius is left)
CAP_PROF = [(0.00, 0.222, 1.000), (0.11, 0.262, 1.012), (0.28, 0.322, 0.982),
            (0.47, 0.380, 0.918), (0.66, 0.428, 0.808), (0.82, 0.462, 0.632),
            (0.93, 0.484, 0.398), (1.00, 0.496, 0.000)]


def _cap_ring(y, s, n, out=0.0):
    ring = []
    for j in range(n):
        a = math.tau * j / n
        sa, ca = math.sin(a), math.cos(a)
        e = 2.02                        # rounder in plan than the skull is
        x = math.copysign(abs(sa) ** (2.0 / e), sa) * (CAP_RX * s + out)
        z = math.copysign(abs(ca) ** (2.0 / e), ca) * (CAP_RZ * s + out)
        ring.append((x, y, z + CAP_CZ))
    return ring


def cap_crown(n=26):
    """The crown, closed underneath by the sweatband so it has no open mouth."""
    rings = []
    # the sweatband, turned under and in: without it you can see up inside the
    # hat from any low camera, and the game has plenty of those
    rings.append(_cap_ring(CAP_RIM - 0.052, 0.905, n))
    for t, y, sc in CAP_PROF:
        rings.append(_cap_ring(y, sc, n))
    m = Mesh()
    idx = [[m.vert(*q) for q in r] for r in rings]
    for i in range(len(idx) - 1):
        a, b = idx[i], idx[i + 1]
        for j in range(n):
            k = (j + 1) % n
            m.quad(a[j], a[k], b[k], b[j])
    # the crown closes to a point at the top, and the underside to a disc
    ring = idx[0]
    c = m.vert(0.0, CAP_RIM - 0.062, CAP_CZ)
    for j in range(n):
        m.tri(c, ring[(j + 1) % n], ring[j])
    return m


def cap_bill(spread=0.98, reach=0.248, droop=0.044, curl=0.062, thick=0.058,
             nu=16, nv=7):
    """The bill: a sheet curved down its length and up across its width.

    Both curves matter. Without the droop it is a shelf; without the curl the
    sides sit level with the middle and the thing goes invisible the moment
    the camera is anywhere near its plane — which, on a ball player, is most
    of the time. `reach` tapers toward the corners, so the outline is a
    rounded tongue rather than a rectangle with the ends sawn off.

    `thick` has a floor that has nothing to do with caps: the outline pass
    pushes every face out along its normal by A.ink, so a sheet thinner than
    two of those is two black shells with no fill left between them. At a
    realistic 34mm the bill came out a solid black band across the eyes.
    """
    def surf(u, v):
        a = u * spread
        L = reach * (1.0 - 0.40 * u * u)
        r = 1.0 + L * v / max(CAP_RX, 1e-6)
        w = max(0.0, v)
        sa, ca = math.sin(a), math.cos(a)
        x = sa * (CAP_RX * 0.995) * r
        z = ca * (CAP_RZ * 0.995) * r + CAP_CZ
        # off the lip, not off the bottom of the sweatband. Hung lower and
        # drooped like a real one it crossed the eyes from any camera below
        # the head, which is most of them, and a bear you cannot see the eyes
        # of is not cute, it is a silhouette in a hat.
        y = CAP_RIM + 0.026 - droop * (w ** 1.55) + curl * u * u * w
        return (x, y, z)

    m = Mesh()
    top, bot = [], []
    for i in range(nv + 1):
        # the root starts inside the crown rather than flush against it: two
        # surfaces that meet exactly z-fight, and along the sweatband that
        # showed up as a row of dark dashes whenever the camera got under him
        v = -0.20 + (i / float(nv)) * 1.20
        rt, rb = [], []
        for j in range(nu + 1):
            u = (j / float(nu)) * 2 - 1
            p = surf(u, v)
            rt.append(m.vert(*p))
            rb.append(m.vert(p[0], p[1] - thick, p[2]))
        top.append(rt)
        bot.append(rb)
    for i in range(nv):
        for j in range(nu):
            m.quad(top[i][j], top[i][j + 1], top[i + 1][j + 1], top[i + 1][j])
            m.quad(bot[i + 1][j], bot[i + 1][j + 1], bot[i][j + 1], bot[i][j])
    for i in range(nv):                       # the two side edges
        m.quad(top[i][0], top[i + 1][0], bot[i + 1][0], bot[i][0])
        m.quad(bot[i][nu], bot[i + 1][nu], top[i + 1][nu], top[i][nu])
    for j in range(nu):                       # the leading edge, and the root
        m.quad(top[nv][j], top[nv][j + 1], bot[nv][j + 1], bot[nv][j])
        m.quad(bot[0][j], bot[0][j + 1], top[0][j + 1], top[0][j])
    return m


def build_cap():
    # Both are closed solids, so the winding is oriented()'s problem, not one
    # for a human to reason about ring by ring. The bill came out inside-out
    # on the first cut and rendered as a solid black band — the fill culled,
    # the outline shell all that was left.
    return {'cap_crown': oriented(cap_crown()), 'cap_bill': oriented(cap_bill())}


# ------------------------------------------------------------------- beetle
# A male Trypoxylus dichotomus, as the living insect: horizontal on six legs,
# body low, head down in front, the horn rising out of it.
#
# Canonical pose: the character's own frame. +z is forward (the horn), +y up
# with 0 on the ground, +x his LEFT side. Scale 1 is life size on the field:
# 1.36m from the tip of the wing cases to the front of the head, the back
# 0.80m up, the horn tips 1.33m up.
#
# The three tagmata are three separate shells — head, pronotum, elytra — in
# the real proportions (elytra : pronotum : head = 58 : 27 : 15). Every one of
# them is the same kind of surface (`bee_shell`): a superelliptic section that
# rises from a margin to a dome above and drops a little way below it, read off
# smooth profiles along the body, collapsing to a point at both ends so there
# are no caps to shade wrong. The legs are drawn by 30-actors.js out of baked
# bones (coxa, femur, tibia, tarsus) that it places by IK, feet on the ground.

def _sup(v, e):
    return math.copysign(abs(v) ** (2.0 / e), v)


def _ends(t, a, b):
    """1 in the middle, rounding to 0 over the first `a` and last `b` of t."""
    k = 1.0
    if a > 0 and t < a:
        k *= math.sqrt(max(0.0, 1.0 - ((a - t) / a) ** 2))
    if b > 0 and t > 1.0 - b:
        k *= math.sqrt(max(0.0, 1.0 - ((t - (1.0 - b)) / b) ** 2))
    return k


# z0 + dz*t along the body; half width; dome top; margin (the widest line);
# how far the shell drops below the margin; exponent; rounding at the ends;
# sutural groove depth
BEE_E = dict(z0=0.10, dz=-0.91, e=2.15, ends=(0.05, 0.085), groove=0.010,
             W=[(0.0, 0.272), (0.06, 0.312), (0.16, 0.336), (0.35, 0.352), (0.56, 0.360),
                (0.72, 0.346), (0.84, 0.305), (0.92, 0.240), (0.97, 0.180), (1.0, 0.130)],
             top=[(0.0, 0.735), (0.10, 0.785), (0.30, 0.805), (0.50, 0.800), (0.68, 0.772),
                  (0.82, 0.718), (0.92, 0.645), (1.0, 0.560)],
             mar=[(0.0, 0.440), (0.5, 0.425), (0.85, 0.432), (1.0, 0.465)],
             hb=[(0.0, 0.045), (1.0, 0.045)])
BEE_P = dict(z0=0.035, dz=0.425, e=2.25, ends=(0.06, 0.16), groove=0.0,
             W=[(0.0, 0.288), (0.3, 0.300), (0.6, 0.288), (0.8, 0.252), (0.92, 0.208), (1.0, 0.175)],
             top=[(0.0, 0.765), (0.3, 0.800), (0.55, 0.805), (0.75, 0.775), (0.9, 0.700), (1.0, 0.600)],
             mar=[(0.0, 0.445), (1.0, 0.440)],
             hb=[(0.0, 0.070), (1.0, 0.070)])
BEE_V = dict(z0=-0.78, dz=1.29, e=2.2, ends=(0.08, 0.10), groove=0.0,
             W=[(0.0, 0.150), (0.1, 0.215), (0.3, 0.272), (0.55, 0.268), (0.75, 0.222),
                (0.9, 0.172), (1.0, 0.120)],
             top=[(0.0, 0.540), (0.3, 0.520), (0.7, 0.500), (1.0, 0.500)],
             mar=[(0.0, 0.430), (0.3, 0.420), (0.7, 0.405), (1.0, 0.400)],
             hb=[(0.0, 0.040), (0.12, 0.105), (0.3, 0.150), (0.6, 0.150), (0.85, 0.112), (1.0, 0.065)])
BEE_H = dict(z0=0.42, dz=0.27, e=2.3, ends=(0.15, 0.30), groove=0.0,
             W=[(0.0, 0.140), (0.4, 0.172), (0.75, 0.160), (1.0, 0.115)],
             top=[(0.0, 0.495), (1.0, 0.445)],
             mar=[(0.0, 0.400), (1.0, 0.355)],
             hb=[(0.0, 0.080), (1.0, 0.060)])


def bee_shell(P, t, th, out=0.0):
    """`t` along the body, `th` round the section from the top (0) toward
    his left (+x)."""
    sp = smooth_profile
    k = _ends(t, *P['ends'])
    W = sp(t, P['W']) * k
    mar = sp(t, P['mar'])
    up = (sp(t, P['top']) - mar) * k
    dn = sp(t, P['hb']) * k
    e = P['e']
    s, c = math.sin(th), math.cos(th)
    x = (W + out) * _sup(s, e)
    y = mar + ((up + out) if c >= 0 else (dn + out)) * _sup(c, e)
    if P['groove'] and c > 0:
        y -= P['groove'] * math.exp(-(x / 0.03) ** 2) * k
    return (x, y, P['z0'] + P['dz'] * t)


def bee_lift(P, t, th, out):
    """The surface pushed out along its true normal (not radially: CLAUDE.md)."""
    h = 1e-4
    p = bee_shell(P, t, th)
    a = bee_shell(P, t + h, th)
    b = bee_shell(P, t, th + h)
    u = [a[i] - p[i] for i in range(3)]
    v = [b[i] - p[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    L = math.sqrt(sum(q * q for q in n)) or 1.0
    n = [q / L for q in n]
    mar = smooth_profile(t, P['mar'])
    if n[0] * p[0] + n[1] * (p[1] - mar) < 0:
        n = [-q for q in n]
    return tuple(p[i] + n[i] * out for i in range(3))


def bee_plan(P, x, z, out):
    """The top surface at plan position (x, z), lifted along the normal."""
    t = (z - P['z0']) / P['dz']
    W = smooth_profile(t, P['W']) * _ends(t, *P['ends'])
    q = min(1.0, abs(x) / max(W, 1e-6)) ** (P['e'] / 2.0)
    return bee_lift(P, t, math.copysign(math.asin(min(1.0, q)), x), out)


def bee_tspace(n):
    # rings bunched toward both ends, where the shell turns fastest
    return [0.5 - 0.5 * math.cos(math.pi * i / float(n - 1)) for i in range(n)]


def bee_body(P, nt, na, out=0.0):
    rings = [[bee_shell(P, t, math.tau * j / na, out) for j in range(na)] for t in bee_tspace(nt)]
    return oriented(loft(rings, cap_start=False, cap_end=False))


def bee_strip(fn, nu, nv, inside):
    """An open patch from fn(u, v), u, v in 0..1, faced away from `inside`."""
    m = Mesh()
    g = [[m.vert(*fn(i / float(nu), j / float(nv))) for j in range(nv + 1)] for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            m.quad(g[i][j], g[i + 1][j], g[i + 1][j + 1], g[i][j + 1])
    return oriented_open(m, inside)


def bee_fan(fn, cx, cz, r, nr, nt, out, inside):
    """A round patch on a shell, in plan: a breeder's paint dot, dabbed on by
    hand, so its edge wanders a little."""
    m = Mesh()
    c = m.vert(*fn(cx, cz, out))
    rings = []
    for i in range(1, nr + 1):
        rings.append([])
        for j in range(nt):
            a = math.tau * j / nt
            rr = r * i / float(nr) * (1.0 + 0.10 * math.sin(3 * a + 0.7) + 0.06 * math.cos(5 * a))
            rings[-1].append(m.vert(*fn(cx + rr * math.cos(a), cz + rr * 1.12 * math.sin(a), out)))
    for j in range(nt):
        m.tri(c, rings[0][j], rings[0][(j + 1) % nt])
    for i in range(nr - 1):
        for j in range(nt):
            k = (j + 1) % nt
            m.quad(rings[i][j], rings[i + 1][j], rings[i + 1][k], rings[i][k])
    return oriented_open(m, inside)


def ell(cx, cy, cz, rx, ry, rz, nu=8, nv=10):
    """An ellipsoid, poles on y."""
    rings = []
    for i in range(nu + 1):
        a = math.pi * i / nu
        s = max(1e-4, math.sin(a))
        rings.append(section(cx, cy + math.cos(a) * ry, cz, s * rx, s * rz, nv, e=2.0))
    return oriented(loft(rings, cap_start=False, cap_end=False))


def sweep_e(path, radii, n, fx=1.0):
    """sweep() with the section stretched `fx` across the body (the horn is
    broader than it is deep at the root)."""
    rings = []
    for i, (px, py, pz) in enumerate(path):
        a = path[max(0, i - 1)]
        b = path[min(len(path) - 1, i + 1)]
        d = [b[k] - a[k] for k in range(3)]
        L = math.sqrt(sum(q * q for q in d)) or 1.0
        d = [q / L for q in d]
        u = [1.0, 0.0, 0.0]
        if abs(d[0]) > 0.94:
            u = [0.0, 1.0, 0.0]
        du = sum(u[k] * d[k] for k in range(3))
        u = [u[k] - d[k] * du for k in range(3)]
        Lu = math.sqrt(sum(q * q for q in u)) or 1.0
        u = [q / Lu for q in u]
        v = [d[1] * u[2] - d[2] * u[1], d[2] * u[0] - d[0] * u[2], d[0] * u[1] - d[1] * u[0]]
        r = radii[i]
        ring = []
        for k in range(n):
            ang = math.tau * k / n
            ca, sa = math.cos(ang) * r * fx, math.sin(ang) * r
            ring.append(tuple((px, py, pz)[q] + u[q] * ca + v[q] * sa for q in range(3)))
        rings.append(ring)
    return oriented(loft(rings))


def cubic(a, b, c, d, n):
    out = []
    for i in range(n):
        t = i / float(n - 1)
        u = 1.0 - t
        out.append(tuple(u ** 3 * a[k] + 3 * u * u * t * b[k] + 3 * u * t * t * c[k] + t ** 3 * d[k]
                         for k in range(3)))
    return out


def taper(r0, r1, n, p=1.0):
    return [r0 + (r1 - r0) * (i / float(n - 1)) ** p for i in range(n)]


# Bones, authored from the joint down -Y at life size (30-actors.js scales the
# length to what the IK asks for). +Z is the bone's outer edge, where the
# teeth and spines go; +X is across the leg's plane.
BEE_FEM, BEE_TIB, BEE_TAR = 0.30, 0.30, 0.22
# [z of the coxa, femur, tibia, tarsus]: fore, mid, hind
BEE_ROWS = [(0.375, 0.26, 0.27, 0.20), (0.060, 0.26, 0.27, 0.19), (-0.140, 0.30, 0.31, 0.23)]


def bee_bone(L, rx, rz, nt=14, na=10, ends=(0.10, 0.10)):
    rings = []
    for i in range(nt):
        t = i / float(nt - 1)
        k = _ends(t, *ends)
        rings.append(section(0.0, -L * t, 0.0, max(1e-4, rx(t) * k), max(1e-4, rz(t) * k), na, e=2.2))
    return oriented(loft(rings, cap_start=False, cap_end=False))


def bee_spike(base, d, length, r0, n=6):
    e = tuple(base[k] + d[k] * length for k in range(3))
    return sweep_e([tuple(base[k] + (e[k] - base[k]) * i / 3.0 for k in range(3)) for i in range(4)],
                   taper(r0, r0 * 0.18, 4), n)


def _unit(v):
    L = math.sqrt(sum(q * q for q in v)) or 1.0
    return tuple(q / L for q in v)


def build_beetle():
    out = {}
    out['bee_elytra'] = bee_body(BEE_E, 26, 32)
    out['bee_prono'] = bee_body(BEE_P, 18, 28)
    out['bee_venter'] = bee_body(BEE_V, 16, 18)
    out['bee_head'] = bee_body(BEE_H, 11, 18)

    # the sutural line down the middle of the back, and the scutellum at the
    # top of it: open strips a hair off the lacquer, so no outline swallows them
    out['bee_suture'] = bee_strip(
        lambda u, v: bee_plan(BEE_E, -0.008 + 0.016 * v, 0.03 - 0.86 * u, 0.003),
        34, 1, (0.0, 0.5, -0.3))
    out['bee_scut'] = bee_strip(
        lambda u, v: bee_plan(BEE_E, (v * 2 - 1) * 0.052 * (1 - u) ** 0.9, 0.036 - 0.10 * u, 0.004),
        6, 4, (0.0, 0.5, -0.3))
    # the rolled rim of each wing case (epipleuron)
    rim = Mesh()
    for s in (-1.0, 1.0):
        ts = [0.05 + 0.88 * i / 19.0 for i in range(20)]
        path = []
        for t in ts:
            x, y, z = bee_shell(BEE_E, t, s * math.pi / 2)
            path.append((x - s * 0.010, y + 0.006, z))
        rad = [0.019 * _ends(i / 19.0, 0.12, 0.2) + 0.004 for i in range(20)]
        rim.merge(sweep_e(path, rad, 6))
    out['bee_rim'] = rim
    # the sternites, seen when he goes over on his back
    st = Mesh()
    for z in (-0.64, -0.53, -0.42, -0.31, -0.19):
        t = (z - BEE_V['z0']) / BEE_V['dz']
        st.merge(bee_strip(lambda u, v, t=t: bee_lift(BEE_V, t - 0.006 + 0.012 * v,
                                                      math.pi + (u * 2 - 1) * 1.05, 0.004),
                           12, 1, (0.0, 0.45, z)))
    out['bee_stern'] = st
    # the team's mark: a dab of paint on the right wing case near the shoulder,
    # the way a breeder marks his beetles. It is all he wears.
    out['bee_mark'] = bee_fan(lambda x, z, o: bee_plan(BEE_E, x, z, o),
                              -0.165, -0.07, 0.050, 2, 18, 0.005, (0.0, 0.5, -0.2))

    # The head horn: forward off the front of the head, then up, then forked
    # left and right, and each fork forked again. Four tips. The thoracic horn
    # is the short one off the front of the pronotum, forked at its tip.
    horn = Mesh()
    shaft = cubic((0.0, 0.42, 0.590), (0.0, 0.56, 0.850), (0.0, 0.84, 0.990), (0.0, 1.06, 0.985), 16)
    # slimmer than a pillar: narrowest two thirds of the way up, swelling
    # again into the fork
    hr = [0.070 - 0.022 * math.sin(math.pi * 0.5 * min(1.0, t / 0.62)) + (0.010 * ((t - 0.62) / 0.38) ** 2 if t > 0.62 else 0.0)
          for t in [i / 15.0 for i in range(16)]]
    horn.merge(sweep_e(shaft, hr, 12, 1.18))
    top = shaft[-1]
    for s in (-1.0, 1.0):
        q = (s * 0.110, 1.180, 0.975)
        br = bez(top, (s * 0.030, 1.145, 1.000), q, 6)
        horn.merge(sweep_e(br, taper(0.052, 0.037, 6), 10))
        for e, m in (((s * 0.130, 1.325, 0.900), (s * 0.124, 1.268, 0.950)),
                     ((s * 0.215, 1.240, 1.060), (s * 0.170, 1.225, 1.020))):
            horn.merge(sweep_e(bez(q, m, e, 6), taper(0.036, 0.014, 6), 8))
    th = bez((0.0, 0.740, 0.340), (0.0, 0.812, 0.440), (0.0, 0.832, 0.530), 7)
    horn.merge(sweep_e(th, taper(0.076, 0.042, 7), 12, 1.25))
    for s in (-1.0, 1.0):
        horn.merge(sweep_e(bez(th[-1], (s * 0.020, 0.842, 0.560), (s * 0.046, 0.850, 0.590), 5),
                           taper(0.037, 0.015, 5), 8))
    out['bee_horn'] = horn

    # Compound eyes: on the sides of the head, black, sunk half into it.
    eyes = Mesh()
    hx, hy, hz = bee_shell(BEE_H, 0.55, math.pi / 2)
    for s in (-1.0, 1.0):
        eyes.merge(ell(s * (hx - 0.010), hy + 0.006, hz, 0.032, 0.044, 0.048, 7, 10))
    out['bee_eye'] = eyes
    # clypeus and mouthparts: the plate under the horn, the palps, and the
    # orange brush he drinks sap with
    mouth = Mesh()
    mouth.merge(ell(0.0, 0.336, 0.652, 0.072, 0.022, 0.046, 6, 12))
    for s in (-1.0, 1.0):
        mouth.merge(sweep_e(bez((s * 0.045, 0.305, 0.635), (s * 0.068, 0.280, 0.680),
                                (s * 0.074, 0.232, 0.700), 5), taper(0.014, 0.008, 5), 6))
    out['bee_mouth'] = mouth
    out['bee_brush'] = ell(0.0, 0.298, 0.640, 0.030, 0.020, 0.022, 5, 8)
    # antennae: elbowed, ending in a club of three leaves
    ant = Mesh()
    ax, ay, az = bee_shell(BEE_H, 0.86, math.pi / 2 + 0.35)
    for s in (-1.0, 1.0):
        b0 = (s * (ax - 0.005), ay, az)
        el = (b0[0] + s * 0.055, b0[1] - 0.020, b0[2] + 0.030)
        cl = (el[0] + s * 0.036, el[1] + 0.004, el[2] + 0.032)
        ant.merge(sweep_e([b0, el], [0.011, 0.010], 6))
        ant.merge(sweep_e([el, cl], [0.008, 0.008], 6))
        for i in range(3):
            ant.merge(ell(cl[0] + s * (0.004 + 0.011 * i), cl[1] + 0.004, cl[2] + 0.012 + 0.004 * i,
                          0.0065, 0.026, 0.034, 4, 6))
    out['bee_ant'] = ant

    # the bones
    out['bee_coxa'] = ell(0.0, 0.0, 0.0, 0.062, 0.052, 0.066, 7, 10)
    out['bee_fem'] = bee_bone(BEE_FEM, lambda t: 0.030 + 0.010 * math.sin(math.pi * t),
                              lambda t: 0.044 + 0.024 * math.sin(math.pi * t), 12, 10)
    tib = bee_bone(BEE_TIB, lambda t: 0.025 + 0.010 * t, lambda t: 0.026 + 0.024 * t, 10, 10)
    for t in (0.55, 0.80):                             # spines down the outer edge
        tib.merge(bee_spike((0.0, -BEE_TIB * t, 0.024 + 0.020 * t), _unit((0.0, -0.55, 1.0)), 0.052, 0.014))
    for s in (-1.0, 1.0):                              # and the spurs at the end
        tib.merge(bee_spike((s * 0.012, -BEE_TIB * 0.96, 0.012), _unit((s * 0.35, -1.0, 0.25)), 0.062, 0.013))
    out['bee_tib'] = tib
    # the fore tibia digs: broad, flat, three teeth along the outer edge
    tibf = bee_bone(BEE_TIB, lambda t: 0.024 + 0.006 * t, lambda t: 0.028 + 0.042 * t ** 1.5, 10, 10)
    for t, g in ((0.60, 0.85), (0.79, 0.95), (0.97, 1.0)):
        rz = 0.028 + 0.042 * t ** 1.5
        tibf.merge(bee_spike((0.0, -BEE_TIB * t, rz * 0.75), _unit((0.0, -0.45, 1.0)), 0.072 * g, 0.024 * g))
    out['bee_tibf'] = tibf
    # five beads of tarsus and a pair of claws
    tar = Mesh()
    y = 0.0
    for i, f in enumerate((0.17, 0.15, 0.15, 0.15, 0.38)):
        L = BEE_TAR * f
        r = 0.022 if i < 4 else 0.019
        tar.merge(ell(0.0, y - L * 0.5, 0.0, r, L * 0.60, r * 0.85, 5, 7))
        y -= L
    for s in (-1.0, 1.0):
        tar.merge(sweep_e(bez((s * 0.004, y + 0.006, 0.0), (s * 0.020, y - 0.026, 0.004),
                              (s * 0.026, y - 0.044, -0.018), 4), taper(0.011, 0.003, 4), 5))
    out['bee_tars'] = tar

    # Where the legs hang: the coxae sit in sockets on the underside, solved
    # against the venter's own profile so they move with it.
    rows = []
    for z, lf, lt, ls in BEE_ROWS:
        t = (z - BEE_V['z0']) / BEE_V['dz']
        x, y, _ = bee_shell(BEE_V, t, math.pi * 0.70)
        rows.append((x, y, z, lf, lt, ls))
    DATA.append('/* beetle coxae, solved on the underside: [x, y, z, femur, tibia, tarsus] */')
    DATA.append('const BEE_LEG = [%s];' % ', '.join('[%.4g, %.4g, %.4g, %.3g, %.3g, %.3g]' % r for r in rows))
    DATA.append('const BEE_BONE = [%.3g, %.3g, %.3g];' % (BEE_FEM, BEE_TIB, BEE_TAR))
    DATA.append('')
    return out


# ------------------------------------------------------------------- rabbit
# The head and the jersey are the `mesh:` path's business. What is baked here
# is everything that path does not reach and that a rabbit cannot do without:
# the ears, the haunches, the long hind feet, and the tail.
#
# Canonical pose: the character's own frame — +z is the face, +y is up, +x is
# the LEFT half of the body. Each piece is authored around the joint it hangs
# from, at the size it is drawn, so 30-actors.js places it with the same
# numbers it used for the sphere it replaces. Scale 1 is life size.

RAB_EAR_LEN = 0.88
RAB_EAR_W = [(0.00, 0.052), (0.08, 0.070), (0.22, 0.082), (0.42, 0.086),
             (0.60, 0.081), (0.76, 0.068), (0.88, 0.046), (0.95, 0.024),
             (1.00, 0.005)]
RAB_EAR_T = [(0.00, 0.021), (0.30, 0.019), (0.70, 0.015), (0.90, 0.010),
             (1.00, 0.003)]
RAB_EAR_C = [(0.00, 0.012), (0.18, 0.052), (0.45, 0.072), (0.72, 0.062),
             (0.90, 0.030), (1.00, 0.006)]
RAB_EAR_Z = [(0.00, -0.005), (0.35, -0.030), (0.70, -0.036), (1.00, -0.020)]

# The haunch, hanging off the hip joint: deep rather than wide, and carried
# behind the leg. That mass is most of what makes a rabbit a rabbit, and it is
# below the belt, so it stays out of the way of the jersey.
# (y from the hip joint, half width, half depth, how far back the middle sits)
# `lerp_profile` reads keys in ascending order, so this table runs ankle-end
# first. Written the other way round it silently returns the first value for
# every ring, and the haunch comes out a pencil.
RAB_THIGH = [(-0.245, 0.078, 0.082, -0.004), (-0.200, 0.100, 0.112, -0.016),
             (-0.140, 0.124, 0.150, -0.030), (-0.070, 0.138, 0.168, -0.040),
             (0.010, 0.120, 0.135, -0.026), (0.075, 0.075, 0.080, -0.010)]

# The hind foot, from the ankle forward: long, flat, and turned up at the toe.
# (z along the foot, half width, top, sole)
RAB_FOOT = [(-0.105, 0.050, 0.026, -0.062), (-0.065, 0.079, 0.082, -0.096),
            (-0.010, 0.096, 0.094, -0.110), (0.055, 0.103, 0.064, -0.112),
            (0.140, 0.104, 0.030, -0.110), (0.215, 0.098, 0.006, -0.102),
            (0.270, 0.078, -0.016, -0.090), (0.305, 0.042, -0.032, -0.072),
            (0.325, 0.013, -0.044, -0.058)]


def oriented(m):
    """Flip a closed solid if it came out wound inside-out.

    Back faces are culled, so a mesh wound the wrong way is not an error — it
    is simply invisible, which is a miserable thing to debug. Signed volume
    settles it without anyone having to reason about ring order.
    """
    v = 0.0
    for a, b, c in m.f:
        pa, pb, pc = m.v[a], m.v[b], m.v[c]
        v += (pa[0] * (pb[1] * pc[2] - pb[2] * pc[1])
              - pa[1] * (pb[0] * pc[2] - pb[2] * pc[0])
              + pa[2] * (pb[0] * pc[1] - pb[1] * pc[0])) / 6.0
    if v < 0.0:
        m.f = [(a, c, b) for a, b, c in m.f]
    return m


def cupped(y, cz, w, th, cup, n=12):
    """One slice of an ear: a lens, bowed so the hollow faces forward.

    `cup` turns the two edges toward +z and sinks the middle between them,
    which is the whole difference between an ear and a paddle.
    """
    pts = []
    for k in range(n):
        a = (k / float(n)) * math.tau
        u = math.cos(a)
        pts.append((u * w, y, cz + cup * (u * u - 1.0 / 3.0) + th * math.sin(a)))
    return pts


def ring_xy(z, hw, top, bot, n=12, e=2.5):
    """A superelliptical slice in the x/y plane, for the foot — which is
    stacked along z rather than up."""
    cy, hh = (top + bot) * 0.5, (top - bot) * 0.5
    pts = []
    for k in range(n):
        a = (k / float(n)) * math.tau
        ca, sa = math.cos(a), math.sin(a)
        pts.append((math.copysign(abs(ca) ** (2.0 / e), ca) * hw,
                    cy + math.copysign(abs(sa) ** (2.0 / e), sa) * hh, z))
    return pts


def build_rabbit():
    out = {}
    W = lambda t: lerp_profile(t, RAB_EAR_W)
    TH = lambda t: lerp_profile(t, RAB_EAR_T)
    CU = lambda t: lerp_profile(t, RAB_EAR_C)
    CZ = lambda t: lerp_profile(t, RAB_EAR_Z)
    N = 20

    # The ears stay their own parts rather than going into the head mesh: they
    # are half the silhouette, they lean back when he runs, and the inside is
    # a different colour. A bear's ears can be part of its skull; these cannot.
    rings = []
    for i in range(N):
        t = i / float(N - 1)
        rings.append(cupped(t * RAB_EAR_LEN, CZ(t), W(t), TH(t), CU(t)))
    out['rabbit_ear'] = oriented(loft(rings))

    # The pink inside is a thinner lens lying in the hollow. It has to stand
    # proud of the ear or the outline pass eats it, but it stays under the rim
    # the cup turns up, so it still reads as being inside the ear.
    rings = []
    for i in range(16):
        t = 0.10 + 0.82 * i / 15.0
        cup, th = CU(t) * 0.72, 0.010
        cz = CZ(t) - CU(t) / 3.0 + TH(t) + 0.030 + cup / 3.0 - th
        rings.append(cupped(t * RAB_EAR_LEN, cz, W(t) * 0.62, th, cup, 10))
    out['rabbit_earin'] = oriented(loft(rings))

    w, d, sh = [[(k[0], k[i]) for k in RAB_THIGH] for i in (1, 2, 3)]
    lo, hi, rings = RAB_THIGH[0][0], RAB_THIGH[-1][0], []
    for i in range(14):
        y = lo + (hi - lo) * i / 13.0
        rings.append(section(0.0, y, lerp_profile(y, sh), lerp_profile(y, w),
                             lerp_profile(y, d), 14, e=2.30))
    out['rabbit_thigh'] = oriented(loft(rings))

    out['rabbit_foot'] = oriented(loft([ring_xy(*r) for r in RAB_FOOT]))

    # The cotton tail. One puff was a ball and it read as a ball, so this one
    # grows its lobes out of the radius instead of being six balls merged —
    # same puff, a fifth of the vertices, and no surfaces buried inside it.
    rings, NS, NR = [], 12, 11
    for i in range(NR + 1):
        a = math.pi * i / NR
        cy, sr = math.cos(a), math.sin(a)
        ring = []
        for k in range(NS):
            b = (k / float(NS)) * math.tau
            r = 0.116 * (1.0 + 0.24 * math.sin(3.0 * b) * sr
                        + 0.11 * math.sin(2.0 * b + 1.1) * sr + 0.13 * cy * cy)
            ring.append((math.cos(b) * sr * r, cy * r, math.sin(b) * sr * r))
        rings.append(ring)
    out['rabbit_tail'] = oriented(loft(rings))
    out.update(build_rabbit_torso())
    return out


# The torso. The head is a sphere that the child's drawing is projected onto,
# so it stays; what is baked is the little egg under it. Pear rather than
# barrel: widest at the hips, so the haunches flow out of it instead of
# hanging under a ball, and still wide where it disappears into the head —
# a rabbit toy has no neck any more than the bear does.
# About the torso anchor (y+0.74), so the hem is at y+0.34 and the top is
# buried in the head at y+1.10.
# Round 2: the hem came down to y+0.20 so the haunches are swallowed when he
# stands and only a little fluff and the big shoes show; the widest point
# went down with it (y+0.43) and the shoulders narrowed, so the longer sack
# reads as a squat pear and not a capsule. The chin sits at y+0.95.
RAB_LO, RAB_HI = -0.540, 0.320
RAB_W = [(0.00, 0.100), (0.03, 0.192), (0.07, 0.250), (0.12, 0.290),
         (0.19, 0.316), (0.27, 0.324), (0.36, 0.315), (0.46, 0.292),
         (0.56, 0.260), (0.66, 0.224), (0.75, 0.196), (0.83, 0.176),
         (0.90, 0.161), (0.96, 0.150), (1.00, 0.142)]
RAB_D = 0.90                         # depth as a share of width: an egg, not a board
RAB_Z = [(0.00, 0.000), (0.35, 0.016), (0.62, 0.012), (1.00, -0.010)]


def rab_body_pt(a, t, out=0.0):
    """`a` from the middle of the chest (0) round toward his left, `t` from
    the hem (0) to the top (1)."""
    y = RAB_LO + t * (RAB_HI - RAB_LO)
    hw = lerp_profile(t, RAB_W)
    hd = hw * RAB_D + out
    hw += out
    sa, ca = math.sin(a), math.cos(a)
    return (sa * hw, y, ca * hd + lerp_profile(t, RAB_Z))


def rab_patch(fn, a0, a1, t0, t1, out, na, nt, closed=False):
    """A piece of the torso's own surface, lifted along its normal (the
    surface is round enough that the radial offset rab_body_pt does is it)."""
    m = Mesh()
    cols = na if closed else na + 1
    rows = [[m.vert(*fn(a0 + (a1 - a0) * j / float(na), t0 + (t1 - t0) * i / float(nt), out))
             for j in range(cols)] for i in range(nt + 1)]
    for i in range(nt):
        for j in range(na):
            k = (j + 1) % cols if closed else j + 1
            m.quad(rows[i][j], rows[i][k], rows[i + 1][k], rows[i + 1][j])
    return m


def rab_dot(a_c, t_c, r, out, n=10):
    """A flat round button lying on the torso: a fan in (arc, height)."""
    m = Mesh()
    H = RAB_HI - RAB_LO
    w = lerp_profile(t_c, RAB_W)
    c = m.vert(*rab_body_pt(a_c, t_c, out))
    ring = [m.vert(*rab_body_pt(a_c + r * math.cos(math.tau * k / n) / w,
                                t_c + r * math.sin(math.tau * k / n) / H, out))
            for k in range(n)]
    for k in range(n):
        m.tri(c, ring[k], ring[(k + 1) % n])
    return m


def build_rabbit_torso():
    out = {}
    out['rabbit_body'] = oriented(rab_patch(rab_body_pt, 0.0, math.tau, 0.0, 1.0, 0.0,
                                            20, 17, closed=True))
    b = out['rabbit_body']
    for ring_t, rev in ((0.0, True), (1.0, False)):     # close hem and top
        nr = [i for i, v in enumerate(b.v) if abs(v[1] - (RAB_LO + ring_t * (RAB_HI - RAB_LO))) < 1e-9]
        c = b.vert(sum(b.v[i][0] for i in nr) / len(nr), b.v[nr[0]][1],
                   sum(b.v[i][2] for i in nr) / len(nr))
        for j in range(len(nr)):
            p, q = nr[j], nr[(j + 1) % len(nr)]
            b.tri(c, q, p) if rev else b.tri(c, p, q)
    oriented(b)

    # The trim is what lets white jersey over white fur read at all. A neckline
    # mostly under the chin (shows as a smile of pink below the head), a thin
    # belt where the hips start, a placket and three buttons.
    out['rabbit_collar'] = rab_patch(rab_body_pt, 0.0, math.tau, 0.79, 0.85, 0.007, 20, 1, True)
    out['rabbit_placket'] = rab_patch(rab_body_pt, -0.075, 0.075, 0.10, 0.79, 0.006, 2, 8)
    dots = Mesh()
    for t in (0.35, 0.49, 0.63):
        dots.merge(rab_dot(0.0, t, 0.026, 0.011))
    out['rabbit_button'] = dots

    # The sleeve, hung from the shoulder joint and pointing down -Y, so it is
    # placed exactly like the arm cylinder and swings with it. Short and puffed,
    # with a dome over the joint: the old sleeve was a cylinder whose flat cut
    # end sat on the shoulder like a pipe.
    prof = [(0.075, 0.000), (0.068, 0.045), (0.050, 0.075), (0.020, 0.094),
            (-0.030, 0.100), (-0.090, 0.098), (-0.135, 0.094), (-0.150, 0.082)]
    rings = [[(math.cos(math.tau * k / 14) * r, y, math.sin(math.tau * k / 14) * r)
              for k in range(14)] for y, r in reversed(prof) if r > 0]
    out['rabbit_sleeve'] = oriented(loft(rings, cap_start=True, cap_end=True))
    # the cuff: a painted ring round the opening, like the bear's stripes
    cuff = [[(math.cos(math.tau * k / 14) * (r + 0.006), y, math.sin(math.tau * k / 14) * (r + 0.006))
             for k in range(14)] for y, r in ((-0.130, 0.0952), (-0.100, 0.098))]
    out['rabbit_cuff'] = oriented(loft(cuff, cap_start=False, cap_end=False))
    return out

# --------------------------------------------------------------------- frog
# The bear's recipe, a different head. One (azimuth, elevation) -> point map:
# a wide, low pebble with two eye domes swelling out of its top corners. The
# domes are the frog's ears as far as the silhouette goes, so they are part
# of the skull rather than balls set on it — no seam, no crease, and the eye
# whites, the pupils, the pale chin and the mouth are all patches of the same
# domain, so they sit on the surface by construction.
#
# Round 2: the head went up to 40x26 (it was 24x16 and every silhouette edge
# was a run of straight segments), got shorter front to back (a loaf from the
# side), and the domes got a longer front-to-back footprint so they are humps
# in profile and not wedges. The torso is the frog's own now: a squat egg,
# lower and rounder than the bear's, with the belly forward.
FROG_X, FROG_Y, FROG_Z = 0.590, 0.345, 0.385    # wide and low, shallow front to back
FROG_N = 2.5                     # rounder than the bear's box: a river pebble
FROG_UP = 0.030                  # sits on the jersey, overhanging it
DOME_AZ, DOME_EL = 0.78, 0.70    # the top corners, a little forward
DOME_RA, DOME_RE = 0.46, 0.64    # footprint, in (az, el): long front to back
DOME_AMP = 0.180


def _frog_skull(az, el):
    dx = math.cos(el) * math.sin(az)
    dy = math.sin(el)
    dz = math.cos(el) * math.cos(az)
    k = (abs(dx) ** FROG_N + abs(dy) ** FROG_N + abs(dz) ** FROG_N) ** (-1.0 / FROG_N)
    return dx * k * FROG_X, dy * k * FROG_Y, dz * k * FROG_Z


def frog_head_pt(az, el, out=0.0):
    x, y, z = _frog_skull(az, el)
    L = math.sqrt(x * x + y * y + z * z) or 1.0
    # The domes rise mostly upward. Pushed out along the radius they come out
    # of the face's front corners as cheeks; straight up from a flat top they
    # stand as two pegs. Half and half reads as eyes on top of a head.
    q = ((abs(az) - DOME_AZ) / DOME_RA) ** 2 + ((el - DOME_EL) / DOME_RE) ** 2
    d = bump(q, DOME_AMP)
    ux, uy, uz = x / L * 0.50 + math.copysign(0.10, az), y / L * 0.50 + 0.85, z / L * 0.50
    Lu = math.sqrt(ux * ux + uy * uy + uz * uz)
    # a soft valley between the domes, where the cap perches
    d2 = -0.018 * bump((az / 0.40) ** 2 + ((el - 1.05) / 0.45) ** 2, 1.0)
    # the jaw: a gentle fullness low and wide, so the mouth line wraps round
    d2 += bump((az / 1.30) ** 2 + ((el + 0.25) / 0.45) ** 2, 0.022)
    return (x + ux / Lu * d + x / L * d2,
            y + uy / Lu * d + y / L * d2 + FROG_UP,
            z + uz / Lu * d + z / L * d2)


def frog_surface(fn, naz, nel):
    """surface_of(), but with the samples packed where the detail is: rows
    toward the top, where the domes are, and columns toward the face. The
    chin and the back of the head are plain curves and need fewer."""
    m = Mesh()
    rows = []

    def az_of(j):
        w = (j / float(naz)) * 2 - 1                  # -1 .. 1, the face at 0
        return math.pi * w * (0.65 + 0.35 * w * w)    # dense in front, sparse behind

    for i in range(nel + 1):
        s = i / float(nel)
        s = s ** 0.85                                 # more rows high up
        el = -math.pi / 2 + math.pi * s
        if i == 0 or i == nel:
            rows.append([m.vert(*fn(0.0, el))] * naz)
        else:
            rows.append([m.vert(*fn(az_of(j), el)) for j in range(naz)])
    for i in range(nel):
        a, b = rows[i], rows[i + 1]
        for j in range(naz):
            k = (j + 1) % naz
            if i == 0:
                m.tri(a[j], b[k], b[j])
            elif i == nel - 1:
                m.tri(a[j], a[k], b[j])
            else:
                m.quad(a[j], a[k], b[k], b[j])
    return m


def _metric(fn, az, el):
    """Metres per radian across and up, at a point of the map."""
    h = 1e-3
    pa, pb = fn(az + h, el), fn(az - h, el)
    pc, pd = fn(az, el + h), fn(az, el - h)
    da = math.sqrt(sum((pa[i] - pb[i]) ** 2 for i in range(3))) / (2 * h)
    de = math.sqrt(sum((pc[i] - pd[i]) ** 2 for i in range(3))) / (2 * h)
    return da, de


# The eyes: on the front of each dome, big. Sized in metres and converted to
# (az, el) through the local metric, so an oval in the patch is a circle on
# the dome rather than whatever the map's stretch happens to make it.
EYE_FAZ, EYE_FEL = 0.62, 0.58    # the white's centre on the right-hand dome
EYE_MW, EYE_MH = 0.128, 0.134    # its half width and height, metres
_ea, _ee = _metric(frog_head_pt, EYE_FAZ, EYE_FEL)
EYE_WAZ, EYE_WEL = EYE_MW / _ea, EYE_MH / _ee
EYE_PAD = 1.30                   # the decal patch is this much bigger than the white

# The mouth: one long curve low across the face, corners up.
MOUTH_EL, MOUTH_UP, MOUTH_AZ = -0.17, 0.13, 1.06
# The pale chin: a crescent under the mouth, its top edge running parallel to
# the mouth a lip's width below it and its horns rounding off toward the
# cheeks. A plain oval read as a grey hexagon pasted on the jaw; the first
# lens that reached right up to the mouth line read as a gaping beak.
CHIN_EL, CHIN_AZ, CHIN_ER, CHIN_BEND = -0.76, 1.00, 0.50, 0.48
# the decal patches, as (az centre, az radius, el centre, el radius)
MOUTH_P = (0.0, MOUTH_AZ * 1.10, MOUTH_EL + 0.02, 0.22)
NOSE_AZ, NOSE_EL = 0.11, 0.17                      # two dots, high on the snout
NOSE_P = (0.0, 0.16, NOSE_EL, 0.10)
NOSE_R = (0.0075, 0.0062)                          # a dot, metres: up, across
CHEEK_AZ, CHEEK_UP = 0.84, 0.10                    # blush just above the corners
CHEEK_R = (0.22, 0.13)


def mouth_el(az):
    return MOUTH_EL + MOUTH_UP * (az / MOUTH_AZ) ** 2


def chin_pt(rho, th):
    c = math.cos(th)
    return (rho * c * CHIN_AZ, CHIN_EL + rho * math.sin(th) * CHIN_ER + rho * CHIN_BEND * c * c)


class _FacingMesh(Mesh):
    """A patch whose shading normals lean toward the camera side. The chin is
    the underside of the head: lit by its true normals it fell into the
    shadow band and the cool shift, and a pale cream came out mustard. A
    painted toy keeps its bib one bright colour all round."""
    lean = (0.0, 0.35, 1.0)
    k = 0.85

    def normals(self):
        out = []
        for n in Mesh.normals(self):
            x, y, z = (n[i] + self.lean[i] * self.k for i in range(3))
            L = math.sqrt(x * x + y * y + z * z) or 1.0
            out.append((x / L, y / L, z / L))
        return out


def frog_chin(out, nr=5, nt=40):
    """The crescent, as a fan in (rho, theta) of the head's own map."""
    m = _FacingMesh()
    az, el = chin_pt(0.0, 0.0)
    rings = [[m.vert(*lifted(frog_head_pt, az, el, out))] * nt]
    for r in range(1, nr + 1):
        rho = r / float(nr)
        ring = []
        for j in range(nt):
            az, el = chin_pt(rho, math.tau * j / nt)
            ring.append(m.vert(*lifted(frog_head_pt, az, el, out)))
        rings.append(ring)
    for r in range(nr):
        a, b = rings[r], rings[r + 1]
        for j in range(nt):
            k = (j + 1) % nt
            if r == 0:
                m.tri(a[0], b[j], b[k])
            else:
                m.quad(a[j], b[j], b[k], a[k])
    return m


def uv_sub(fn, P, out, u0, u1, v0, v1, n, mm):
    """uv_patch() onto part of the cell. The eyes and the mouth share one
    cell this way, each at the resolution its own share gives it."""
    m = uv_patch(fn, P[0], P[1], P[2], P[3], out, n, mm)
    m.t = [(u0 + (u1 - u0) * t[0], v0 + (v1 - v0) * t[1]) for t in m.t]
    return m


def frog_foot(yaw):
    """A webbed foot, from the ankle forward: a soft flat pad with three round
    toe lobes, turned out by `yaw` (the feet splay, the way a frog sits).

    Built as a pillow, not a loft: an outline in plan (a polar curve with
    three smooth Gaussian lobes in front) swept through a flat superellipse
    from the sole to the top, closed by one vertex at each pole. Lofted
    along its length with the toes cut into the rings, it came out as a
    block with a jagged front edge and flat facets.
    """
    NU, NV = 40, 10
    ZC = 0.085                                   # the pad's centre, ahead of the ankle
    WX, LZ = 0.168, 0.165                        # half width and half length
    TOES = ((0.0, 0.070), (0.64, 0.060), (-0.64, 0.060))
    cy_, sy_ = math.cos(yaw), math.sin(yaw)

    def outline(phi):                            # phi from straight ahead
        s, c = math.sin(phi), math.cos(phi)
        r = 1.0 / math.sqrt((s / WX) ** 2 + (c / LZ) ** 2)
        r *= 1.0 + 0.16 * max(0.0, c)            # broader toward the front
        for p0, amp in TOES:
            d = math.atan2(math.sin(phi - p0), math.cos(phi - p0))
            r += amp * math.exp(-(d / 0.21) ** 2)
        return s * r, ZC + c * r

    def pt(phi, th):
        ox, oz = outline(phi)
        ct, st = math.cos(th), math.sin(th)
        k = abs(ct) ** (2.0 / 3.0)               # flat top and sole, round rim
        x, z = ox * k, ZC + (oz - ZC) * k
        fwd = max(0.0, min(1.0, (z + 0.06) / 0.34))
        top = 0.050 - 0.034 * fwd                # thins toward the toes
        y = -0.045 + (top + 0.005 if st > 0 else 0.035) * math.copysign(abs(st) ** (2.0 / 3.0), st)
        return (x * cy_ + z * sy_, y, -x * sy_ + z * cy_)

    m = Mesh()
    bot = m.vert(*pt(0.0, -math.pi / 2))
    rings = []
    for i in range(1, NV):
        th = -math.pi / 2 + math.pi * i / NV
        rings.append([m.vert(*pt(math.tau * j / NU, th)) for j in range(NU)])
    top = m.vert(*pt(0.0, math.pi / 2))
    for j in range(NU):
        k = (j + 1) % NU
        m.tri(bot, rings[0][k], rings[0][j])
        m.tri(top, rings[-1][j], rings[-1][k])
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for j in range(NU):
            k = (j + 1) % NU
            m.quad(a[j], a[k], b[k], b[j])
    return oriented(m)


def frog_leg():
    """A short soft leg hung from the hip along -y to the ankle (0.36 down),
    the same joint and length as the rig's limb(): a little fuller at the
    top, tapering, and flaring again where it meets the foot. The plain
    cylinder read as a bright green post in a batting stance."""
    # a round top: spread at the plate the hip end shows beside the hem, and
    # a flat cap there made the leg a post
    PROF = [(-0.30, 0.030), (-0.27, 0.075), (-0.22, 0.104), (-0.15, 0.121),
            (-0.06, 0.134), (0.10, 0.138), (0.40, 0.124), (0.70, 0.100), (0.88, 0.088),
            (0.97, 0.094), (1.03, 0.088), (1.07, 0.060), (1.09, 0.000)]
    NS = 24
    rings = []
    for t, r in PROF[:-1]:
        rings.append([(math.sin(math.tau * j / NS) * r, -0.36 * t,
                       math.cos(math.tau * j / NS) * r) for j in range(NS)])
    m = loft(rings)
    return oriented(m)


# ---- the frog's torso: a squat egg, the belly forward ----------------------
# Lower and rounder than the bear's: the hem comes down to y+0.20 so the
# visible leg is a stub, the widest point sits low, and the top is buried in
# the head (no neck). About the torso anchor (y+0.74).
FB_LO, FB_HI = -0.590, 0.270
FB_W = [(0.00, 0.150), (0.04, 0.236), (0.09, 0.287), (0.16, 0.318),
        (0.25, 0.334), (0.35, 0.340), (0.47, 0.330), (0.59, 0.306),
        (0.71, 0.276), (0.82, 0.250), (0.92, 0.232), (1.00, 0.224)]
FB_D = 0.93
FB_Z = [(0.00, 0.000), (0.30, 0.030), (0.50, 0.034), (0.80, 0.004), (1.00, -0.020)]


def frog_body_pt(a, t, out=0.0):
    """`a` from the middle of the chest (0) round toward his left, `t` from
    the hem (0) to the top (1)."""
    y = FB_LO + t * (FB_HI - FB_LO)
    hw = lerp_profile(t, FB_W)
    hd = hw * FB_D + out
    hw += out
    sa, ca = math.sin(a), math.cos(a)
    # the belly leads: the front half pushes forward, the back stays round
    return (sa * hw, y, ca * hd + lerp_profile(t, FB_Z) * max(0.0, ca))


def build_frog_torso():
    out = {}
    b = rab_patch(frog_body_pt, 0.0, math.tau, 0.0, 1.0, 0.0, 28, 20, closed=True)
    for ring_t, rev in ((0.0, True), (1.0, False)):     # close hem and top
        yy = FB_LO + ring_t * (FB_HI - FB_LO)
        nr = [i for i, v in enumerate(b.v) if abs(v[1] - yy) < 1e-9]
        c = b.vert(sum(b.v[i][0] for i in nr) / len(nr), yy,
                   sum(b.v[i][2] for i in nr) / len(nr))
        for j in range(len(nr)):
            p, q = nr[j], nr[(j + 1) % len(nr)]
            b.tri(c, q, p) if rev else b.tri(c, p, q)
    out['frog_body'] = oriented(b)
    # The neckline is under the chin, the hem trim right at the bottom edge —
    # a band round the widest part cut him in two, as it did the rabbit
    out['frog_collar'] = rab_patch(frog_body_pt, 0.0, math.tau, 0.86, 0.93, 0.007, 28, 1, True)
    out['frog_belt'] = rab_patch(frog_body_pt, 0.0, math.tau, 0.035, 0.085, 0.007, 28, 1, True)
    out['frog_placket'] = rab_patch(frog_body_pt, -0.065, 0.065, 0.12, 0.86, 0.006, 2, 9)
    return out


def build_frog():
    out = build_frog_torso()
    out['frog_head'] = frog_surface(frog_head_pt, 40, 26)

    # The eye whites are geometry — crisp at any distance, and inked by the
    # outline pass like any other part. The decal on top only carries the
    # pupils and the lids, and sits close (2.5mm): further out, the parallax
    # from a camera under the eyes slid the pupils up the whites.
    whites = Mesh()
    for s in (-1.0, 1.0):
        whites.merge(oval_patch(frog_head_pt, s * EYE_FAZ, EYE_FEL, EYE_WAZ, EYE_WEL,
                                0.010, nr=3, nt=30))
    out['frog_earin'] = whites
    out['frog_muz'] = frog_chin(0.012)

    # Draw order decides which cell goes where. The head cell's patches go
    # down before the whites and the chin, which would paint over them (a
    # decal writes no depth), so they get what lies on bare skin: the nostrils
    # (a small patch of their own, so they are crisp) and the two blushes.
    # The muzzle cell's patch goes down last, so it carries the pupils (top
    # half, a quarter each) and the mouth (bottom half).
    # The nostrils' patch lies on its side in the cell: (u, v) = (down, across).
    # Upright it spent 128 texels on 7cm of height and 64 on 19cm of width, and
    # a dot came out as a smudged dash; turned, a texel is about as tall as wide.
    face = uv_patch(frog_head_pt, NOSE_P[0], NOSE_P[1], NOSE_P[2], NOSE_P[3], 0.012, 6, 4)
    face.t = [(0.5 * (1 - t[1]), t[0]) for t in face.t]
    for s, u0 in ((-1.0, 0.5), (1.0, 0.75)):
        face.merge(uv_sub(frog_head_pt, (s * CHEEK_AZ, CHEEK_R[0],
                                         mouth_el(CHEEK_AZ) + CHEEK_UP, CHEEK_R[1]),
                          0.012, u0, u0 + 0.25, 0, 1, 4, 3))
    out['frog_face'] = face
    snout = Mesh()
    for s in (-1.0, 1.0):
        u0 = 0.0 if s < 0 else 0.5
        snout.merge(uv_sub(frog_head_pt, (s * EYE_FAZ, EYE_WAZ * EYE_PAD, EYE_FEL,
                                          EYE_WEL * EYE_PAD), 0.0125, u0, u0 + 0.5, 0, 0.5, 9, 9))
    snout.merge(uv_sub(frog_head_pt, MOUTH_P, 0.013, 0, 1, 0.5, 1, 16, 5))
    out['frog_snout'] = snout

    out['frog_foot_r'] = frog_foot(-0.30)     # his right foot (-x) turns out to -x
    out['frog_foot_l'] = frog_foot(0.30)
    out['frog_leg'] = frog_leg()

    # the layout the face painters need, in each patch's own 0..1 cell
    def cell(P, az, el, v0=0.0, v1=1.0):
        u = 0.5 + (az - P[0]) / (2 * P[1])
        v = 0.5 - (el - P[2]) / (2 * P[3])
        return u, v0 + (v1 - v0) * v
    mouth = []
    for j in range(17):
        az = (j / 16.0 * 2 - 1) * MOUTH_AZ
        mouth.append('%.4f,%.4f' % cell(MOUTH_P, az, mouth_el(az), 0.5, 1.0))
    nose = cell(NOSE_P, NOSE_AZ, NOSE_EL)
    na, ne = _metric(frog_head_pt, NOSE_AZ, NOSE_EL)
    nrx = NOSE_R[0] / (2 * NOSE_P[3] * ne / 0.5)       # cell x runs down the face
    nry = NOSE_R[1] / (2 * NOSE_P[1] * na)             # cell y runs across it
    DATA.append('/* the frog\'s face layout, solved off the head map */')
    DATA.append('const FROG_FACE = { eyeR: %.4f, mouth: [%s],'
                % (0.5 / EYE_PAD, ','.join(mouth)))
    # nostrils in the head cell's left half; each blush fills its own quarter
    # metres per unit of u over metres per unit of v, in the mouth's half of
    # the cell: the painter draws in a space squeezed by this, so a stroke is
    # as thick across as along and the corner curls come out round
    ma, me = _metric(frog_head_pt, 0.0, MOUTH_EL)
    mk = (2 * MOUTH_P[1] * ma) / (2 * MOUTH_P[3] * me / 0.5)
    DATA.append('  nose: [%.4f, %.4f, %.4f, %.4f], mouthK: %.3f };'
                % (0.5 * nose[1], nose[0] - 0.5, nrx, nry, mk))
    DATA.append('')
    return out

# ------------------------------------------------------------------ penguin
# One soft egg with a round head on it, flippers at the sides and two orange
# feet peeking out from under the hem. It keeps the shared rig's anchors —
# torso y+0.74, head y+1.34, hips y+0.44 — so running, sliding, tumbling, the
# camera and the shadow all work unchanged; the legs are simply inside him.
#
# Everything is authored in the character's own frame (+z the face, +y up,
# +x his LEFT side), about the anchor 30-actors.js places it at.
#
# The white face is not geometry. It is painted into the face cell along with
# the eyes, on a patch cut from the same (az, el) map as the skull — so it
# follows the head exactly, and a heart shape costs nothing.
PEN_X, PEN_Y, PEN_Z = 0.430, 0.400, 0.392     # the skull: as wide as the body's widest
PEN_UP, PEN_FWD = 0.000, 0.015                # 46% of his height, chin over the jersey
PEN_N = 2.25                                  # just off a sphere: soft, not a ball
PEN_FACE_AZ_R, PEN_FACE_EL_C, PEN_FACE_EL_R = 1.20, -0.10, 0.86
PEN_BEAK_EL = -0.20                           # just under the eye line
PEN_BEAK_TILT = 0.20                          # pointing forward and a little down
PEN_BEAK_S = 1.15


def pen_skull(az, el):
    dx = math.cos(el) * math.sin(az)
    dy = math.sin(el)
    dz = math.cos(el) * math.cos(az)
    k = (abs(dx) ** PEN_N + abs(dy) ** PEN_N + abs(dz) ** PEN_N) ** (-1.0 / PEN_N)
    return dx * k * PEN_X, dy * k * PEN_Y, dz * k * PEN_Z


def pen_head_pt(az, el, out=0.0):
    x, y, z = pen_skull(az, el)
    # soft cheeks low on the face, so the head is a little pear and not a ball
    d = bump(((abs(az) - 0.75) / 0.70) ** 2 + ((el + 0.35) / 0.50) ** 2, 0.024)
    L = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x + x / L * d, y + y / L * d + PEN_UP, z + z / L * d + PEN_FWD)


# The body: a pear, widest low, deep enough not to go flat when he turns, and
# coming down nearly to the ground so the legs vanish inside it.
PEN_LO, PEN_HI = -0.640, 0.300                # about the torso anchor: y+0.10 .. y+1.04
PEN_W = [(0.00, 0.100), (0.04, 0.220), (0.10, 0.310), (0.18, 0.370),
         (0.28, 0.402), (0.38, 0.408), (0.50, 0.392), (0.62, 0.362),
         (0.74, 0.312), (0.85, 0.270), (0.94, 0.236), (1.00, 0.210)]
PEN_DK = 0.90                                 # depth as a share of width
PEN_ZS = [(0.00, 0.020), (0.40, 0.034), (0.80, 0.004), (1.00, -0.022)]
PEN_HEM = 0.50                                # where the jersey ends


def smooth_profile(t, keys):
    """Catmull-Rom through [(t, value), ...] (ascending). The straight pieces
    of lerp_profile show as corners on a silhouette this round."""
    n = len(keys)
    if t <= keys[0][0]:
        return keys[0][1]
    if t >= keys[-1][0]:
        return keys[-1][1]
    i = 0
    while keys[i + 1][0] < t:
        i += 1
    t0, t1 = keys[i][0], keys[i + 1][0]
    u = (t - t0) / (t1 - t0)
    p0 = keys[max(0, i - 1)][1]
    p1, p2 = keys[i][1], keys[i + 1][1]
    p3 = keys[min(n - 1, i + 2)][1]
    return 0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                  + (-p0 + 3 * p1 - 3 * p2 + p3) * u * u * u)


def pen_body_pt(a, t, out=0.0):
    """`a` from the middle of the chest (0) round toward his left; `t` from the
    bottom (0) to the top (1)."""
    y = PEN_LO + t * (PEN_HI - PEN_LO)
    w = smooth_profile(t, PEN_W)
    hw, hd = w + out, w * PEN_DK + out
    sa, ca = math.sin(a), math.cos(a)
    return (sa * hw, y, ca * hd + smooth_profile(t, PEN_ZS))


def pen_body_rings(t0, t1, nt, out, na=32):
    return [[pen_body_pt(math.tau * j / na, t0 + (t1 - t0) * i / float(nt), out)
             for j in range(na)] for i in range(nt + 1)]


def pen_disc(fn, ac, bc, ar, br, out, nr=3, nt=24, lo=0.0, hi=math.tau):
    """A disc (or a fan of one, lo..hi) of a surface map, in its own domain."""
    m = Mesh()
    full = abs(hi - lo - math.tau) < 1e-9
    na = nt if full else nt + 1
    rings = [[m.vert(*fn(ac, bc, out))] * na]
    for r in range(1, nr + 1):
        rho = r / float(nr)
        rings.append([m.vert(*fn(ac + rho * math.cos(th) * ar, bc + rho * math.sin(th) * br, out))
                      for th in [lo + (hi - lo) * j / float(nt) for j in range(na)]])
    for r in range(nr):
        a, b = rings[r], rings[r + 1]
        for j in range(nt):
            k = (j + 1) % na
            if r == 0:
                m.tri(a[0], b[j], b[k])
            else:
                m.quad(a[j], b[j], b[k], a[k])
    return m


def pen_lens_loft(table, n, closed=True):
    """Rings of a flat paddle hanging along -y: (t, half width in z, half
    thickness in x, z offset), t a fraction of PEN_FLIP down."""
    rings = [section(0.0, -t * PEN_FLIP, cz, th, w, n, e=2.0) for t, w, th, cz in table]
    return loft(rings, cap_start=closed, cap_end=closed)


PEN_FLIP = 0.44
# Wider than the first cut and round at the tip, so it reads as a flipper and
# not a stick from any side. drawPenguin holds it flat on to the camera.
PEN_FL = [(-0.02, 0.040, 0.030, 0.000), (0.00, 0.062, 0.040, 0.000),
          (0.15, 0.094, 0.041, -0.004), (0.38, 0.108, 0.038, -0.014),
          (0.60, 0.102, 0.035, -0.024), (0.78, 0.086, 0.032, -0.032),
          (0.89, 0.066, 0.029, -0.036), (0.955, 0.044, 0.025, -0.038),
          (0.990, 0.022, 0.018, -0.038), (1.00, 0.006, 0.008, -0.038)]


def build_penguin():
    out = {}
    out['penguin_head'] = oriented(surface_of(pen_head_pt, naz=32, nel=20))
    # the face cell — the white mask, the eyes and the blush are all art on it.
    # Dense, so the mask's edge comes out as a curve and not a run of kinks
    out['penguin_face'] = uv_patch(pen_head_pt, 0.0, PEN_FACE_AZ_R, PEN_FACE_EL_C,
                                   PEN_FACE_EL_R, 0.010, n=16, mm=16)

    # The beak. Shut, it is one closed soft cone — two halves drawn shut left a
    # dark seam and a lower half a shade off, and read as a little burger.
    # Pleased, it splits: the half is drawn twice, the lower one turned over
    # about its own axis and dropped open.
    BK = [(-0.050, 0.064, 0.048), (-0.010, 0.066, 0.052), (0.030, 0.062, 0.050),
          (0.066, 0.050, 0.042), (0.092, 0.036, 0.032), (0.112, 0.022, 0.020),
          (0.126, 0.010, 0.010), (0.131, 0.002, 0.002)]
    S = PEN_BEAK_S
    rings = []
    for z, w, h in BK:
        ring = []
        for k in range(13):
            a = math.pi * k / 12.0
            ring.append((math.cos(a) * w * S, math.sin(a) ** 0.85 * h * S, z * S))
        ring.append((0.0, 0.0, z * S))             # the flat underside
        rings.append(ring)
    out['penguin_beak'] = oriented(loft(rings))
    rings = []
    for z, w, h in BK:
        ring = []
        for k in range(20):
            a = math.tau * k / 20.0
            sa = math.sin(a)
            ring.append((math.cos(a) * w * S, sa * (h if sa > 0 else h * 0.82) * S, z * S))
        rings.append(ring)
    out['penguin_beakc'] = oriented(loft(rings))
    root = lifted(pen_head_pt, 0.0, PEN_BEAK_EL, -0.014)

    # the flipper: a flat paddle hanging from the shoulder along -y. Thin in x,
    # broad in z, widest a third of the way down; 2 x A.ink thick or more.
    out['penguin_flip'] = oriented(pen_lens_loft(PEN_FL, 16))

    # The sleeve: a short cap round the flipper's root, hung from the same
    # shoulder and turned with it, domed on top so no cut end shows — and the
    # navy edge round its mouth. A ball over the joint read as a bolt.
    SL = [(-0.100, 0.030, 0.022, 0.0), (-0.088, 0.070, 0.050, 0.0),
          (-0.062, 0.094, 0.064, 0.0), (-0.020, 0.108, 0.072, 0.0),
          (0.050, 0.114, 0.076, -0.002), (0.150, 0.112, 0.074, -0.004),
          (0.210, 0.108, 0.072, -0.005)]
    out['penguin_sleeve'] = oriented(pen_lens_loft(SL, 16))
    cuff = [(0.200, 0.114, 0.078, -0.005), (0.238, 0.113, 0.077, -0.006)]
    out['penguin_cuff'] = oriented_open(pen_lens_loft(cuff, 16, closed=False),
                                        (0.0, -0.22 * PEN_FLIP, 0.0))

    # The foot, from the ankle forward: flat, wide, webbed. The ankle is 8cm
    # off the ground when he stands, so the sole is 8cm under it.
    FT = [(-0.074, 0.020, -0.030, -0.066), (-0.066, 0.040, -0.016, -0.074),
          (-0.040, 0.060, 0.000, -0.079), (0.000, 0.074, 0.002, -0.080),
          (0.050, 0.088, -0.006, -0.080), (0.100, 0.102, -0.018, -0.080),
          (0.150, 0.115, -0.026, -0.080), (0.200, 0.126, -0.030, -0.080),
          (0.245, 0.126, -0.032, -0.079), (0.278, 0.110, -0.034, -0.077),
          (0.298, 0.080, -0.036, -0.075), (0.309, 0.040, -0.040, -0.072)]
    out['penguin_foot'] = oriented(loft([ring_xy(z, hw, top, bot, 16, 2.4)
                                         for z, hw, top, bot in FT]))

    # the dark egg below the hem, closed at the bottom, open at the top where
    # the jersey takes over
    body = loft(pen_body_rings(0.0, PEN_HEM + 0.04, 14, 0.0), cap_start=True, cap_end=False)
    out['penguin_body'] = oriented_open(body, (0.0, PEN_LO + 0.3, 0.0))
    # the jersey: the same profile, a hair proud, closed over the top
    jer = loft(pen_body_rings(PEN_HEM, 1.0, 12, 0.012), cap_start=False, cap_end=True)
    out['penguin_jersey'] = oriented_open(jer, (0.0, 0.0, 0.0))
    # the hem, in the trim — what tells jersey from belly at any distance
    hem = loft(pen_body_rings(PEN_HEM - 0.030, PEN_HEM + 0.030, 2, 0.022),
               cap_start=False, cap_end=False)
    out['penguin_hem'] = oriented_open(hem, (0.0, PEN_LO + 0.5, 0.0))
    # a placket down the front, so it is a jersey and not a T-shirt
    pk = Mesh()
    rows = [[pk.vert(*pen_body_pt((j - 1) * 0.045, PEN_HEM + (0.93 - PEN_HEM) * i / 8.0, 0.017))
             for j in range(3)] for i in range(9)]
    for i in range(8):
        for j in range(2):
            pk.quad(rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])
    out['penguin_placket'] = pk
    # and two buttons on it — the one detail the front gets
    bt = Mesh()
    for t in (0.63, 0.78):
        w = smooth_profile(t, PEN_W)
        bt.merge(pen_disc(pen_body_pt, 0.0, t, 0.030 / w, 0.030 / (PEN_HI - PEN_LO), 0.024,
                          nr=2, nt=14))
    out['penguin_button'] = bt
    # The white belly: a soft U, round at the bottom, whose top runs straight
    # across under the hem, so it tucks in there instead of ending in corners.
    tt, tb = PEN_HEM - 0.012, 0.07
    out['penguin_belly'] = pen_disc(pen_body_pt, 0.0, tt, 0.98, tt - tb, 0.012,
                                    nr=8, nt=32, lo=math.pi, hi=math.tau)

    DATA.append('/* the penguin, solved off its own skull and body by the baker */')
    DATA.append('const PEN = { beak: [%.4f, %.4f, %.4f], flip: %.3f };'
                % (root[1], root[2], PEN_BEAK_TILT, PEN_FLIP))
    DATA.append('')
    return out


def oriented_open(m, inside):
    """oriented() for a surface that is not closed: make the faces point away
    from a point known to be inside it."""
    s = 0.0
    for a, b, c in m.f:
        pa, pb, pc = m.v[a], m.v[b], m.v[c]
        u = [pb[i] - pa[i] for i in range(3)]
        v = [pc[i] - pa[i] for i in range(3)]
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        s += sum(n[i] * (pa[i] - inside[i]) for i in range(3))
    if s < 0.0:
        m.f = [(a, c, b) for a, b, c in m.f]
    return m

# ------------------------------------------------------------------- packing

def load_obj(path):
    m = Mesh()
    for line in io.open(path, encoding='utf-8'):
        p = line.split()
        if not p:
            continue
        if p[0] == 'v':
            m.vert(float(p[1]), float(p[2]), float(p[3]))
        elif p[0] == 'f':
            idx = [int(q.split('/')[0]) - 1 for q in p[1:]]
            for i in range(1, len(idx) - 1):
                m.tri(idx[0], idx[i], idx[i + 1])
    return m


def _varint(v, out):
    while v >= 128:
        out.append((v & 127) | 128)
        v >>= 7
    out.append(v)


def rle_index(flat, lag):
    """Index stream as runs of a constant difference from the entry `lag`
    back. A grid of quads repeats +1 every 6 entries, so a whole ring of the
    loft collapses to one run. Token = (zigzag(delta) << 1 | repeated), then
    the run length - 2 if repeated. The runtime in geoMesh() undoes it."""
    out = bytearray()
    r = [q - (flat[k - lag] if k >= lag else 0) for k, q in enumerate(flat)]
    k = 0
    while k < len(r):
        n = 1
        while k + n < len(r) and r[k + n] == r[k]:
            n += 1
        z = (r[k] << 1) ^ (r[k] >> 63)
        _varint((z << 1) | (n > 1), out)
        if n > 1:
            _varint(n - 2, out)
        k += n
    return '%d|%s' % (lag, base64.b64encode(bytes(out)).decode())


def pack_index(flat, raw64):
    """The smallest of: raw Uint16 base64, or RLE-of-differences at the best lag."""
    best = raw64
    for lag in range(1, 13):
        e = rle_index(flat, lag)
        if len(e) < len(best):
            best = e
    return best


def pack(m):
    nor = m.normals()
    xs = [v[0] for v in m.v]
    ys = [v[1] for v in m.v]
    zs = [v[2] for v in m.v]
    lo = (min(xs), min(ys), min(zs))
    hi = (max(xs), max(ys), max(zs))
    sc = [(hi[i] - lo[i]) / 32000.0 or 1e-6 for i in range(3)]
    pb, nb = bytearray(), bytearray()
    for v, n in zip(m.v, nor):
        for i in range(3):
            pb += struct.pack('<h', int(round((v[i] - lo[i]) / sc[i])) - 16000)
        for i in range(3):
            nb += struct.pack('<b', max(-127, min(127, int(round(n[i] * 127)))))
    ib = bytearray()
    for a, b, c in m.f:
        ib += struct.pack('<HHH', a, b, c)
    flat = [q for f in m.f for q in f]
    off = [lo[i] + 16000 * sc[i] for i in range(3)]
    d = {
        'sc': sc, 'off': off,
        'p': base64.b64encode(bytes(pb)).decode(),
        'n': base64.b64encode(bytes(nb)).decode(),
        'i': pack_index(flat, base64.b64encode(bytes(ib)).decode()),
        'nv': len(m.v), 'nf': len(m.f),
    }
    # UVs ride along only on the patches that carry a face decal; Uint16 over
    # 0..1 is far finer than a 128px cell needs
    if m.has_uv():
        tb = bytearray()
        for t in m.t:
            u, w = t or (0.0, 0.0)
            tb += struct.pack('<HH', int(round(max(0.0, min(1.0, u)) * 65535)),
                              int(round(max(0.0, min(1.0, w)) * 65535)))
        d['t'] = base64.b64encode(bytes(tb)).decode()
    return d


def main():
    meshes = {}
    meshes.update(build_salmon())
    meshes.update(build_bear())
    meshes.update(build_cap())
    meshes.update(build_beetle())
    meshes.update(build_rabbit())
    meshes.update(build_frog())
    meshes.update(build_penguin())

    # anything hand-made wins over the procedural version of the same name
    objdir = os.path.join('tools', 'obj')
    if os.path.isdir(objdir):
        for fn in sorted(os.listdir(objdir)):
            if fn.endswith('.obj'):
                meshes[fn[:-4]] = load_obj(os.path.join(objdir, fn))
                print('  from obj: %s' % fn[:-4])

    out = [
        '/* GENERATED by tools/mesh2js.py — do not edit.',
        '   Positions Int16 over each mesh\'s own box, normals Int8, indices',
        '   Uint16. Re-run the script after changing a model or dropping a new',
        '   .obj into tools/obj/. */',
        '',
    ]
    total_v = total_f = 0
    for name in sorted(meshes):
        d = pack(meshes[name])
        total_v += d['nv']
        total_f += d['nf']
        out.append("geoMesh('%s', [%s], [%s]," % (
            name,
            ','.join('%.8g' % x for x in d['sc']),
            ','.join('%.6g' % x for x in d['off'])))
        out.append("  '%s'," % d['p'])
        out.append("  '%s'," % d['n'])
        if 't' in d:
            out.append("  '%s'," % d['i'])
            out.append("  '%s');   // %d verts, %d tris, uv" % (d['t'], d['nv'], d['nf']))
        else:
            out.append("  '%s');   // %d verts, %d tris" % (d['i'], d['nv'], d['nf']))
        out.append('')
        print('  %-12s %5d verts %5d tris' % (name, d['nv'], d['nf']))

    out.extend(DATA)
    io.open('src/15-meshes.js', 'w', encoding='utf-8').write('\n'.join(out))
    kb = os.path.getsize('src/15-meshes.js') / 1024.0
    print('src/15-meshes.js  %d verts, %d tris, %.0f KB' % (total_v, total_f, kb))
    if total_v > 60000:
        print('!! the shared index buffer is Uint16: keep the total under 65536')


main()
