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

# ----------------------------------------------------------------- mesh core


class Mesh(object):
    def __init__(self):
        self.v = []      # [x, y, z]
        self.f = []      # [i, j, k]

    def vert(self, x, y, z):
        self.v.append((x, y, z))
        return len(self.v) - 1

    def tri(self, a, b, c):
        self.f.append((a, b, c))

    def quad(self, a, b, c, d):
        self.tri(a, b, c)
        self.tri(a, c, d)

    def merge(self, other):
        n = len(self.v)
        self.v.extend(other.v)
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
        # a stable frame: x stays across the body, the other axis follows
        ux, uy, uz = 1.0, 0.0, 0.0
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
    band = Mesh()
    N, SEC = 46, 18
    for side, centre in ((-1, 4), (1, 14)):
        rows = []
        for i in range(N):
            t = 0.13 + (i / float(N - 1)) * 0.66
            # a lens: wraps furthest round the flank at the middle of the run
            spread = 2.6 * math.sin(math.pi * (i / float(N - 1))) ** 0.75
            y = 1.30 - t * 1.30
            d = lerp_profile(t, SAL_DEPTH) * 1.022
            w = lerp_profile(t, SAL_WIDTH) * 1.022
            cz = lerp_profile(t, SAL_SHIFT)
            ring = section(0.0, y, cz, w, d, SEC, e=2.35, back_flat=0.86)
            k0 = int(round(centre - spread))
            k1 = int(round(centre + spread))
            rows.append([ring[j % SEC] for j in range(k0, k1 + 1)])
        width = min(len(r) for r in rows)
        rows = [r[:width] for r in rows]
        idx = [[band.vert(*q) for q in r] for r in rows]
        for k in range(len(rows) - 1):
            a, b = idx[k], idx[k + 1]
            for i in range(width - 1):
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


# ------------------------------------------------------------------- beetle
# Canonical pose: standing, elytra to the back (-Z), head and horn forward
# (+Z). The six legs stay as animated primitives; only the shell is baked.

def build_beetle():
    out = {}

    # elytra: two hard cases, domed along the back and meeting at a seam
    ely = Mesh()
    for s in (-1.0, 1.0):
        rings = []
        n = 20
        for i in range(n):
            t = i / float(n - 1)
            y = 1.03 - t * 0.75
            w = 0.140 * math.sin(math.pi * (0.12 + 0.80 * t)) ** 0.55
            d = 0.285 * math.sin(math.pi * (0.10 + 0.82 * t)) ** 0.45
            rings.append(section(s * 0.108 * (1.0 - 0.58 * t), y, -0.03, w, d,
                                 14, e=2.6, back_flat=1.0))
        ely.merge(loft(rings))
    out['bee_elytra'] = ely

    # The team colour has to hug the wing cases. A sphere laid over them only
    # pokes through where it happens to be bigger, which reads as a blob.
    def ely_rings(swell, lo, hi, n=14):
        rs = []
        for i in range(n):
            t = lo + (hi - lo) * i / float(n - 1)
            y = 1.03 - t * 0.75
            w = 0.140 * math.sin(math.pi * (0.12 + 0.80 * t)) ** 0.55 * swell
            d = 0.285 * math.sin(math.pi * (0.10 + 0.82 * t)) ** 0.45 * swell
            rs.append((y, w, d))
        return rs

    for name, lo, hi, sw in (('bee_band', 0.13, 0.32, 1.03),
                             ('bee_trim', 0.32, 0.39, 1.035)):
        m = Mesh()
        for s2 in (-1.0, 1.0):
            rows = []
            for j, (y, w, d) in enumerate(ely_rings(sw, lo, hi)):
                t = lo + (hi - lo) * j / 13.0
                rows.append(section(s2 * 0.108 * (1.0 - 0.58 * t), y, -0.03, w, d, 14, e=2.6))
            m.merge(loft(rows, cap_start=False, cap_end=False))
        out[name] = m

    # pronotum: the shield, wider than head or cases
    rings = []
    n = 12
    for i in range(n):
        t = i / float(n - 1)
        y = 1.24 - t * 0.28
        w = 0.265 * math.sin(math.pi * (0.20 + 0.66 * t)) ** 0.40
        d = 0.275 * math.sin(math.pi * (0.22 + 0.62 * t)) ** 0.40
        rings.append(section(0.0, y, -0.02, w, d, 16, e=2.8, back_flat=1.0))
    out['bee_prono'] = loft(rings)

    # the head, small and low and tucked under the horn
    rings = []
    n = 10
    for i in range(n):
        t = i / float(n - 1)
        rings.append(section(0.0, 1.02 - t * 0.20, 0.16,
                             0.20 * math.sin(math.pi * (0.22 + 0.60 * t)) ** 0.4,
                             0.17 * math.sin(math.pi * (0.24 + 0.58 * t)) ** 0.4,
                             14, e=2.6))
    out['bee_head'] = loft(rings)

    # the horn: up, forward, forked — and each fork forks again. That double
    # fork is what makes it a Trypoxylus and not any old beetle.
    horn = Mesh()
    main = bez((0.0, 0.94, 0.20), (0.0, 1.18, 0.34), (0.0, 1.24, 0.48), 11)
    horn.merge(sweep(main, [0.075 - 0.040 * (i / 10.0) for i in range(11)], 10))
    tip = main[-1]
    for s in (-1.0, 1.0):
        br = bez(tip, (s * 0.050, 1.30, 0.54), (s * 0.092, 1.31, 0.62), 8)
        horn.merge(sweep(br, [0.036 - 0.014 * (i / 7.0) for i in range(8)], 8))
        t2 = br[-1]
        for dx, dy, dz in ((0.024, 0.058, 0.042), (0.058, 0.016, 0.038)):
            e = (t2[0] + s * dx, t2[1] + dy, t2[2] + dz)
            mid = ((t2[0] + e[0]) / 2, (t2[1] + e[1]) / 2 + 0.012, (t2[2] + e[2]) / 2)
            horn.merge(sweep(bez(t2, mid, e, 5),
                             [0.021, 0.017, 0.013, 0.009, 0.005], 7))
    # the smaller thoracic horn that comes off the shield
    horn.merge(sweep(bez((0.0, 1.10, 0.10), (0.0, 1.22, 0.24), (0.0, 1.18, 0.34), 7),
                     [0.058, 0.050, 0.042, 0.034, 0.026, 0.018, 0.010], 8))
    out['bee_horn'] = horn

    eyes, glint = Mesh(), Mesh()
    for s in (-1.0, 1.0):
        eyes.merge(ball(s * 0.130, 0.905, 0.175, 0.048, 10))
        glint.merge(ball(s * 0.146, 0.928, 0.202, 0.019, 8))
    out['bee_eye'] = eyes
    out['bee_glint'] = glint
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
    return {
        'sc': sc, 'off': off,
        'p': base64.b64encode(bytes(pb)).decode(),
        'n': base64.b64encode(bytes(nb)).decode(),
        'i': base64.b64encode(bytes(ib)).decode(),
        'nv': len(m.v), 'nf': len(m.f),
    }


def main():
    meshes = {}
    meshes.update(build_salmon())
    meshes.update(build_beetle())

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
        out.append("  '%s');   // %d verts, %d tris" % (d['i'], d['nv'], d['nf']))
        out.append('')
        print('  %-12s %5d verts %5d tris' % (name, d['nv'], d['nf']))

    io.open('src/15-meshes.js', 'w', encoding='utf-8').write('\n'.join(out))
    kb = os.path.getsize('src/15-meshes.js') / 1024.0
    print('src/15-meshes.js  %d verts, %d tris, %.0f KB' % (total_v, total_f, kb))
    if total_v > 60000:
        print('!! the shared index buffer is Uint16: keep the total under 65536')


main()
