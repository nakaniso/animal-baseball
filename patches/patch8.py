# Field markings to the rule book: a real pentagonal home plate, continuous foul
# lines from the plate apex to the poles, batter's/catcher's/coach's boxes, the
# three-foot running lane, on-deck circles, a 95-ft infield arc and a regulation
# 18-ft mound. Adds an extruded-polygon primitive and a point-to-point segment
# draw call to the renderer.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def rep(s, a, b, label):
    if a not in s: raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

# ============================================================
# 10-core.js — extruded polygon primitive + segment helper
# ============================================================
p = 'src/10-core.js'; s = rd(p)
s = rep(s, """/* half sphere (dome) — caps, hats, hills */""",
"""/* extruded polygon: pts are [x,z] wound counter-clockwise seen from above,
   the slab spans y = -0.5 .. +0.5 */
function geoPrism(name, pts) {
  geoPart(name, (v, t) => {
    const n = pts.length;
    for (const q of pts) v(q[0], 0.5, q[1], 0, 1, 0);
    for (let i = 1; i < n - 1; i++) t(0, i, i + 1);
    const b = n;
    for (const q of pts) v(q[0], -0.5, q[1], 0, -1, 0);
    for (let i = 1; i < n - 1; i++) t(b, b + i + 1, b + i);
    let k = 2 * n;
    for (let i = 0; i < n; i++) {
      const a = pts[i], c = pts[(i + 1) % n];
      const dx = c[0] - a[0], dz = c[1] - a[1];
      const l = Math.hypot(dx, dz) || 1;
      const nx = -dz / l, nz = dx / l;
      v(a[0], 0.5, a[1], nx, 0, nz);  v(c[0], 0.5, c[1], nx, 0, nz);
      v(c[0], -0.5, c[1], nx, 0, nz); v(a[0], -0.5, a[1], nx, 0, nz);
      t(k, k + 3, k + 2); t(k, k + 2, k + 1); k += 4;
    }
  });
}

/* Home plate, to the rule: a 17in front edge, two 8.5in sides, two 12in sides
   meeting at the back point. Built with that point on the local origin so it
   can be dropped straight onto the corner of the diamond, and normalised so a
   uniform scale of 0.4318 gives the regulation size. */
geoPrism('plate5', [[0, 0], [-0.5, 0.5], [-0.5, 1.0], [0.5, 1.0], [0.5, 0.5]]);

/* half sphere (dome) — caps, hats, hills */""", 'geoPrism')

s = rep(s, """  /* pre-baked matrix (static scenery) */""",
"""  /* a primitive stretched between two points — limbs, bats, rails */
  seg(prim, ax, ay, az, bx, by, bz, r, c) {
    const dx = bx - ax, dy = by - ay, dz = bz - az;
    const len = Math.hypot(dx, dy, dz) || 1e-4;
    const rx = Math.acos(clamp(dy / len, -1, 1));
    const ry = Math.atan2(dx, dz);
    this.d(prim, (ax + bx) / 2, (ay + by) / 2, (az + bz) / 2, rx, ry, 0, r * 2, len, r * 2, c);
  },

  /* pre-baked matrix (static scenery) */""", 'R.seg')
wr(p, s)

# ============================================================
# 20-world.js — the marked field
# ============================================================
p = 'src/20-world.js'; s = rd(p)

old = s[s.index("/* ---------- shared field furniture ---------- */"):s.index("function addCrowdArc")]
new = """/* ---------- shared field furniture ---------- */
/* Regulation dimensions, in metres. */
const PLATE_W = 0.4318;      // 17in across the front edge
const BASE_SZ = 0.40;        // 15in bag (a hair oversized so it reads)
const CHALK_W = 0.09;        // 3in line, widened slightly for legibility
const BOX_W = 1.22, BOX_L = 1.83, BOX_GAP = 0.152;   // batter's box, 6in off the plate
const CATCH_W = 1.09, CATCH_L = 2.44;                // catcher's box
const LANE_W = 0.91;         // three-foot running lane
const MOUND_R = 2.74;        // 18ft circle
const INFIELD_ARC = 28.96;   // 95ft from the centre of the mound
const HOME_CIRCLE = 3.96;    // 13ft
const PATH_W = 1.83;         // 6ft base path
const SQ2 = Math.SQRT1_2;

function chalkLine(S, x1, z1, x2, z2, c, w, y) {
  const len = Math.hypot(x2 - x1, z2 - z1);
  if (len < 1e-4) return;
  S.plate((x1 + x2) / 2, y || 0.030, (z1 + z2) / 2, w || CHALK_W, len, c,
          Math.atan2(x2 - x1, z2 - z1));
}

/* outline of a rectangle centred on (cx,cz), `l` long in its own +z, rotated ry */
function chalkRect(S, cx, cz, w, l, ry, c, y) {
  const co = Math.cos(ry), si = Math.sin(ry);
  const P = (u, v) => [cx + u * co + v * si, cz - u * si + v * co];
  const a = P(-w / 2, -l / 2), b = P(w / 2, -l / 2), d = P(w / 2, l / 2), e = P(-w / 2, l / 2);
  chalkLine(S, a[0], a[1], b[0], b[1], c, CHALK_W, y);
  chalkLine(S, b[0], b[1], d[0], d[1], c, CHALK_W, y);
  chalkLine(S, d[0], d[1], e[0], e[1], c, CHALK_W, y);
  chalkLine(S, e[0], e[1], a[0], a[1], c, CHALK_W, y);
}

function chalkCircle(S, cx, cz, r, c, y) {
  const N = 26;
  for (let i = 0; i < N; i++) {
    const a1 = (i / N) * Math.PI * 2, a2 = ((i + 1) / N) * Math.PI * 2;
    chalkLine(S, cx + Math.cos(a1) * r, cz + Math.sin(a1) * r,
                 cx + Math.cos(a2) * r, cz + Math.sin(a2) * r, c, CHALK_W, y);
  }
}

/* opt = { dirt, chalk, ground, fill (skinned infield), grass (inside the paths),
          foulLen (how far the foul lines run) } */
function addDiamond(S, opt) {
  const dirt = opt.dirt, chalk = opt.chalk, foulLen = opt.foulLen || 95;

  if (opt.fill) {
    // the skinned infield is an arc of 95ft struck from the centre of the mound
    S.ring(0, 0.010, 18.0, INFIELD_ARC, dirt);
    // ...cut off behind the plate, where the ground takes over again
    if (opt.ground) S.plate(0, 0.012, -10.2, 96, 12.4, opt.ground);
    // grass inside the base paths
    if (opt.grass) S.plate(0, 0.014, 19.4, 25.6, 25.6, opt.grass, 45 * DEG);
  }

  // base paths
  const pts = [HOME_POS, BASE_POS[0], BASE_POS[1], BASE_POS[2]];
  for (let i = 0; i < 4; i++) {
    const a = pts[i], b = pts[(i + 1) % 4];
    S.plate((a[0] + b[0]) / 2, 0.016, (a[1] + b[1]) / 2, PATH_W,
            Math.hypot(b[0] - a[0], b[1] - a[1]), dirt,
            Math.atan2(b[0] - a[0], b[1] - a[1]));
  }
  S.ring(0, 0.018, 0, HOME_CIRCLE, dirt);
  S.ring(0, 0.019, 18.0, MOUND_R, shade(dirt, 1.05));

  /* ---- chalk, per the rule book ---- */
  // foul lines run from the back point of the plate through the outside
  // corners of first and third, out to the poles
  for (const sgn of [-1, 1]) {
    const [fx, fz] = polar(45 * sgn, foulLen);
    chalkLine(S, 0, 0, fx, fz, chalk, CHALK_W);
  }
  // batter's boxes: 4ft x 6ft, 6in either side of the plate
  for (const sgn of [-1, 1]) {
    chalkRect(S, sgn * (PLATE_W / 2 + BOX_GAP + BOX_W / 2), PLATE_W / 2,
              BOX_W, BOX_L, 0, chalk);
  }
  // catcher's box: 43in wide, 8ft deep, running back from the batter's boxes
  {
    const zBack = PLATE_W / 2 - BOX_L / 2, zEnd = zBack - CATCH_L, hw = CATCH_W / 2;
    chalkLine(S, -hw, zBack, -hw, zEnd, chalk);
    chalkLine(S, hw, zBack, hw, zEnd, chalk);
    chalkLine(S, -hw, zEnd, hw, zEnd, chalk);
  }
  // three-foot running lane: the last half of the line to first, in foul ground
  {
    const ux = -SQ2, uz = SQ2;                 // toward first base
    const nx = -SQ2, nz = -SQ2;                // into foul territory
    const half = 13.72, full = 27.43;
    const ax = ux * half, az = uz * half, bx = ux * full, bz = uz * full;
    chalkLine(S, ax + nx * LANE_W, az + nz * LANE_W, bx + nx * LANE_W, bz + nz * LANE_W, chalk);
    chalkLine(S, ax, az, ax + nx * LANE_W, az + nz * LANE_W, chalk);
  }
  // coach's boxes, 20ft x 10ft, set back from the baselines
  for (const sgn of [-1, 1]) {
    const dx = sgn * SQ2, dz = SQ2;            // along that foul line
    const nx = sgn * SQ2, nz = -SQ2;           // out into foul territory
    chalkRect(S, dx * 20.5 + nx * 5.6, dz * 20.5 + nz * 5.6,
              3.05, 6.1, sgn * 45 * DEG, chalk);
  }
  // on-deck circles, 5ft across, back in foul ground
  for (const sgn of [-1, 1]) chalkCircle(S, sgn * 7.6, -3.6, 0.76, chalk);

  /* ---- the bags ---- */
  // first and third sit just inside the line, so the line touches their edge
  const inset = BASE_SZ / 2;
  const bagPos = [
    [BASE_POS[0][0] + inset * SQ2, BASE_POS[0][1] + inset * SQ2],
    [BASE_POS[1][0], BASE_POS[1][1]],
    [BASE_POS[2][0] - inset * SQ2, BASE_POS[2][1] + inset * SQ2],
  ];
  for (const b of bagPos) S.box(b[0], 0.038, b[1], BASE_SZ, 0.076, BASE_SZ, '#FFFFFF', 45 * DEG);
  // home plate: the real pentagon, its back point on the corner of the diamond
  S.add('plate5', 0, 0.026, 0, 0, 0, 0, PLATE_W, 0.05, PLATE_W, col('#FBFBF7'));
  // pitcher's plate, 24in x 6in, front edge 60ft 6in from the point of home
  S.box(0, 0.055, 18.44 + 0.076, 0.61, 0.05, 0.152, '#F4F4F0');
}

"""
s = s.replace(old, new)

# every park now tells the diamond how far its foul lines run, and what the
# surrounding surface is
s = rep(s, "      addDiamond(S, { dirt: '#C08551', chalk: '#F4EFE2', fill: 1, grass: '#42964F' });",
           "      addDiamond(S, { dirt: '#C08551', chalk: '#F4EFE2', fill: 1, grass: '#42964F',\n        ground: '#3E8F4C', foulLen: fenceAt(this, 45) });", 'dome call')
s = rep(s, "      addDiamond(S, { dirt: '#6C7177', chalk: '#F0EDE4' });",
           "      addDiamond(S, { dirt: '#6C7177', chalk: '#F0EDE4', foulLen: fenceAt(this, 45) });", 'road call')
s = rep(s, "      addDiamond(S, { dirt: '#C6BCA6', chalk: '#FFFFFF' });",
           "      addDiamond(S, { dirt: '#C6BCA6', chalk: '#FFFFFF', foulLen: fenceAt(this, 45) });", 'market call')
s = rep(s, "      addDiamond(S, { dirt: '#B08A56', chalk: '#EFEDE0', fill: 1 });",
           "      addDiamond(S, { dirt: '#B08A56', chalk: '#EFEDE0', fill: 1,\n        ground: '#8B9455', foulLen: fenceAt(this, 45) });", 'river call')
s = rep(s, "      addDiamond(S, { dirt: '#9A9AA2', chalk: '#E8ECF4', fill: 1 });",
           "      addDiamond(S, { dirt: '#9A9AA2', chalk: '#E8ECF4', fill: 1,\n        ground: '#83838C', foulLen: fenceAt(this, 45) });", 'moon call')
wr(p, s)
print('patched ok')
