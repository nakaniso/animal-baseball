# Character pass from the reference sketch: a rounded-box head, a big oval
# muzzle with the nose set into it, brow lines, small semicircular ears high on
# the corners of the head, pinstriped jersey with a belt, dark shoes and short
# thick arms. The head shape and face come from a per-species table so the bear
# matches the drawing while the others keep their own identity.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def mk(path):
    box = {'s': rd(path)}
    def rep(a, b, label):
        if a not in box['s']: raise SystemExit('MISS %s: %s' % (path, label))
        box['s'] = box['s'].replace(a, b)
    return box, rep

# ============================================================
# 10-core.js — a rounded-box primitive (superellipsoid)
# ============================================================
box, rep = mk('src/10-core.js')
rep("""/* extruded polygon: pts are [x,z] wound counter-clockwise seen from above,""",
"""/* Rounded box — a superellipsoid with |x|^4+|y|^4+|z|^4 = 1. Heads drawn as a
   soft square read far more like a drawn character than a plain sphere does. */
geoPart('rbox', (v, t) => {
  const RN = 10, SN = 16, e = 0.5;
  const pw = (a, k) => (a < 0 ? -Math.pow(-a, k) : Math.pow(a, k));
  for (let r = 0; r <= RN; r++) {
    const phi = (r / RN) * Math.PI, sp = Math.sin(phi), cp = Math.cos(phi);
    for (let s = 0; s <= SN; s++) {
      const th = (s / SN) * Math.PI * 2;
      const x = pw(sp, e) * pw(Math.cos(th), e);
      const y = pw(cp, e);
      const z = pw(sp, e) * pw(Math.sin(th), e);
      const nx = x * x * x, ny = y * y * y, nz = z * z * z;
      const l = Math.hypot(nx, ny, nz) || 1;
      v(x * 0.5, y * 0.5, z * 0.5, nx / l, ny / l, nz / l);
    }
  }
  for (let r = 0; r < RN; r++) for (let s = 0; s < SN; s++) {
    const a = r * (SN + 1) + s, b = a + SN + 1;
    t(a, b, a + 1); t(a + 1, b, b + 1);
  }
});

/* extruded polygon: pts are [x,z] wound counter-clockwise seen from above,""", 'rbox')
wr('src/10-core.js', box['s'])

# ============================================================
# 30-actors.js — the character rig
# ============================================================
box, rep = mk('src/30-actors.js')

# feet can be foot-shaped rather than round
rep("""function limb(f, jx, jy, jz, rx, rz, len, rad, c, endC, endS) {""",
    """function limb(f, jx, jy, jz, rx, rz, len, rad, c, endC, endS, flat) {""", 'limb sig')
rep("""  if (endC) {
    const s = endS || rad * 2.5;
    part(f, 'sphere', jx + dx * len, jy + dy * len, jz + dz * len, s, s * 0.9, s, endC);
  }""",
"""  if (endC) {
    const s = endS || rad * 2.5;
    if (flat) part(f, 'rbox', jx + dx * len, jy + dy * len - s * 0.08, jz + dz * len + s * 0.16,
                   s * 0.92, s * 0.66, s * 1.34, endC, rx, rz);
    else part(f, 'sphere', jx + dx * len, jy + dy * len, jz + dz * len, s, s * 0.9, s, endC);
  }""", 'limb foot')

# per-species head and face
rep("""const ANIMALS = {
  bear:    { ear: 'round',  fur: '#9A7150', fur2: '#D9BC96', belly: 1, tail: 'nub' },""",
"""/* hw/hh/hd scale the head; muz is the size of the muzzle; brow adds the drawn
   eyebrow strokes; earR/earX/earY place the ears. */
const ANIMALS = {
  bear:    { ear: 'round',  fur: '#9A7150', fur2: '#CDA87E', belly: 1, tail: 'nub',
             head: 'rbox', hw: 1.16, hh: 1.08, hd: 1.00,
             muz: [0.50, 0.40, 0.32], muzY: -0.11, muzZ: 0.24, noseR: 0.13,
             brow: 1, earR: 0.25, earX: 0.325, earY: 0.30, earD: 0.62,
             eyeX: 0.165, eyeW: 0.175, eyeH: 0.155 },""", 'bear spec')

rep("""  const hy = y + 1.34;
  part(fh, 'sphere', 0, hy, 0.02, 0.68 * big, 0.66, 0.64 * big, fur);
  if (A.patch) { // panda eye patches
    part(fh, 'sphere', -0.16, hy + 0.05, 0.24, 0.24, 0.26, 0.14, fur2);
    part(fh, 'sphere', 0.16, hy + 0.05, 0.24, 0.24, 0.26, 0.14, fur2);
  }
  if (A.beak) {
    part(fh, 'cone', 0, hy - 0.05, 0.34, 0.24, 0.26, 0.24, col(A.beak), -Math.PI / 2);
  } else {
    part(fh, 'sphere', 0, hy - 0.09, 0.26, 0.30, 0.22, 0.22, fur2);
    part(fh, 'sphere', 0, hy - 0.05, 0.34, 0.11, 0.09, 0.09, col('#2E2A2A'));
  }
  // eyes
  for (const s of [-1, 1]) {
    part(fh, 'sphere', s * 0.145, hy + 0.06, 0.28, 0.115, 0.13, 0.09, col(EYE));
    part(fh, 'sphere', s * 0.145 + 0.035, hy + 0.095, 0.315, 0.05, 0.05, 0.04, col(SHINE));
  }
  // ears
  if (A.ear === 'round') for (const s of [-1, 1]) {
    part(fh, 'sphere', s * 0.26, hy + 0.26, -0.02, 0.26, 0.26, 0.20, fur);
    part(fh, 'sphere', s * 0.26, hy + 0.27, 0.05, 0.15, 0.15, 0.10, fur2);
  }""",
"""  const hy = y + 1.34;
  const HW = A.hw || 1, HH = A.hh || 1, HD = A.hd || 1;
  const hzF = 0.32 * HD + 0.02;                 // where the front of the face is
  part(fh, A.head || 'sphere', 0, hy, 0.02, 0.68 * big * HW, 0.66 * HH, 0.64 * big * HD, fur);
  if (A.patch) { // panda eye patches
    part(fh, 'sphere', -0.16, hy + 0.05, 0.24, 0.24, 0.26, 0.14, fur2);
    part(fh, 'sphere', 0.16, hy + 0.05, 0.24, 0.24, 0.26, 0.14, fur2);
  }
  if (A.beak) {
    part(fh, 'cone', 0, hy - 0.05, 0.34, 0.24, 0.26, 0.24, col(A.beak), -Math.PI / 2);
  } else {
    // a big soft muzzle with the nose sunk into the top of it
    const mz = A.muz || [0.30, 0.22, 0.22];
    const my = hy + (A.muzY === undefined ? -0.09 : A.muzY);
    const mzz = A.muzZ === undefined ? 0.26 : A.muzZ;
    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], fur2);
    const nr = A.noseR || 0.11;
    part(fh, 'sphere', 0, my + mz[1] * 0.24, mzz + mz[2] * 0.42,
         nr, nr * 0.80, nr * 0.80, col('#33291F'));
  }
  // eyes, with the drawn brow line above them
  const ex = A.eyeX || 0.145, ew = A.eyeW || 0.115, eh = A.eyeH || 0.13;
  for (const s of [-1, 1]) {
    part(fh, 'sphere', s * ex, hy + 0.07, hzF - 0.03, ew, eh, 0.10, col(EYE));
    part(fh, 'sphere', s * ex + 0.035, hy + 0.105, hzF + 0.005, 0.05, 0.05, 0.04, col(SHINE));
    if (A.brow)
      part(fh, 'box', s * ex, hy + 0.215, hzF - 0.035, 0.215, 0.048, 0.07,
           shade(A.fur, 0.48), 0, s * 0.13);
  }
  // ears
  if (A.ear === 'round') {
    const er = A.earR || 0.26, exx = A.earX || 0.26, eyy = A.earY || 0.26, ed = A.earD || 0.77;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, -0.02, er, er, er * ed, fur);
      part(fh, 'sphere', s * exx, hy + eyy + 0.01, 0.04, er * 0.55, er * 0.55, er * 0.5, fur2);
    }
  }""", 'head face')

# jersey: pinstripes and a belt, dark shoes, thicker arms
rep("""  part(f, 'sphere', 0, y + 0.97, 0.01, 0.50, 0.14, 0.45, trim);   // jersey collar
  part(f, 'box', 0, y + 0.72, 0.185, 0.075, 0.42, 0.05, trim);  // button placket""",
"""  part(f, 'sphere', 0, y + 0.97, 0.01, 0.50, 0.14, 0.45, trim);   // jersey collar
  part(f, 'box', 0, y + 0.72, 0.185, 0.075, 0.42, 0.05, trim);  // button placket
  // pinstripes down the front, and the belt at the waist
  const stripe = shade(look.uni, 0.80);
  for (const i of [-2, -1, 1, 2]) {
    const px = i * 0.098 * big;
    const k = Math.max(0, 1 - (px / (0.34 * big)) ** 2);
    part(f, 'box', px, y + 0.74, 0.28 * big * Math.sqrt(k) - 0.01, 0.026, 0.34, 0.035, stripe);
  }
  part(f, 'sphere', 0, y + 0.515, 0.02, 0.60 * big, 0.10, 0.50 * big, shade(look.cap, 0.85));""", 'jersey')

rep("""  const sp = p.spread || 0;
  limb(f, -(0.155 * big + sp), y + 0.44, 0, p.legL || 0, -0.04, 0.36, 0.115, uni, fur, 0.30);
  limb(f, 0.155 * big + sp, y + 0.44, 0, p.legR || 0, 0.04, 0.36, 0.115, uni, fur, 0.30);""",
"""  const sp = p.spread || 0;
  const pant = shade(look.uni, 0.93), shoe = shade(look.cap, 0.66);
  limb(f, -(0.155 * big + sp), y + 0.44, 0, p.legL || 0, -0.04, 0.36, 0.12, pant, shoe, 0.30, 1);
  limb(f, 0.155 * big + sp, y + 0.44, 0, p.legR || 0, 0.04, 0.36, 0.12, pant, shoe, 0.30, 1);""", 'legs')

rep("""    hl = limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
    hr = limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);
  }""",
"""    hl = limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.34, 0.112, uni, fur, 0.27);
    hr = limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.34, 0.112, uni, fur, 0.27);
  }""", 'arms thick')
rep("""      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);""",
"""      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.34, 0.112, uni, fur, 0.27);""", 'arms thick 2')
rep("""      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);""",
"""      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.34, 0.112, uni, fur, 0.27);""", 'arms thick 3')
wr('src/30-actors.js', box['s'])
print('patched ok')
