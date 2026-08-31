# 1. Indoors the camera was climbing straight through the roof on fly balls and
#    on the wide view. Every camera is now capped below the ceiling.
# 2. Traffic on the road park: cars run the lanes through the middle of the
#    game. The ball caroms off them (simulated inside simFlight, so the ruling
#    still matches what you see) and anyone standing in a lane gets flattened.
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
# 10-core.js — a crash / horn
# ============================================================
box, rep = mk('src/10-core.js')
rep("  cheer(){ this.noise(0.9, 0.07, 700); this.tone(520, 0.5, 'triangle', 0.05, 780); },",
"""  cheer(){ this.noise(0.9, 0.07, 700); this.tone(520, 0.5, 'triangle', 0.05, 780); },
  horn() { this.tone(392, 0.30, 'square', 0.05); setTimeout(() => this.tone(330, 0.34, 'square', 0.05), 120); },
  crash(){ this.noise(0.30, 0.14, 260); this.tone(150, 0.28, 'sawtooth', 0.10, 60); },
  clang(){ this.tone(880, 0.16, 'square', 0.10, 320); this.noise(0.12, 0.09, 2400); },""", 'sounds')
wr('src/10-core.js', box['s'])

# ============================================================
# 30-actors.js — characters can be knocked flat
# ============================================================
box, rep = mk('src/30-actors.js')
rep("""function yawFrame(x, z, ry) { return { x, z, ry, c: Math.cos(ry), s: Math.sin(ry) }; }
function L2W(f, lx, lz) { return [f.x + lx * f.c + lz * f.s, f.z - lx * f.s + lz * f.c]; }

function part(f, prim, lx, ly, lz, sx, sy, sz, c, rx, rz) {
  const [wx, wz] = L2W(f, lx, lz);
  R.d(prim, wx, ly, wz, rx || 0, f.ry, rz || 0, sx, sy, sz, c);
}""",
"""function yawFrame(x, z, ry) { return { x, z, ry, c: Math.cos(ry), s: Math.sin(ry), t: 0 }; }
function L2W(f, lx, lz) { return [f.x + lx * f.c + lz * f.s, f.z - lx * f.s + lz * f.c]; }

/* f.t tips the whole body about its hips — used when a car flattens someone */
function part(f, prim, lx, ly, lz, sx, sy, sz, c, rx, rz) {
  let Y = ly, Z = lz;
  if (f.t) {
    const dy = ly - f.pivot;
    Y = f.pivot + dy * f.ct - lz * f.st;
    Z = dy * f.st + lz * f.ct;
  }
  const [wx, wz] = L2W(f, lx, Z);
  R.d(prim, wx, Y, wz, (rx || 0) + f.t, f.ry, rz || 0, sx, sy, sz, c);
}""", 'part tilt')
rep("""  const f = yawFrame(x, z, ry);
  const y = (y0 || 0) + (p.bob || 0);""",
"""  const f = yawFrame(x, z, ry);
  const y = (y0 || 0) + (p.bob || 0);
  if (p.fall) { f.t = p.fall; f.ct = Math.cos(p.fall); f.st = Math.sin(p.fall); f.pivot = y + 0.34; }""", 'fall frame')
rep("  shadow(x, z, 0.44 * big, 0.34);",
    "  shadow(x, z, (p.fall ? 0.72 : 0.44) * big, 0.34);", 'fall shadow')
wr('src/30-actors.js', box['s'])

# ============================================================
# 20-world.js — traffic data, tunnel mouth, car drawing
# ============================================================
box, rep = mk('src/20-world.js')
rep("""/* ============================================================
   The five ballparks
   ============================================================ */""",
"""/* ---------- live traffic (the road park) ---------- */
const CAR_PAINT = ['#D9483B', '#3E6FBF', '#EFEFEF', '#2E3B45', '#E8B23A', '#48A96B', '#B44D8C', '#5FB6C4'];
const ROAD_Z0 = -58, ROAD_Z1 = 86;

function makeTraffic(st) {
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
}

/* does this box contain the point? used for both the ball and for people */
function carHits(c, x, y, z, pad) {
  const p = pad || 0;
  return Math.abs(x - c.x) < c.hw + p && Math.abs(z - c.z) < c.hl + p && y < c.hh + p;
}

function drawCar(c) {
  const b = col(c.col), dark = shade(c.col, 0.72);
  const back = c.vz > 0 ? -1 : 1;
  shadow(c.x, c.z, c.hl * 0.62, 0.30);
  if (c.truck) {
    R.b('box', c.x, 1.05, c.z - back * 0.9, c.hw * 2, 1.9, c.hl * 1.35, b);
    R.b('box', c.x, 2.05, c.z - back * 0.9, c.hw * 2 - 0.1, 2.0, c.hl * 1.3, shade(c.col, 1.08));
    R.b('box', c.x, 1.20, c.z + back * c.hl * 0.72, c.hw * 1.9, 2.1, 1.7, dark);
    R.b('box', c.x, 1.85, c.z + back * (c.hl * 0.72 + 0.16), c.hw * 1.6, 0.9, 0.2, '#2A3A48');
  } else {
    R.b('box', c.x, 0.72, c.z, c.hw * 2, 0.86, c.hl * 2, b);
    R.b('box', c.x, 1.36, c.z - back * 0.2, c.hw * 1.72, 0.66, c.hl * 1.05, shade(c.col, 0.86));
    R.b('box', c.x, 1.38, c.z - back * 0.2, c.hw * 1.6, 0.46, c.hl * 1.0, '#2A3A48');
  }
  for (const ox of [-1, 1]) for (const oz of [-1, 1])
    R.d('cyl', c.x + ox * c.hw * 0.92, 0.34, c.z + oz * c.hl * 0.62,
        0, 0, Math.PI / 2, 0.68, 0.28, 0.68, col('#1B222A'));
  R.b('box', c.x - c.hw * 0.55, 0.85, c.z + back * (c.hl - 0.02), 0.42, 0.24, 0.14, '#FFE9A8');
  R.b('box', c.x + c.hw * 0.55, 0.85, c.z + back * (c.hl - 0.02), 0.42, 0.24, 0.14, '#FFE9A8');
  R.b('box', c.x, 0.80, c.z - back * (c.hl - 0.02), c.hw * 1.5, 0.20, 0.12, '#C8342A');
}

/* ============================================================
   The five ballparks
   ============================================================ */""", 'traffic model')

rep("""    fenceFn: (a) => Math.min(88, 40 / Math.max(0.10, Math.abs(Math.sin(a * DEG)))),""",
"""    fenceFn: (a) => Math.min(88, 40 / Math.max(0.10, Math.abs(Math.sin(a * DEG)))),
    // Japan drives on the left: heading away from home you keep to +x
    lanes: [{ x: 10, dir: 1 }, { x: 23, dir: 1 }, { x: -10, dir: -1 }, { x: -23, dir: -1 }],""", 'lanes')
rep("    quirk: '左右のビルが壁。引っぱるほどフェンスが近い',",
    "    quirk: '車は止まらない。当たった打球は生きたまま転がる',", 'road quirk')
rep("""    desc: '正面の高架壁まで88m。左右はビルがそのまま壁なので、引っぱるほどフェンスが近づく。ライン際なら57mでビルの窓へ。',""",
"""    desc: '正面の高架壁まで88m。左右はビルがそのまま壁で、引っぱるほどフェンスが近い。おまけに車が試合の中を走り抜けるので、打球は跳ね、選手は轢かれる。',""", 'road desc')
rep("""      // overpass wall straight ahead = centre-field fence
      S.box(0, 5, 88, 84, 10, 2, '#7E8489');""",
"""      // the road ducks under the overpass; cars appear and vanish in the mouth
      S.box(0, 3.1, 87.2, 56, 6.2, 0.5, '#1B2026');
      S.box(0, 6.4, 87.0, 58, 0.7, 1.0, '#5B6167');
      for (let i = -3; i <= 3; i++) S.box(i * 8, 6.9, 87.0, 1.4, 0.5, 0.9, '#E8C23A');
      // overpass wall straight ahead = centre-field fence
      S.box(0, 5, 88, 84, 10, 2, '#7E8489');""", 'tunnel')
wr('src/20-world.js', box['s'])
print('patched ok (part 1)')
