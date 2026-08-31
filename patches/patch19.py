# Traffic, part 2: wire the cars into the ball simulation, the fielding model,
# the frame loop and the drawing; cap the camera under an indoor ceiling.
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
# 40-game.js
# ============================================================
box, rep = mk('src/40-game.js')

rep("  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null,",
    "  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null, traffic: null,", 'traffic field')
rep("  G.fielders = G.stations.map((s) => ({ st: s, x: s.x, z: s.z, tx: s.x, tz: s.z, ry: Math.PI, run: 0, hold: false }));",
    "  G.fielders = G.stations.map((s) => ({ st: s, x: s.x, z: s.z, tx: s.x, tz: s.z, ry: Math.PI, run: 0, hold: false, down: 0, dvz: 0 }));\n  G.traffic = makeTraffic(st);", 'traffic init')
rep("function placeFielders() {\n  for (const f of G.fielders) { f.tx = f.st.x; f.tz = f.st.z; f.hold = false; }\n}",
    "function placeFielders() {\n  for (const f of G.fielders) { f.tx = f.st.x; f.tz = f.st.z; f.hold = false; }\n}\n\n/* traffic keeps rolling whatever the game is doing */\nfunction updateTraffic(dt) {\n  if (!G.traffic) return;\n  stepTraffic(G.traffic, dt);\n  for (const f of G.fielders) {\n    if (f.down > 0) { f.down -= dt; f.z += f.dvz * dt; f.dvz *= 0.90; continue; }\n    for (const c of G.traffic) {\n      if (carHits(c, f.x, 0.6, f.z, 0.42)) {\n        f.down = 2.0; f.dvz = Math.sign(c.vz) * 6.0; Snd.crash();\n        logLine(`${f.st.sn}が車にはねられた！`, true);\n        break;\n      }\n    }\n  }\n}", 'updateTraffic')

# --- ball vs cars, inside the flight simulation ---
rep("""function simFlight(v0, laDeg, dirDeg, st) {""",
"""/* a snapshot of the traffic, advanced with the ball so the carom is part of
   the same simulation the ruling is read from */
function carsSnapshot() {
  return (G.traffic || []).map((c) => ({ x: c.x, z0: c.z, vz: c.vz, hw: c.hw, hh: c.hh, hl: c.hl }));
}

function simFlight(v0, laDeg, dirDeg, st) {""", 'snapshot')
rep("""  const path = [];
  let t = 0, hr = false, ceilHit = false, apex = y, hang = 0, bounced = 0, groundIdx = -1;""",
"""  const path = [];
  const cars = carsSnapshot();
  let carHit = 0;
  let t = 0, hr = false, ceilHit = false, apex = y, hang = 0, bounced = 0, groundIdx = -1;""", 'cars var')
rep("""    const w = st.fenceH > 0 ? wallTest() : 0;""",
"""    if (carHit < 3) {
      for (const c of cars) {
        const cz = c.z0 + c.vz * t;
        if (Math.abs(x - c.x) >= c.hw + BALL_R || Math.abs(z - cz) >= c.hl + BALL_R || y >= c.hh + BALL_R) continue;
        const px = (c.hw + BALL_R) - Math.abs(x - c.x);
        const pz = (c.hl + BALL_R) - Math.abs(z - cz);
        const py = (c.hh + BALL_R) - y;
        if (py <= px && py <= pz) {                       // off the roof
          y = c.hh + BALL_R; vy = Math.abs(vy) * 0.45 + 2.2; vz += c.vz * 0.25;
        } else if (px < pz) {                             // off the flank
          const s2 = Math.sign(x - c.x) || 1;
          x = c.x + s2 * (c.hw + BALL_R);
          vx = s2 * (Math.abs(vx) * 0.55 + 3.5); vz += c.vz * 0.35; vy = Math.abs(vy) * 0.4 + 1.2;
        } else {                                          // off the nose or tail
          const s2 = Math.sign(z - cz) || 1;
          z = cz + s2 * (c.hl + BALL_R);
          vz = s2 * (Math.abs(vz) * 0.5 + 2.0) + c.vz * 0.55; vy = Math.abs(vy) * 0.4 + 1.5;
        }
        carHit++; groundIdx = groundIdx < 0 ? -1 : groundIdx;
        break;
      }
    }
    const w = st.fenceH > 0 ? wallTest() : 0;""", 'ball vs car')
rep("""    groundIdx: groundIdx < 0 ? path.length : groundIdx,""",
"""    groundIdx: groundIdx < 0 ? path.length : groundIdx, carHit,""", 'carHit out')

# --- a flattened fielder cannot make the play ---
rep("""  for (let i = 0; i < G.stations.length; i++) {
    const s = G.stations[i], pl = fielderOf(def, s.k);
    const spd = 6.0 * st.fielderSpeed * (0.86 + pl.defense * 0.28);
    const it = interceptOn(fl, s.x, s.z, spd);
    if (!best || it.t < best.it.t) best = { i, s, pl, spd, it };
  }""",
"""  for (let i = 0; i < G.stations.length; i++) {
    if (G.fielders[i] && G.fielders[i].down > 0) continue;   // flattened by a car
    const s = G.stations[i], pl = fielderOf(def, s.k);
    const spd = 6.0 * st.fielderSpeed * (0.86 + pl.defense * 0.28);
    const it = interceptOn(fl, G.fielders[i] ? G.fielders[i].x : s.x,
                               G.fielders[i] ? G.fielders[i].z : s.z, spd);
    if (!best || it.t < best.it.t) best = { i, s, pl, spd, it };
  }
  if (!best) {   // everybody is down — the ball just sits there
    const q = fl.path[fl.path.length - 1];
    return { kind: 'hit', bases: 3, hit: true, text: '誰も追いつけない！\\nスリーベース',
             play: { fidx: 0, cutIdx: fl.path.length - 1, cutT: q.t,
                     pt: { x: q.x, y: q.y, z: q.z }, air: false, coverIdx: -1 } };
  }""", 'skip downed')

# a carom off a car is worth announcing
rep("""  const text = safeTo === 3 ? `${best.s.sn}へ\\nスリーベースヒット！`""",
"""  const carNote = fl.carHit ? '車に当たった！\\n' : '';
  const text = carNote + (safeTo === 3 ? `${best.s.sn}へ\\nスリーベースヒット！`""", 'car note a')
rep("""    : outDist < 46 ? 'ポテンヒット！' : `${best.s.sn}前ヒット！`;""",
"""    : outDist < 46 ? 'ポテンヒット！' : `${best.s.sn}前ヒット！`);""", 'car note b')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js — loop, camera, drawing
# ============================================================
box, rep = mk('src/50-main.js')

rep("""  // runners
  for (const m of G.movers) m.t += dt;""",
"""  updateTraffic(dt);
  // runners (a flattened one lies there until he can get up)
  let stalled = false;
  for (const m of G.movers) {
    if (m.down > 0) { m.down -= dt; stalled = true; continue; }
    m.t += dt;
    if (G.traffic && m.t > 0 && m.t < m.dur) {
      const r = runnerAt(m);
      for (const c of G.traffic) {
        if (carHits(c, r.x, 0.6, r.z, 0.42)) { m.down = 1.6; Snd.crash(); stalled = true; break; }
      }
    }
  }
  if (stalled && G.phase === 'play' && G.carStall < 2.6) { G.phaseLen += dt; G.carStall += dt; }""", 'runner traffic')

rep("""function updateCamera(dt) {
  let ex, ey, ez, tx, ty, tz, fov = 46, sp = 3.2;
  if (G.camMode === 'bat') {""",
"""function updateCamera(dt) {
  // indoors the camera must stay under the roof or it looks through it
  const ceilY = G.st && G.st.ceiling ? G.st.ceiling - 1.4 : 1e9;
  let ex, ey, ez, tx, ty, tz, fov = 46, sp = 3.2;
  if (G.camMode === 'bat') {""", 'ceil var')
rep("""  } else {
    ex = 0; ey = 33; ez = -26;
    tx = 0; ty = 0; tz = 30; fov = 50; sp = 1.8;
  }
  const k = Math.min(1, dt * sp);""",
"""  } else if (ceilY < 40) {
    ex = 0; ey = Math.min(8.8, ceilY); ez = -32;
    tx = 0; ty = 1.0; tz = 26; fov = 68; sp = 1.8;
  } else {
    ex = 0; ey = 33; ez = -26;
    tx = 0; ty = 0; tz = 30; fov = 50; sp = 1.8;
  }
  ey = Math.min(ey, ceilY);
  ty = Math.min(ty, ceilY - 0.6);
  const k = Math.min(1, dt * sp);""", 'ceil clamp')

rep("""      if (G.pt >= G.phaseLen) endPlay();
      break;
    }""",
"""      if (G.pt >= G.phaseLen) endPlay();
      break;
    }""", 'noop')

rep("""function endPlay() {
  G.ball.vis = false;""",
"""function endPlay() {
  G.carStall = 0;
  G.ball.vis = false;""", 'carStall reset')
rep("""  G.pendingCount = null;
  finishAtBat(o);""",
"""  G.pendingCount = null;
  G.carStall = 0;
  if (G.flight.carHit) Snd.clang();
  finishAtBat(o);""", 'car sound')

# draw the traffic and the flattened players
rep("""  const bt = batTeam(), ft = fldTeam();
  const bob = Math.sin(clock * 2.2) * 0.03;""",
"""  const bt = batTeam(), ft = fldTeam();
  const bob = Math.sin(clock * 2.2) * 0.03;
  if (G.traffic) for (const c of G.traffic) drawCar(c);""", 'draw cars')

rep("""    const isP = f.st.k === 'P', isC = f.st.k === 'C';""",
"""    if (f.down > 0) {                       // run over: flat on his back
      const settle = clamp(f.down * 2.2, 0, 1);
      drawAnimal(f.x, f.z, f.ry, pl.look, {
        fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4,
        armL: -1.1, armR: 1.1, bob: -0.30,
      }, 0);
      for (let s2 = 0; s2 < 3; s2++) {
        const a2 = clock * 5 + s2 * 2.1;
        R.b('sphere', f.x + Math.cos(a2) * 0.34, 0.92 + Math.sin(clock * 6 + s2) * 0.05,
            f.z + Math.sin(a2) * 0.34, 0.13, 0.13, 0.13, col('#FFE04A'));
      }
      continue;
    }
    const isP = f.st.k === 'P', isC = f.st.k === 'C';""", 'downed fielder')

rep("""    const sw = r.done ? 0 : Math.sin(clock * 15) * 0.9;
    drawAnimal(r.x, r.z, r.ry, m.p.look, {""",
"""    if (m.down > 0) {
      drawAnimal(r.x, r.z, r.ry, m.p.look,
        { fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4, armL: -1.1, armR: 1.1,
          bob: -0.30, helmet: 1 }, 0);
      for (let s2 = 0; s2 < 3; s2++) {
        const a2 = clock * 5 + s2 * 2.1;
        R.b('sphere', r.x + Math.cos(a2) * 0.34, 0.92 + Math.sin(clock * 6 + s2) * 0.05,
            r.z + Math.sin(a2) * 0.34, 0.13, 0.13, 0.13, col('#FFE04A'));
      }
      continue;
    }
    const sw = r.done ? 0 : Math.sin(clock * 15) * 0.9;
    drawAnimal(r.x, r.z, r.ry, m.p.look, {""", 'downed runner')
wr('src/50-main.js', box['s'])
print('patched ok (part 2)')
