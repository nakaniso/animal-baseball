# 1 count pips reset with the batter, 2 no chalk inside the batter's box,
# 3 runners take a lead and advance on grounders, 4 a longer pause before the
# first pitch, 5 the ball shrinks with distance, 6 やめる -> ポーズ,
# 7 a ball through the outfield is usually a double, 8 the pitcher misses his
# spot sometimes and his speed varies.
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
# 00-shell.html — the button is a pause, not a quit
# ============================================================
box, rep = mk('src/00-shell.html')
rep('<button id="btn-quit">やめる</button>', '<button id="btn-quit">ポーズ</button>', 'pause label')
wr('src/00-shell.html', box['s'])

# ============================================================
# 20-world.js — the batter's box is open on the plate side
# ============================================================
box, rep = mk('src/20-world.js')
rep("""  // batter's boxes: 4ft x 6ft, 6in either side of the plate
  for (const sgn of [-1, 1]) {
    chalkRect(S, sgn * (PLATE_W / 2 + BOX_GAP + BOX_W / 2), PLATE_W / 2,
              BOX_W, BOX_L, 0, chalk);
  }""",
"""  // batter's boxes: 4ft x 6ft, 6in either side of the plate. The line next to
  // the plate is not chalked — on a real field that side is left open.
  for (const sgn of [-1, 1]) {
    const inX = sgn * (PLATE_W / 2 + BOX_GAP), outX = sgn * (PLATE_W / 2 + BOX_GAP + BOX_W);
    const z0 = PLATE_W / 2 - BOX_L / 2, z1 = PLATE_W / 2 + BOX_L / 2;
    chalkLine(S, inX, z0, outX, z0, chalk);
    chalkLine(S, outX, z0, outX, z1, chalk);
    chalkLine(S, outX, z1, inX, z1, chalk);
  }""", 'batter box')
wr('src/20-world.js', box['s'])

# ============================================================
# 30-actors.js — perspective on the ball
# ============================================================
box, rep = mk('src/30-actors.js')
rep("""function ballScale(x, y, z) {
  const d = Math.hypot(x - R.eye[0], y - R.eye[1], z - R.eye[2]);
  return BALL_R * 2 * clamp(d / 13, 1, 4.2);
}""",
"""function ballScale(x, y, z) {
  const d = Math.hypot(x - R.eye[0], y - R.eye[1], z - R.eye[2]);
  // grow with the square root of distance: still findable far away, but it
  // clearly shrinks as it goes, which is what reads as depth
  return BALL_R * 2 * clamp(Math.sqrt(d / 11), 1, 2.8);
}""", 'ballScale')
wr('src/30-actors.js', box['s'])

# ============================================================
# 40-game.js
# ============================================================
box, rep = mk('src/40-game.js')

# --- (1) the count display follows the new batter ---
rep("""  placeFielders();
  uiBatter();
  setPhase('ready', 0.75);""",
"""  placeFielders();
  uiScore();                       // the pips belong to this batter, not the last
  uiBatter();
  setPhase('ready', G.firstPitch ? 2.4 : 0.75);""", 'nextBatter')

# --- (4) settle before the first pitch of the game ---
rep("  G.over = false; G.active = true; G.paused = false; G.movers = []; G.flight = null; G.playScript = null;",
"""  G.over = false; G.active = true; G.paused = false; G.movers = []; G.flight = null; G.playScript = null;
  G.firstPitch = true;
  // start already looking down the barrel instead of swinging in from the menu
  CAM.ex = 0.55; CAM.ey = 4.6; CAM.ez = -9.0; CAM.tx = 0; CAM.ty = 0.4; CAM.tz = 7.0; CAM.fov = 40;
  CAM.wx = CAM.ex; CAM.wy = CAM.ey; CAM.wz = CAM.ez;""", 'startGame cam')
rep("  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null, traffic: null, carStall: 0,",
    "  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null, traffic: null, carStall: 0,\n  firstPitch: false,", 'firstPitch field')

# --- (8) the pitcher is not a machine ---
rep("""  const acc = 0.62 + p.arm * 0.38;
  return { ti, ax: ax + gauss((1 - acc) * 0.20), ay: ay + gauss((1 - acc) * 0.20) };""",
"""  const acc = 0.62 + p.arm * 0.38;
  let fx = ax + gauss((1 - acc) * 0.30), fy = ay + gauss((1 - acc) * 0.28);
  if (chance(0.10)) { fx += gauss(0.40); fy += gauss(0.38); }   // he misses his spot
  return { ti, ax: fx, ay: fy };""", 'cpu scatter')

rep("""  const P = PITCHES[ti];
  const spd = P.spd * (0.90 + p.arm * 0.16);
  const T = 18.15 / spd;
  const arrive = { x: clamp(ax, -0.95, 0.95), y: clamp(ay, 0.22, 1.68) };
  const pf = G.fielders[0];
  G.pitch = {
    P, T, t: 0, ti,
    x0: (pf ? pf.x : 0) + 0.46, y0: 1.92, z0: (pf ? pf.z : MOUND_POS[1]) - 0.16,
    tx: arrive.x - P.bx, ty: arrive.y - P.by,""",
"""  const P = PITCHES[ti];
  // no two pitches come out quite the same
  const spd = P.spd * (0.90 + p.arm * 0.16) * (1 + gauss(0.040));
  const T = 18.15 / spd;
  const slip = (1 - p.arm) * 0.11;             // even his own aim drifts a little
  const bx = P.bx * (1 + gauss(0.20)), by = P.by * (1 + gauss(0.20));
  const arrive = { x: clamp(ax + gauss(slip), -0.95, 0.95),
                   y: clamp(ay + gauss(slip), 0.22, 1.68) };
  const pf = G.fielders[0];
  G.pitch = {
    P, T, t: 0, ti, bx, by,
    x0: (pf ? pf.x : 0) + 0.46, y0: 1.92, z0: (pf ? pf.z : MOUND_POS[1]) - 0.16,
    tx: arrive.x - bx, ty: arrive.y - by,""", 'pitch variance')
rep("""  G.ball.vis = true; G.trail.length = 0;""",
    """  G.ball.vis = true; G.trail.length = 0; G.firstPitch = false;""", 'clear firstPitch')
rep("""  return {
    x: lerp(pc.x0, pc.tx, u) + pc.P.bx * k,
    y: lerp(pc.y0, pc.ty, u) + pc.P.by * k - (u > 1 ? (u - 1) * 0.5 : 0),""",
"""  return {
    x: lerp(pc.x0, pc.tx, u) + pc.bx * k,
    y: lerp(pc.y0, pc.ty, u) + pc.by * k - (u > 1 ? (u - 1) * 0.5 : 0),""", 'pitchPos break')

# --- (3) runners take their lead into the path, and go on grounders ---
rep("""  const pts = [];
  for (let b = from; b <= to; b++) {
    const q = basePt(b);""",
"""  const pts = [];
  for (let b = from; b <= to; b++) {
    let q = basePt(b);
    if (b === from && b >= 0 && b <= 2) {      // he was already off the bag
      const n2 = basePt(b + 1);
      const ux = n2[0] - q[0], uz = n2[1] - q[1], ul = Math.hypot(ux, uz) || 1;
      q = [q[0] + (ux / ul) * LEAD_OFF, q[1] + (uz / ul) * LEAD_OFF];
    }""", 'lead start')
rep("""/* seconds from contact for a runner to reach base n (1 = first) */""",
"""const LEAD_OFF = 2.6;              // how far a runner edges off the bag

/* seconds from contact for a runner to reach base n (1 = first) */""", 'LEAD_OFF')

rep("""    case 'groundout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);
      if (chance(0.55)) runs += advanceOneAll(bat, G.outs < 2);
      Snd.mitt();
      break;""",
"""    case 'groundout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);
      // with the play going to first, everyone else moves up
      if (chance(0.86)) runs += advanceOneAll(bat, G.outs < 2 && chance(0.85));
      Snd.mitt();
      break;""", 'groundout advance')
rep("""      } else if (G.outs < 2 && G.bases[1] && o.canSac && chance(0.4)) {
        G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null;
      }""",
"""      } else if (G.outs < 2 && G.bases[1] && o.canSac && chance(0.62)) {
        G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null;
      }""", 'tag up')
rep("""      const forced = G.bases[0];
      G.bases[0] = null;
      moveRunner(bat, -1, 0, 0, true);
      if (forced) moveRunner(forced, 0, 1, 0, true);""",
"""      const forced = G.bases[0];
      G.bases[0] = null;
      moveRunner(bat, -1, 0, 0, true);
      if (forced) moveRunner(forced, 0, 1, 0, true);
      runs += advanceOneAll(bat, G.outs < 2);""", 'dp advance')

# --- (7) a ball through the outfield is a double ---
rep("""  const infield = best.s.infield;
  const outDist = Math.hypot(P.x, P.z);
  // nobody throws the batter out at first from deep in the outfield
  if (safeTo === 0 && !infield && outDist > 40) safeTo = 1;""",
"""  const infield = best.s.infield;
  const outDist = Math.hypot(P.x, P.z);
  // nobody throws the batter out at first from deep in the outfield
  if (safeTo === 0 && !infield && outDist > 40) safeTo = 1;
  // once it is past the outfielders he is standing on second before the relay
  if (!infield && outDist > fenceAt(st, fl.ang) * 0.76 + 6) safeTo = Math.max(safeTo, 2);""", 'through OF')
rep("""  return 0.55 + d / (27 + (arm || 0.6) * 13) + (d > 42 ? 0.70 : 0);""",
    """  return 0.55 + d / (27 + (arm || 0.6) * 13) + (d > 42 ? 1.05 : 0);""", 'relay cost')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js — runners lead off the bag
# ============================================================
box, rep = mk('src/50-main.js')
rep("""    const b = BASE_POS[i];
    drawAnimal(b[0] * 1.06, b[1] - 1.15, Math.PI, p.look,
               { armL: 0.3, armR: -0.3, bob, helmet: 1 }, 0);""",
"""    // he takes his lead down the line, shuffling and watching the pitcher
    const b = BASE_POS[i], n2 = basePt(i + 1);
    const ux = n2[0] - b[0], uz = n2[1] - b[1], ul = Math.hypot(ux, uz) || 1;
    const off = LEAD_OFF + Math.sin(clock * 1.7 + i * 2) * 0.34;
    drawAnimal(b[0] + (ux / ul) * off, b[1] + (uz / ul) * off,
               Math.atan2(ux, uz), p.look,
               { armL: 0.5, armR: 0.5, legL: 0.14, legR: -0.14, spread: 0.13,
                 lean: 0.14, headRy: -0.8, bob: bob * 0.6, helmet: 1 }, 0);""", 'lead off')
wr('src/50-main.js', box['s'])
print('patched ok')
