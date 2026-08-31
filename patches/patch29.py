# Road: being run over now actually costs you — a runner flattened between bases
# is out (a double becomes an out), and the run he was about to score comes off
# the board. Supermarket: shoppers with trolleys walk the aisles and bowl players
# over the same way, the ball caroms off them, and the floor is no longer white.
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
# 30-actors.js — a character can go bare-headed (shoppers)
# ============================================================
box, rep = mk('src/30-actors.js')
rep("""  // headwear: a batting helmet at the plate and on the bases, otherwise a cap
  if (p.helmet) {""",
"""  // headwear: a batting helmet at the plate and on the bases, otherwise a cap
  if (p.noHat) { /* a shopper, not a ballplayer */ }
  else if (p.helmet) {""", 'noHat')
wr('src/30-actors.js', box['s'])

# ============================================================
# 20-world.js — walkers, the shopper model, and the market's look
# ============================================================
box, rep = mk('src/20-world.js')

rep("""function makeTraffic(st) {
  if (!st.lanes) return null;
  const cars = [];
  for (const lane of st.lanes) {
    const n = 2 + (chance(0.4) ? 1 : 0);
    for (let i = 0; i < n; i++) {
      const truck = chance(0.22);
      cars.push({
        x: lane.x + rnd(-0.4, 0.4),
        z: ROAD_Z0 + ((i + rnd(0, 0.7)) / n) * (ROAD_Z1 - ROAD_Z0),
        vz: lane.dir * rnd(12, 19) * (truck ? 0.8 : 1),
        col: pick(CAR_PAINT), truck,
        hw: truck ? 1.28 : 1.02, hh: truck ? 2.5 : 1.55, hl: truck ? 3.6 : 2.25,
      });
    }
  }
  return cars;
}

function stepTraffic(cars, dt) {
  for (const c of cars) {
    c.z += c.vz * dt;
    if (c.vz > 0 && c.z > ROAD_Z1) c.z = ROAD_Z0;
    else if (c.vz < 0 && c.z < ROAD_Z0) c.z = ROAD_Z1;
  }
}""",
"""const SHOPPER_WEAR = ['#C4483A', '#3E6FBF', '#4E8A5E', '#B4823A', '#7A5A9A', '#3C6E78'];
const SHOPPER_KIND = ['panda', 'hippo', 'rabbit', 'cat', 'bear', 'frog', 'fox'];
const GROCERY = ['#E8734A', '#F2C14E', '#7FB3D5', '#8ED0A8', '#C97BA0'];

function makeTraffic(st) {
  if (!st.lanes) return null;
  const cars = [];
  const z0 = st.laneZ ? st.laneZ[0] : ROAD_Z0, z1 = st.laneZ ? st.laneZ[1] : ROAD_Z1;
  for (const lane of st.lanes) {
    const n = lane.walk ? 3 : 2 + (chance(0.4) ? 1 : 0);
    for (let i = 0; i < n; i++) {
      const z = z0 + ((i + rnd(0, 0.7)) / n) * (z1 - z0);
      if (lane.walk) {
        const wear = pick(SHOPPER_WEAR);
        cars.push({
          x: lane.x + rnd(-0.7, 0.7), z, z0, z1, walk: 1,
          vz: lane.dir * rnd(1.0, 1.8), phase: rnd(0, 6.3),
          look: { animal: pick(SHOPPER_KIND), uni: wear, trim: '#EFE9DC', cap: shade(wear, 0.7) },
          goods: pick(GROCERY),
          hw: 0.40, hh: 1.55, hl: 0.52,
        });
      } else {
        const truck = chance(0.22);
        cars.push({
          x: lane.x + rnd(-0.4, 0.4), z, z0, z1,
          vz: lane.dir * rnd(12, 19) * (truck ? 0.8 : 1),
          col: pick(CAR_PAINT), truck,
          hw: truck ? 1.28 : 1.02, hh: truck ? 2.5 : 1.55, hl: truck ? 3.6 : 2.25,
        });
      }
    }
  }
  return cars;
}

function stepTraffic(cars, dt) {
  for (const c of cars) {
    const a = c.z0 === undefined ? ROAD_Z0 : c.z0, b = c.z1 === undefined ? ROAD_Z1 : c.z1;
    c.z += c.vz * dt;
    if (c.vz > 0 && c.z > b) c.z = a;
    else if (c.vz < 0 && c.z < a) c.z = b;
  }
}""", 'makeTraffic')

rep("""/* ============================================================
   The five ballparks
   ============================================================ */""",
"""/* a customer pushing a trolley down the aisle */
function drawShopper(c) {
  const dir = c.vz > 0 ? 1 : -1;
  const t = clock * 5.5 + c.phase;
  const sw = Math.sin(t) * 0.5;
  drawAnimal(c.x, c.z, c.vz > 0 ? 0 : Math.PI, c.look,
    { armL: -1.25, armR: -1.25, legL: sw, legR: -sw, noHat: 1,
      bob: Math.abs(Math.sin(t)) * 0.04 }, 0);
  const cz = c.z + dir * 0.92, bar = col('#B8BEC4');
  R.b('box', c.x, 0.66, cz, 0.64, 0.06, 0.88, bar);
  R.b('box', c.x, 0.34, cz, 0.58, 0.05, 0.80, bar);
  for (const s of [-1, 1]) {
    R.b('box', c.x + s * 0.31, 0.50, cz, 0.05, 0.34, 0.84, bar);
    R.b('box', c.x + s * 0.31, 0.50, cz - dir * 0.44, 0.05, 0.34, 0.05, bar);
  }
  R.b('box', c.x, 0.90, cz - dir * 0.46, 0.58, 0.05, 0.05, bar);
  R.b('box', c.x, 0.54, cz + dir * 0.08, 0.46, 0.28, 0.46, col(c.goods));
  for (const s of [-1, 1]) for (const o of [-1, 1])
    R.d('cyl', c.x + s * 0.27, 0.10, cz + o * 0.36, 0, 0, Math.PI / 2, 0.18, 0.06, 0.18, col('#3A4048'));
  shadow(c.x, cz, 0.55, 0.26);
}

/* ============================================================
   The five ballparks
   ============================================================ */""", 'drawShopper')

# ---- the market: aisles of shoppers, and a floor that is not white ----
rep("    fog: '#B9C0BA', skyTint: '#E4E8E0', gndTint: '#8E958E', fogDist: 300,",
    "    fog: '#A9B0A8', skyTint: '#D6DBD2', gndTint: '#79807A', fogDist: 300,", 'market fog')
rep("    light: [0.18, 0.94, 0.28], fielderSpeed: 0.84,",
"""    light: [0.18, 0.94, 0.28], fielderSpeed: 0.84,
    lanes: [{ x: -25, dir: 1, walk: 1 }, { x: 25, dir: -1, walk: 1 },
            { x: -9, dir: -1, walk: 1 }, { x: 9, dir: 1, walk: 1 }],
    laneZ: [-16, 74],""", 'market lanes')
rep("    quirk: '天井10.5m。ホームランは低いライナーだけ',",
    "    quirk: '天井10.5m。買い物客とぶつかると倒される',", 'market quirk')
rep("""    desc: '天井が10.5mしかない。高く上げた打球は天井に当たって落ちてくるので、冷凍ケースの壁（中堅62m）を越えたければ低いライナーで運ぶしかない。床はすべる。',""",
"""    desc: '天井が10.5mしかない。高く上げた打球は天井に当たって落ちてくるので、冷凍ケースの壁（中堅62m）を越えたければ低いライナーで運ぶしかない。通路を歩く買い物客にぶつかると転ばされる。',""", 'market desc')
rep("""      for (let x = -6; x <= 6; x++) for (let z = -2; z <= 10; z++)
        S.plate(x * 8, 0, z * 8, 8, 8, (x + z) % 2 ? '#D2D6CC' : '#B6BCB2');
      // vinyl guide stripes, like a real shop floor
      for (let z = -16; z < 100; z += 24) S.plate(0, 0.008, z, 104, 1.2, '#8FA8A2');""",
"""      for (let x = -6; x <= 6; x++) for (let z = -2; z <= 10; z++)
        S.plate(x * 8, 0, z * 8, 8, 8, (x + z) % 2 ? '#B5AE9E' : '#A29A89');
      // vinyl guide stripes, like a real shop floor
      for (let z = -16; z < 100; z += 24) S.plate(0, 0.008, z, 104, 1.2, '#6F8C86');""", 'market floor')
rep("      addDiamond(S, { dirt: '#C6BCA6', chalk: '#FFFFFF', foulLen: fenceAt(this, 45) });",
    "      addDiamond(S, { dirt: '#C2A155', chalk: '#FFFFFF', foulLen: fenceAt(this, 45) });", 'market tape')
wr('src/20-world.js', box['s'])

# ============================================================
# 40-game.js — being run over costs you
# ============================================================
box, rep = mk('src/40-game.js')

rep("""  G.movers.push({
    p, from, to, pts, segs, total, t: -(delay || 0), dur,
    scored: to >= 3, retired: !!retired,
  });""",
"""  G.movers.push({
    p, from, to, pts, segs, total, t: -(delay || 0), dur,
    scored: to >= 3, retired: !!retired,
    rbiOwner: to >= 3 ? curBatter() : null,
  });""", 'rbiOwner')

rep("""/* traffic keeps rolling whatever the game is doing */
function updateTraffic(dt) {
  if (!G.traffic) return;
  stepTraffic(G.traffic, dt);
  for (const f of G.fielders) {
    if (f.down > 0) { f.down -= dt; f.z += f.dvz * dt; f.dvz *= 0.90; continue; }
    for (const c of G.traffic) {
      if (carHits(c, f.x, 0.6, f.z, 0.42)) {
        f.down = 2.0; f.dvz = Math.sign(c.vz) * 6.0; Snd.crash();
        logLine(`${f.st.sn}が車にはねられた！`, true);
        break;
      }
    }
  }
}""",
"""/* traffic keeps rolling whatever the game is doing */
function updateTraffic(dt) {
  if (!G.traffic) return;
  stepTraffic(G.traffic, dt);
  for (const f of G.fielders) {
    if (f.down > 0) { f.down -= dt; f.z += f.dvz * dt; f.dvz *= 0.90; continue; }
    if (f.scripted) continue;            // he is on the play; leave him to it
    for (const c of G.traffic) {
      if (carHits(c, f.x, 0.6, f.z, 0.42)) {
        f.down = c.walk ? 1.4 : 2.0;
        f.dvz = Math.sign(c.vz) * (c.walk ? 2.0 : 6.0);
        Snd.crash();
        logLine(c.walk ? `${f.st.sn}が買い物客とぶつかって転倒！`
                       : `${f.st.sn}が車にはねられた！`, true);
        break;
      }
    }
  }
}

/* A runner flattened between the bags never gets there: he is out, and any run
   he was in the middle of scoring comes back off the board. */
function runOverRunner(m, walk) {
  if (m.retired) return;
  m.retired = true;
  for (let i = 0; i < 3; i++) if (G.bases[i] === m.p) G.bases[i] = null;
  if (m.scored) {
    G.score[G.half] = Math.max(0, G.score[G.half] - 1);
    G.inningRuns = Math.max(0, G.inningRuns - 1);
    if (m.rbiOwner) m.rbiOwner.rbi = Math.max(0, m.rbiOwner.rbi - 1);
    m.scored = false;
  }
  if (G.outs < 3) G.outs++;
  banner(walk ? `${m.p.name} 買い物客と衝突\\nアウト！` : `${m.p.name} 車にはねられ\\nアウト！`, true);
  logLine(walk ? `${m.p.name}が買い物客とぶつかってアウト！` : `${m.p.name}が車にはねられてアウト！`, true);
  uiScore();
}""", 'updateTraffic')

# a hit that got through because someone was flat on the deck says so
rep("""  if (!best) {   // everybody is down — the ball just sits there""",
"""  let downNote = '';
  {
    let nd = null;
    for (let i = 0; i < G.stations.length; i++) {
      const st2 = G.stations[i], d = dist2(st2.x, st2.z, fl.land.x, fl.land.z);
      if (!nd || d < nd.d) nd = { i, d, sn: st2.sn };
    }
    if (nd && G.fielders[nd.i] && G.fielders[nd.i].down > 0 && nd.d < 22)
      downNote = `${nd.sn}が倒れている！\\n`;
  }
  if (!best) {   // everybody is down — the ball just sits there""", 'downNote')
rep("""  const carNote = fl.carHit ? '車に当たった！\\n' : '';""",
    """  const carNote = fl.carHit ? '車に当たった！\\n' : downNote;""", 'use downNote')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js — hook the runner up, and draw shoppers
# ============================================================
box, rep = mk('src/50-main.js')
rep("""      for (const c of G.traffic) {
        if (carHits(c, r.x, 0.6, r.z, 0.42)) { m.down = 1.6; Snd.crash(); stalled = true; break; }
      }""",
"""      for (const c of G.traffic) {
        if (carHits(c, r.x, 0.6, r.z, 0.42)) {
          m.down = c.walk ? 1.3 : 1.6;
          Snd.crash();
          runOverRunner(m, !!c.walk);      // he is out where he stands
          stalled = true;
          break;
        }
      }""", 'runner hit')
rep("  if (G.traffic) for (const c of G.traffic) drawCar(c);",
    "  if (G.traffic) for (const c of G.traffic) { if (c.walk) drawShopper(c); else drawCar(c); }", 'draw shoppers')
wr('src/50-main.js', box['s'])
print('patched ok')
