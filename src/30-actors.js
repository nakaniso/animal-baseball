/* ============================================================
   30-actors.js — deformed animal players, bats, gloves, the ball
   ============================================================ */
'use strict';

/* local(character) -> world, given a yaw frame */
function yawFrame(x, z, ry) { return { x, z, ry, c: Math.cos(ry), s: Math.sin(ry), t: 0 }; }
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
}

/* where a bone of this length, hung at these angles, puts its far end. Baked
   bones (the beetle's toothed shin) are placed with it, so they land exactly
   where `limb` would have drawn a cylinder. */
function limbTip(jx, jy, jz, rx, rz, len) {
  const cz = Math.cos(rz), cx = Math.cos(rx);
  return [jx + Math.sin(rz) * len, jy - cx * cz * len, jz - Math.sin(rx) * cz * len];
}

/* a limb hanging from a joint, rotated by rx (swing) and rz (splay) */
function limb(f, jx, jy, jz, rx, rz, len, rad, c, endC, endS, flat) {
  const e = limbTip(jx, jy, jz, rx, rz, len);
  part(f, 'cyl', (jx + e[0]) / 2, (jy + e[1]) / 2, (jz + e[2]) / 2,
       rad * 2, len, rad * 2, c, rx, rz);
  if (endC === null) return e;
  if (endC) {
    const s = endS || rad * 2.5;
    if (flat) part(f, 'rbox', e[0], e[1] - s * 0.08, e[2] + s * 0.16,
                   s * 0.92, s * 0.66, s * 1.34, endC, rx, rz);
    else part(f, 'sphere', e[0], e[1], e[2], s, s * 0.9, s, endC);
  }
  return e;
}

/* Two-bone IK in world space: the hand lands exactly on the target, so whatever
   it is holding stays held. Cartoon arms stretch rather than fall short. */
function armIK(sx, sy, sz, hx, hy, hz, L1, L2, pole, rad, c, handC) {
  let dx = hx - sx, dy = hy - sy, dz = hz - sz;
  let d = Math.hypot(dx, dy, dz) || 1e-4;
  if (d > (L1 + L2) * 0.995) {
    // cartoon arms give a little, but never more than a third of their length;
    // past that the hand is pulled in rather than the limb turned into a pole
    const need = d / (L1 + L2);
    const give = Math.min(need, 1.32);
    L1 *= give * 1.02; L2 *= give * 1.02;
    if (need > 1.32) {
      const k = ((L1 + L2) * 0.995) / d;
      hx = sx + dx * k; hy = sy + dy * k; hz = sz + dz * k;
      dx *= k; dy *= k; dz *= k; d *= k;
    }
  }
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
  if (handC !== null) R.b('sphere', hx, hy, hz, rad * 2.2, rad * 2.1, rad * 2.2, handC || c);
  return [hx, hy, hz];
}

/* ---------- animal species ---------- */
/* hw/hh/hd scale the head; muz is the size of the muzzle; brow adds the drawn
   eyebrow strokes; earR/earX/earY place the ears. */
const ANIMALS = {
  // Stage 3. `mesh` swaps the head, the muzzle, the ears and the torso for
  // shells baked by tools/mesh2js.py, so the skull and the snout are one
  // surface and the jersey has shoulders. Everything else — arms, legs, cap,
  // the four expressions — still comes from the shared rig. The head numbers
  // the other mammals carry (hw/muz/earR/eyeX) are the mesh's business now.
  bear:    { ink: 0.022, mesh: 'bear', tail: 'nub', tailZ: -0.235,
             fur: '#96683F', fur2: '#DFC49B' },

  // Drawn from the reference sketch: tall straight ears, round head, dot eyes.
  // Ears, haunches, hind feet and tail are baked (段階3); the head is still a
  // sphere because that is the surface the drawn face is projected onto.
  rabbit:  { ink: 0.022, ear: 'bunny', fur: '#F4F0E8', fur2: '#F6D7DA', tail: 'cotton',
             head: 'sphere', hw: 1.08, hh: 1.06, hd: 0.98, capY: -0.075,
             buttons: 1,                   // no muzzle — the nose is drawn on
             legs: 'bunny', earX: 0.148, earY: 0.18, earTilt: 0.13,
             earIn: '#F6D7DA',
             dotEyes: 1, eyeX: 0.150, eyeW: 0.086, eyeH: 0.098 },

  cat:     { ink: 0.022, ear: 'point', fur: '#E0A44F', fur2: '#F7EDDD', tail: 'long',
             head: 'rbox', hw: 1.10, hh: 0.98, hd: 0.94,
             muz: [0.46, 0.255, 0.26], muzY: -0.125, muzZ: 0.245,
             noseR: 0.085, noseC: '#C2705E', whisk: 1,
             earR: 0.255, earX: 0.235, earY: 0.36, earT: 0.26,
             eyeX: 0.156, eyeW: 0.145, eyeH: 0.100, eyeTilt: 0.16 },

  frog:    { ink: 0.022, ear: 'toad', fur: '#7DC163', fur2: '#E8F0C8', tail: 'none',
             head: 'rbox', hw: 1.24, hh: 0.86, hd: 1.02,
             noFaceEyes: 1, mouth: 1,
             earR: 0.285, earX: 0.275, earY: 0.13, earZ: 0.24 },

  penguin: { ink: 0.022, ear: 'none', fur: '#2E3B4A', fur2: '#F4F1E6', tail: 'nub',
             beak: '#F2A93B', head: 'sphere', hw: 1.02, hh: 1.08, hd: 0.98,
             facePatch: [0.54, 0.58, 0.30],
             eyeX: 0.138, eyeW: 0.104, eyeH: 0.104 },

  fox:     { ink: 0.022, ear: 'point', fur: '#D96F3A', fur2: '#F6EFE2', tail: 'bushy',
             head: 'rbox', hw: 1.04, hh: 0.96, hd: 1.08,
             muz: [0.33, 0.235, 0.46], muzY: -0.115, muzZ: 0.30, noseR: 0.082,
             cheek: 0.21, cheekC: '#F6EFE2',
             earR: 0.275, earX: 0.255, earY: 0.38, earT: 0.22, earTip: '#3C2A20',
             eyeX: 0.156, eyeW: 0.140, eyeH: 0.098, eyeTilt: 0.20 },

  // Drawn as the real animal rather than a round cartoon of one, and given no
  // face cell, so they never change expression.
  salmon:  { ink: 0.013, body: 'fish', ear: 'none', tail: 'none', noHat: 1, shadow: 1.5,
             noGlove: 1, noBat: 1,
             fur: '#B4C2CB', fur2: '#EFF2F0', back: '#3C5E71', blush: '#B0524C',
             fin: '#7F909B', spot: '#22323C', jaw: '#9DAAB2',
             head: 'sphere', hw: 0.60, hh: 0.78, hd: 1.30 },

  beetle:  { ink: 0.013, body: 'beetle', ear: 'none', tail: 'none', capY: -0.20, capS: 0.40,
             noGlove: 1, noBat: 1,
             fur: '#3E2717', fur2: '#5C3C22', horn: '#20130A', leg: '#281A0E',
             head: 'rbox', hw: 0.66, hh: 0.50, hd: 0.66 },

  panda:   { ink: 0.022, ear: 'round', fur: '#F0EDE6', fur2: '#2C3138', tail: 'nub', patch: 1,
             head: 'rbox', hw: 1.12, hh: 1.04, hd: 0.98,
             muz: [0.44, 0.28, 0.28], muzY: -0.13, muzZ: 0.24, noseR: 0.10,
             earR: 0.25, earX: 0.32, earY: 0.315, earD: 0.60, earC: '#2C3138',
             eyeX: 0.166, eyeW: 0.135, eyeH: 0.110 },

  hippo:   { ink: 0.022, ear: 'round', fur: '#9E86C4', fur2: '#D8C9EC', tail: 'nub', big: 1,
             head: 'rbox', hw: 1.18, hh: 0.92, hd: 1.02,
             muz: [0.62, 0.36, 0.38], muzY: -0.115, muzZ: 0.24, noseR: 0.072, nostril: 1,
             earR: 0.165, earX: 0.34, earY: 0.30, earD: 0.60,
             eyeX: 0.186, eyeW: 0.115, eyeH: 0.095 },
};

const EYE = '#22282F', SHINE = '#FFFFFF';

/* ============================================================
   Face atlas — the faces are drawn as art into a texture rather
   than assembled out of spheres. 8 cells across x 8 down, 128px
   each: row = species, cols 0-3 = the head (eyes, brows, cheeks),
   cols 4-7 = the muzzle (nose, mouth), one column per expression.
   ============================================================ */
const FACE_N = 8, FACE_PX = 128;
const FACE_ORDER = ['bear', 'rabbit', 'cat', 'frog', 'penguin', 'fox', 'panda', 'hippo'];
const EXPR = { idle: 0, focus: 1, happy: 2, down: 3 };

/* eye/nose/mouth art per species, in 0..1 of a cell, y measured from the top */
const FACES = {
  bear:    { eye: 'round',  eyeX: 0.190, eyeY: 0.340, eyeR: 0.086, brow: '#5B3E24',
             nose: 'tri',   noseC: '#3A2A22', noseY: 0.300, noseR: 0.150, mouth: 'w' },
  // the rabbit has no muzzle at all, so its nose and mouth go on the head
  rabbit:  { eye: 'dot',    eyeX: 0.200, eyeY: 0.355, eyeR: 0.062, onHead: 1,
             nose: 'dot',   noseC: '#4A3438', noseY: 0.655, noseR: 0.050, mouth: 'w',
             mouthC: '#4A3438', mouthY: 0.745, mouthW: 0.085 },
  cat:     { eye: 'almond', eyeX: 0.205, eyeY: 0.355, eyeR: 0.092, tilt: 0.16, whisk: '#B0895A',
             nose: 'tri',   noseC: '#C2705E', noseY: 0.295, noseR: 0.140, mouth: 'w' },
  frog:    { eye: 'none',   headMouth: 'wide', mouthC: '#3E6B33' },
  penguin: { eye: 'bead',   eyeX: 0.250, eyeY: 0.300, eyeR: 0.076, onPatch: 1 },
  fox:     { eye: 'almond', eyeX: 0.205, eyeY: 0.350, eyeR: 0.084, tilt: 0.20,
             nose: 'tri',   noseC: '#3C2A20', noseY: 0.300, noseR: 0.175, mouth: 'w',
             mouthY: 0.560, mouthW: 0.200 },
  panda:   { eye: 'round',  eyeX: 0.215, eyeY: 0.345, eyeR: 0.076,
             nose: 'tri',   noseC: '#2C3138', noseY: 0.295, noseR: 0.140, mouth: 'w' },
  hippo:   { eye: 'round',  eyeX: 0.245, eyeY: 0.360, eyeR: 0.062,
             nose: 'nostril', noseC: '#6B5487', noseY: 0.300, noseR: 0.095, mouth: 'line' },
};

function fStroke(g, c, w) { g.strokeStyle = c; g.lineWidth = w; g.lineCap = 'round'; g.lineJoin = 'round'; }

/* one eye, centred on (x,y). s is -1 for the reader's left eye, +1 the right */
function drawEye(g, F, exp, x, y, s) {
  const r = F.eyeR, tilt = (F.tilt || 0) * s;
  if (exp === EXPR.happy) {                       // a closed upward arc
    fStroke(g, EYE, r * 0.52);
    g.beginPath();
    g.arc(x, y + r * 0.42, r * 0.98, Math.PI * 1.12, Math.PI * 1.88);
    g.stroke();
    return;
  }
  const squash = exp === EXPR.focus ? 0.74 : exp === EXPR.down ? 0.58 : 1;
  const drop = exp === EXPR.down ? r * 0.20 : 0;
  g.save();
  g.translate(x, y + drop);
  g.rotate(tilt);
  g.fillStyle = EYE;
  g.beginPath();
  g.ellipse(0, 0, r, r * (F.eye === 'almond' ? 1.06 : 1) * squash, 0, 0, Math.PI * 2);
  g.fill();
  if (exp !== EXPR.down) {                        // catchlight
    const k = F.eye === 'dot' || F.eye === 'bead' ? 0.22 : 0.30;
    g.fillStyle = SHINE;
    g.beginPath();
    g.ellipse(r * 0.28, -r * 0.32 * squash, r * k, r * k * squash, 0, 0, Math.PI * 2);
    g.fill();
  }
  g.restore();
}

/* the brow stroke: level when idle, driven in when focused, up at the outer
   end when dejected — it carries most of the expression */
function drawBrow(g, F, exp, x, y, s, col) {
  if (exp === EXPR.happy) return;
  const r = F.eyeR, w = r * 1.55, lift = exp === EXPR.focus ? r * 0.62 : r * 1.05;
  const inner = exp === EXPR.focus ? r * 0.46 : exp === EXPR.down ? -r * 0.34 : 0;
  fStroke(g, col, r * 0.40);
  g.beginPath();
  g.moveTo(x - s * w * 0.5, y - lift - inner);
  g.quadraticCurveTo(x, y - lift - inner * 0.45 - r * 0.18, x + s * w * 0.5, y - lift + inner * 0.30);
  g.stroke();
}

function drawHeadCell(g, F, exp) {
  if (F.eye !== 'none') {
    for (const s of [-1, 1]) drawEye(g, F, exp, 0.5 + s * F.eyeX, F.eyeY, s);
    if (F.brow) for (const s of [-1, 1]) drawBrow(g, F, exp, 0.5 + s * F.eyeX, F.eyeY, s, F.brow);
  }
  if (F.whisk) {
    fStroke(g, F.whisk, 0.013);
    for (const s of [-1, 1]) for (let i = 0; i < 3; i++) {
      const y = 0.50 + (i - 1) * 0.055;
      g.beginPath();
      g.moveTo(0.5 + s * 0.20, y);
      g.quadraticCurveTo(0.5 + s * 0.36, y - 0.02 + (i - 1) * 0.02,
                         0.5 + s * 0.49, y - 0.05 + (i - 1) * 0.05);
      g.stroke();
    }
  }
  if (F.nose && F.onHead) drawSnout(g, F, exp);
  if (F.headMouth === 'wide') {                   // the frog's grin spans the head
    const y = 0.60;
    fStroke(g, F.mouthC, 0.036);
    g.beginPath();
    if (exp === EXPR.down) { g.moveTo(0.16, y + 0.09); g.quadraticCurveTo(0.5, y - 0.05, 0.84, y + 0.09); }
    else if (exp === EXPR.happy) { g.moveTo(0.14, y - 0.07); g.quadraticCurveTo(0.5, y + 0.16, 0.86, y - 0.07); }
    else { g.moveTo(0.16, y - 0.02); g.quadraticCurveTo(0.5, y + 0.10, 0.84, y - 0.02); }
    g.stroke();
  }
}

function drawSnout(g, F, exp) {
  const nx = 0.5, ny = F.noseY, nr = F.noseR;
  g.fillStyle = F.noseC;
  if (F.nose === 'tri') {                         // a rounded triangle, point down
    const w = nr, h = nr * 0.80;
    g.beginPath();
    g.moveTo(nx - w, ny - h * 0.55);
    g.quadraticCurveTo(nx, ny - h * 0.95, nx + w, ny - h * 0.55);
    g.quadraticCurveTo(nx + w * 0.55, ny + h * 0.75, nx, ny + h);
    g.quadraticCurveTo(nx - w * 0.55, ny + h * 0.75, nx - w, ny - h * 0.55);
    g.fill();
  } else if (F.nose === 'nostril') {
    for (const s of [-1, 1]) {
      g.beginPath();
      g.ellipse(nx + s * nr * 1.5, ny, nr * 0.52, nr * 0.72, 0, 0, Math.PI * 2);
      g.fill();
    }
  } else {
    g.beginPath(); g.ellipse(nx, ny, nr, nr * 0.82, 0, 0, Math.PI * 2); g.fill();
  }

  const my = F.mouthY || 0.520, mw = F.mouthW || 0.180, mc = F.mouthC || F.noseC;
  fStroke(g, mc, 0.028);
  if (F.mouth === 'line') {
    g.beginPath();
    if (exp === EXPR.happy) { g.moveTo(nx - mw, my); g.quadraticCurveTo(nx, my + mw * 0.55, nx + mw, my); }
    else if (exp === EXPR.down) { g.moveTo(nx - mw, my + mw * 0.40); g.quadraticCurveTo(nx, my - mw * 0.25, nx + mw, my + mw * 0.40); }
    else { g.moveTo(nx - mw, my); g.lineTo(nx + mw, my); }
    g.stroke();
    return;
  }
  // the default: a stem down from the nose, splitting into two lobes
  g.beginPath(); g.moveTo(nx, ny + nr * 0.72); g.lineTo(nx, my - mw * 0.30); g.stroke();
  if (exp === EXPR.happy) {                       // open, filled
    g.fillStyle = mc;
    g.beginPath();
    g.moveTo(nx - mw, my - mw * 0.22);
    g.quadraticCurveTo(nx, my + mw * 1.15, nx + mw, my - mw * 0.22);
    g.quadraticCurveTo(nx, my + mw * 0.10, nx - mw, my - mw * 0.22);
    g.fill();
    return;
  }
  for (const s of [-1, 1]) {
    g.beginPath();
    if (exp === EXPR.down) {
      g.moveTo(nx, my + mw * 0.34);
      g.quadraticCurveTo(nx + s * mw * 0.52, my + mw * 0.20, nx + s * mw, my - mw * 0.22);
    } else if (exp === EXPR.focus) {
      g.moveTo(nx, my - mw * 0.10);
      g.lineTo(nx + s * mw * 0.86, my - mw * 0.10);
    } else {
      g.moveTo(nx, my - mw * 0.18);
      g.quadraticCurveTo(nx + s * mw * 0.55, my + mw * 0.42, nx + s * mw, my - mw * 0.08);
    }
    g.stroke();
  }
}

/* built once at boot; nothing here runs per frame */
function drawMuzCell(g, F, exp) { if (F.nose && !F.onHead) drawSnout(g, F, exp); }

function buildFaceAtlas() {
  const S = FACE_PX, cv = document.createElement('canvas');
  cv.width = cv.height = FACE_N * S;
  const g = cv.getContext('2d');
  FACE_ORDER.forEach((name, row) => {
    const F = FACES[name];
    if (!F) return;
    for (let e = 0; e < 4; e++) {
      for (const cell of [[e, drawHeadCell], [e + 4, drawMuzCell]]) {
        g.save();
        g.translate(cell[0] * S, row * S);
        g.beginPath(); g.rect(0, 0, S, S); g.clip();
        g.scale(S, S);
        cell[1](g, F, e);
        g.restore();
      }
    }
  });
  return cv;
}

/* Hand-drawn cells, baked from a scan by tools/face-lab.html and pasted in
   here as PNG data URIs. The key is 'species:cell', where cell 0-3 is the head
   and 4-7 the muzzle, one per expression — the same numbering as the atlas.
   A cell listed here replaces the drawn-in-code one; everything else is
   untouched. */
const FACE_SCANS = {
  'rabbit:0': 'data:image/png;base64,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',
};

/* data URIs still decode asynchronously, so the atlas goes up as-is first and
   again once the scans have landed */
function applyFaceScans(cv, done) {
  const keys = Object.keys(FACE_SCANS);
  if (!keys.length) return;
  const g = cv.getContext('2d');
  let left = keys.length;
  for (const k of keys) {
    const bits = k.split(':'), row = FACE_ORDER.indexOf(bits[0]), col = +bits[1];
    const img = new Image();
    img.onload = img.onerror = () => {
      if (img.width && row >= 0) {
        g.clearRect(col * FACE_PX, row * FACE_PX, FACE_PX, FACE_PX);
        g.drawImage(img, col * FACE_PX, row * FACE_PX, FACE_PX, FACE_PX);
      }
      if (--left === 0) done();
    };
    img.src = FACE_SCANS[k];
  }
}

/* uv rect for one cell: [scaleU, scaleV, offsetU, offsetV] */
function faceRect(animal, exp, muz) {
  const row = FACE_ORDER.indexOf(animal);
  if (row < 0) return null;
  const col = (exp || 0) + (muz ? 4 : 0), k = 1 / FACE_N;
  return [k, k, col * k, row * k];
}

/* ============================================================
   The odd ones out.

   Every mammal here is a round cartoon of an animal. These two are the animal:
   their shells come from tools/mesh2js.py, which lofts a salmon through real
   elliptical sections and sweeps a Trypoxylus horn along a curve that forks
   twice. Stacked spheres cannot make either shape.

   Neither has arms, and neither stands still.
     * The salmon has no limbs at all. It flops — in the box, in the field, on
       the base paths — and it hits with its body.
     * The beetle has six legs and hits with its horn. No bat, no glove.

   They keep the shared rig's anchors (torso y+0.74, head y+1.34) so the
   camera, the shadow, knockdowns and slides all still work on them.
   ============================================================ */

/* The flop. A salmon out of water does not stand up — it lies over on its side
   and thrashes, slapping itself clear of the ground every other beat.

   `pitch` is how far it has gone over from upright (about 68 degrees at rest),
   and the body turns about a point partway up rather than about its tail, so
   the nose does not swing a metre across the infield every time it twitches. */
const SAL_PIVOT = 0.60;

function fishFlop(seed) {
  const t = clock * 5.4 + seed;
  const s = Math.sin(t);
  return {
    pitch: 1.19 + s * 0.27,                          // over on its side, whipping
    roll: Math.sin(t * 1.63 + 1.1) * 0.40,           // the sideways snap
    up: Math.max(0, s) * Math.max(0, s) * 0.30,      // and it gets air
    fwd: 0,
  };
}

/* The swing. He has no bat and no arms, so he throws the whole fish at the
   ball: coils up off the dirt, launches, and cartwheels away after contact. */
function fishSwing(st) {
  const u = clamp(st / SWING_LAG, 0, 1);
  const rear = Math.max(0, 1 - u * 2.3);          // the brief coil off the dirt
  const fire = Math.sin(u * Math.PI * 0.5);       // and then all of it at once
  const v = clamp((st - SWING_LAG) / 0.66, 0, 1), w = v * v;
  // Every channel comes back to where the flop rests, and the pitch winds a
  // whole extra turn, so the cartwheel lands in the resting orientation
  // instead of popping. G.batSwingT keeps counting for seconds after the
  // swing, so this has to settle on its own.
  return {
    pitch: 1.19 - rear * 0.44 + fire * 0.50 * (1 - w) + w * Math.PI * 2,
    roll: Math.sin(w * Math.PI) * 2.4 - rear * 0.18,
    up: 0.06 + fire * 0.66 * (1 - w),
    fwd: -rear * 0.32 + fire * 0.92 * (1 - w),
  };
}


/* ---------- 鮭 ---------- */
function drawSalmon(f, A, look, p, y, big) {
  const flank = col(A.fur), back = col(A.back), belly = col(A.fur2);
  const finC = col(A.fin), jaw = col(A.jaw);
  const uni = col(look.uni), trim = col(look.trim);
  const sw = p.swingT;
  const fl = p.fall ? { pitch: 1.50, roll: 0.55, up: 0, fwd: 0 }
    : (sw >= 0 && sw <= SWING_LAG + 0.66 ? fishSwing(sw) : fishFlop(f.ry * 3.1));
  // keep the pivot point on the spot; the rest of the fish swings around it
  const cp = Math.cos(fl.pitch), sp = Math.sin(fl.pitch);
  const by = y + 0.30 + fl.up - SAL_PIVOT * cp;
  const bz = fl.fwd - SAL_PIVOT * sp;
  const rx = fl.pitch + (p.lean || 0), rz = fl.roll;
  const put = (prim, c) => part(f, prim, 0, by, bz, 1, 1, 1, c, rx, rz);

  put('sal_body', flank);
  put('sal_back', back);
  put('sal_belly', belly);
  put('sal_fins', finC);
  put('sal_jaw', jaw);

  // the flush he gets on the run upriver, and the eyes — both solved against
  // the body profile in the baker, so they stay on the surface at any angle
  put('sal_blush', col(A.blush));
  put('sal_eye', col('#D6C489'));
  put('sal_pupil', col('#0E0B09'));

  // team colour, hugging the body: a sphere laid over a fish this narrow just
  // bulges out of it as a ball
  put('sal_band', uni);
  put('sal_collar', trim);
  put('sal_belt', trim);
}

/* ---------- カブトムシ ---------- */

/* The legs. Six of them, and the reason the first six looked like they came
   out of his middle is that they were hung on numbers that looked about right
   — all of them inside the shell. `BEE_LEG` comes out of the baker instead,
   solved against the same profile the wing cases are lofted from, so each one
   starts on the shell however the shell is retuned.

   Each leg is coxa, femur, shin, tarsus. The joint ball at the top is what
   lets the femur swing wide without the leg reading as stuck on, which is
   what stopped the last attempt at pushing them outward.

   The bones are solved against the drop the row actually has to cover, so the
   feet reach the ground from all three anchor heights rather than being three
   hand-tuned lengths that go wrong the moment an anchor moves. */
const BEE_SPLAY = 0.80;             // how far out from the body the femur goes
const BEE_SHIN = [0.10, -0.30];     // and how the shin comes back under him
const BEE_TARS = 0.55;

function beetleLeg(f, A, y, row, sg, sp2, s, legC, ln) {
  const [lx, ly, lz, , rake] = row;
  const jx = s * (lx + sp2), jy = y + ly;
  const fRx = rake + sg * 0.30, fRz = s * BEE_SPLAY;
  const sRx = BEE_SHIN[0] + sg * 0.85, sRz = s * BEE_SHIN[1];
  const tRx = BEE_TARS + sg * 0.40, tRz = s * -0.10;

  // share the drop out among the three bones, then let the shin take up the
  // slack; `ly` is exactly how far the foot has to fall to reach the ground
  const Lf = ly * 0.40, Lt = ly * 0.34;
  const drop = (rx, rz, L) => Math.cos(rx) * Math.cos(rz) * L;
  const Ls = Math.max(0.10, (ly - drop(fRx, fRz, Lf) - drop(tRx, tRz, Lt))
                            / (Math.cos(sRx) * Math.cos(sRz)));

  part(f, 'sphere', jx, jy, lz, 0.105, 0.098, 0.105, legC, ln);   // coxa
  const kn = limb(f, jx, jy, lz, fRx, fRz, Lf, 0.040, legC, null, 0);
  part(f, 'sphere', kn[0], kn[1], kn[2], 0.072, 0.072, 0.072, legC);   // knee
  let an;
  if (row === BEE_LEG[0]) {
    // the front pair digs, so it gets the toothed shin off the baker
    part(f, s < 0 ? 'bee_tibR' : 'bee_tibL', kn[0], kn[1], kn[2],
         1, Ls / 0.30, 1, legC, sRx, sRz);
    an = limbTip(kn[0], kn[1], kn[2], sRx, sRz, Ls);
  } else {
    an = limb(f, kn[0], kn[1], kn[2], sRx, sRz, Ls, 0.030, legC, null, 0);
  }
  part(f, 'sphere', an[0], an[1], an[2], 0.052, 0.052, 0.052, legC);   // ankle
  limb(f, an[0], an[1], an[2], tRx, tRz, Lt, 0.019, legC, legC, 0.046);
}

function drawBeetle(f, A, look, p, y, big) {
  const legC = col(A.leg), horn = col(A.horn);
  const uni = col(look.uni), trim = col(look.trim);
  const ln = p.lean || 0;

  const sw = p.legL || 0, sw2 = p.legR || 0, sp2 = p.spread || 0;
  for (const row of BEE_LEG) for (const s of [-1, 1])
    beetleLeg(f, A, y, row, (s < 0 ? sw : sw2) * row[3], sp2, s, legC, ln);

  // The shell, in three separated values. They were within a shade of each
  // other before, and three brown domes of the same brown read as one lump.
  part(f, 'bee_elytra', 0, y, 0, 1, 1, 1, shade(A.fur, 1.70), ln);
  part(f, 'bee_seam', 0, y, 0, 1, 1, 1, shade(A.fur, 0.60), ln);
  part(f, 'bee_scut', 0, y, 0, 1, 1, 1, shade(A.fur, 0.42), ln);
  part(f, 'bee_prono', 0, y, 0, 1, 1, 1, shade(A.fur, 1.18), ln);
  part(f, 'bee_head', 0, y, 0, 1, 1, 1, shade(A.fur, 1.02), ln);
  part(f, 'bee_horn', 0, y, 0, 1, 1, 1, horn, ln);

  // compound eyes, flat and black and entirely unreadable
  part(f, 'bee_eye', 0, y, 0, 1, 1, 1, col('#120A05'), ln);
  part(f, 'bee_glint', 0, y, 0, 1, 1, 1, col('#93795C'), ln);

  // Team colour: one saddle across the wing cases, and a collar on the shield
  // in the trim rather than the uniform. Three bands of yellow made a wasp of
  // him — the saddle is the jersey and everything else is edging.
  part(f, 'bee_band', 0, y, 0, 1, 1, 1, uni, ln);
  part(f, 'bee_trim', 0, y, 0, 1, 1, 1, trim, ln);
  part(f, 'bee_cband', 0, y, 0, 1, 1, 1, trim, ln);
}

/* pose: { armL, armR, legL, legR, lean, bob, ry } — all radians */
const IDLE = { armL: 0.12, armR: -0.12, legL: 0, legR: 0, lean: 0, bob: 0 };

/* run `draw` once as an ink shell and once as the fill, for species drawn in
   the line-art style */
function inked(look, draw) {
  const A = ANIMALS[look.animal];
  if (A && A.ink && R.inkW === 0) { R.ink(A.ink); draw(); R.ink(0); }
  draw();
}

function drawAnimal(x, z, ry, look, pose, y0) {
  const A = ANIMALS[look.animal];
  if (A.ink && R.inkW === 0) {                  // outline shell first
    R.ink(A.ink);
    drawAnimal(x, z, ry, look, pose, y0);
    R.ink(0);
  }
  const p = pose || IDLE;
  const FC = FACES[look.animal] || null;
  const f = yawFrame(x, z, ry);
  const y = (y0 || 0) + (p.bob || 0);
  if (p.fall) { f.t = p.fall; f.ct = Math.cos(p.fall); f.st = Math.sin(p.fall); f.pivot = y + 0.34; }
  const big = A.big ? 1.12 : 1;
  const fur = col(A.fur), fur2 = col(A.fur2);
  const uni = col(look.uni), trim = col(look.trim), cap = col(look.cap);
  const trim2 = shade(look.trim, 0.72);

  shadow(x, z, (p.fall ? 0.72 : 0.44) * big * (A.shadow || 1), 0.34);

  // legs (local -x is the character's right side, +x their left)
  const sp = p.spread || 0;
  const pant = shade(look.uni, 0.93), shoe = shade(look.cap, 0.66);
  if (A.legs === 'bunny') {
    // haunch, a thin shin, and a long hind foot — all three hang off the same
    // hip joint the plain legs use, so running and sliding are unchanged
    for (const s of [-1, 1]) {
      const jx = s * (0.155 * big + sp), lr = s < 0 ? (p.legL || 0) : (p.legR || 0);
      part(f, 'rabbit_thigh', jx, y + 0.44, 0, 1, 1, 1, pant, lr, s * 0.04);
      const e = limb(f, jx, y + 0.44, 0, lr, s * 0.04, 0.34, 0.088, pant, null, 0);
      part(f, 'rabbit_foot', e[0], e[1], e[2], 1, 1, 1, shoe, lr, s * 0.04);
    }
  } else if (!A.body) {             // the fish has none and the beetle has six
    limb(f, -(0.155 * big + sp), y + 0.44, 0, p.legL || 0, -0.04, 0.36, 0.12, pant, shoe, 0.30, 1);
    limb(f, 0.155 * big + sp, y + 0.44, 0, p.legR || 0, 0.04, 0.36, 0.12, pant, shoe, 0.30, 1);
  }

  // torso
  if (A.body === 'fish') drawSalmon(f, A, look, p, y, big);
  else if (A.body === 'beetle') drawBeetle(f, A, look, p, y, big);
  else if (A.mesh) {
    // the kit is baked as slices of the same profile as the body: laying a
    // sphere over a shaped torso makes it bulge out rather than cover
    const M = A.mesh + '_', ln = p.lean || 0;
    part(f, M + 'body', 0, y + 0.74, 0, 1, 1, 1, uni, ln);
    part(f, M + 'stripe', 0, y + 0.74, 0, 1, 1, 1, shade(look.uni, 0.80), ln);
    part(f, M + 'placket', 0, y + 0.74, 0, 1, 1, 1, trim, ln);
    part(f, M + 'collar', 0, y + 0.74, 0, 1, 1, 1, trim, ln);
    part(f, M + 'belt', 0, y + 0.74, 0, 1, 1, 1, shade(look.cap, 0.85), ln);
  } else {
  part(f, 'sphere', 0, y + 0.74, 0, 0.66 * big, 0.70, 0.56 * big, uni, p.lean || 0);
  part(f, 'sphere', 0, y + 0.97, 0.01, 0.50, 0.14, 0.45, trim);   // jersey collar
  part(f, 'box', 0, y + 0.72, 0.185, 0.075, 0.42, 0.05, trim);  // button placket
  if (A.buttons) for (let i = 0; i < 3; i++)                     // ...and its buttons
    part(f, 'sphere', 0, y + 0.86 - i * 0.145, 0.292 - i * 0.012, 0.058, 0.058, 0.050, trim2);
  // pinstripes down the front, and the belt at the waist
  const stripe = shade(look.uni, 0.80);
  for (const i of [-2, -1, 1, 2]) {
    const px = i * 0.098 * big;
    const k = Math.max(0, 1 - (px / (0.34 * big)) ** 2);
    part(f, 'box', px, y + 0.74, 0.28 * big * Math.sqrt(k) - 0.01, 0.026, 0.34, 0.035, stripe);
  }
  part(f, 'sphere', 0, y + 0.515, 0.02, 0.60 * big, 0.10, 0.50 * big, shade(look.cap, 0.85));
  }

  // arms — either swung by rotation, or aimed at a world-space grip
  const shY = y + 0.94;
  let hl, hr;
  if (A.body) { hl = [x, y + 0.9, z]; hr = [x, y + 0.9, z]; }
  else if (p.handL || p.handR) {
    // reaching arms hang off narrower shoulders and get a longer bone pair, so
    // the front arm can cross the chest to the knob without rubber-banding
    const SH = 0.17 * big, BONE = 0.32;
    const [slx, slz] = L2W(f, -SH, 0);
    const [srx, srz] = L2W(f, SH, 0);
    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    const hand = p.gloveC ? col(p.gloveC) : fur;
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.075, uni,
              p.noPawL ? null : hand)
      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.34, 0.112, uni, fur, 0.27);
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.075, uni,
              p.noPawR ? null : hand)
      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.34, 0.112, uni,
             p.noPawR ? null : fur, 0.27);
  } else {
    hl = limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.34, 0.112, uni,
              p.noPawL ? null : fur, 0.27);
    hr = limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.34, 0.112, uni,
              p.noPawR ? null : fur, 0.27);
  }

  // head — may be turned independently of the body (a batter watching the ball)
  const fh = p.headRy ? yawFrame(x, z, ry + p.headRy) : f;
  const hy = y + 1.34;
  const HW = A.hw || 1, HH = A.hh || 1, HD = A.hd || 1;
  const hzF = 0.32 * HD + 0.02;                 // where the front of the face is
  if (A.mesh) part(fh, A.mesh + '_head', 0, hy, 0, 1, 1, 1, fur);   // ears included
  else if (!A.body)
    part(fh, A.head || 'sphere', 0, hy, 0.02, 0.68 * big * HW, 0.66 * HH, 0.64 * big * HD, fur);

  if (A.patch) {                                // panda mask
    for (const s of [-1, 1])
      part(fh, 'sphere', s * 0.17, hy + 0.08, hzF - 0.07, 0.27, 0.29, 0.16, fur2);
  }
  if (A.facePatch) {                            // the penguin's white face
    const fp = A.facePatch;
    part(fh, 'sphere', 0, hy - 0.02, hzF - 0.10, fp[0], fp[1], fp[2], fur2);
  }
  if (A.cheek) {                                // fluffy cheeks
    for (const s of [-1, 1])
      part(fh, 'sphere', s * 0.29, hy - 0.09, 0.09, A.cheek, A.cheek * 0.94, A.cheek * 0.88,
           A.cheekC ? col(A.cheekC) : fur2);
  }

  if (FC && R.atlas && R.inkW === 0) {            // eyes and brows, as art
    R.decal(faceRect(look.animal, p.face || 0, 0));
    const k = 1.015;
    if (A.mesh) {
      // the patch was baked out of the same (azimuth, elevation) map as the
      // skull, so it lies on the surface rather than being fitted to it
      part(fh, A.mesh + '_face', 0, hy, 0, 1, 1, 1, fur);
    } else if (FC.onPatch && A.facePatch) {
      const fp = A.facePatch;                      // the patch stands proud of
      part(fh, 'facep', 0, hy - 0.02, hzF - 0.10,  // the skull, so sit on that
           fp[0] * k, fp[1] * k, fp[2] * k, fur);
    } else {
      part(fh, A.head === 'rbox' ? 'facepr' : 'facep', 0, hy, 0.02,
           0.68 * big * HW * k, 0.66 * HH * k, 0.64 * big * HD * k, fur);
    }
    R.decal(null);
  }

  if (A.mesh) {
    part(fh, A.mesh + '_muz', 0, hy, 0, 1, 1, 1, fur2);     // the pale mask
    part(fh, A.mesh + '_earin', 0, hy, 0, 1, 1, 1, fur2);
    if (FC && !FC.onHead && R.atlas && R.inkW === 0) {
      R.decal(faceRect(look.animal, p.face || 0, 1));
      part(fh, A.mesh + '_snout', 0, hy, 0, 1, 1, 1, fur);
      R.decal(null);
    }
  } else if (A.beak) {
    part(fh, 'cone', 0, hy - 0.045, hzF - 0.03, 0.27, 0.32, 0.27, col(A.beak), -Math.PI / 2);
    part(fh, 'box', 0, hy - 0.045, hzF + 0.07, 0.19, 0.022, 0.16, shade(A.beak, 0.62));
  } else if (A.muz) {
    const mz = A.muz, my = hy + (A.muzY === undefined ? -0.09 : A.muzY);
    const mzz = A.muzZ === undefined ? 0.26 : A.muzZ;
    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], A.muzC ? col(A.muzC) : fur2);
    if (FC && !FC.onHead && R.atlas && R.inkW === 0) {   // nose and mouth, as art
      R.decal(faceRect(look.animal, p.face || 0, 1));
      part(fh, 'facep', 0, my, mzz, mz[0] * 1.03, mz[1] * 1.03, mz[2] * 1.03, fur);
      R.decal(null);
    }
    const nr = A.noseR || 0.11;
    if (!FC && A.nostril) {
      for (const s of [-1, 1])
        part(fh, 'sphere', s * mz[0] * 0.24, my + mz[1] * 0.28, mzz + mz[2] * 0.40,
             nr, nr * 0.90, nr * 0.60, col('#3A3040'));
    } else if (!FC) {
      part(fh, 'sphere', 0, my + mz[1] * 0.40, mzz + mz[2] * 0.40,
           nr, nr * 0.74, nr * 0.72, col(A.noseC || '#33291F'));
    }
    if (!FC && A.whisk) for (const s of [-1, 1]) for (let i = 0; i < 3; i++)
      part(fh, 'box', s * (mz[0] * 0.60 + 0.13), my + 0.02 + (i - 1) * 0.05, mzz + 0.03,
           0.28, 0.017, 0.017, col('#6B5A48'), 0, s * ((i - 1) * 0.24 + 0.05));
  }
  if (A.mouth && !FC) {                         // the frog's wide grin
    for (const s of [-1, 1])
      part(fh, 'box', s * 0.17, hy - 0.16, hzF - 0.02, 0.36, 0.036, 0.07,
           shade(A.fur, 0.42), 0, s * -0.11);
  }

  // eyes, with the drawn brow line above them
  if (A.smallMouth && !FC && R.inkW === 0) {    // a little mouth under the nose
    const mz = A.muz || [0.2, 0.13, 0.16];
    const my2 = hy + (A.muzY === undefined ? -0.09 : A.muzY) + mz[1] * 0.40 - 0.078;
    for (const s of [-1, 1])
      part(fh, 'box', s * 0.038, my2, hzF - 0.062, 0.074, 0.024, 0.05,
           col('#4A3438'), 0, s * 0.30);
  }
  // a species with its own body draws its own eyes, in the mesh
  if (FC || A.body) { /* the eyes live in the face cell, or in the mesh */ }
  else if (!A.noFaceEyes && A.dotEyes) {         // simple dots, as drawn
    const ex = A.eyeX || 0.150, ew = A.eyeW || 0.078, eh = A.eyeH || 0.086;
    if (R.inkW === 0) for (const s of [-1, 1]) {
      part(fh, 'sphere', s * ex, hy + 0.085, hzF - 0.028, ew, eh, 0.070, col(EYE));
      part(fh, 'sphere', s * ex + 0.016, hy + 0.102, hzF - 0.006, 0.021, 0.021, 0.018, col(SHINE));
    }
  } else if (!A.noFaceEyes) {
    const ex = A.eyeX || 0.150, ew = A.eyeW || 0.140, eh = A.eyeH || 0.115;
    const et = A.eyeTilt || 0;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * ex, hy + 0.098, hzF - 0.025, ew, eh, 0.085, col('#F6F1E6'), 0, s * et);
      part(fh, 'sphere', s * ex - s * 0.008, hy + 0.094, hzF + 0.012,
           ew * 0.60, eh * 0.74, 0.058, col(EYE), 0, s * et);
      part(fh, 'sphere', s * ex + 0.024, hy + 0.118, hzF + 0.028, 0.034, 0.034, 0.028, col(SHINE));
      if (A.brow)
        part(fh, 'box', s * ex, hy + 0.205, hzF - 0.030, 0.215, 0.040, 0.085,
             shade(A.fur, 0.34), 0, s * 0.16);
    }
  }

  // ears
  const earC = A.earC ? col(A.earC) : fur;
  if (A.ear === 'round') {
    const er = A.earR || 0.26, exx = A.earX || 0.26, eyy = A.earY || 0.26, ed = A.earD || 0.77;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, -0.02, er, er, er * ed, earC);
      part(fh, 'sphere', s * exx, hy + eyy + 0.01, 0.04, er * 0.55, er * 0.55, er * 0.50, fur2);
    }
  }
  if (A.ear === 'point') {
    const er = A.earR || 0.26, exx = A.earX || 0.21, eyy = A.earY || 0.34, tl = A.earT || 0.22;
    for (const s of [-1, 1]) {
      part(fh, 'cone', s * exx, hy + eyy, -0.02, er, er * 1.30, er * 0.76, earC, 0, s * tl);
      part(fh, 'cone', s * exx, hy + eyy - 0.01, 0.035, er * 0.52, er * 0.86, er * 0.42, fur2, 0, s * tl);
      if (A.earTip)
        part(fh, 'cone', s * (exx + er * 0.32), hy + eyy + er * 0.46, -0.02,
             er * 0.60, er * 0.50, er * 0.46, col(A.earTip), 0, s * tl);
    }
  }
  if (A.ear === 'bunny') {
    // Baked: they taper, the hollow faces forward, and the pink sits in it.
    // `earY` is where the root goes — the length is the mesh's business. They
    // stay separate parts rather than going into the head: a rabbit's ears
    // have to be able to move.
    const exx = A.earX || 0.148, eyy = A.earY || 0.18;
    const tl = A.earTilt === undefined ? 0.13 : A.earTilt;
    // and they lean back when the legs are going. Driven by the pose, not by
    // `clock` — that lives in 50-main.js, which the face lab does not load.
    const back = Math.min(0.30, (Math.abs(p.legL || 0) + Math.abs(p.legR || 0)) * 0.16);
    const inC = A.earIn ? col(A.earIn) : fur2;
    for (const s of [-1, 1]) {
      part(fh, 'rabbit_ear', s * exx, hy + eyy, -0.02, 1, 1, 1, fur, -back, -s * tl);
      part(fh, 'rabbit_earin', s * exx, hy + eyy, -0.02, 1, 1, 1, inC, -back, -s * tl);
    }
  }
  if (A.ear === 'toad') {
    const er = A.earR || 0.28, exx = A.earX || 0.19, eyy = A.earY || 0.26;
    const ez = A.earZ === undefined ? 0.05 : A.earZ;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, ez, er, er, er * 0.92, fur);
      part(fh, 'sphere', s * exx, hy + eyy + 0.02, ez + 0.11, er * 0.66, er * 0.66, er * 0.46, col('#F6F1E6'));
      part(fh, 'sphere', s * exx - s * 0.014, hy + eyy + 0.02, ez + 0.15,
           er * 0.34, er * 0.42, er * 0.28, col(EYE));
      part(fh, 'sphere', s * exx + 0.05, hy + eyy + 0.09, ez + 0.17, 0.036, 0.036, 0.030, col(SHINE));
    }
  }
  // tail
  if (A.tail === 'puff') part(f, 'sphere', 0, y + 0.66, -0.30, 0.24, 0.24, 0.24, fur2);
  if (A.tail === 'cotton') part(f, 'rabbit_tail', 0, y + 0.66, -0.30, 1, 1, 1, fur2);
  // the baked torso has a shallower back than the sphere one, so the nub has
  // to be seated further in or it floats off the jersey
  if (A.tail === 'nub') part(f, 'sphere', 0, y + 0.60, A.tailZ || -0.30, 0.16, 0.16, 0.16, fur);
  if (A.tail === 'long') part(f, 'sphere', 0, y + 0.78, -0.36, 0.14, 0.44, 0.14, fur, 0.5);
  if (A.tail === 'bushy') {
    part(f, 'sphere', 0, y + 0.72, -0.38, 0.26, 0.46, 0.26, fur, 0.6);
    part(f, 'sphere', 0, y + 0.94, -0.50, 0.20, 0.20, 0.20, fur2);
  }
  // headwear: a batting helmet at the plate and on the bases, otherwise a cap
  if (p.noHat || A.noHat) { /* a shopper, or a fish — nothing to hang a cap on */ }
  else if (p.helmet) {
    const cy = A.capY || 0, cs = A.capS || 1;
    part(fh, 'dome', 0, hy + 0.27 * cs + cy, 0.01, 0.80 * big * cs, 0.44 * cs, 0.78 * big * cs, cap);
    part(fh, 'sphere', 0, hy + 0.285 * cs + cy, 0.01, 0.80 * big * cs, 0.22 * cs, 0.78 * big * cs, cap);
    part(fh, 'box', 0, hy + 0.265 * cs + cy, 0.34 * cs, 0.50 * cs, 0.075 * cs, 0.26 * cs, cap);
    // the flap covers the ear turned toward the pitcher (local +x)
    part(fh, 'sphere', 0.335 * big * cs, hy + 0.12 * cs + cy, 0.02,
         0.14 * cs, 0.32 * cs, 0.40 * cs, cap);
    part(fh, 'box', 0, hy + 0.40 * cs + cy, 0.10 * cs, 0.09 * cs, 0.06 * cs, 0.60 * cs, trim);
  } else {
    const cy = A.capY || 0, cs = A.capS || 1;
    part(fh, 'dome', 0, hy + 0.29 * cs + cy, 0.01 * cs, 0.74 * big * cs, 0.38 * cs, 0.70 * big * cs, cap);
    part(fh, 'box', 0, hy + 0.283 * cs + cy, 0.31 * cs, 0.46 * cs, 0.07 * cs, 0.30 * cs, cap);
    part(fh, 'sphere', 0, hy + 0.46 * cs + cy, 0.01, 0.09 * cs, 0.09 * cs, 0.09 * cs, trim);
  }

  return { f, hl, hr, hy, y };
}

/* A bat to real proportions: 2.5cm handle, a taper, a 6.5cm barrel, knob at the
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
}

/* A fielder's mitt: palm, four finger ridges, a thumb and the web between
   them. All one leather; the shape does the work, not a painted pocket. */
function drawGlove(pt, ry) {
  if (!pt) return;
  const a = ry || 0, fx = Math.sin(a), fz = Math.cos(a);
  const sx = fz, sz = -fx;                       // across the mitt
  const x = pt[0] + fx * 0.05, y = pt[1], z = pt[2] + fz * 0.05;
  const hide = col('#7A4A22'), dark = col('#46280F'), web = col('#9A6B38');
  R.d('rbox', x, y - 0.02, z, 0, a, 0, 0.38, 0.36, 0.20, hide);          // palm
  for (let i = -1; i <= 2; i++)                                          // fingers
    R.d('rbox', x + sx * i * 0.083, y + 0.20, z + sz * i * 0.083, 0, a, 0,
        0.072, 0.22, 0.18, hide);
  R.d('rbox', x - sx * 0.235, y - 0.03, z - sz * 0.235, 0, a, 0, 0.11, 0.30, 0.19, hide);
  R.d('rbox', x - sx * 0.145, y + 0.18, z - sz * 0.145, 0, a, 0, 0.11, 0.20, 0.16, web);
  R.d('rbox', x + fx * 0.075, y - 0.05, z + fz * 0.075, 0, a, 0, 0.20, 0.18, 0.05, dark);
  R.d('rbox', x, y - 0.22, z, 0, a, 0, 0.32, 0.10, 0.18, dark);          // heel
}

/* ---------- the ball ---------- */
const BALL_R = 0.14;
/* a real ball is a speck at 80m — grow it with distance so the player can
   always follow the flight */
function ballScale(x, y, z) {
  const d = Math.hypot(x - R.eye[0], y - R.eye[1], z - R.eye[2]);
  // Nearly true perspective: the compensation is small enough that the ball
  // visibly shrinks as it flies away, which is the whole depth cue.
  return BALL_R * 2 * clamp(Math.pow(d / 12, 0.15), 1, 1.5) * (G.ballBoost || 1);
}
function drawBall(x, y, z, spin) {
  const s = ballScale(x, y, z);
  R.b('sphere', x, y, z, s, s, s, col('#FBF7EC'));
  R.d('cyl', x, y, z, Math.PI / 2, spin || 0, 0, s * 0.78, s * 0.25, s * 0.78, col('#D9402E'));
}
function drawTrail(tr) {
  for (let i = 0; i < tr.length; i += 3) {
    const k = 1 - i / tr.length;
    const s = ballScale(tr[i], tr[i + 1], tr[i + 2]) * 0.72 * k * k;
    if (s < 0.012) continue;
    R.b('sphere', tr[i], tr[i + 1], tr[i + 2], s, s, s, col('#FFE9B0'));
  }
}

/* ============================================================
   Teams
   ============================================================ */
const NAME_POOL = {
  bear:    ['ゴロー', 'ブンタ', 'クマキチ', 'ドスコイ', 'ハチベエ', 'テツ', 'モリオ', 'ガンタ', 'ノボル'],
  rabbit:  ['ミミ', 'ピョン', 'ラビ', 'シロタ', 'ハネダ', 'ツキノ', 'コハネ', 'トビオ', 'ユキ'],
  cat:     ['タマ', 'ミケ', 'ニャン太', 'トラキチ', 'クロベエ', 'シッポ', 'モモ', 'ヒゲオ', 'コタツ'],
  frog:    ['ケロ', 'ゲコタ', 'アマガエル', 'ピョンジ', 'ヌマオ', 'ハスオ', 'グエコ', 'ミズキ', 'カジカ'],
  penguin: ['ペンタ', 'コオリ', 'フブキ', 'ヨチヨチ', 'シラス', 'アデリー', 'ヒレタ', 'ナンキョク', 'ツララ'],
  salmon:  ['サケオ', 'シャケ', 'ベニ', 'ソジロウ', 'アキアジ', 'トキシラズ', 'ハラス', 'イクラ', 'メジカ'],
  beetle:  ['カブト', 'ツノオ', 'クヌギ', 'ゲンジ', 'ムシタロウ', 'コクワ', 'ジュエキ', 'ヨナガ', 'カブオ'],
  fox:     ['コン', 'キツネビ', 'アカネ', 'シッポリ', 'イナリ', 'ゴンタ', 'ヒノ', 'ミミナガ', 'ユウ'],
  panda:   ['パンダ丸', 'シャンシャン', 'ササオ', 'モウソウ', 'クロシロ', 'マルオ', 'ゴロゴロ', 'タケゾウ', 'リンリン'],
  hippo:   ['カバオ', 'ドロン', 'ヌマヅ', 'オオクチ', 'ブクブク', 'ミズベ', 'ズッシリ', 'アグリ', 'ハナ'],
};

const TEAMS = [
  { id: 'bears',    name: 'もりのクマーズ',   animal: 'bear',    uni: '#7B4B2A', trim: '#F0D9A8', cap: '#5E3620',
    tag: 'POWER',   desc: 'とにかく長打。当たれば飛ぶが、確実性は低め。', pow: 5, con: 2, spd: 2, def: 3 },
  { id: 'rabbits',  name: 'はらっぱラビッツ', animal: 'rabbit',  uni: '#E8EDF2', trim: '#E86A8A', cap: '#D9527A',
    tag: 'SPEED',   desc: '足が速い。内野安打も盗塁もお手のもの。', pow: 2, con: 4, spd: 5, def: 4 },
  { id: 'salmons',  name: 'そじょうサーモンズ', animal: 'salmon', uni: '#2F5C7A', trim: '#F0B9A8', cap: '#22455C',
    tag: 'CONTACT', desc: 'バットに当てるのがうまい。四球も選ぶ。', pow: 3, con: 5, spd: 3, def: 3 },
  { id: 'frogs',    name: 'ぬまたフロッグス', animal: 'frog',    uni: '#4E8A4E', trim: '#E8F0C8', cap: '#2E5E34',
    tag: 'BALANCE', desc: 'すべてが平均的。クセがなく扱いやすい。', pow: 3, con: 3, spd: 3, def: 3 },
  { id: 'penguins', name: 'こおりやまペンギンズ', animal: 'penguin', uni: '#28405E', trim: '#F4F1E6', cap: '#1B2C42',
    tag: 'DEFENSE', desc: '守備が堅い。相手の打球をよく捕る。', pow: 3, con: 3, spd: 2, def: 5 },
  { id: 'beetles',  name: 'くぬぎカブトズ', animal: 'beetle', uni: '#D6A63E', trim: '#F6E7BC', cap: '#241408',
    tag: 'PITCHING',desc: '投手陣が強力。変化球のキレがちがう。', pow: 3, con: 3, spd: 3, def: 4, arm: 5 },
];

const teamById = (id) => TEAMS.find((t) => t.id === id);

/* Build a 9-man roster with a batting order and fielding positions. */
function makeTeam(def) {
  const names = NAME_POOL[def.animal].slice();
  const order = ['CF', 'SS', 'RF', '1B', 'LF', '3B', 'C', '2B', 'P'];
  const roster = order.map((posK, i) => {
    const v = (s, spread) => clamp(s / 5 + rnd(-spread, spread), 0.12, 1.0);
    return {
      name: names[i], no: i + 1, pos: posK,
      look: { animal: def.animal, uni: def.uni, trim: def.trim, cap: def.cap },
      power: v(def.pow, 0.14), contact: v(def.con, 0.14), speed: v(def.spd, 0.12), defense: v(def.def, 0.12),
      arm: (def.arm || 3) / 5,
      ab: 0, h: 0, hr: 0, rbi: 0, k: 0, bb: 0, hbp: 0,
    };
  });
  // the pitcher bats ninth but is the best arm
  roster[8].arm = clamp((def.arm || 3) / 5 + 0.18, 0, 1);
  roster[8].power = clamp(roster[8].power - 0.22, 0.1, 1);
  roster[8].contact = clamp(roster[8].contact - 0.18, 0.1, 1);
  return { def, name: def.name, roster, animal: def.animal, uni: def.uni, trim: def.trim, cap: def.cap };
}
