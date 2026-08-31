# The grip was placed by azimuth and radius around the spine, which pushed the
# hands so far from the chest that the front arm locked out straight and the
# bat read as balanced on the paws rather than held. The rig now names the grip
# point directly, the shoulders sit narrower, and the bat is built to real
# proportions (2.5cm handle, 6.5cm barrel) instead of a uniform club.
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
# 30-actors.js — slimmer reaching arms, a properly turned bat
# ============================================================
box, rep = mk('src/30-actors.js')
rep("    const SH = 0.24 * big, BONE = 0.32;",
    "    const SH = 0.17 * big, BONE = 0.32;", 'shoulders')
rep("""      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.088, uni, hand)""",
    """      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.075, uni, hand)""", 'armL')
rep("""      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.088, uni, hand)""",
    """      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.075, uni, hand)""", 'armR')
rep("  R.b('sphere', hx, hy, hz, rad * 2.5, rad * 2.3, rad * 2.5, handC || c);",
    "  R.b('sphere', hx, hy, hz, rad * 2.2, rad * 2.1, rad * 2.2, handC || c);", 'hand size')

rep("""/* Bat built along a grip point and a direction, so the hands can be placed on
   the handle rather than the bat being parked near them. */
function drawBatRig(grip, dir, len, wood, tape) {
  const P = (t) => [grip[0] + dir[0] * t, grip[1] + dir[1] * t, grip[2] + dir[2] * t];
  const knob = P(-0.055), hEnd = P(0.30), shoulder = P(0.30), tip = P(len);
  const w = col(wood), g = col(tape);
  R.seg('cyl', knob[0], knob[1], knob[2], hEnd[0], hEnd[1], hEnd[2], 0.024, g);
  R.seg('taper', tip[0], tip[1], tip[2], shoulder[0], shoulder[1], shoulder[2], 0.047, w);
  R.b('sphere', knob[0], knob[1], knob[2], 0.078, 0.062, 0.078, g);
  R.b('sphere', tip[0], tip[1], tip[2], 0.092, 0.092, 0.092, w);
}""",
"""/* A bat to real proportions: 2.5cm handle, a taper, a 6.5cm barrel, knob at the
   bottom. `grip` is where the bottom hand sits, `dir` points at the barrel. */
function drawBatRig(grip, dir, len, wood, tape) {
  const P = (t) => [grip[0] + dir[0] * t, grip[1] + dir[1] * t, grip[2] + dir[2] * t];
  const w = col(wood), g = col(tape);
  const knob = P(-0.055), hEnd = P(0.34), taper = P(0.60), tip = P(len);
  R.seg('cyl', knob[0], knob[1], knob[2], hEnd[0], hEnd[1], hEnd[2], 0.017, g);
  R.seg('taper', taper[0], taper[1], taper[2], hEnd[0], hEnd[1], hEnd[2], 0.033, w);
  R.seg('cyl', taper[0], taper[1], taper[2], tip[0], tip[1], tip[2], 0.033, w);
  R.b('sphere', tip[0], tip[1], tip[2], 0.070, 0.070, 0.070, w);
  const k2 = P(-0.02);
  R.seg('cyl', knob[0], knob[1], knob[2], k2[0], k2[1], k2[2], 0.031, g);
}

/* the two fists wrapped around the handle */
function drawGrip(grip, dir, at, c) {
  const P = (t) => [grip[0] + dir[0] * t, grip[1] + dir[1] * t, grip[2] + dir[2] * t];
  const a = P(at - 0.055), b = P(at + 0.055);
  R.seg('sphere', a[0], a[1], a[2], b[0], b[1], b[2], 0.082, col(c));
}""", 'bat model')
wr('src/30-actors.js', box['s'])

# ============================================================
# 50-main.js — grip placed by coordinate, not by radius
# ============================================================
box, rep = mk('src/50-main.js')
rep("""const BAT_LEN = 0.98;
const SWING = [
  { t: 0.000, az: -234, tilt: 0.92, r: 0.40, gy: 1.00, ry: -0.34, lean: 0.05, spread: 0.05, lgL: 0.10, lgR: -0.10, shift: 0.00, head: 1.64 },
  { t: 0.032, az: -252, tilt: 1.02, r: 0.42, gy: 1.05, ry: -0.52, lean: 0.02, spread: 0.06, lgL: 0.13, lgR: -0.17, shift: -0.03, head: 1.86 },
  { t: 0.090, az: -92,  tilt: 0.02, r: 0.34, gy: 1.00, ry: 0.26,  lean: 0.14, spread: 0.15, lgL: -0.02, lgR: 0.07, shift: 0.11, head: 0.79 },
  { t: 0.200, az: -44,  tilt: -0.18, r: 0.34, gy: 1.06, ry: 0.70, lean: 0.17, spread: 0.16, lgL: -0.05, lgR: 0.09, shift: 0.13, head: 0.15 },
  { t: 0.520, az: 18,   tilt: 0.66, r: 0.26, gy: 1.24, ry: 1.10, lean: 0.09, spread: 0.12, lgL: -0.02, lgR: 0.05, shift: 0.11, head: -0.15 },
];""",
"""const BAT_LEN = 0.98;
/* gx/gy/gz put the bottom hand at an explicit point (gx and gz are offsets from
   the batter's spot); az/tilt aim the barrel from there. px/py/pz hint which
   way the elbows break. */
const SWING = [
  { t: 0.000, gx: 0.13, gy: 1.05, gz: -0.40, az: 145, tilt: 0.95, ry: -0.34, lean: 0.05, spread: 0.05, lgL: 0.10, lgR: -0.10, shift: 0.00, head: 1.64, px: 0.35, py: -0.70, pz: -0.45 },
  { t: 0.032, gx: 0.17, gy: 1.10, gz: -0.48, az: 152, tilt: 1.05, ry: -0.50, lean: 0.02, spread: 0.06, lgL: 0.13, lgR: -0.17, shift: -0.03, head: 1.86, px: 0.40, py: -0.65, pz: -0.50 },
  { t: 0.090, gx: -0.40, gy: 1.00, gz: 0.05, az: -90, tilt: 0.02, ry: 0.26, lean: 0.14, spread: 0.15, lgL: -0.02, lgR: 0.07, shift: 0.11, head: 0.79, px: 0.20, py: -0.90, pz: 0.10 },
  { t: 0.200, gx: -0.20, gy: 1.06, gz: 0.30, az: -40, tilt: -0.15, ry: 0.70, lean: 0.17, spread: 0.16, lgL: -0.05, lgR: 0.09, shift: 0.13, head: 0.15, px: 0.10, py: -0.90, pz: 0.30 },
  { t: 0.520, gx: 0.05, gy: 1.26, gz: 0.34, az: 45, tilt: 0.75, ry: 1.10, lean: 0.09, spread: 0.12, lgL: -0.02, lgR: 0.05, shift: 0.11, head: -0.15, px: 0.10, py: -0.75, pz: 0.45 },
];""", 'swing keys')

rep("""  if (t < 0) {
    k = Object.assign({}, SWING[0]);           // waiting: a small bat waggle
    k.az += Math.sin(clk * 2.4) * 5.5;
    k.tilt += Math.sin(clk * 2.4 + 0.6) * 0.07;
    k.gy += Math.sin(clk * 1.9) * 0.014;
  } else {""",
"""  if (t < 0) {
    k = Object.assign({}, SWING[0]);           // waiting: a small bat waggle
    k.az += Math.sin(clk * 2.4) * 6.0;
    k.tilt += Math.sin(clk * 2.4 + 0.6) * 0.08;
    k.gy += Math.sin(clk * 1.9) * 0.015;
    k.gz += Math.sin(clk * 1.9 + 1.1) * 0.012;
  } else {""", 'waggle')

rep("""  const az = k.az * DEG;
  const hx = Math.sin(az), hz = Math.cos(az);
  const bx = BAT_X, bz = BAT_Z + k.shift;
  const grip = [bx + hx * k.r, k.gy, bz + hz * k.r];
  const ct = Math.cos(k.tilt), st = Math.sin(k.tilt);
  const dir = [hx * ct, st, hz * ct];
  const on = (d) => [grip[0] + dir[0] * d, grip[1] + dir[1] * d, grip[2] + dir[2] * d];
  k.grip = grip; k.dir = dir; k.bx = bx; k.bz = bz;
  // right-handed hitter: left hand on the knob, right hand above it. The
  // character's left arm is its local +x side, which faces the pitcher.
  k.handTop = on(0.17);
  k.handBot = on(0.035);
  k.pole = [hx * 0.5, -1, hz * 0.5];
  return k;""",
"""  const az = k.az * DEG, ct = Math.cos(k.tilt), st = Math.sin(k.tilt);
  const grip = [BAT_X + k.gx, k.gy, BAT_Z + k.gz];
  const dir = [Math.sin(az) * ct, st, Math.cos(az) * ct];
  const on = (d) => [grip[0] + dir[0] * d, grip[1] + dir[1] * d, grip[2] + dir[2] * d];
  k.grip = grip; k.dir = dir; k.bx = BAT_X; k.bz = BAT_Z + k.shift;
  // right-handed hitter: left hand at the knob, right hand above it. The
  // character's local +x side faces the pitcher, so that is the left arm.
  k.topAt = 0.20; k.botAt = 0.06;
  k.handTop = on(k.topAt);
  k.handBot = on(k.botAt);
  k.pole = [k.px, k.py, k.pz];
  return k;""", 'rig math')

rep("""    drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');""",
"""    drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');
    drawGrip(rig.grip, rig.dir, rig.botAt, bt.trim);
    drawGrip(rig.grip, rig.dir, rig.topAt, bt.trim);""", 'grips')
wr('src/50-main.js', box['s'])
print('patched ok')
