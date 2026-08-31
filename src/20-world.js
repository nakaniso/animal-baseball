/* ============================================================
   20-world.js — field geometry, the five ballparks, scenery
   ============================================================ */
'use strict';

/* Diamond is regulation-ish in metres: 27.4m between bases. */
const BASE_POS = [[-19.4, 19.4], [0, 38.8], [19.4, 19.4]]; // 1st, 2nd, 3rd
const HOME_POS = [0, 0];
const MOUND_POS = [0, 18.44];

/* polar helper: angle 0 = straight to centre field (+z), + = LEFT field (+x,
   third-base side). Screen-right is world -x, so +x draws on the left. */
const polar = (aDeg, d) => [Math.sin(aDeg * DEG) * d, Math.cos(aDeg * DEG) * d];
const angOf = (x, z) => Math.atan2(x, z) / DEG;

function fenceAt(st, aDeg) {
  if (st.fenceFn) return st.fenceFn(aDeg);
  const t = clamp(Math.abs(aDeg) / 45, 0, 1);
  return lerp(st.fenceCenter, st.fenceLine, t * t * 0.55 + t * 0.45);
}

/* ---------- scene builder: bakes static props into matrices ---------- */
class Scene {
  constructor() { this.items = []; }
  add(p, x, y, z, rx, ry, rz, sx, sy, sz, c) {
    this.items.push({ p, m: mTRS(m4(), x, y, z, rx, ry, rz, sx, sy, sz), c: typeof c === 'string' ? col(c) : c });
  }
  box(x, y, z, sx, sy, sz, c, ry) { this.add('box', x, y, z, 0, ry || 0, 0, sx, sy, sz, c); }
  cyl(x, y, z, r, h, c, ry) { this.add('cyl', x, y, z, 0, ry || 0, 0, r * 2, h, r * 2, c); }
  sph(x, y, z, r, c) { this.add('sphere', x, y, z, 0, 0, 0, r * 2, r * 2, r * 2, c); }
  plate(x, y, z, sx, sz, c, ry) { this.add('quad', x, y, z, 0, ry || 0, 0, sx, 1, sz, c); }
  ring(x, y, z, r, c) { this.add('disc', x, y, z, 0, 0, 0, r * 2, 1, r * 2, c); }
  draw() { for (const it of this.items) R.m(it.p, it.m, it.c); }
}

/* ---------- shared field furniture ---------- */
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
    // the skinned infield is an arc of 95ft struck from the centre of the mound,
    // then trimmed back to fair territory and to the front of the plate
    S.ring(0, 0.010, 18.0, INFIELD_ARC, dirt);
    if (opt.ground) {
      for (const sgn of [-1, 1]) {   // everything outside a foul line is ground
        const dx = sgn * SQ2, dz = SQ2, nx = sgn * SQ2, nz = -SQ2;
        S.plate(dx * 40 + nx * 30, 0.012, dz * 40 + nz * 30, 60, 132, opt.ground, sgn * 45 * DEG);
      }
      S.plate(0, 0.0122, -10.4, 110, 12.8, opt.ground);
    }
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
  // The foul lines are never chalked across a batter's box, nor in the gap
  // between the box and the plate: each line starts where it leaves the front
  // edge of the box and runs from there out to the pole.
  const boxFront = PLATE_W / 2 + BOX_L / 2;
  const foulStart = boxFront / Math.cos(45 * DEG);
  for (const sgn of [-1, 1]) {
    const [sx, sz] = polar(45 * sgn, foulStart);
    const [fx, fz] = polar(45 * sgn, foulLen);
    chalkLine(S, sx, sz, fx, fz, chalk, CHALK_W);
  }
  // batter's boxes: a closed 4ft x 6ft rectangle, 6in either side of the plate
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
  // coach's boxes, 20ft x 10ft. They are chalked as three lines: the side
  // facing the field is left open so the coach can step out of it.
  for (const sgn of [-1, 1]) {
    const dx = sgn * SQ2, dz = SQ2;            // along that foul line
    const nx = sgn * SQ2, nz = -SQ2;           // out into foul territory
    const cx = dx * 20.5 + nx * 5.6, cz = dz * 20.5 + nz * 5.6;
    const hw = 1.525, hl = 3.05;
    const P = (u, v) => [cx + nx * u + dx * v, cz + nz * u + dz * v];
    const inA = P(-hw, -hl), inB = P(-hw, hl), outB = P(hw, hl), outA = P(hw, -hl);
    // the line the coach must stay behind is the one next to the foul line, so
    // that side is always chalked; the box is left open away from the field
    chalkLine(S, inA[0], inA[1], inB[0], inB[1], chalk);     // field side
    chalkLine(S, inB[0], inB[1], outB[0], outB[1], chalk);   // far end
    chalkLine(S, outA[0], outA[1], inA[0], inA[1], chalk);   // near end
  }
  // on-deck circles, 5ft across, 37ft from home in foul ground
  for (const sgn of [-1, 1]) chalkCircle(S, sgn * 9.0, -6.8, 0.76, chalk);

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

function addCrowdArc(S, from, to, dist, palette, tiers) {
  const N = 34;
  for (let i = 0; i <= N; i++) {
    const a = lerp(from, to, i / N);
    for (let t = 0; t < (tiers || 3); t++) {
      const d = dist + t * 3.4;
      const [x, z] = polar(a, d);
      const h = 1.6 + t * 1.7;
      S.box(x, h / 2, z, 4.2, h, 3.4, t % 2 ? '#3A4A5C' : '#31404F', a * DEG);
      if (i % 2 === 0) { // sparse crowd suggestion, cheap to draw
        const [hx, hz] = polar(a, d - 1.1);
        S.sph(hx, h + 0.42, hz, 0.42, pick(palette));
        S.box(hx, h + 0.02, hz, 0.9, 0.9, 0.7, pick(palette), a * DEG);
      }
    }
  }
}

function addFenceArc(S, st, colr, capC) {
  const N = 56;
  for (let i = 0; i <= N; i++) {
    const a = lerp(-46, 46, i / N);
    const d = fenceAt(st, a);
    const [x, z] = polar(a, d);
    S.box(x, st.fenceH / 2, z, 5.0, st.fenceH, 0.5, colr, a * DEG);
    S.box(x, st.fenceH + 0.09, z, 5.0, 0.22, 0.72, capC, a * DEG);
  }
  // foul poles
  for (const s of [-1, 1]) {
    const [x, z] = polar(45 * s, fenceAt(st, 45));
    S.cyl(x, 6, z, 0.22, 12, '#FFD24A');
  }
}

function addTree(S, x, z, h, leaf, trunk) {
  S.cyl(x, h * 0.3, z, 0.34, h * 0.6, trunk || '#6B4A32');
  S.sph(x, h * 0.72, z, h * 0.36, leaf);
  S.sph(x - h * 0.22, h * 0.58, z + h * 0.1, h * 0.26, shade(leaf, 0.88));
  S.sph(x + h * 0.2, h * 0.6, z - h * 0.12, h * 0.24, shade(leaf, 1.08));
}

function addCar(S, x, z, ry, body) {
  S.box(x, 0.72, z, 2.0, 0.85, 4.4, body, ry);
  S.box(x, 1.42, z + 0.15 * Math.cos(ry), 1.7, 0.7, 2.2, shade(body, 0.8), ry);
  S.box(x, 1.44, z + 0.16, 1.55, 0.5, 2.0, '#2A3A48', ry);
  for (const [ox, oz] of [[-1.0, 1.5], [1.0, 1.5], [-1.0, -1.5], [1.0, -1.5]])
    S.add('cyl', x + ox, 0.34, z + oz, 0, 0, Math.PI / 2, 0.68, 0.3, 0.68, col('#1B222A'));
  S.box(x, 0.95, z + 2.24, 1.6, 0.28, 0.14, '#FFE9A8', ry);
}

/* ---------- live traffic (the road park) ---------- */
const CAR_PAINT = ['#D9483B', '#3E6FBF', '#EFEFEF', '#2E3B45', '#E8B23A', '#48A96B', '#B44D8C', '#5FB6C4'];
const ROAD_Z0 = -58, ROAD_Z1 = 86;

const SHOPPER_WEAR = ['#C4483A', '#3E6FBF', '#4E8A5E', '#B4823A', '#7A5A9A', '#3C6E78'];
const SHOPPER_KIND = ['panda', 'hippo', 'rabbit', 'cat', 'bear', 'frog', 'fox'];
const GROCERY = ['#E8734A', '#F2C14E', '#7FB3D5', '#8ED0A8', '#C97BA0'];

function makeTraffic(st) {
  if (!st.lanes) return null;
  const cars = [];
  const z0 = st.laneZ ? st.laneZ[0] : ROAD_Z0, z1 = st.laneZ ? st.laneZ[1] : ROAD_Z1;
  for (const lane of st.lanes) {
    const n = lane.walk ? 2 : 2 + (chance(0.4) ? 1 : 0);
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
    R.b('box', c.x, 1.85, c.z + back * (c.hl * 0.72 + 0.16), c.hw * 1.6, 0.9, 0.2, col('#2A3A48'));
  } else {
    R.b('box', c.x, 0.72, c.z, c.hw * 2, 0.86, c.hl * 2, b);
    R.b('box', c.x, 1.36, c.z - back * 0.2, c.hw * 1.72, 0.66, c.hl * 1.05, shade(c.col, 0.86));
    R.b('box', c.x, 1.38, c.z - back * 0.2, c.hw * 1.6, 0.46, c.hl * 1.0, col('#2A3A48'));
  }
  for (const ox of [-1, 1]) for (const oz of [-1, 1])
    R.d('cyl', c.x + ox * c.hw * 0.92, 0.34, c.z + oz * c.hl * 0.62,
        0, 0, Math.PI / 2, 0.68, 0.28, 0.68, col('#1B222A'));
  R.b('box', c.x - c.hw * 0.55, 0.85, c.z + back * (c.hl - 0.02), 0.42, 0.24, 0.14, col('#FFE9A8'));
  R.b('box', c.x + c.hw * 0.55, 0.85, c.z + back * (c.hl - 0.02), 0.42, 0.24, 0.14, col('#FFE9A8'));
  R.b('box', c.x, 0.80, c.z - back * (c.hl - 0.02), c.hw * 1.5, 0.20, 0.12, col('#C8342A'));
}

/* a customer pushing a trolley down the aisle */
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
   ============================================================ */
const STADIUMS = [
  /* ---------------------------------------------------- 1 */
  {
    id: 'dome', name: 'みどりが丘スタジアム', tag: 'STANDARD',
    desc: '芝も土もきれいに整った、ふつうの野球場。フェンスは中堅104m。まずはここで基本を。',
    gravity: 9.8, fenceCenter: 104, fenceLine: 86, fenceH: 3.2, ceiling: 0,
    fog: '#8FC6E4', skyTint: '#BFE4F5', gndTint: '#4C7A45', fogDist: 330,
    light: [0.42, 0.80, 0.43], fielderSpeed: 1.0,
    quirk: '素直な打球がそのまま結果になる',
    cardColors: ['#4FA85C', '#C98A50', '#8FC6E4'],
    build() {
      const S = new Scene();
      S.plate(0, 0, 40, 460, 460, '#3E8F4C');
      // mowing stripes
      for (let i = -6; i <= 8; i++)
        if (i % 2 === 0) S.plate(0, 0.006, i * 16 + 8, 300, 16, '#469B54');
      addDiamond(S, { dirt: '#C08551', chalk: '#F4EFE2', fill: 1, grass: '#42964F',
        ground: '#3E8F4C', foulLen: fenceAt(this, 45) });
      addFenceArc(S, this, '#2F6C57', '#E9E4D4');
      addCrowdArc(S, -104, 104, 118, ['#E8734A', '#F2C14E', '#7FB3D5', '#E4E1D6', '#C97BA0', '#8ED0A8'], 3);
      // light towers
      for (const a of [-70, -34, 34, 70]) {
        const [x, z] = polar(a, 136);
        S.cyl(x, 15, z, 0.7, 30, '#5A6A78');
        S.box(x, 31.5, z, 9, 3.4, 1.0, '#2C3946', a * DEG);
        for (let i = -3; i <= 3; i++) S.sph(x + i * 1.3 * Math.cos(a * DEG), 31.5, z - i * 1.3 * Math.sin(a * DEG), 0.6, '#FFF6D0');
      }
      // scoreboard
      S.box(0, 13, 132, 34, 16, 1.4, '#243240');
      S.box(0, 13, 131, 30, 12.5, 0.6, '#11202C');
      for (let i = 0; i < 11; i++) for (let j = 0; j < 3; j++)
        S.box(-13 + i * 2.6, 15.5 - j * 3.2, 130.5, 1.7, 2.1, 0.3, j === 0 ? '#FFC44D' : '#2B4356');
      S.cyl(0, 24, 133, 0.4, 6, '#8C9AA6');
      return S;
    },
  },

  /* ---------------------------------------------------- 2 */
  {
    id: 'road', name: '国道１７号線のまんなか', tag: 'TRAFFIC',
    desc: '正面の高架壁まで88m。左右はビルがそのまま壁で、引っぱるほどフェンスが近い。おまけに車が試合の中を走り抜けるので、打球は跳ね、選手は轢かれる。',
    gravity: 9.8, fenceCenter: 88, fenceLine: 57, fenceH: 9.0, ceiling: 0,
    fenceFn: (a) => Math.min(88, 40 / Math.max(0.10, Math.abs(Math.sin(a * DEG)))),
    // Japan drives on the left: heading away from home you keep to +x
    lanes: [{ x: 8, dir: 1 }, { x: 18, dir: 1 }, { x: 27, dir: 1 },
            { x: -8, dir: -1 }, { x: -18, dir: -1 }, { x: -27, dir: -1 }],
    fog: '#A8B4BE', skyTint: '#CBD6DE', gndTint: '#5A5F63', fogDist: 240,
    light: [0.30, 0.86, 0.42], fielderSpeed: 0.94,
    quirk: '車は止まらない。当たった打球は生きたまま転がる',
    cardColors: ['#5C6268', '#E4E7EA', '#E8B23A'],
    build() {
      const S = new Scene();
      S.plate(0, 0, 40, 420, 420, '#54595E');
      // lane markings down the middle of the field
      for (let z = -14; z < 130; z += 8) S.box(0, 0.012, z, 0.5, 0.02, 4.6, '#E8E8DE');
      for (const s of [-1, 1]) {
        S.box(s * 26, 0.012, 45, 0.34, 0.02, 190, '#E8E8DE');
        S.box(s * 35, 0.16, 45, 7.0, 0.32, 210, '#8E9298');   // sidewalk
        S.box(s * 31.4, 0.2, 45, 0.4, 0.42, 210, '#B9BDC1');  // curb
      }
      addDiamond(S, { dirt: '#6C7177', chalk: '#F0EDE4', foulLen: fenceAt(this, 45) });
      // buildings on both sides — these are the outfield walls
      const bc = ['#8C7F72', '#7A8A93', '#9A8577', '#6F7C86', '#A0907F'];
      for (const s of [-1, 1]) {
        for (let z = -18; z < 140; z += 13) {
          const h = rnd(14, 34), w = rnd(10, 12.4), x = s * (40 + rnd(0, 2.5));
          const c = pick(bc);
          S.box(x, h / 2, z, w, h, 11, c);
          for (let fy = 3; fy < h - 2; fy += 3.4)
            for (let fx = -1; fx <= 1; fx++)
              S.box(x - s * 5.6, fy, z + fx * 3.4, 0.3, 1.5, 1.9, chance(0.3) ? '#FFE9AE' : '#3C4C58');
          S.box(x, h + 0.4, z, w + 0.7, 0.8, 11.7, shade(c, 0.8));
        }
      }
      // the road ducks under the overpass; cars appear and vanish in the mouth
      S.box(0, 3.1, 87.2, 56, 6.2, 0.5, '#1B2026');
      S.box(0, 6.4, 87.0, 58, 0.7, 1.0, '#5B6167');
      for (let i = -3; i <= 3; i++) S.box(i * 8, 6.9, 87.0, 1.4, 0.5, 0.9, '#E8C23A');
      // overpass wall straight ahead = centre-field fence
      S.box(0, 5, 88, 84, 10, 2, '#7E8489');
      S.box(0, 10.6, 88, 84, 1.4, 3.2, '#666C71');
      for (let i = -5; i <= 5; i++) S.box(i * 7.6, 12, 88, 1.2, 2.6, 3.6, '#565C61');
      S.box(0, 3.4, 87, 26, 3.0, 0.3, '#2C5FA8');
      S.box(0, 3.4, 86.8, 22, 2.2, 0.2, '#EDF1F4');
      // parked cars along the sidewalks + traffic lights
      for (let z = -10; z < 120; z += 22) {
        addCar(S, -29, z, 0, pick(['#D9483B', '#3E6FBF', '#EFEFEF', '#2E3B45', '#E8B23A']));
        addCar(S, 29, z + 11, Math.PI, pick(['#48A96B', '#EFEFEF', '#B44D8C', '#3E6FBF']));
      }
      for (const s of [-1, 1]) {
        S.cyl(s * 32, 3, 30, 0.16, 6, '#4A555F');
        S.box(s * 32, 6.2, 30, 0.7, 1.9, 0.5, '#2C3841');
        S.sph(s * 32, 6.7, 29.7, 0.2, '#E85A3A'); S.sph(s * 32, 6.2, 29.7, 0.2, '#E8C23A'); S.sph(s * 32, 5.7, 29.7, 0.2, '#5ECB7A');
        S.cyl(s * 32.6, 1.7, 62, 0.13, 3.4, '#4A555F');
        S.box(s * 32.6, 3.6, 62, 1.5, 1.1, 0.2, '#2E7D4F');
      }
      return S;
    },
  },

  /* ---------------------------------------------------- 3 */
  {
    id: 'market', name: 'スーパーおおぞら 店内', tag: 'INDOOR',
    desc: '天井が10.5mしかない。高く上げた打球は天井に当たって落ちてくるので、冷凍ケースの壁（中堅62m）を越えたければ低いライナーで運ぶしかない。通路を歩く買い物客にぶつかると転ばされる。',
    gravity: 9.8, fenceCenter: 62, fenceLine: 48, fenceH: 3.4, ceiling: 10.5,
    fog: '#A9B0A8', skyTint: '#D6DBD2', gndTint: '#79807A', fogDist: 300,
    light: [0.18, 0.94, 0.28], fielderSpeed: 0.84,
    lanes: [{ x: -25, dir: 1, walk: 1 }, { x: 25, dir: -1, walk: 1 },
            { x: -17, dir: -1, walk: 1 }, { x: 17, dir: 1, walk: 1 },
            { x: -9, dir: -1, walk: 1 }, { x: 9, dir: 1, walk: 1 }],
    laneZ: [-16, 74],
    quirk: '天井10.5m。買い物客とぶつかると倒される',
    cardColors: ['#E4E6DE', '#E8734A', '#5FB6C4'],
    build() {
      const S = new Scene();
      // tiled floor
      for (let x = -6; x <= 6; x++) for (let z = -2; z <= 10; z++)
        S.plate(x * 8, 0, z * 8, 8, 8, (x + z) % 2 ? '#B5AE9E' : '#A29A89');
      // vinyl guide stripes, like a real shop floor
      for (let z = -16; z < 100; z += 24) S.plate(0, 0.008, z, 104, 1.2, '#6F8C86');
      addDiamond(S, { dirt: '#C2A155', chalk: '#FFFFFF', foulLen: fenceAt(this, 45) });
      // ceiling + light panels + ducts
      S.plate(0, 10.5, 40, 230, 230, '#9BA29B');
      for (let x = -4; x <= 4; x++) for (let z = 0; z <= 8; z++)
        S.box(x * 13, 10.3, z * 11 - 8, 9.4, 0.3, 1.2, '#FFF8DC');
      for (let x = -3; x <= 3; x += 3) S.box(x * 13, 9.7, 40, 1.6, 1.0, 140, '#AAB0AC');
      // side walls
      for (const s of [-1, 1]) {
        S.box(s * 54, 5.25, 40, 1.0, 10.5, 160, '#C9CEC4');
        for (let z = -10; z < 110; z += 16) S.box(s * 53.2, 2.4, z, 0.4, 4.8, 9, pick(['#5FB6C4', '#E8B23A', '#E8734A']));
      }
      // back wall = freezer cases (the outfield fence)
      addFenceArc(S, this, '#B9C6C9', '#8FA2A8');
      for (let i = -4; i <= 4; i++) {
        const [x, z] = polar(i * 10, fenceAt(this, i * 10) + 2.4);
        S.box(x, 2.4, z, 7.4, 4.8, 2.4, '#C9D6D8', i * 10 * DEG);
        S.box(x, 2.6, z - 1.2, 6.4, 3.6, 0.2, '#7FB8C4', i * 10 * DEG);
        S.box(x, 5.4, z, 7.4, 1.0, 2.6, '#5FB6C4', i * 10 * DEG);
      }
      // shelf aisles in the outfield — outfielders have to run around them
      const goods = ['#E8734A', '#F2C14E', '#7FB3D5', '#8ED0A8', '#C97BA0', '#E4E1D6'];
      for (const [sx, sz, len, rot] of [[-32, 34, 16, 0], [32, 34, 16, 0], [-17, 52, 13, 0], [17, 52, 13, 0], [0, 50, 15, Math.PI / 2]]) {
        for (let i = -len / 2; i < len / 2; i += 2) {
          const dx = rot ? i : 0, dz = rot ? 0 : i;
          S.box(sx + dx, 1.1, sz + dz, rot ? 2.0 : 3.0, 2.2, rot ? 3.0 : 2.0, '#77807C');
          for (let t = 0; t < 3; t++)
            S.box(sx + dx, 0.5 + t * 0.72, sz + dz + (rot ? 0 : 1.05), rot ? 1.8 : 2.6, 0.5, rot ? 2.6 : 0.4, pick(goods));
        }
      }
      // checkout lanes behind home plate
      for (let i = -2; i <= 2; i++) {
        S.box(i * 6, 0.5, -14, 4.4, 1.0, 2.4, '#D8CFC0');
        S.box(i * 6 + 1.6, 1.3, -14, 1.0, 0.7, 1.4, '#465059');
        S.cyl(i * 6 - 1.8, 1.6, -14, 0.12, 3.2, '#8E9298');
        S.box(i * 6 - 1.8, 3.3, -14, 1.4, 0.9, 0.2, '#E8B23A');
      }
      S.box(0, 7.6, -22, 26, 2.4, 0.5, '#E8734A');
      S.box(0, 7.6, -22.4, 22, 1.4, 0.3, '#FFF8E8');
      return S;
    },
  },

  /* ---------------------------------------------------- 4 */
  {
    id: 'river', name: '河川敷グラウンド', tag: 'NO FENCE',
    desc: 'フェンスなし。抜けたら止まるまで走れるのでランニングホームランが出る。川まで届けば文句なしの一発。',
    gravity: 9.8, fenceCenter: 112, fenceLine: 96, fenceH: 0, ceiling: 0,
    fog: '#C6D3B8', skyTint: '#DCEAF2', gndTint: '#7A8A5C', fogDist: 300,
    light: [-0.36, 0.82, 0.44], fielderSpeed: 1.0,
    quirk: 'フェンスなし。長打はランニングホームランになりうる',
    cardColors: ['#A8A06C', '#6FA8C4', '#7FA24E'],
    build() {
      const S = new Scene();
      S.plate(0, 0, 40, 460, 460, '#8B9455');
      for (let i = -5; i <= 8; i++) S.plate(rnd(-60, 60), 0.006, i * 18, rnd(14, 34), rnd(8, 16), '#7C8A4C');
      addDiamond(S, { dirt: '#B08A56', chalk: '#EFEDE0', fill: 1,
        ground: '#8B9455', foulLen: fenceAt(this, 45) });
      // river across the back
      S.plate(0, 0.2, 150, 460, 66, '#5E93B8');
      for (let i = 0; i < 30; i++) S.plate(rnd(-150, 150), 0.24, rnd(126, 176), rnd(6, 16), rnd(1.2, 2.6), '#7FB2D2');
      S.box(0, 0.55, 117, 460, 1.1, 6, '#8A8A6E');   // levee path
      S.box(0, 1.6, 121, 460, 1.0, 1.4, '#C8C4A8');  // rail
      // bridge in the distance
      S.box(64, 8, 150, 12, 1.6, 80, '#9AA0A6');
      for (const z of [128, 150, 172]) { S.cyl(60, 4, z, 1.4, 8, '#8A9098'); S.cyl(68, 4, z, 1.4, 8, '#8A9098'); }
      for (let i = 0; i < 9; i++) S.box(64, 11, 118 + i * 9, 12.6, 5, 0.6, '#B4BAC0');
      // trees, benches, bikes along the sides
      for (let i = 0; i < 26; i++) {
        const s = i % 2 ? 1 : -1;
        addTree(S, s * rnd(62, 108), rnd(-24, 128), rnd(6, 11), pick(['#5E8A3E', '#6E9A46', '#4E7A36']));
      }
      for (let i = 0; i < 5; i++) {
        const x = -54 - i * 3, z = -14 + i * 16;
        S.box(x, 0.46, z, 3.4, 0.16, 1.0, '#8A6A46'); S.box(x, 0.86, z - 0.42, 3.4, 0.8, 0.16, '#8A6A46');
        S.cyl(x - 1.3, 0.24, z, 0.1, 0.48, '#5A5A5A'); S.cyl(x + 1.3, 0.24, z, 0.1, 0.48, '#5A5A5A');
      }
      for (let i = 0; i < 8; i++) {
        const x = 50 + i * 2.2, z = -6;
        S.add('cyl', x, 0.62, z, Math.PI / 2, 0, 0, 1.24, 0.1, 1.24, col('#3C3C3C'));
        S.add('cyl', x, 0.62, z + 1.5, Math.PI / 2, 0, 0, 1.24, 0.1, 1.24, col('#3C3C3C'));
        S.box(x, 1.0, z + 0.75, 0.16, 0.7, 1.7, pick(['#C4483A', '#3E6FBF', '#4E8A5E']));
      }
      S.box(-40, 2.4, -20, 0.3, 4.8, 12, '#B0B4B8'); // backstop netting posts
      S.box(40, 2.4, -20, 0.3, 4.8, 12, '#B0B4B8');
      return S;
    },
  },

  /* ---------------------------------------------------- 5 */
  {
    id: 'moon', name: '月面クレーター球場', tag: 'LOW GRAVITY',
    desc: '重力は地球のおよそ半分。打球はよく伸びるがフェンスも中堅176mと遠く、滞空時間が1.4倍になるぶんフライは外野に追いつかれやすい。',
    gravity: 5.4, fenceCenter: 176, fenceLine: 146, fenceH: 3.0, ceiling: 0,
    fog: '#1B2230', skyTint: '#3E4C66', gndTint: '#5A5A5E', fogDist: 560,
    light: [0.52, 0.72, 0.46], fielderSpeed: 0.9,
    quirk: '低重力。飛距離も滞空時間も伸びる',
    cardColors: ['#8E8E94', '#1B2230', '#C8D4E8'],
    build() {
      const S = new Scene();
      S.plate(0, 0, 40, 700, 700, '#83838C');
      for (let i = 0; i < 110; i++) {
        const x = rnd(-280, 280), z = rnd(-70, 320);
        if (dist2(x, z, 0, 19.4) < 30) continue;    // keep the diamond clear
        const r = rnd(2.5, 16);
        S.ring(x, 0.02, z, r, '#63636B'); S.ring(x, 0.03, z, r * 0.7, '#8E8E97');
      }
      for (let i = 0; i < 70; i++) {                 // scattered rocks
        const x = rnd(-160, 160), z = rnd(-40, 220);
        if (dist2(x, z, 0, 19.4) < 26) continue;
        const r = rnd(0.5, 2.2);
        S.sph(x, r * 0.4, z, r, i % 3 ? '#72727A' : '#8A8A93');
      }
      addDiamond(S, { dirt: '#9A9AA2', chalk: '#E8ECF4', fill: 1,
        ground: '#83838C', foulLen: fenceAt(this, 45) });
      addFenceArc(S, this, '#3E4658', '#96A2B8');
      // stars
      for (let i = 0; i < 150; i++) {
        const a = rnd(-Math.PI, Math.PI), e = rnd(0.08, 0.9), d = 700;
        S.sph(Math.sin(a) * Math.cos(e) * d, Math.sin(e) * d + 10, Math.cos(a) * Math.cos(e) * d, rnd(0.8, 2.4), '#E8EEFA');
      }
      // Earth hanging over centre field
      S.sph(-66, 158, 560, 48, '#3E6FA8');
      S.sph(-86, 172, 520, 19, '#5E9A5E'); S.sph(-36, 136, 526, 16, '#5E9A5E');
      S.sph(-56, 186, 522, 12, '#E4EAF2'); S.sph(-78, 130, 528, 11, '#E4EAF2');
      // base modules + rovers
      for (const a of [-62, 62]) {
        const [x, z] = polar(a, 218);
        S.cyl(x, 4, z, 8, 8, '#C4C8D2'); S.add('dome', x, 8, z, 0, 0, 0, 16, 10, 16, col('#D6DAE4'));
        S.cyl(x + 12, 3, z + 6, 1.0, 6, '#9AA0AC');
        S.box(x + 12, 6.6, z + 6, 5, 0.4, 5, '#2E3A4E');
      }
      S.cyl(0, 6, 206, 0.4, 12, '#B4BAC6');
      S.box(1.9, 11, 206, 3.6, 2.2, 0.12, '#D94A3A');
      return S;
    },
  },
];

const stadiumById = (id) => STADIUMS.find((s) => s.id === id);

/* ---------- fielder stations, derived from the park ---------- */
const POS_DEF = [
  { k: 'P',  a: 0,   d: () => 18.44,          nm: '投手',   sn: 'ピッチャー' },
  { k: 'C',  a: 0,   d: () => -3.4,           nm: '捕手',   sn: 'キャッチャー' },
  { k: '1B', a: -38, d: () => 27,             nm: '一塁手', sn: 'ファースト' },
  { k: '2B', a: -20, d: () => 36,             nm: '二塁手', sn: 'セカンド' },
  { k: 'SS', a: 20,  d: () => 36,             nm: '遊撃手', sn: 'ショート' },
  { k: '3B', a: 38,  d: () => 27,             nm: '三塁手', sn: 'サード' },
  { k: 'LF', a: 30,  d: (st) => fenceAt(st, 30) * 0.76,  nm: '左翼手', sn: 'レフト' },
  { k: 'CF', a: 0,   d: (st) => fenceAt(st, 0) * 0.78,   nm: '中堅手', sn: 'センター' },
  { k: 'RF', a: -30, d: (st) => fenceAt(st, -30) * 0.76, nm: '右翼手', sn: 'ライト' },
];

function stationsFor(st) {
  return POS_DEF.map((p) => {
    const d = p.d(st);
    const [x, z] = polar(p.a, Math.abs(d));
    return { k: p.k, nm: p.nm, sn: p.sn, x, z: d < 0 ? d : z, infield: ['P', 'C', '1B', '2B', 'SS', '3B'].includes(p.k) };
  });
}
