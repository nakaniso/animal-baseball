# Stance corrections: the hands were riding at head height right against the
# skull, and the front arm had to stretch a third of its length to reach across
# the chest. Narrower shoulders, longer arm bones, hands back at shoulder height
# behind the rear shoulder, and a head that stays pointed at the pitcher while
# the body turns under it.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)

# ---------- 30-actors.js: IK shoulders sit narrower, bones are longer ----------
p = 'src/30-actors.js'; s = rd(p)
a = """  if (p.handL || p.handR) {
    const [slx, slz] = L2W(f, -0.33 * big, 0);
    const [srx, srz] = L2W(f, 0.33 * big, 0);
    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], 0.26, 0.26, poleL, 0.095, uni, fur)
      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], 0.26, 0.26, poleR, 0.095, uni, fur)
      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);
  } else {"""
b = """  if (p.handL || p.handR) {
    // reaching arms hang off narrower shoulders and get a longer bone pair, so
    // the front arm can cross the chest to the knob without rubber-banding
    const SH = 0.24 * big, BONE = 0.32;
    const [slx, slz] = L2W(f, -SH, 0);
    const [srx, srz] = L2W(f, SH, 0);
    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.088, uni, fur)
      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.088, uni, fur)
      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);
  } else {"""
assert a in s, 'MISS ik shoulders'
s = s.replace(a, b)

# a smaller chest patch — the old one read as a bib in close-up
a = "  part(f, 'sphere', 0, y + 0.70, 0.13, 0.40, 0.44, 0.30, trim, p.lean || 0);"
b = "  part(f, 'sphere', 0, y + 0.66, 0.155, 0.34, 0.34, 0.22, trim, p.lean || 0);"
assert a in s, 'MISS chest'
s = s.replace(a, b)
wr(p, s)

# ---------- 50-main.js: rebuilt swing keys ----------
p = 'src/50-main.js'; s = rd(p)
a = """const SWING = [
  { t: 0.000, az: -232, tilt: 0.95, r: 0.30, gy: 1.15, ry: -0.34, lean: 0.05, spread: 0.05, lgL: 0.10, lgR: -0.10, shift: 0.00, head: 1.25 },
  { t: 0.032, az: -254, tilt: 1.08, r: 0.31, gy: 1.21, ry: -0.52, lean: 0.02, spread: 0.06, lgL: 0.13, lgR: -0.17, shift: -0.03, head: 1.30 },
  { t: 0.090, az: -92,  tilt: 0.02, r: 0.33, gy: 1.02, ry: 0.26,  lean: 0.14, spread: 0.15, lgL: -0.02, lgR: 0.07, shift: 0.11, head: 0.85 },
  { t: 0.200, az: -44,  tilt: -0.20, r: 0.32, gy: 1.08, ry: 0.70, lean: 0.17, spread: 0.16, lgL: -0.05, lgR: 0.09, shift: 0.13, head: 0.55 },
  { t: 0.520, az: 16,   tilt: 0.62, r: 0.23, gy: 1.31, ry: 1.10, lean: 0.09, spread: 0.12, lgL: -0.02, lgR: 0.05, shift: 0.11, head: 0.35 },
];"""
b = """const SWING = [
  { t: 0.000, az: -234, tilt: 0.92, r: 0.40, gy: 1.00, ry: -0.34, lean: 0.05, spread: 0.05, lgL: 0.10, lgR: -0.10, shift: 0.00, head: 1.64 },
  { t: 0.032, az: -252, tilt: 1.02, r: 0.42, gy: 1.05, ry: -0.52, lean: 0.02, spread: 0.06, lgL: 0.13, lgR: -0.17, shift: -0.03, head: 1.86 },
  { t: 0.090, az: -92,  tilt: 0.02, r: 0.34, gy: 1.00, ry: 0.26,  lean: 0.14, spread: 0.15, lgL: -0.02, lgR: 0.07, shift: 0.11, head: 0.79 },
  { t: 0.200, az: -44,  tilt: -0.18, r: 0.34, gy: 1.06, ry: 0.70, lean: 0.17, spread: 0.16, lgL: -0.05, lgR: 0.09, shift: 0.13, head: 0.15 },
  { t: 0.520, az: 18,   tilt: 0.66, r: 0.26, gy: 1.24, ry: 1.10, lean: 0.09, spread: 0.12, lgL: -0.02, lgR: 0.05, shift: 0.11, head: -0.15 },
];"""
assert a in s, 'MISS swing keys'
s = s.replace(a, b)
wr(p, s)
print('patched ok')
