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
# Canonical pose: body axis along +Y with the snout up, dorsal toward -Z and
# belly toward +Z, so it stands the way a Magikarp does. Scaled to about 1.3
# tall, which puts it alongside the mammals.

SAL_DEPTH = [(0.00, 0.020), (0.04, 0.090), (0.10, 0.150), (0.18, 0.196),
             (0.28, 0.226), (0.38, 0.234), (0.50, 0.222), (0.62, 0.194),
             (0.74, 0.152), (0.84, 0.104), (0.92, 0.062), (0.97, 0.040),
             (1.00, 0.032)]
SAL_WIDTH = [(0.00, 0.016), (0.06, 0.070), (0.14, 0.098), (0.28, 0.106),
             (0.44, 0.094), (0.62, 0.078), (0.80, 0.052), (0.92, 0.030),
             (1.00, 0.022)]
# the belly hangs below the axis; the back is nearly straight, as on the fish
SAL_SHIFT = [(0.00, 0.010), (0.20, 0.030), (0.40, 0.040), (0.70, 0.026),
             (1.00, 0.004)]


def salmon_rings(n=44, sec=18, swell=1.0):
    rings = []
    for i in range(n):
        t = i / float(n - 1)
        y = 1.30 - t * 1.30
        d = lerp_profile(t, SAL_DEPTH) * swell
        w = lerp_profile(t, SAL_WIDTH) * swell
        cz = lerp_profile(t, SAL_SHIFT)
        rings.append(section(0.0, y, cz, w, d, sec, e=2.35, back_flat=0.86))
    return rings


def build_salmon():
    out = {}
    rings = salmon_rings()
    out['sal_body'] = loft(rings)

    # a thin shell over the dark of the back and another under the pale belly,
    # pushed just proud of the body so they read as markings, not as geometry
    sec = 18
    for name, lo, hi, swell in (('sal_back', 11, 18, 1.035), ('sal_belly', 3, 10, 1.03)):
        rs = salmon_rings(swell=swell)
        band = [r[lo:hi + 1] for r in rs]
        m = Mesh()
        idx = [[m.vert(*p) for p in r] for r in band]
        for k in range(len(band) - 1):
            a, b = idx[k], idx[k + 1]
            for i in range(len(a) - 1):
                m.quad(a[i], a[i + 1], b[i + 1], b[i])
        out[name] = m

    fins = Mesh()
    # dorsal, along the back
    root = [(0.0, 1.30 - t * 1.30, lerp_profile(t, SAL_SHIFT) - lerp_profile(t, SAL_DEPTH) * 0.86)
            for t in [0.34, 0.40, 0.46, 0.52]]
    tip = [(0.0, r[1] + 0.02, r[2] - 0.16 * math.sin(math.pi * (0.2 + 0.8 * i / 3.0)))
           for i, r in enumerate(root)]
    fins.merge(blade(root, tip, 0.012))
    # anal fin, underneath and further back
    root2 = [(0.0, 1.30 - t * 1.30, lerp_profile(t, SAL_SHIFT) + lerp_profile(t, SAL_DEPTH) * 0.92)
             for t in [0.76, 0.80, 0.84]]
    tip2 = [(0.0, r[1] - 0.01, r[2] + 0.09) for r in root2]
    fins.merge(blade(root2, tip2, 0.010))
    # the adipose fin, which is small and pointless and unmistakably salmonid
    root3 = [(0.0, 1.30 - t * 1.30, lerp_profile(t, SAL_SHIFT) - lerp_profile(t, SAL_DEPTH) * 0.86)
             for t in [0.70, 0.745]]
    fins.merge(blade(root3, [(0.0, r[1], r[2] - 0.045) for r in root3], 0.008))
    # caudal: forked, and the reason a salmon is not a trout at a glance
    for s in (-1.0, 1.0):
        rt = [(0.0, 0.02, 0.006), (0.0, 0.00, 0.006)]
        tp = [(0.0, 0.02 + s * 0.20, -0.24), (0.0, 0.00 + s * 0.10, -0.20)]
        fins.merge(blade(rt, tp, 0.011))
    # pectorals, low on the flank where they belong
    for s in (-1.0, 1.0):
        rt = [(s * 0.070, 0.82, 0.03), (s * 0.070, 0.74, 0.03)]
        tp = [(s * 0.150, 0.74, 0.10), (s * 0.150, 0.70, 0.07)]
        fins.merge(blade(rt, tp, 0.009))
    out['sal_fins'] = fins

    # Eyes and markings go in the mesh too. Placed by hand against the old
    # sphere model they floated off the surface; solved for the profile they
    # sit where they belong at any angle.
    def surface(t, k=0.82):
        y = 1.30 - t * 1.30
        return (lerp_profile(t, SAL_WIDTH) * k, y, lerp_profile(t, SAL_SHIFT))

    eyes, iris = Mesh(), Mesh()
    t_eye = 0.175
    w = lerp_profile(t_eye, SAL_WIDTH)
    ey = 1.30 - t_eye * 1.30
    ez = lerp_profile(t_eye, SAL_SHIFT) - lerp_profile(t_eye, SAL_DEPTH) * 0.28
    r = 0.036
    for s2 in (-1.0, 1.0):
        eyes.merge(ball(s2 * (w - r * 0.42), ey, ez, r, 10))
        iris.merge(ball(s2 * (w - r * 0.12), ey, ez + 0.002, r * 0.58, 8))
    out['sal_eye'] = eyes
    out['sal_pupil'] = iris

    # the flush a fish gets on the run upriver, a band along the flank only
    # 46 rings of 9 along a smooth lens is nine hundred vertices spent on a
    # stripe, and vertices here are bytes in the one HTML file the whole game
    # ships as. At 24 by 7 it is the same shape and 13KB cheaper.
    band = Mesh()
    N, COLS = 24, 7
    for a_c in (0.0, math.pi):
        rows = []
        for i in range(N):
            u = i / float(N - 1)
            t = 0.20 + u * 0.52
            # a lens along the lateral line, not a coat of paint: at full width
            # it wrapped most of the flank and the fish read as skinned
            spread = 0.34 * math.sin(math.pi * u) ** 0.75
            y = 1.30 - t * 1.30
            d = lerp_profile(t, SAL_DEPTH) * 1.022
            w = lerp_profile(t, SAL_WIDTH) * 1.022
            cz = lerp_profile(t, SAL_SHIFT)
            rows.append([band.vert(*section_pt(0.0, y, cz, w, d,
                                               a_c + ((j / float(COLS - 1)) * 2 - 1) * spread,
                                               e=2.35, back_flat=0.86))
                         for j in range(COLS)])
        for k in range(N - 1):
            a, b = rows[k], rows[k + 1]
            for i in range(COLS - 1):
                band.quad(a[i], a[i + 1], b[i + 1], b[i])
    out['sal_blush'] = band

    # the kit, hugging the body for the same reason the beetle's does
    for name, lo, hi, sw in (('sal_band', 0.40, 0.66, 1.022),
                             ('sal_collar', 0.34, 0.40, 1.028),
                             ('sal_belt', 0.66, 0.71, 1.028)):
        m = Mesh()
        rows = []
        for i in range(16):
            t = lo + (hi - lo) * i / 15.0
            rows.append(section(0.0, 1.30 - t * 1.30, lerp_profile(t, SAL_SHIFT),
                                lerp_profile(t, SAL_WIDTH) * sw,
                                lerp_profile(t, SAL_DEPTH) * sw,
                                18, e=2.35, back_flat=0.86))
        m.merge(loft(rows, cap_start=False, cap_end=False))
        out[name] = m

    # the kype: a spawning male's hooked lower jaw. Nothing else about the fish
    # says "not cute" as loudly.
    jaw = sweep(bez((0.0, 1.16, 0.055), (0.0, 1.10, 0.16), (0.0, 1.21, 0.215), 9),
                [0.052, 0.050, 0.046, 0.041, 0.036, 0.031, 0.026, 0.021, 0.016], 9)
    out['sal_jaw'] = jaw
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

# the envelope the cap and the ears were sized against; keep it
HEAD_X, HEAD_Y, HEAD_Z = 0.393, 0.352, 0.318
HEAD_FWD = 0.02                 # the head primitive sat this far forward
SNOUT_EL = -0.325               # a bear's muzzle points down as well as out


def bump(q, amp):
    """A smooth blob over an elliptical footprint, zero outside it.

    The obvious `max(0, 1 - q) ** p` looks the same but its curvature blows up
    at the rim, which digs a crease the surface cannot be offset out of: the
    pale muzzle patch sat 6mm proud and the skull still bit a chunk out of it.
    Smoothstep is flat at both ends, so the rim is a valley with a radius.
    """
    u = max(0.0, min(1.0, 1.0 - q))
    return amp * u * u * (3 - 2 * u)


def mesa(q, amp, flat=0.46):
    """A blob with a flat top and a steep flank — a muzzle, not a swelling.

    `bump` falls away from its own centre, so the snout it makes is a dome:
    broadest where it meets the skull and pointed where the nose is, which is
    a mouse. A bear's muzzle is the other way round — it holds its width out
    to the end and drops back to the skull down a short flank. That flank is
    the stop, and the stop is what reads as "bear" in profile. `flat` is the
    share of the footprint that keeps full height; the rest is the flank,
    still smoothstep, so the rim keeps a radius the pale patch can clear.
    """
    if q <= flat * flat:
        return amp
    u = (1.0 - math.sqrt(max(0.0, q))) / (1.0 - flat)
    u = max(0.0, min(1.0, u))
    return amp * u * u * (3 - 2 * u)


def bear_head_pt(az, el, out=0.0):
    """A point on the bear's skull. Star-shaped in (az, el) by construction."""
    dx = math.cos(el) * math.sin(az)
    dy = math.sin(el)
    dz = math.cos(el) * math.cos(az)
    n = 3.1                     # a rounded box, softer than the rbox it replaces
    k = (abs(dx) ** n + abs(dy) ** n + abs(dz) ** n) ** (-1.0 / n)
    x, y, z = dx * k * HEAD_X, dy * k * HEAD_Y, dz * k * HEAD_Z

    # the muzzle: broad, shallow, and part of the same surface. Wider than it
    # is tall is what stops it reading as a ball glued to the front, and a
    # mesa rather than a bump is what gives it a stop to meet the skull at.
    d = mesa((az / 0.70) ** 2 + ((el - SNOUT_EL) / 0.46) ** 2, 0.176, 0.44)

    # the lower jaw, carrying on behind the muzzle. Without it the chin cuts
    # straight back to the throat and the profile is a dome with a peg on it.
    d += bump((az / 0.64) ** 2 + ((el + 0.80) / 0.42) ** 2, 0.042)

    # the brow ridge. More than anything else this is what separates a bear
    # from a teddy, and it is exactly what a stack of spheres cannot do.
    d += bump((az / 0.95) ** 2 + ((el - 0.19) / 0.24) ** 2, 0.032)

    # jowls, low and wide, carrying the line from the muzzle back to the ears
    d += bump(((abs(az) - 1.00) / 0.58) ** 2 + ((el + 0.20) / 0.44) ** 2, 0.034)

    # and the flat of the crown, so the cap has something to sit on
    d -= 0.020 * max(0.0, (el - 0.95) / 0.62) ** 2

    L = math.sqrt(x * x + y * y + z * z) or 1.0
    return (x + x / L * d, y + y / L * d, z + z / L * d + HEAD_FWD)


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


EAR_AZ, EAR_EL = 1.70, 0.74      # where on the skull the ear is rooted
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


EAR_R = 0.138
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


# ---- the body. A barrel with shoulders, which the sphere never had. --------
BODY_W = [(0.00, 0.228), (0.05, 0.284), (0.15, 0.305), (0.30, 0.322),
          (0.45, 0.338), (0.60, 0.352), (0.72, 0.356), (0.84, 0.330),
          (0.92, 0.262), (1.00, 0.165)]
# A bear is deep, not wide: seen side-on the old torso was a slab barely two
# thirds the width it had front-on, which is a mascot suit, not an animal.
# The chest now carries nearly as much depth as width and the waist gives
# some back, so the silhouette changes when he turns.
BODY_D = [(0.00, 0.206), (0.05, 0.252), (0.15, 0.268), (0.30, 0.286),
          (0.45, 0.304), (0.60, 0.318), (0.72, 0.314), (0.84, 0.276),
          (0.92, 0.214), (1.00, 0.142)]
BODY_Z = [(0.00, 0.004), (0.25, 0.018), (0.50, 0.006), (0.72, -0.026),
          (1.00, -0.042)]


def bear_body_pt(a, t, out=0.0):
    """A point on the torso. `a` runs from the centre of the chest (0) round
    toward the character's left; `t` from the hem (0) to the collar (1)."""
    y = -0.300 + t * 0.625
    hw = lerp_profile(t, BODY_W) + out
    hd = lerp_profile(t, BODY_D) + out
    cz = lerp_profile(t, BODY_Z)
    sa, ca = math.sin(a), math.cos(a)
    e = 2.05                            # barely off round; 2.45 was a packing case
    x = math.copysign(abs(sa) ** (2.0 / e), sa) * hw
    z = math.copysign(abs(ca) ** (2.0 / e), ca) * hd

    # Shoulder caps. The sleeve is a capped cylinder hung at x = +/-0.33 with a
    # 0.112 radius, so its top is a flat disc reaching out to 0.44 — and at
    # 0.022 the old cap left that cut end in plain sight from the front and the
    # back, a pair of tabs on the shoulders. The jersey has to come out far
    # enough to swallow it and roll over the top, which is also what makes an
    # arm look like it is in a sleeve rather than parked beside one.
    q = ((abs(x) - 0.310) / 0.190) ** 2 + ((y - 0.158) / 0.175) ** 2
    if q < 1.0:
        x += math.copysign(bump(q, 0.078), x)

    # The shoulder hump. Bears carry a mass of muscle over the shoulder blades,
    # and under a jersey it is the one line that says bear from fifty metres —
    # but only if it shows in the outline. Lifting it alone put it inside the
    # back's own curve, so it also pushes back: at 6cm of rise and nothing
    # behind it the hump was invisible from every angle that mattered.
    back = max(0.0, -z / hd)
    up = max(0.0, min(1.0, (t - 0.40) / 0.24)) * max(0.0, min(1.0, (0.95 - t) / 0.15))
    up = up * up * (3 - 2 * up)
    hump = (back ** 1.6) * up
    y += 0.082 * hump
    z -= 0.056 * hump
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
    out['bear_muz'] = oval_patch(bear_head_pt, 0.0, SNOUT_EL - 0.008, 0.53, 0.31, 0.008)
    out['bear_face'] = uv_patch(bear_head_pt, 0.0, 60 * math.pi / 180,
                                0.0, 50 * math.pi / 180, 0.009)
    out['bear_snout'] = uv_patch(bear_head_pt, 0.0, 34 * math.pi / 180,
                                 SNOUT_EL - 0.015, 20 * math.pi / 180, 0.011)

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

    out['bear_collar'] = bear_band(0.93, 1.00, 0.008)
    out['bear_belt'] = bear_band(0.055, 0.135, 0.008)
    out['bear_placket'] = bear_strip(0.0, 0.072, 0.14, 0.93, 0.007)
    stripes = Mesh()
    for a_c in (-0.80, -0.42, 0.42, 0.80):
        stripes.merge(bear_strip(a_c, 0.030, 0.18, 0.88, 0.006, na=3))
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
# Canonical pose: standing, wing cases to the back (-Z), head and horn forward
# (+Z), Y up with 0 on the ground. The legs stay animated primitives; the
# shell, the horns and the toothed foreleg shin are baked.
#
# The proportions are the real animal's rather than the mammals': the wing
# cases are the widest part of him, the shield is narrower and trapezoid, and
# the head horn is long enough to read as a horn from the outfield. That horn
# is the whole identity of the species — at sixty metres it is the only part of
# him anyone can name — so it gets the length and the thickness it deserves.

BEE_Z = -0.05                       # the cases sit a little behind the axis
BEE_TOP, BEE_BOT = 1.00, 0.26
BEE_E = 2.6                         # superellipse exponent of the sections

# Half width of ONE wing case, how far its centre sits off the midline, and
# half the depth. The widest point is up at the shoulders, as it is on him.
BEE_W = [(0.00, 0.088), (0.08, 0.122), (0.20, 0.152), (0.35, 0.162),
         (0.55, 0.156), (0.75, 0.128), (0.90, 0.082), (1.00, 0.030)]
BEE_CX = [(0.00, 0.072), (0.35, 0.090), (0.70, 0.070), (1.00, 0.028)]
BEE_D = [(0.00, 0.150), (0.10, 0.230), (0.30, 0.290), (0.55, 0.300),
         (0.78, 0.262), (0.92, 0.180), (1.00, 0.070)]

# the shield, as its own trapezoid profile
BEE_PTOP, BEE_PBOT, BEE_PZ = 1.26, 0.94, 0.005
BEE_PW = [(0.00, 0.118), (0.55, 0.176), (1.00, 0.200)]
BEE_PD = [(0.00, 0.195), (0.55, 0.245), (1.00, 0.266)]
BEE_PE = 2.8

# the head is its own little loft, out in front of the shield
BEE_HZ = 0.235
BEE_HW = [(0.00, 0.150), (0.45, 0.186), (1.00, 0.120)]
BEE_HD = [(0.00, 0.120), (0.45, 0.158), (1.00, 0.100)]
BEE_HE = 2.5


def bee_y(t):
    return BEE_TOP - (BEE_TOP - BEE_BOT) * t


def bee_prof(t):
    return (lerp_profile(t, BEE_W), lerp_profile(t, BEE_CX), lerp_profile(t, BEE_D))


def bee_shell_x(t, z, s=1.0):
    """Where the wing case's surface is, at this height and this depth.

    Hanging a leg off a number that looked about right is what put all six of
    them inside the silhouette. Solve it from the same profile the shell is
    lofted from — the lesson the salmon's eyes taught — and the leg starts on
    the shell no matter how the shell is retuned.
    """
    w, cx, d = bee_prof(t)
    k = min(1.0, abs(z - BEE_Z) / d)
    return s * (cx + w * (1.0 - k ** (BEE_E / 2.0)) ** (2.0 / BEE_E))


def bee_head_z(y, x):
    """The same solve on the head, for sitting the compound eyes on it."""
    t = max(0.0, min(1.0, (1.00 - y) / 0.21))
    w, d = lerp_profile(t, BEE_HW), lerp_profile(t, BEE_HD)
    k = min(1.0, abs(x) / w)
    return BEE_HZ + d * (1.0 - k ** (BEE_HE / 2.0)) ** (2.0 / BEE_HE)


# [height, depth, share of the running swing, how far forward it rakes].
# Front pair does the work, middle pair does nothing much, back pair carries.
BEE_ROWS = [(0.68, 0.17, 1.00, -0.40),
            (0.56, -0.04, 0.55, 0.02),
            (0.47, -0.24, 0.24, 0.40)]


def build_beetle():
    out = {}

    # wing cases: two hard domes meeting at a seam down the back
    ely = Mesh()
    for s in (-1.0, 1.0):
        rings = []
        n = 22
        for i in range(n):
            t = i / float(n - 1)
            w, cx, d = bee_prof(t)
            rings.append(section(s * cx, bee_y(t), BEE_Z, w, d, 16, e=BEE_E))
        ely.merge(loft(rings))
    out['bee_elytra'] = ely

    # The team colour has to hug the wing cases. A sphere laid over them only
    # pokes through where it happens to be bigger, which reads as a blob.
    # a short strip does not need many rings across it; the profile it follows
    # barely bends over a tenth of the body
    for name, lo, hi, swell, rings in (('bee_band', 0.16, 0.36, 1.03, 5),
                                       ('bee_trim', 0.36, 0.43, 1.035, 3)):
        m = Mesh()
        for s in (-1.0, 1.0):
            rows = []
            for i in range(rings):
                t = lo + (hi - lo) * i / float(rings - 1)
                w, cx, d = bee_prof(t)
                rows.append(section(s * cx, bee_y(t), BEE_Z,
                                    w * swell, d * swell, 16, e=BEE_E))
            m.merge(loft(rows, cap_start=False, cap_end=False))
        out[name] = m

    # The seam. Where the two cases meet is the one line that says "beetle"
    # about a brown oval, so it is a cord laid in the groove rather than a
    # painted stripe: it catches the light down one side and stays visible
    # when the body turns.
    path, radii = [], []
    for i in range(16):
        t = 0.015 + 0.955 * i / 15.0
        w, cx, d = bee_prof(t)
        k = (1.0 - min(1.0, cx / w) ** (BEE_E / 2.0)) ** (2.0 / BEE_E)
        path.append((0.0, bee_y(t), BEE_Z - d * k + 0.010))
        radii.append(0.020 * (1.0 - 0.5 * t))
    out['bee_seam'] = sweep(path, radii, 8)

    # the scutellum: the little triangle dropped in at the top of the seam
    scut = Mesh()
    w0, cx0, d0 = bee_prof(0.055)
    zs = BEE_Z - d0 * 0.92 + 0.012
    a = scut.vert(-0.062, bee_y(0.03), zs)
    b = scut.vert(0.062, bee_y(0.03), zs)
    c = scut.vert(0.0, bee_y(0.135), zs)
    e2 = scut.vert(0.0, bee_y(0.08), zs - 0.030)
    scut.tri(a, b, c)
    scut.tri(b, a, e2)
    scut.tri(c, b, e2)
    scut.tri(a, c, e2)
    out['bee_scut'] = scut

    # The shield. Trapezoid, glossier than the cases, and — unlike the version
    # this replaces — narrower than them, which is what lets the three parts of
    # him read as three parts instead of one brown lump.
    def prono_rings(lo, hi, n, swell=1.0):
        rs = []
        for i in range(n):
            t = lo + (hi - lo) * i / float(n - 1)
            rs.append(section(0.0, BEE_PTOP - (BEE_PTOP - BEE_PBOT) * t, BEE_PZ,
                              lerp_profile(t, BEE_PW) * swell,
                              lerp_profile(t, BEE_PD) * swell, 16, e=BEE_PE))
        return rs

    out['bee_prono'] = loft(prono_rings(0.0, 1.0, 14))
    # the team's colour on the shield, hugging it the way the saddle hugs the
    # cases — a disc laid over a trapezoid cuts its corners off
    out['bee_cband'] = loft(prono_rings(0.74, 0.86, 6, 1.035),
                            cap_start=False, cap_end=False)

    # the head, pushed out in front of the shield so that there is a face there
    rings = []
    n = 12
    for i in range(n):
        t = i / float(n - 1)
        rings.append(section(0.0, 1.00 - t * 0.21, BEE_HZ,
                             lerp_profile(t, BEE_HW), lerp_profile(t, BEE_HD),
                             14, e=BEE_HE))
    out['bee_head'] = loft(rings)

    # The head horn: up off the front of the head, forward over the shield,
    # then up — and forked, and each fork forked again. Four tips.
    horn = Mesh()
    shaft = bez((0.0, 0.97, 0.26), (0.0, 1.33, 0.40), (0.0, 1.38, 0.63), 13)
    horn.merge(sweep(shaft, [0.086 - 0.038 * (i / 12.0) for i in range(13)], 12))
    tip = shaft[-1]
    for s in (-1.0, 1.0):
        br = bez(tip, (s * 0.072, 1.47, 0.70), (s * 0.150, 1.45, 0.81), 10)
        horn.merge(sweep(br, [0.046 - 0.020 * (i / 9.0) for i in range(10)], 10))
        t2 = br[-1]
        # one prong up and in, one out and forward
        for dx, dy, dz in ((0.026, 0.086, 0.030), (0.076, 0.028, 0.052)):
            e = (t2[0] + s * dx, t2[1] + dy, t2[2] + dz)
            mid = ((t2[0] + e[0]) / 2, (t2[1] + e[1]) / 2 + 0.018, (t2[2] + e[2]) / 2)
            horn.merge(sweep(bez(t2, mid, e, 6),
                             [0.026, 0.022, 0.018, 0.013, 0.009, 0.005], 8))
    # the shorter thoracic horn off the shield, bifid like the real one. It
    # rides under the head horn and closes the gap between horn and body.
    th = bez((0.0, 1.09, 0.12), (0.0, 1.24, 0.28), (0.0, 1.22, 0.45), 9)
    horn.merge(sweep(th, [0.072 - 0.042 * (i / 8.0) for i in range(9)], 10))
    t3 = th[-1]
    for s in (-1.0, 1.0):
        e = (t3[0] + s * 0.050, t3[1] + 0.046, t3[2] + 0.056)
        mid = ((t3[0] + e[0]) / 2, (t3[1] + e[1]) / 2 + 0.010, (t3[2] + e[2]) / 2)
        horn.merge(sweep(bez(t3, mid, e, 6),
                         [0.030, 0.026, 0.021, 0.015, 0.010, 0.006], 8))
    out['bee_horn'] = horn

    # compound eyes, flat and black and entirely unreadable — solved onto the
    # head's surface so they sit in it rather than float off it
    eyes, glint = Mesh(), Mesh()
    for s in (-1.0, 1.0):
        ex, ey = s * 0.150, 0.900
        ez = bee_head_z(ey, ex)
        eyes.merge(ball(ex, ey, ez - 0.014, 0.068, 10))
        glint.merge(ball(ex + s * 0.016, ey + 0.028, ez + 0.030, 0.026, 8))
    out['bee_eye'] = eyes
    out['bee_glint'] = glint

    # The foreleg's shin. He digs with these, and the teeth down the outer edge
    # are why his front legs look nothing like his back ones. Authored from the
    # knee straight down -Y so it drops into the place limb() would otherwise
    # have put a plain cylinder: same joint, same angles, same length.
    for name, s in (('bee_tibL', 1.0), ('bee_tibR', -1.0)):
        tib = Mesh()
        rings = []
        n = 10
        for i in range(n):
            t = i / float(n - 1)
            r = 0.036 - 0.013 * t
            rings.append(section(0.0, -0.30 * t, 0.0, r, r * 0.82, 10, e=2.2))
        tib.merge(loft(rings))
        for j, ty in enumerate((0.11, 0.185, 0.255)):
            g = 1.0 - j * 0.16
            base = (s * 0.014, -ty, 0.0)
            end = (s * 0.078 * g, -ty - 0.030, 0.0)
            mid = ((base[0] + end[0]) / 2, (base[1] + end[1]) / 2, 0.004)
            tib.merge(sweep(bez(base, mid, end, 5),
                            [0.024 * g, 0.019 * g, 0.014 * g, 0.009 * g, 0.004], 7))
        out[name] = tib

    # Where the six legs hang. Solved against the shell here rather than typed
    # into the drawing code, so retuning the profile moves the legs with it.
    rows = []
    for y, z, k, rake in BEE_ROWS:
        t = (BEE_TOP - y) / (BEE_TOP - BEE_BOT)
        rows.append((bee_shell_x(t, z) - 0.014, y, z, k, rake))
    DATA.append('/* beetle leg anchors, solved against the wing-case profile:')
    DATA.append('   [x, y, z, share of the running swing, rake forward] */')
    DATA.append('const BEE_LEG = [%s];' % ', '.join(
        '[%.4g, %.4g, %.4g, %.3g, %.3g]' % r for r in rows))
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
    return out

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
    off = [lo[i] + 16000 * sc[i] for i in range(3)]
    d = {
        'sc': sc, 'off': off,
        'p': base64.b64encode(bytes(pb)).decode(),
        'n': base64.b64encode(bytes(nb)).decode(),
        'i': base64.b64encode(bytes(ib)).decode(),
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
