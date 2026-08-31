# Three fixes:
#  1. the batted ball was hidden the instant it was hit (finishAtBat cleared
#     ball.vis for every outcome, not just strikeouts and walks)
#  2. runners cut straight across the infield instead of touching each bag
#  3. the batter did not actually hold the bat — the arms are now placed by IK
#     onto the bat handle, driven by a real keyframed swing
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def rep(s, a, b, label):
    if a not in s: raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

# ============================================================
# 1. ball visibility + 2. base paths
# ============================================================
p = 'src/40-game.js'; s = rd(p)
s = rep(s, """  G.order[G.half] = (G.order[G.half] + 1) % 9;
  G.ball.vis = false;
  setPhase('play', Math.max(1.5, playLength()));""",
"""  G.order[G.half] = (G.order[G.half] + 1) % 9;
  if (!G.flight) G.ball.vis = false;   // a batted ball stays on screen
  setPhase('play', Math.max(1.5, playLength()));""", 'ball vis')

s = rep(s, """function moveRunner(p, from, to, delay) {
  const a = basePt(from), b = basePt(to);
  const d = Math.hypot(a[0] - b[0], a[1] - b[1]);
  G.movers.push({
    p, from, to, t: -(delay || 0),
    dur: Math.max(0.5, d / (7.6 * (0.82 + p.speed * 0.36))),
    scored: to >= 3,
  });
}""",
"""/* A runner follows the base paths and touches every bag on the way, so a man
   on first going to third rounds second instead of cutting the corner. */
function moveRunner(p, from, to, delay) {
  const pts = [];
  for (let b = from; b <= to; b++) pts.push(basePt(b));
  if (pts.length < 2) pts.push(basePt(to));
  const segs = [];
  let total = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const d = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]);
    segs.push(d); total += d;
  }
  const legs = Math.max(1, to - from);
  const pace = 0.86 + p.speed * 0.30;
  G.movers.push({
    p, from, to, pts, segs, total, t: -(delay || 0),
    dur: (0.95 + 0.62 * (legs - 1)) / pace,
    scored: to >= 3,
  });
}""", 'moveRunner')
wr(p, s)

# ============================================================
# 3. arms that grip: two-bone IK in world space
# ============================================================
p = 'src/30-actors.js'; s = rd(p)
s = rep(s, """/* ---------- animal species ---------- */""",
"""/* Two-bone IK in world space: the hand lands exactly on the target, so whatever
   it is holding stays held. Cartoon arms stretch rather than fall short. */
function armIK(sx, sy, sz, hx, hy, hz, L1, L2, pole, rad, c, handC) {
  let dx = hx - sx, dy = hy - sy, dz = hz - sz;
  let d = Math.hypot(dx, dy, dz) || 1e-4;
  if (d > (L1 + L2) * 0.995) { const k = (d / (L1 + L2)) * 1.02; L1 *= k; L2 *= k; }
  const ux = dx / d, uy = dy / d, uz = dz / d;
  const a = clamp((d * d + L1 * L1 - L2 * L2) / (2 * d), -L1, L1);
  const h = Math.sqrt(Math.max(0, L1 * L1 - a * a));
  // project the pole hint onto the plane perpendicular to the shoulder->hand axis
  let px = pole[0], py = pole[1], pz = pole[2];
  const dot = px * ux + py * uy + pz * uz;
  px -= ux * dot; py -= uy * dot; pz -= uz * dot;
  let pl = Math.hypot(px, py, pz);
  if (pl < 1e-4) { px = -ux * uy; py = 1 - uy * uy; pz = -uz * uy; pl = Math.hypot(px, py, pz) || 1; }
  px /= pl; py /= pl; pz /= pl;
  const ex = sx + ux * a + px * h, ey = sy + uy * a + py * h, ez = sz + uz * a + pz * h;
  R.seg('cyl', sx, sy, sz, ex, ey, ez, rad, c);
  R.seg('cyl', ex, ey, ez, hx, hy, hz, rad * 0.9, c);
  R.b('sphere', ex, ey, ez, rad * 2, rad * 2, rad * 2, c);
  R.b('sphere', hx, hy, hz, rad * 2.5, rad * 2.3, rad * 2.5, handC || c);
  return [hx, hy, hz];
}

/* ---------- animal species ---------- */""", 'armIK')

# drawAnimal: leg spread, IK hands, a head that can turn on its own
s = rep(s, """  // legs
  limb(f, -0.155 * big, y + 0.44, 0, p.legL || 0, -0.04, 0.36, 0.115, uni, fur, 0.30);
  limb(f, 0.155 * big, y + 0.44, 0, p.legR || 0, 0.04, 0.36, 0.115, uni, fur, 0.30);""",
"""  // legs (local -x is the character's right side, +x their left)
  const sp = p.spread || 0;
  limb(f, -(0.155 * big + sp), y + 0.44, 0, p.legL || 0, -0.04, 0.36, 0.115, uni, fur, 0.30);
  limb(f, 0.155 * big + sp, y + 0.44, 0, p.legR || 0, 0.04, 0.36, 0.115, uni, fur, 0.30);""", 'legs')

s = rep(s, """  // arms
  const shY = y + 0.94;
  const hl = limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
  const hr = limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);

  // head
  const hy = y + 1.34;""",
"""  // arms — either swung by rotation, or aimed at a world-space grip
  const shY = y + 0.94;
  let hl, hr;
  if (p.handL || p.handR) {
    const [slx, slz] = L2W(f, -0.33 * big, 0);
    const [srx, srz] = L2W(f, 0.33 * big, 0);
    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], 0.26, 0.26, poleL, 0.095, uni, fur)
      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], 0.26, 0.26, poleR, 0.095, uni, fur)
      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);
  } else {
    hl = limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
    hr = limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);
  }

  // head — may be turned independently of the body (a batter watching the ball)
  const fh = p.headRy ? yawFrame(x, z, ry + p.headRy) : f;
  const hy = y + 1.34;""", 'arms')

# every head part draws in the head frame
head_block_old = """  part(f, 'sphere', 0, hy, 0.02, 0.68 * big, 0.66, 0.64 * big, fur);
  if (A.patch) { // panda eye patches
    part(f, 'sphere', -0.16, hy + 0.05, 0.24, 0.24, 0.26, 0.14, fur2);
    part(f, 'sphere', 0.16, hy + 0.05, 0.24, 0.24, 0.26, 0.14, fur2);
  }
  if (A.beak) {
    part(f, 'cone', 0, hy - 0.05, 0.34, 0.24, 0.26, 0.24, col(A.beak), -Math.PI / 2);
  } else {
    part(f, 'sphere', 0, hy - 0.09, 0.26, 0.30, 0.22, 0.22, fur2);
    part(f, 'sphere', 0, hy - 0.05, 0.34, 0.11, 0.09, 0.09, col('#2E2A2A'));
  }
  // eyes
  for (const s of [-1, 1]) {
    part(f, 'sphere', s * 0.145, hy + 0.06, 0.28, 0.115, 0.13, 0.09, col(EYE));
    part(f, 'sphere', s * 0.145 + 0.035, hy + 0.095, 0.315, 0.05, 0.05, 0.04, col(SHINE));
  }
  // ears
  if (A.ear === 'round') for (const s of [-1, 1]) {
    part(f, 'sphere', s * 0.26, hy + 0.26, -0.02, 0.26, 0.26, 0.20, fur);
    part(f, 'sphere', s * 0.26, hy + 0.27, 0.05, 0.15, 0.15, 0.10, fur2);
  }
  if (A.ear === 'point') for (const s of [-1, 1]) {
    part(f, 'cone', s * 0.21, hy + 0.34, -0.02, 0.26, 0.34, 0.20, fur, 0, s * 0.22);
    part(f, 'cone', s * 0.21, hy + 0.33, 0.03, 0.14, 0.22, 0.12, fur2, 0, s * 0.22);
  }
  if (A.ear === 'long') for (const s of [-1, 1]) {
    part(f, 'sphere', s * 0.15, hy + 0.44, -0.03, 0.17, 0.56, 0.15, fur, 0, s * 0.20);
    part(f, 'sphere', s * 0.16, hy + 0.45, 0.02, 0.09, 0.40, 0.08, fur2, 0, s * 0.20);
  }
  if (A.ear === 'toad') for (const s of [-1, 1]) {
    part(f, 'sphere', s * 0.19, hy + 0.26, 0.04, 0.28, 0.28, 0.28, fur);
    part(f, 'sphere', s * 0.19, hy + 0.30, 0.14, 0.15, 0.15, 0.10, col(EYE));
  }"""
assert head_block_old in s, 'MISS head block'
s = s.replace(head_block_old, head_block_old.replace("part(f, ", "part(fh, "))

cap_old = """  // cap
  part(f, 'dome', 0, hy + 0.24, 0.01, 0.70 * big, 0.42, 0.66 * big, cap);
  part(f, 'box', 0, hy + 0.235, 0.30, 0.44, 0.07, 0.30, cap);
  part(f, 'sphere', 0, hy + 0.44, 0.01, 0.09, 0.09, 0.09, trim);"""
s = rep(s, cap_old, cap_old.replace("part(f, ", "part(fh, "), 'cap frame')

# ---------- the bat ----------
s = rep(s, """/* bat: pivot at the hands, barrel aimed at `ang` (0 = toward centre field) */
function drawBat(x, z, ry, ang, tilt, c1, c2) {
  const px = x, pz = z, py = 1.02;
  const dx = Math.sin(ang), dz = Math.cos(ang);
  const len = 0.98, up = Math.sin(tilt || 0) * len;
  R.d('taper', px + dx * len * 0.5, py + up * 0.5, pz + dz * len * 0.5,
      -Math.PI / 2 + (tilt || 0), ang, 0, 0.115, len, 0.115, col(c1));
  R.b('sphere', px, py, pz, 0.12, 0.12, 0.12, col(c2));
}""",
"""/* Bat built along a grip point and a direction, so the hands can be placed on
   the handle rather than the bat being parked near them. */
function drawBatRig(grip, dir, len, wood, tape) {
  const P = (t) => [grip[0] + dir[0] * t, grip[1] + dir[1] * t, grip[2] + dir[2] * t];
  const knob = P(-0.055), hEnd = P(0.30), shoulder = P(0.30), tip = P(len);
  const w = col(wood), g = col(tape);
  R.seg('cyl', knob[0], knob[1], knob[2], hEnd[0], hEnd[1], hEnd[2], 0.024, g);
  R.seg('taper', tip[0], tip[1], tip[2], shoulder[0], shoulder[1], shoulder[2], 0.047, w);
  R.b('sphere', knob[0], knob[1], knob[2], 0.078, 0.062, 0.078, g);
  R.b('sphere', tip[0], tip[1], tip[2], 0.092, 0.092, 0.092, w);
}""", 'drawBatRig')
wr(p, s)
print('patched ok')
