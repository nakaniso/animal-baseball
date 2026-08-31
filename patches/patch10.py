# The batting rig: a keyframed swing drives the bat, and the batter's hands are
# placed on the bat handle by IK, so he is genuinely holding it through stance,
# load, contact, extension and follow-through. Also draws runners along the
# base-path polyline built by moveRunner.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

p = 'src/50-main.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b)

rep("""function batAngle() {
  const t = G.batSwingT;
  if (t < 0) return { ang: -215 * DEG, tilt: 0.85 };
  const p = clamp(t / 0.36, 0, 1);
  if (p < 0.265) return { ang: lerp(-215, -90, p / 0.265) * DEG, tilt: lerp(0.85, 0, p / 0.265) };
  return { ang: lerp(-90, -2, (p - 0.265) / 0.735) * DEG, tilt: lerp(0, -0.25, (p - 0.265) / 0.735) };
}

function runnerAt(m) {
  const a = basePt(m.from), b = basePt(m.to);
  const u = clamp(m.t / m.dur, 0, 1);
  const e = u * u * (3 - 2 * u);
  return { x: lerp(a[0], b[0], e), z: lerp(a[1], b[1], e), done: u >= 1, u };
}""",
"""/* ---------- the swing ----------
   Keyframes in seconds from the press. Contact lands at 0.090s, which is
   SWING_LAG, so the barrel is in the zone exactly when the hit is judged.
     az    bat azimuth, degrees (0 = toward centre field)
     tilt  barrel elevation
     r/gy  where the hands ride: radius from the spine, and height
     ry    body turn, added to the batter's facing
     shift stride toward the pitcher                                        */
const BAT_LEN = 0.98;
const SWING = [
  { t: 0.000, az: -232, tilt: 0.95, r: 0.30, gy: 1.15, ry: -0.34, lean: 0.05, spread: 0.05, lgL: 0.10, lgR: -0.10, shift: 0.00, head: 1.25 },
  { t: 0.032, az: -254, tilt: 1.08, r: 0.31, gy: 1.21, ry: -0.52, lean: 0.02, spread: 0.06, lgL: 0.13, lgR: -0.17, shift: -0.03, head: 1.30 },
  { t: 0.090, az: -92,  tilt: 0.02, r: 0.33, gy: 1.02, ry: 0.26,  lean: 0.14, spread: 0.15, lgL: -0.02, lgR: 0.07, shift: 0.11, head: 0.85 },
  { t: 0.200, az: -44,  tilt: -0.20, r: 0.32, gy: 1.08, ry: 0.70, lean: 0.17, spread: 0.16, lgL: -0.05, lgR: 0.09, shift: 0.13, head: 0.55 },
  { t: 0.520, az: 16,   tilt: 0.62, r: 0.23, gy: 1.31, ry: 1.10, lean: 0.09, spread: 0.12, lgL: -0.02, lgR: 0.05, shift: 0.11, head: 0.35 },
];

function batterRig(t, clk) {
  let k;
  if (t < 0) {
    k = Object.assign({}, SWING[0]);           // waiting: a small bat waggle
    k.az += Math.sin(clk * 2.4) * 5.5;
    k.tilt += Math.sin(clk * 2.4 + 0.6) * 0.07;
    k.gy += Math.sin(clk * 1.9) * 0.014;
  } else {
    const last = SWING[SWING.length - 1];
    const tt = Math.min(t, last.t);
    let i = 0;
    while (i < SWING.length - 2 && tt > SWING[i + 1].t) i++;
    const a = SWING[i], b = SWING[i + 1];
    const u = clamp((tt - a.t) / (b.t - a.t), 0, 1);
    const e = u * u * (3 - 2 * u);
    k = {};
    for (const key in a) k[key] = lerp(a[key], b[key], e);
  }
  const az = k.az * DEG;
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
  return k;
}

/* runners follow the base-path polyline, touching every bag */
function runnerAt(m) {
  const u = clamp(m.t / m.dur, 0, 1);
  const e = u * u * (3 - 2 * u);
  let d = e * m.total;
  const n = m.segs.length;
  for (let i = 0; i < n; i++) {
    if (d <= m.segs[i] || i === n - 1) {
      const k = m.segs[i] > 1e-6 ? clamp(d / m.segs[i], 0, 1) : 1;
      const a = m.pts[i], b = m.pts[i + 1];
      return { x: lerp(a[0], b[0], k), z: lerp(a[1], b[1], k), done: u >= 1, u,
               ry: Math.atan2(b[0] - a[0], b[1] - a[1]) };
    }
    d -= m.segs[i];
  }
  return { x: m.pts[0][0], z: m.pts[0][1], done: u >= 1, u, ry: 0 };
}""", 'swing rig')

rep("""  const batterRunning = G.movers.some((m) => m.from === -1);
  if (!batterRunning) {
    const b = curBatter();
    const sw = batAngle();
    const cocked = G.batSwingT < 0;
    const pose = {
      armL: cocked ? -0.9 : -1.2, armR: cocked ? -1.1 : -1.4,
      legL: 0.12, legR: -0.12, bob: cocked ? bob : 0.02,
    };
    drawAnimal(BAT_X, BAT_Z, -Math.PI / 2, b.look, pose, 0);
    drawBat(BAT_X - 0.42, BAT_Z + 0.05, -Math.PI / 2, sw.ang, sw.tilt, '#C99A5E', '#7A5A34');
  }""",
"""  const batterRunning = G.movers.some((m) => m.from === -1);
  if (!batterRunning) {
    const b = curBatter();
    const rig = batterRig(G.batSwingT, clock);
    drawAnimal(rig.bx, rig.bz, -Math.PI / 2 + rig.ry, b.look, {
      handL: rig.handTop, handR: rig.handBot, pole: rig.pole,
      legL: rig.lgL, legR: rig.lgR, spread: rig.spread,
      lean: rig.lean, headRy: rig.head,
      bob: G.batSwingT < 0 ? bob * 0.5 : 0.015,
    }, 0);
    drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');
  }""", 'batter draw')

rep("""    const r = runnerAt(m);
    if (r.done && m.scored) continue;
    const a = basePt(m.from), b = basePt(m.to);
    const ry = Math.atan2(b[0] - a[0], b[1] - a[1]);
    const sw = r.done ? 0 : Math.sin(clock * 15) * 0.9;
    drawAnimal(r.x, r.z, ry, m.p.look, {""",
"""    const r = runnerAt(m);
    if (r.done && m.scored) continue;
    const sw = r.done ? 0 : Math.sin(clock * 15) * 0.9;
    drawAnimal(r.x, r.z, r.ry, m.p.look, {""", 'runner draw')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
