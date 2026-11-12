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
function armIK(sx, sy, sz, hx, hy, hz, L1, L2, pole, rad, c, handC, slv) {
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
  // `slv` = {sleeve, cuff, c, trim}: the species' baked sleeve, hung from the
  // shoulder along the upper arm (it is authored pointing down -Y)
  if (slv) {
    const qx = sx - ex, qy = sy - ey, qz = sz - ez, ql = Math.hypot(qx, qy, qz) || 1;
    const rx = Math.acos(clamp(qy / ql, -1, 1)), ry = Math.atan2(qx, qz);
    R.d(slv.sleeve, sx, sy, sz, rx, ry, 0, 1, 1, 1, slv.c);
    R.d(slv.cuff, sx, sy, sz, rx, ry, 0, 1, 1, 1, slv.trim);
  }
  if (handC !== null) R.b('sphere', hx, hy, hz, rad * 2.2, rad * 2.1, rad * 2.2, handC || c);
  return [hx, hy, hz];
}

/* ---------- animal species ---------- */
/* hw/hh/hd scale the head; muz is the size of the muzzle; earR/earX/earY
   place the ears. The face itself is art, in FACES below. */
const ANIMALS = {
  // Stage 3. `mesh` swaps the head, the muzzle, the ears and the torso for
  // shells baked by tools/mesh2js.py, so the skull and the snout are one
  // surface and the jersey has shoulders. Everything else — arms, legs, cap,
  // the four expressions — still comes from the shared rig. The head numbers
  // the other mammals carry (hw/muz/earR) are the mesh's business now.
  //
  // Drawn from the owner's pencil sketch (2026-09-23): no cap, so the big head
  // and the little ears are the silhouette. The ears have no pale disc in
  // them, the arms end in a dark tip rather than a mitten-sized ball, and the
  // legs are stubs in the trouser colour with only the soles dark — the
  // sketch draws no boots.
  bear:    { ink: 0.022, mesh: 'bear', tail: 'nub', tailZ: -0.300, noHat: 1,
             legW: 0.132, footS: 0.300, sole: 1, handS: 0.235, noCollar: 1,
             fur: '#96683F', fur2: '#E6D2AE', paw: '#4A3020', earIn: '#7C5431' },

  // Drawn from the reference sketch: tall straight ears, round head, dot eyes.
  // Ears, haunches, hind feet and tail are baked (段階3); the head is still a
  // sphere because that is the surface the drawn face is projected onto.
  // The torso is baked too (`torso: 'rabbit'`): a little pear the haunches
  // flow out of, the pink trim baked onto it. The arms are fur in a short
  // puffed sleeve (`sleeve`), and the cap is a toy cap perched on the crown.
  rabbit:  { ink: 0.022, ear: 'bunny', fur: '#F4F0E8', fur2: '#F6D7DA', tail: 'cotton',
             head: 'sphere', hw: 1.08, hh: 1.06, hd: 0.98,
             legs: 'bunny', earX: 0.128, earY: 0.18, earTilt: 0.09,
             earIn: '#F6D7DA', torso: 'rabbit', tailY: 0.48, tailZ: -0.275,
             headS: 1.22, headUp: -0.013,     // 1.22x about a chin lowered to y+0.90
             sleeve: 'rabbit', armX: 0.235, armY: 0.80, armRz: 0.42, armLen: 0.25,
             armW: 0.074, handS: 0.21,
             capS: 0.70, capY: 0.087, capZ: 0.01, capT: -0.12, billW: 0.78,
             helm: { s: 0.80, y: 0.0, z: -0.03, bill: 1.0 } },

  cat:     { ink: 0.022, ear: 'point', fur: '#E0A44F', fur2: '#F7EDDD', tail: 'long',
             head: 'rbox', hw: 1.10, hh: 0.98, hd: 0.94,
             muz: [0.46, 0.255, 0.26], muzY: -0.125, muzZ: 0.245,
             earR: 0.255, earX: 0.235, earY: 0.36, earT: 0.26 },

  // A wide low pebble of a head with the eyes on two domes on top — baked
  // like the bear's, one surface. The torso is the frog's own squat egg in a
  // plain jersey, the arms green in the rabbit's puffed sleeve, the hands
  // round pads. A small cap perches between the domes; the feet are flat
  // webbed pads, turned out, and almost all the leg is under the jersey.
  // `lidHappy`: the happy face shuts the eyes, so the baked whites go.
  frog:    { ink: 0.022, mesh: 'frog', noStripe: 1, tail: 'none', lidHappy: 1,
             legs: 'frog', legW: 0.112, hipX: 0.175, headUp: -0.105,
             sleeve: 'rabbit', armX: 0.255, armY: 0.80, armRz: 0.44, armLen: 0.24,
             armW: 0.074, handS: 0.20,
             capS: 0.54, capSY: 0.74, capY: 0.150,
             fur: '#86C25A', fur2: '#F8F4B2', paw: '#86C25A', earIn: '#FCFAF0', foot: '#6FAE4C' },

  // One soft egg with a round head, flippers and orange feet: everything is
  // baked (penguin_*), and drawPenguin draws all of it. The white face is art
  // in the face cell, not a ball stuck on the front.
  penguin: { ink: 0.022, form: 'penguin', ear: 'none', tail: 'none',
             fur: '#34475E', fur2: '#F7F5EE', beak: '#F29A35', foot: '#EE9338',
             capS: 0.70, capY: 0.160, capT: -0.16 },

  fox:     { ink: 0.022, ear: 'point', fur: '#D96F3A', fur2: '#F6EFE2', tail: 'bushy',
             head: 'rbox', hw: 1.04, hh: 0.96, hd: 1.08,
             muz: [0.33, 0.235, 0.46], muzY: -0.115, muzZ: 0.30,
             cheek: 0.21, cheekC: '#F6EFE2',
             earR: 0.275, earX: 0.255, earY: 0.38, earT: 0.22, earTip: '#3C2A20' },

  // Drawn as the real animal rather than a round cartoon of one, and given no
  // face cell, so they never change expression. Their eyes are in the mesh.
  // a male chum on the spawning run: dark olive back, grey-green flanks under
  // ragged maroon and dusky-green bars, a dirty cream belly, dusky fins
  salmon:  { ink: 0.013, body: 'fish', ear: 'none', tail: 'none', noHat: 1, shadow: 1.5,
             noGlove: 1, noBat: 1,
             fur: '#8B9B89', fur2: '#C2BBA3', back: '#1E2819', bar: '#4E3036', bar2: '#283020',
             line: '#3A4034', oper: '#68705A', jaw: '#484A3F',
             fin: '#474C3C', finEdge: '#23251E', finTip: '#CFCBB6' },

  beetle:  { ink: 0.013, body: 'beetle', ear: 'none', tail: 'none', noHat: 1,
             noGlove: 1, noBat: 1,
             // elytra / pronotum / head / horn / legs / underside
             fur: '#55260F', fur2: '#2A170E', headC: '#21130B', horn: '#1B100A',
             leg: '#1F130B', venter: '#3E2414', brush: '#8A6838',
             // no cap, no helmet: a beetle wears nothing but a breeder's
             // dab of paint (bee_mark)
           },

  panda:   { ink: 0.022, ear: 'round', fur: '#F0EDE6', fur2: '#2C3138', tail: 'nub', patch: 1,
             head: 'rbox', hw: 1.12, hh: 1.04, hd: 0.98,
             muz: [0.44, 0.28, 0.28], muzY: -0.13, muzZ: 0.24,
             earR: 0.25, earX: 0.32, earY: 0.315, earD: 0.60, earC: '#2C3138' },

  hippo:   { ink: 0.022, ear: 'round', fur: '#9E86C4', fur2: '#D8C9EC', tail: 'nub', big: 1,
             head: 'rbox', hw: 1.18, hh: 0.92, hd: 1.02,
             muz: [0.62, 0.36, 0.38], muzY: -0.115, muzZ: 0.24,
             earR: 0.165, earX: 0.34, earY: 0.30, earD: 0.60 },
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
  // Its own painters, read off the owner's sketch; the layout comes from the
  // baker (BEAR_FACE), which solved it off the skull
  bear:    Object.assign({ paintHead: bearHeadCell, paintSnout: bearSnoutCell,
                           ink: '#2B1D14', noseC: '#2B1D14', fur: ANIMALS.bear.fur }, BEAR_FACE),
  // the rabbit has no muzzle at all, so its nose and mouth go on the head
  rabbit:  { eye: 'dot',    eyeX: 0.200, eyeY: 0.355, eyeR: 0.062, onHead: 1,
             nose: 'dot',   noseC: '#4A3438', noseY: 0.655, noseR: 0.050, mouth: 'w',
             mouthC: '#4A3438', mouthY: 0.745, mouthW: 0.085 },
  cat:     { eye: 'almond', eyeX: 0.205, eyeY: 0.355, eyeR: 0.092, tilt: 0.16, whisk: '#B0895A',
             nose: 'tri',   noseC: '#C2705E', noseY: 0.295, noseR: 0.140, mouth: 'w' },
  // its own painters; where everything goes comes from the baker (FROG_FACE)
  frog:    Object.assign({ paintHead: frogHeadCell, paintSnout: frogSnoutCell,
                           ink: '#22401F', lip: '#2E3A1E', fur: ANIMALS.frog.fur }, FROG_FACE),
  penguin: { paintHead: penguinHeadCell },
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
  if (F.paintHead) return F.paintHead(g, F, exp);
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

/* ---------- the bear, from the owner's sketch ----------
   Read off the paper rather than off the idea of a teddy bear:

   * The eyes are wide white almonds with a small pupil stuck to the top edge,
     white showing underneath (三白眼). That, not a drooping lid, is the look
     he gives you: unimpressed, a bit shifty, still round and harmless.
   * The brows are short dashes a long way above the eyes.
   * The muzzle is drawn as an outline. The nose sits on its top edge, half
     in and half out, and the mouth is a thick mark along its bottom edge.
     There is no line from the nose down to the mouth.

   The fur shows through everywhere the paint is not, and the paint is lit
   like the skull it lies on, so a lid painted in the fur colour is fur. */
function bearHeadCell(g, F, exp) {
  for (const s of [-1, 1]) bearEye(g, F, exp, 0.5 + s * F.eyeX, F.eyeY, s);
  for (const s of [-1, 1]) bearBrow(g, F, exp, 0.5 + s * F.eyeX, F.browY, s);
}

/* s is -1 for the eye on the reader's left; the nose is toward -s */
function bearEye(g, F, exp, x, y, s) {
  const r = F.eyeR, ink = F.ink;
  if (exp === EXPR.happy) {                       // shut, pleased with himself
    fStroke(g, ink, r * 0.30);
    g.beginPath();
    g.moveTo(x - r * 0.95, y - r * 0.05);
    g.quadraticCurveTo(x, y + r * 0.50, x + r * 0.95, y - r * 0.05);
    g.stroke();
    return;
  }
  const focus = exp === EXPR.focus, down = exp === EXPR.down;
  const h = r * (focus ? 0.40 : 0.48), pr = r * 0.27;
  g.save();
  g.translate(x, y);
  g.rotate(focus ? -s * 0.16 : down ? s * 0.14 : 0);  // + drops the outer end
  g.save();
  g.beginPath(); g.ellipse(0, 0, r, h, 0, 0, Math.PI * 2); g.clip();
  g.fillStyle = '#FBF8F1'; g.fillRect(-r, -h, 2 * r, 2 * h);
  // idle, the pupils ride up and in; set, they both slide the same way —
  // a sidelong look; down, they drop and the lid comes after them
  const px = focus ? r * 0.34 : down ? -s * r * 0.05 : -s * r * 0.14;
  const py = down ? h - pr * 0.9 : -h + pr * 0.92;
  g.fillStyle = EYE; g.beginPath(); g.arc(px, py, pr, 0, Math.PI * 2); g.fill();
  if (down) {
    g.fillStyle = F.fur;
    g.fillRect(-r, -h, 2 * r, h * 0.85);
  }
  g.restore();
  fStroke(g, ink, r * 0.13);
  g.beginPath(); g.ellipse(0, 0, r, h, 0, 0, Math.PI * 2); g.stroke();
  fStroke(g, ink, r * 0.24);                      // the top edge is the heavy one
  g.beginPath();
  if (down) { g.moveTo(-r, -h * 0.15); g.lineTo(r, -h * 0.15); }
  else g.ellipse(0, 0, r, h, 0, Math.PI * 1.06, Math.PI * 1.94);
  g.stroke();
  g.restore();
}

function bearBrow(g, F, exp, x, y, s) {
  const r = F.eyeR, w = r * 0.62, cx = x - s * r * 0.08;
  let inner = 0, outer = 0, lift = 0;
  if (exp === EXPR.idle) { if (s > 0) lift = r * 0.10; }
  else if (exp === EXPR.focus) { inner = r * 0.30; outer = -r * 0.12; lift = -r * 0.10; }
  else if (exp === EXPR.happy) { lift = r * 0.20; }
  else { inner = -r * 0.26; outer = r * 0.10; }
  fStroke(g, F.ink, r * 0.21);
  g.beginPath();
  g.moveTo(cx - s * w, y - lift + inner);
  g.lineTo(cx + s * w, y - lift + outer);
  g.stroke();
}

function bearSnoutCell(g, F, exp) {
  const [cx, cy, rx, ry] = F.muz, ink = F.ink;
  const at = (a) => [cx + Math.cos(a) * rx, cy + Math.sin(a) * ry];
  fStroke(g, ink, 0.020);                         // the oval, as drawn
  g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); g.stroke();

  const B = Math.PI / 2;                          // the bottom of the oval
  if (exp === EXPR.happy) {                       // open, hanging off the edge
    const a0 = B - 0.80, a1 = B + 0.64, p0 = at(a0);
    g.fillStyle = ink;
    g.beginPath();
    g.moveTo(p0[0], p0[1]);
    g.ellipse(cx, cy, rx, ry, 0, a0, a1);
    g.quadraticCurveTo(cx - rx * 0.05, cy + ry * 0.02, p0[0], p0[1]);
    g.fill();
    g.fillStyle = '#B9564F';
    g.beginPath(); g.ellipse(cx + rx * 0.05, cy + ry * 0.66, rx * 0.26, ry * 0.11, 0, 0, Math.PI * 2);
    g.fill();
  } else if (exp === EXPR.down) {                 // clamped shut, corners down
    fStroke(g, ink, 0.050);
    g.beginPath();
    g.moveTo(cx - rx * 0.34, cy + ry * 0.74);
    g.quadraticCurveTo(cx, cy + ry * 0.50, cx + rx * 0.34, cy + ry * 0.74);
    g.stroke();
  } else {
    // A thick mark along the bottom edge, heavier and a touch longer on one
    // side. Set in the box, it only gets shorter. It rides a little inside
    // the edge: the bottom of the muzzle turns under, and a mark right on the
    // rim foreshortens to a hairline from any camera above the chin.
    const L = exp === EXPR.focus ? 0.30 : 0.42, my = ry * 0.68;
    fStroke(g, ink, 0.100);
    g.beginPath(); g.ellipse(cx, cy, rx * 0.86, my, 0, B - L, B + L * 0.72); g.stroke();
    if (exp === EXPR.idle) {                      // and the kink in it
      const k = [cx + Math.cos(B - L) * rx * 0.86, cy + Math.sin(B - L) * my];
      fStroke(g, ink, 0.050);
      g.beginPath(); g.moveTo(k[0], k[1]); g.lineTo(k[0] + rx * 0.05, k[1] - ry * 0.16); g.stroke();
    }
  }

  // the nose on the top edge, half in and half out
  const nw = rx * 0.24, nh = nw * 0.66, ny = cy - ry;
  g.fillStyle = F.noseC;
  g.beginPath(); g.ellipse(cx, ny, nw, nh, 0, 0, Math.PI * 2); g.fill();
  g.fillStyle = 'rgba(255,255,255,0.45)';
  g.beginPath(); g.ellipse(cx - nw * 0.32, ny - nh * 0.38, nw * 0.30, nh * 0.20, -0.2, 0, Math.PI * 2);
  g.fill();
}

/* ---------- the frog ----------
   A decal writes no depth, so whatever is drawn after it paints over it. The
   head cell goes down before the eye whites and the pale chin, so it only
   carries what lies on bare skin: the nostrils (its left half, a patch of
   their own so they come out as crisp dots) and the two blushes (a quarter
   each). The muzzle cell goes down last and carries the pupils (a quarter of
   the cell each, at the top) and the mouth (the bottom half). The layout is
   the baker's (FROG_FACE): a circle in an eye's quarter is a circle on the
   dome, and the mouth runs along the line the chin was baked under.
   The whites are geometry (frog_earin) and the decal does not paint them
   again: painted, their edge was the texture's, soft and a pixel wide. Lids
   are painted in the skin colour — the decal is lit like the dome under it,
   so painted skin is skin. */
function frogHeadCell(g, F, exp) {
  // two nostrils: small dots. Their patch lies on its side in the left half
  // (x runs down the face, y across it), so the texels come out square
  const N = F.nose;
  g.fillStyle = F.ink;
  for (const s of [-1, 1]) {
    g.beginPath(); g.ellipse(N[0], 0.5 + s * N[1], N[2], N[3], 0, 0, Math.PI * 2); g.fill();
  }
  for (const u of [0.625, 0.875]) {               // blush, soft-edged
    for (let k = 0; k < 4; k++) {
      g.fillStyle = 'rgba(246,140,140,' + (0.28 + k * 0.10).toFixed(2) + ')';
      const w = 1 - k * 0.18;
      g.beginPath(); g.ellipse(u, 0.5, 0.048 * w, 0.36 * w, 0, 0, Math.PI * 2); g.fill();
    }
  }
}

/* s is -1 for the eye on the reader's left; drawn in a unit square */
function frogEye(g, F, exp, s) {
  const r = F.eyeR, ink = F.ink;
  if (exp === EXPR.happy) {                       // shut, smiling: ^ ^
    // (the baked whites are not drawn for this face: see drawAnimal)
    fStroke(g, ink, r * 0.34);
    g.beginPath();
    g.moveTo(-r * 0.70, r * 0.30);
    g.quadraticCurveTo(0, -r * 0.70, r * 0.70, r * 0.30);
    g.stroke();
    return;
  }
  const focus = exp === EXPR.focus, down = exp === EXPR.down;
  g.save();
  g.beginPath(); g.arc(0, 0, r * 0.995, 0, Math.PI * 2); g.clip();
  // The pupil: big and round, and looking straight out — both a little in
  // toward the nose. The shine is in the same place on both eyes; mirrored,
  // it made them look in two directions.
  const pr = r * 0.60, px = focus ? s * r * 0.12 : -s * r * 0.08;
  const py = down ? r * 0.40 : focus ? r * 0.12 : r * 0.04;
  g.fillStyle = '#1B2420';
  g.beginPath();
  g.ellipse(px, py, pr * (focus ? 1.04 : 1), pr * (focus ? 0.70 : 1), 0, 0, Math.PI * 2);
  g.fill();
  g.fillStyle = SHINE;
  g.beginPath(); g.arc(px - pr * 0.36, py - pr * (focus ? 0.22 : 0.38), pr * 0.28, 0, Math.PI * 2); g.fill();
  // the lid: level and low when set, half down and drooping when beaten
  if (focus || down) {
    const lid = focus ? -r * 0.40 : r * 0.06, tilt = down ? s * r * 0.24 : -s * r * 0.12;
    g.fillStyle = F.fur;
    g.beginPath();
    g.moveTo(-r * 1.2, -r * 1.2); g.lineTo(r * 1.2, -r * 1.2);
    g.lineTo(r * 1.2, lid + tilt); g.lineTo(-r * 1.2, lid - tilt);
    g.closePath(); g.fill();
    fStroke(g, ink, r * 0.16);
    g.beginPath(); g.moveTo(-r * 1.2, lid - tilt); g.lineTo(r * 1.2, lid + tilt); g.stroke();
  }
  g.restore();
}

function frogSnoutCell(g, F, exp) {
  for (const s of [-1, 1]) {                      // the eyes, a quarter each
    g.save();
    g.translate(s < 0 ? 0.25 : 0.75, 0.25);
    g.scale(0.5, 0.5);
    g.beginPath(); g.rect(-0.5, -0.5, 1, 1); g.clip();
    frogEye(g, F, exp, s);
    g.restore();
  }

  // The mouth's half of the cell is ~4x longer in metres across than up, so
  // it is drawn squeezed by `mouthK`: a stroke is then as thick along the
  // line as across it, and the corners curl instead of ending in a smear.
  const M = F.mouth, n = M.length / 2, ink = F.lip, K = F.mouthK;
  const pt = (i) => [M[2 * i] * K, M[2 * i + 1]];
  const flat = () => 0;
  // the curve through the baker's points, smoothed through the midpoints
  const trace = (from, to, dy) => {
    let p = pt(from);
    g.moveTo(p[0], p[1] + dy(from));
    for (let i = from + 1; i < to; i++) {
      const a = pt(i), b = pt(i + 1);
      g.quadraticCurveTo(a[0], a[1] + dy(i), (a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + (dy(i) + dy(i + 1)) / 2);
    }
    p = pt(to);
    g.lineTo(p[0], p[1] + dy(to));
  };
  // a little hook up at each corner, into the blush (d points inward)
  const curl = (i, d) => {
    const p = pt(i);
    g.moveTo(p[0], p[1]);
    g.quadraticCurveTo(p[0] - d * 0.030, p[1] - 0.004, p[0] - d * 0.034, p[1] - 0.050);
  };
  g.beginPath(); g.rect(0, 0.5, 1, 0.5); g.clip();
  g.scale(1 / K, 1);
  if (exp === EXPR.happy) {                       // open wide: a clean crescent
    const deep = (i) => { const u = i / (n - 1) * 2 - 1; return 0.17 * (1 - u * u) ** 1.2; };
    g.beginPath(); trace(2, n - 3, flat);
    for (let i = n - 3; i >= 2; i--) { const p = pt(i); g.lineTo(p[0], p[1] + deep(i)); }
    g.closePath();
    g.fillStyle = '#E2797A'; g.fill();
    fStroke(g, ink, 0.040); g.stroke();
    fStroke(g, ink, 0.064);
    g.beginPath(); trace(0, n - 1, flat); curl(0, 1); curl(n - 1, -1); g.stroke();
    return;
  }
  if (exp === EXPR.down) {                        // a short frown, corners down
    fStroke(g, ink, 0.058);
    g.beginPath(); trace(3, n - 4, (i) => { const u = i / (n - 1) * 2 - 1; return 0.36 * u * u - 0.05; });
    g.stroke();
    return;
  }
  // the long smile; set, it presses flatter and loses the curls
  fStroke(g, ink, exp === EXPR.focus ? 0.070 : 0.064);
  g.beginPath(); trace(0, n - 1, flat);
  if (exp !== EXPR.focus) { curl(0, 1); curl(n - 1, -1); }
  g.stroke();
}

/* ---------- the penguin's face ----------
   The whole white mask is in the cell: a heart with its point at the chin and
   a widow's peak of dark between the eyes. The cell is laid over the skull's
   own (az, el) patch, which is about 0.92m across and 0.62m tall, so the art
   is drawn in metres about the patch centre (y down) and comes out round. */
const PEN_CELL = [0.92, 0.62];
function penguinHeadCell(g, F, exp) {
  g.save();
  g.translate(0.5, 0.5);
  g.scale(1 / PEN_CELL[0], 1 / PEN_CELL[1]);

  // the mask
  g.fillStyle = '#F7F5EE';
  g.beginPath();
  g.moveTo(0, -0.150);
  for (const s of [1, -1]) {
    if (s < 0) g.moveTo(0, -0.150);
    g.bezierCurveTo(s * 0.040, -0.235, s * 0.150, -0.262, s * 0.215, -0.205);
    g.bezierCurveTo(s * 0.300, -0.135, s * 0.305, 0.000, s * 0.275, 0.080);
    g.bezierCurveTo(s * 0.240, 0.180, s * 0.120, 0.270, 0, 0.300);
    g.lineTo(0, -0.150);
  }
  g.fill();

  // cheeks
  g.fillStyle = 'rgba(244,150,160,0.55)';
  for (const s of [-1, 1]) {
    g.beginPath(); g.ellipse(s * 0.205, 0.020, 0.046, 0.026, 0, 0, Math.PI * 2); g.fill();
  }

  // eyes: wide set, round, a shine in each
  const ink = '#1C2430';
  for (const s of [-1, 1]) {
    const ex = s * 0.135, ey = -0.070, r = 0.040;
    if (exp === EXPR.happy) {                       // closed, curved up
      fStroke(g, ink, 0.018);
      g.beginPath(); g.arc(ex, ey + 0.012, r * 0.95, Math.PI * 1.15, Math.PI * 1.85); g.stroke();
      continue;
    }
    const down = exp === EXPR.down, focus = exp === EXPR.focus;
    g.fillStyle = ink;
    g.beginPath();
    g.ellipse(ex, ey + (down ? 0.010 : 0), r * 0.92, r * (focus ? 0.86 : 1.06), 0, 0, Math.PI * 2);
    g.fill();
    if (down) {                                    // a heavy lid, sliding down
      g.fillStyle = '#F7F5EE';
      g.beginPath();
      g.moveTo(ex - r * 1.3, ey - r * 1.4);
      g.lineTo(ex + r * 1.3, ey - r * 1.4);
      g.lineTo(ex + r * 1.3, ey - r * (0.05 - s * 0.35));
      g.lineTo(ex - r * 1.3, ey - r * (0.05 + s * 0.35));
      g.fill();
      fStroke(g, ink, 0.010);
      g.beginPath();
      g.moveTo(ex - r * 1.0, ey - r * (0.05 + s * 0.30));
      g.lineTo(ex + r * 1.0, ey - r * (0.05 - s * 0.30));
      g.stroke();
    } else {
      g.fillStyle = '#FFFFFF';
      g.beginPath(); g.ellipse(ex + r * 0.30, ey - r * 0.36, r * 0.32, r * 0.32, 0, 0, Math.PI * 2); g.fill();
      g.beginPath(); g.ellipse(ex - r * 0.30, ey + r * 0.42, r * 0.13, r * 0.13, 0, 0, Math.PI * 2); g.fill();
    }
    if (focus) {                                   // a stern little brow
      fStroke(g, ink, 0.016);
      g.beginPath();
      g.moveTo(ex - s * r * 1.00, ey - r * 1.25);
      g.lineTo(ex + s * r * 1.10, ey - r * 1.80);
      g.stroke();
    }
  }
  g.restore();
}

/* built once at boot; nothing here runs per frame */
function drawMuzCell(g, F, exp) {
  if (F.paintSnout) return F.paintSnout(g, F, exp);
  if (F.nose && !F.onHead) drawSnout(g, F, exp);
}

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
  'rabbit:0': 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAACACAYAAADDPmHLAAAJH0lEQVR4Aeyda4wbVxXHzxlvAqlKILRKKI0SP7brhxJ701SkpYCAD6gIAYU2QfRDiFSkVoLwCGpARYVSSgUtSiWKEB9AVVUhRPcDBRVEhUQj+qFV0bYeE7C3u2tvxSr0LbXpI23Wc3vuxrPxTmbsceyduXfusebuvXPvnXvP+Z/fPDxejy3gl9EKMABGhx+AAWAADFfAcPf5CMAAGK6A4e7zEYABMFwBQ9133eYjgKuEoTkDYGjgXbcZAFcJQ3MGwNDAu24zAK4ShuYMgKGBd91mAFwlDM0ZAMMC73WXAfAqYtg6A2BYwL3uMgBeRQxbZwAMC7jXXQbAq4hh6wyAYQH3ussAeBUxbJ0BMCTgQW4yAEHKGFLPABgS6CA3GYAgZQypZwAMCXSQmwxAkDKG1DMAhgQ6yE0GIEgZQ+oZgIQHup97DEA/hRLezgAkPMD93GMA+imU8HYGIOEB7uceA9BPoYS3MwAJD3A/9xiAfgolvJ0BSGiAw7rFAIRVKqH9tAOgVCqdP16Y/HgmX/6cTNt27tykYmzGx/dszJTKHx0v7SqpaJ9rk0YA7E3liuXbTzrrTjggHkHEPyGlsVPWy9l85Y+uQ3HnW7desSFTLF/vjJ2cRQf/6TjOf7KFSituu4Lm1waAbP7prwiB3/d1BOHqXLHyB9+2CCvT6fS717/njSMo8Dc07WZK7pLOFMovpovly90KVXItAMgVdu4WCP7B7ygpBOzLFisPdFZjyVIbNu4DATf6TY6AF1gCH/Vri7NOeQDkOV5A6ggCZPsKJWCv7N+33xp0yBYqXxQC7+sz9Fi6MJnu0yfSZuUBSC2lLgMQHwurytjb1tVh+46qX2bHji0A+E0I8UKES0J0i6yLFdlM5zqR47x3kE0FiosG6T+KvriUokN7SEjpMDGKOYPGGLReeQAsy1oaxCkEHBuk/7B9t9JVP40Req8mQF+l/sosygMwX68+OIhaCPDcIP2H7bu4+Nibg4xhgfXSIP3Xuq/yACwLgDC1nOv/Z3HblvcpdU9ACwCadXsfvQ3cT/F/nVLvBXGga4beg4189YGjR48OdEobuQWeAbUAQNrcqtv3p9pOGRCekOtByRGiGtS2hvV3hxm73U7JG0RhukbWRxsApCKzs/9uWqfENbIckBa2f2DTPwLa1qy62bAPOSiu6DmBgEefmX2y3rNPDI1aASD1mZurLVL+HUp+y8G4DrEL9drjgDhBdwLlReupFePoiEXv/X/QnJn4xEqdQgXtAJDa0R53xFqyuu+1y+o5qn9IFuJKzXp1tjljf4HsWE8Jl1Pd3jNft38MMNVeS7vOdWwtAZDOzs099UIbxz6IgAdoz/sMiR36vbjcntNpBbQFQJr/TH36//ON6n205/1VrnMaXAGtARjcXd7CqwAD4FXEsHUGwLCAe91lALyKGLbOABgWcK+7DIBXEc3WhzWXARhWQc23ZwA0D+Cw5jMAwyqo+fYMgOYBHNZ8BmBYBTXfngHQPIDDms8ADKug5tszAJoGcFRmMwCjUlLTcRgATQM3KrMZgFEpqek4xgOQK1QOZgsVQWk2my+H+vduTWPta3ZiAZCPZ/H1uKsyM7GrIgB+0akaB8Rvhdmu0z8RWSIByOYrN8rHs2QL5X/l8pM3+UVqPD/5ebScR8D7ajuveKuSvJ44AJYfwIBw8HTQ8DKB4k7v42Pko1ocFLdQn02Uupe33n/+u5T78ka3gaMuJw6AhUZ1gURqUlpZhHx8zOnzvDzXC0vgY9S4m1L38l86BVwzPT195ksd3a2KlEdtRuIAkALR3v0TmYdNdB3wN9rm+ma9+pew2ySlXyIBWP6aFojrwgRJgLip1bA/fXqbMFskq08iAZAhajZqvweEQ7LsmwQ86ABc1WrUfu7bbkhlYgGQ8WvW7bvp8H6PLHcnBLxDfodvoWE/3F1vYjnRAMiAthr2NxDFl2XZTXTYv8Atm54nHoBOgI9R/iQld7nBLZieGwFAW6TkHn9pd7Cz9LZwvFheVdfdbkrZCAAQ2lf6BdQROD0xUbnYr021urWyJ/EAZCcqH6GLvm8HCbhkwWKuMDnQfYOgsXSsTzwAdNvvTgrMhZQCF7oovDlbKP8usEOngT5XuJI+PbwnU6jMZ+kUQuneTpO2WaIByBXL+2nv9zy8CWv+0cLrKKCCPkj6abpU3pPLlTfLH6fYXtx9Ubo0OZkplG+mzxXup7eVX0eAbGeMA5mJyoc6ZS0zbQHYfsmlxV6K0556gxB4q9sHAf+MY+1tzUa10mzYiAC/dNtW5QjftRx8XKzD5+SPU6TE0nHLEU8hoDxNZFb1lSspca3MdE1aAkDn7A+nxtp02K7cmytW6FO9vSk3APKijvbin9Ge+muqWwnYUtv63vyxY/+juuVlvmEfXCdObqS9+q7linP8Qx8srYx5jkPEupmWAAhonwAhCqTcASHgtmzh6Wcz+fK1mfyOMl3UHaJbwIeprXt5yO8ZfTMzMyda9dphOhyE/6EJAVUAcatA/NTbr513HoF01p1G0OilJQDrYcNxAfhil84XIuIUYsqmukOUziwCfkuH/M+eqTi7NF+3v0R9UCDcTq0vIMBxmaj8PCX5TyO3CYH72u1UiW4h72o2aj9q1at/H/RB0TSWcoulnEUhDGo0nngJhVj1mb/PZi/LPZUC9lWfNt+qVt2+hUDYTHv1xTJReQulT1L6YWumOuV3FPEdaISVaz2UlgBIUZozta/RaeBXsnxWQpgCxMvlnnpWG1esUkBbAKQXEgLaO1GAkD8oZdNh+2EUeNh585X9zXp1Vvbh1FsBrQFwXWs1anc0G/YkHbavmp+p3rWwsHDSbeO8twKJAKC3i9zaSwEGoJc6BrQxAAYEuZeLDEAvdQxoYwAUDXJUZjEAUSmt6DwMgKKBicosBiAqpRWdhwFQNDBRmcUARKW0ovMwAIoGJiqzGIColFZ0HgZAscBEbQ4DELXiis3HACgWkKjNYQCiVlyx+RgAxQIStTkMQNSKKzYfA6BYQKI2hwGIWnHF5mMAFAlIXGYwAHEpr8i8DIAigYjLDAYgLuUVmZcBUCQQcZnBAMSlvCLzMgCKBCIuMxiAuJRXZF4GIOZAxD39OwAAAP//IPop3AAAAAZJREFUAwCnAhQfxvxEHAAAAABJRU5ErkJggg==',
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

/* The flop. A salmon out of water lies on its flank and thrashes: the body
   curls into a C and back (R.bend, so it is the spine that bends, not a plank
   that tips), the tail slaps, the head lifts. Between bursts he lies still and
   gasps — the jaw drops and the gill covers lift.

   Channels: `side` rolls him about his own spine (0 = left flank up, -pi/2 =
   upright, back to the sky), `tilt` lifts the nose, `yaw` turns him on the
   dirt, `bend` is the curl [k1, k2, k3] (rad/m, see R.bend), `up`/`fwd` move
   the body's middle. The ground is solved each frame (salLift), so whatever
   the curl, he lies on the dirt rather than through it or above it. */
const SAL_REST = { side: -0.30, tilt: 0.04, yaw: 0, up: 0, fwd: 0, bend: [0, 0, 0],
                   gape: 0.10, flare: 0, pec: 0.15, h: null };

function fishFlop(seed, tq) {
  const T = (tq !== undefined ? tq : clock) + seed;
  // he thrashes in bursts and lies still between them
  const env = clamp(Math.sin(T * 0.62) * 1.7 + 0.35, 0, 1);
  const ph = T * 11.0, s = Math.sin(ph);
  const gasp = 0.5 + 0.5 * Math.sin(T * 2.6);
  return {
    side: SAL_REST.side + env * 0.22 * Math.sin(ph + 0.8),
    tilt: 0.04 + env * 0.16 * Math.max(0, Math.sin(ph + 0.5)),
    yaw: env * 0.10 * Math.sin(ph * 0.5),
    up: env * 0.07 * Math.pow(Math.max(0, s), 3),
    fwd: 0,
    bend: [env * 0.95 * s, env * 0.85 * Math.sin(ph - 1.3), 0],
    gape: 0.02 + 0.16 * gasp * (1 - env * 0.6),
    flare: 0.20 * Math.max(0, Math.sin(T * 2.6 - 0.9)) * (1 - env * 0.5),
    pec: (0.10 + 0.25 * env) * Math.sin(T * 7.3) + 0.12,
    h: null,
  };
}

/* The swing. No bat and no arms: he throws the whole fish at the ball the way
   a salmon clears a weir — rolls upright and curls into a C (the start of a
   real fish's leap), snaps straight through the zone at SWING_LAG, cartwheels
   once and lands back on his flank. `tilt` winds a whole turn, so the landing
   is the resting pose and not a pop; G.batSwingT keeps counting for seconds
   after the swing, so this has to settle on its own. */
function fishSwing(st) {
  const L = SWING_LAG;
  // [time, side, tilt, fwd, h (height of the middle), k1, k2, gape]
  const S0 = SAL_REST.side;
  const K = [[0, S0, 0.04, 0, 0.0, 0, 0, 0.10],
             [0.05, -1.25, 0.20, -0.22, 0.30, 1.4, 0.3, 0.30],
             [L, -1.57, 0.02, 0.62, 0.70, -0.5, -0.9, 0.42],
             [L + 0.22, -1.40, -2.4, 0.78, 0.95, 0.6, -0.4, 0.30],
             [L + 0.46, -0.40, -5.2, 0.40, 0.42, -0.5, 0.3, 0.20],
             [L + 0.66, S0, 0.04 - Math.PI * 2, 0, 0.0, 0, 0, 0.10]];
  let i = 0;
  while (i < K.length - 2 && st > K[i + 1][0]) i++;
  const u = clamp((st - K[i][0]) / (K[i + 1][0] - K[i][0]), 0, 1), e = u * u * (3 - 2 * u);
  const a = K[i], b = K[i + 1], m = (j) => lerp(a[j], b[j], e);
  const h = m(4);
  return { side: m(1), tilt: m(2), yaw: 0, up: 0, fwd: m(3), h: h > 0.001 ? h : null,
           bend: [m(5), m(6), 0], gape: m(7), flare: 0.25 * Math.sin(Math.PI * clamp(st / (L + 0.4), 0, 1)),
           pec: 0.5 * Math.sin(Math.PI * clamp(st / (L + 0.3), 0, 1)) };
}

/* the spine of the bent body at local height y, the same sums the vertex
   shader does: [x, y, angle] */
function salSpine(y, b) {
  const u = SAL.piv - y;
  if (u <= 0 || !(b[0] || b[1] || b[2])) return [0, y, 0];
  const du = u / 8;
  let sx = 0, sy = 0, th = 0;
  for (let i = 0; i < 8; i++) {
    const v = (i + 0.5) * du;
    th = v * (b[0] + v * (b[1] + v * b[2]));
    sx += Math.sin(th); sy += Math.cos(th);
  }
  th = u * (b[0] + u * (b[1] + u * b[2]));
  return [sx * du, SAL.piv - sy * du, th];
}

/* how far below the middle of the fish his lowest point is, for this pose:
   each section of the table, bent, turned and dropped onto the ground */
function salDrop(M, b) {
  let lo = 1e9;
  // world down, back in the fish's own axes (M's rotation is orthonormal)
  const dx = -M[1], dy = -M[5], dz = -M[9];
  for (const s of SAL.sec) {
    const sp = salSpine(s[0], b), c = Math.cos(sp[2]), sn = Math.sin(sp[2]);
    // down in the section's own (unbent) axes
    const lx = dx * c + dy * sn, lz = dz;
    const hz = lz < 0 ? s[4] - s[1] : s[2] - s[4], w = s[3];
    const q = Math.hypot(w * lx, hz * lz) || 1e-6;
    const px = w * w * lx / q, pz = s[4] + hz * hz * lz / q;
    const X = sp[0] + px * c, Y = sp[1] + px * sn, Z = pz;
    const wy = M[1] * X + M[5] * Y + M[9] * Z;
    if (wy < lo) lo = wy;
  }
  return lo;
}

const _sm = { o: m4(), i: m4(), M: m4(), h: m4(), t: m4(), j: m4() };
/* M ← world · placement; the fish's mesh hangs about local y = pl */
function salMatrix(f, fl, Y, pl) {
  const [wx, wz] = L2W(f, 0, fl.fwd);
  mTRS(_sm.o, wx, Y, wz, fl.tilt, f.ry + fl.yaw, 0, 1, 1, 1);
  const b = fl.side, I = _sm.i, cb = Math.cos(b), sb = Math.sin(b);
  // mesh x (left flank) up when side = 0, the spine forward, the back toward -x
  I.fill(0);
  I[0] = -sb; I[1] = cb;
  I[6] = 1;
  I[8] = cb; I[9] = sb;
  I[14] = -pl; I[15] = 1;
  return mMul(_sm.M, _sm.o, I);
}

/* a hinge inside the fish: rotate by `ang` about the line a→b (mesh space) */
function salHinge(M, a, b, ang, out) {
  let x = b[0] - a[0], y = b[1] - a[1], z = b[2] - a[2];
  const L = Math.hypot(x, y, z) || 1;
  x /= L; y /= L; z /= L;
  const c = Math.cos(ang), s = Math.sin(ang), k = 1 - c, H = _sm.h;
  H[0] = c + x * x * k;     H[1] = y * x * k + z * s; H[2] = z * x * k - y * s; H[3] = 0;
  H[4] = x * y * k - z * s; H[5] = c + y * y * k;     H[6] = z * y * k + x * s; H[7] = 0;
  H[8] = x * z * k + y * s; H[9] = y * z * k - x * s; H[10] = c + z * z * k;    H[11] = 0;
  // keep a on the spot
  H[12] = a[0] - (H[0] * a[0] + H[4] * a[1] + H[8] * a[2]);
  H[13] = a[1] - (H[1] * a[0] + H[5] * a[1] + H[9] * a[2]);
  H[14] = a[2] - (H[2] * a[0] + H[6] * a[1] + H[10] * a[2]);
  H[15] = 1;
  return mMul(out, M, H);
}


/* ---------- 鮭 ---------- */
function drawSalmon(f, A, look, p, y) {
  const sw = p.swingT;
  let fl;
  if (p.still) fl = Object.assign({}, SAL_REST, { side: -Math.PI / 2, tilt: 0, gape: 0.04, pec: 0.25, h: 0.20 });
  else if (p.fall) fl = Object.assign({}, SAL_REST, { side: 0.38, bend: [0.35, 0, 0], gape: 0.32, flare: 0.16 });
  else if (sw >= 0 && sw <= SWING_LAG + 0.66) fl = fishSwing(sw);
  else {
    fl = fishFlop(p.flopT !== undefined ? 0 : f.ry * 3.1, p.flopT);
    // just after the swing, ease back into the thrash rather than snapping
    if (sw > 0) {
      const k = clamp((sw - SWING_LAG - 0.66) / 0.6, 0, 1);
      fl.bend = fl.bend.map((v) => v * k); fl.side = lerp(SAL_REST.side, fl.side, k);
      fl.tilt = lerp(SAL_REST.tilt, fl.tilt, k); fl.up *= k; fl.yaw *= k;
    }
  }
  const PL = 0.56;                           // the middle of the body, where it is held
  const M = salMatrix(f, fl, 0, PL);
  const b = fl.bend;
  // lie on the dirt: the lowest point of this pose goes to the ground
  const lift = -salDrop(M, b);
  M[13] = y + Math.max(lift, fl.h || 0) + fl.up;

  const ink = R.inkW > 0;
  const put = (prim, c, mat) => R.m(prim, mat || M, ink ? inkOf(col(c)) : col(c));
  R.bend = (b[0] || b[1] || b[2]) ? [SAL.piv, b[0], b[1], b[2]] : null;

  // wet skin: the body and its markings, then the fins a little duller
  R.gloss = 0.32;
  put('sal_body', A.fur);
  put('sal_belly', A.fur2);
  put('sal_bars', A.bar);
  put('sal_dbars', A.bar2);
  put('sal_back', A.back);
  put('sal_line', A.line);
  put('sal_band', look.uni);
  put('sal_gill', '#9E2A34');
  // the gill covers lift on their hinge at the preopercle
  const O = SAL.oper, fa = fl.flare || 0;
  put('sal_operl', A.oper, salHinge(M, [O[0], O[1], O[2]], [O[3], O[4], O[5]], fa, _sm.t));
  put('sal_operr', A.oper, salHinge(M, [-O[0], O[1], O[2]], [-O[3], O[4], O[5]], -fa, _sm.t));
  put('sal_mouth', '#3B262B');
  // the lower jaw drops about its hinge under the eye; its teeth come with it
  const J = SAL.jaw, mJ = salHinge(M, [0, J[0], J[1]], [1, J[0], J[1]], fl.gape || 0, _sm.j);
  R.gloss = 0.18;
  put('sal_jaw', A.jaw, mJ);
  put('sal_dorsal', A.fin);
  put('sal_dorsal_m', A.finEdge);
  put('sal_adipose', A.back);
  put('sal_caudal', A.fin);
  put('sal_caudal_m', A.finEdge);
  put('sal_anal', A.fin);
  put('sal_anal_m', A.finTip);
  put('sal_pelvic', A.fin);
  put('sal_pelvic_m', A.finTip);
  put('sal_axil', A.fin);
  // pectorals flick on their own root
  const P = SAL.pec, pa = fl.pec || 0;
  put('sal_pecl', A.fin, salHinge(M, [P[0], P[1], P[2]], [P[3], P[4], P[5]], pa, _sm.t));
  put('sal_pecr', A.fin, salHinge(M, [-P[0], P[1], P[2]], [-P[3], P[4], P[5]], -pa, _sm.t));
  // teeth and the eye carry no outline: at this size the line would swallow them
  if (!ink) {
    R.gloss = 0.3;
    put('sal_teeth', '#E9DFC4');
    put('sal_lteeth', '#E9DFC4', mJ);
    R.gloss = 0.9;
    put('sal_eye', '#262A22');
    put('sal_iris', '#B39446');
    put('sal_pupil', '#0A0908');
  }
  R.gloss = 0;
  R.bend = null;
}

/* ---------- カブトムシ ----------
   A male Trypoxylus dichotomus, as the insect: horizontal on six legs, belly
   a hand off the dirt, head down in front and the horn rising out of it.

   He is drawn with his own matrices rather than `part()`, because a beetle
   that rears, twists its prothorax and rolls onto its back needs rotations
   that one pitch about the hips cannot give. Everything goes through
   W (where he stands, which way he faces) · B (the body: rear, yaw, roll,
   lift) · F (the prothorax hinge: head, pronotum, horns and fore legs flip
   up together, which is how the real one throws a rival).

   The legs are coxa, femur, tibia, tarsus, solved every frame by IK from the
   coxa (BEE_LEG, solved on the underside in the baker) to a foot on the
   ground. When he runs the feet are planted in the world: the stride phase
   is how far he has come along his own heading, so a planted foot does not
   skate. It is an alternating tripod — left fore, right mid, left hind
   against the other three — the way every insect walks. */
const BEE_REAR = [0, 0.10, -0.50];      // he rears about his hind legs
const BEE_NECK = [0, 0.60, 0.08];       // the prothorax hinge
const BEE_ROLL = [0, 0.42, -0.05];
// the feet at rest, his left side: fore reach forward, mid out, hind back
// tucked in the way the real one stands: about 1.45x the shell's width across
// the feet, the hind pair trailing back along the body. Splayed twice as wide,
// the outfield read a dark spider instead of a shell with a horn.
const BEE_FOOT = [[0.42, 0.80], [0.54, 0.02], [0.46, -0.84]];
const BEE_SLIDE = [[0.30, 0.98], [0.60, -0.20], [0.42, -1.05]];
const BEE_STRIDE = 0.34;
const _bm = { W: m4(), B: m4(), F: m4(), T: m4(), U: m4(), V: m4(), M: m4(), S: m4() };

/* rotate about the point p (the Y*X*Z order mTRS uses) */
function mPiv(o, p, rx, ry, rz) {
  mTRS(o, 0, 0, 0, rx, ry, rz, 1, 1, 1);
  o[12] = p[0] - (o[0] * p[0] + o[4] * p[1] + o[8] * p[2]);
  o[13] = p[1] - (o[1] * p[0] + o[5] * p[1] + o[9] * p[2]);
  o[14] = p[2] - (o[2] * p[0] + o[6] * p[1] + o[10] * p[2]);
  return o;
}
function mPt(m, p) {
  return [m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
          m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
          m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14]];
}
function mDir(m, p) {
  return [m[0] * p[0] + m[4] * p[1] + m[8] * p[2],
          m[1] * p[0] + m[5] * p[1] + m[9] * p[2],
          m[2] * p[0] + m[6] * p[1] + m[10] * p[2]];
}
const v3sub = (a, b) => [a[0] - b[0], a[1] - b[1], a[2] - b[2]];
const v3dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const v3cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
function v3unit(a) { const l = Math.hypot(a[0], a[1], a[2]) || 1e-6; return [a[0] / l, a[1] / l, a[2] / l]; }

/* one baked part under a full matrix (R.d only takes Euler angles) */
function beeDraw(prim, M, c) {
  const gl = R.gl, pt = GEO.parts[prim];
  gl.uniformMatrix4fv(R.u.uM, false, M);
  gl.uniform3fv(R.u.uColor, R.inkW > 0 ? inkOf(c) : c);
  R._g();
  gl.drawElements(gl.TRIANGLES, pt.count, gl.UNSIGNED_SHORT, pt.offset);
}
/* a part authored at the origin, placed by `base` (in his frame) then W */
function beeAt(prim, base, c, tx, ty, tz, rx, sc) {
  mTRS(_bm.T, tx || 0, ty || 0, tz || 0, rx || 0, 0, 0, sc || 1, sc || 1, sc || 1);
  mMul(_bm.U, base, _bm.T);
  mMul(_bm.M, _bm.W, _bm.U);
  beeDraw(prim, _bm.M, c);
}
/* a bone from joint a to joint b (yaw frame). The baked bone runs down -Y
   from its joint at length L0; `ref` says which way its outer edge faces. */
function beeBone(prim, a, b, L0, ref, side, c) {
  const d = v3sub(a, b), len = Math.hypot(d[0], d[1], d[2]) || 1e-4;
  const Y = [d[0] / len, d[1] / len, d[2] / len];
  let X = v3sub(side, Y.map((q) => q * v3dot(side, Y)));
  if (Math.hypot(X[0], X[1], X[2]) < 1e-4) X = [0, 0, 1];
  X = v3unit(X);
  let Z = v3cross(X, Y);
  if (v3dot(Z, ref) < 0) { X = X.map((q) => -q); Z = Z.map((q) => -q); }
  const S = _bm.S, k = len / L0;
  S[0] = X[0]; S[1] = X[1]; S[2] = X[2]; S[3] = 0;
  S[4] = Y[0] * k; S[5] = Y[1] * k; S[6] = Y[2] * k; S[7] = 0;
  S[8] = Z[0]; S[9] = Z[1]; S[10] = Z[2]; S[11] = 0;
  S[12] = a[0]; S[13] = a[1]; S[14] = a[2]; S[15] = 1;
  mMul(_bm.M, _bm.W, S);
  beeDraw(prim, _bm.M, c);
}

/* The swing. He has no bat; he hits the way a rhinoceros beetle throws a
   rival off a branch. Side-on to the plate, horn low over the dirt — then
   the prothorax snaps up and across while he rears on his hind legs, which
   flings the horn up through the zone. `flex` is the prothorax hinge (+ is
   head down), `rear` the body about the hind legs (- is up), `yaw` turns the
   horn toward the pitcher (+). Contact is at SWING_LAG; G.batSwingT keeps
   counting long after the swing, so the last key is the stance again. */
function beetleSwing(st) {
  const L = SWING_LAG;
  const K = [[0, 0.30, 0, -0.22, 0], [0.05, 0.42, 0.02, -0.30, 0.04],
             [L, -0.15, -0.05, 0.0, -0.08], [L + 0.12, -0.58, -0.28, 0.45, -0.20],
             [L + 0.40, -0.34, -0.14, 0.35, -0.08], [L + 0.85, 0.30, 0, -0.22, 0]];
  const o = { flex: K[0][1], rear: K[0][2], yaw: K[0][3], roll: K[0][4] };
  if (!(st > 0)) return o;
  if (st >= K[K.length - 1][0]) return o;
  let i = 0;
  while (st > K[i + 1][0]) i++;
  const u = (st - K[i][0]) / (K[i + 1][0] - K[i][0]), e = u * u * (3 - 2 * u);
  o.flex = lerp(K[i][1], K[i + 1][1], e); o.rear = lerp(K[i][2], K[i + 1][2], e);
  o.yaw = lerp(K[i][3], K[i + 1][3], e); o.roll = lerp(K[i][4], K[i + 1][4], e);
  return o;
}

function drawBeetle(x, z, ry, A, look, p, bob) {
  const bat = p.swingT !== undefined;
  if (bat) ry = -Math.PI / 2;               // squarely side-on, whatever the rig turns
  const fall = p.fall || 0, flip = Math.abs(fall) > 1.3;
  const slide = !flip && fall < 0 ? clamp(-fall / 1.18, 0, 1) : 0;
  const aL = p.armL || 0, aR = p.armR || 0;
  const cheer = !flip && !bat && aL < -1.8 && aR < -1.8;
  const lg = p.legL || 0, run = !bat && !fall && lg !== 0 && Math.abs(lg + (p.legR || 0)) < 1e-6;
  const cs = Math.cos(ry), sn = Math.sin(ry);
  const ph = p.gait !== undefined ? p.gait : run ? (x * sn + z * cs) / (2 * BEE_STRIDE) : null;

  // ---- body pose
  let lift = fall ? 0 : bob, rear = 0, yaw = 0, roll = 0, flex = 0;
  if (bat) { const k = beetleSwing(p.swingT); flex = k.flex; rear = k.rear; yaw = k.yaw; roll = k.roll; }
  if (cheer) { rear = -0.46; flex = -0.30; }
  if (slide) { lift -= 0.23 * slide; flex = -0.08 * slide; }
  if (ph !== null) {
    const w = Math.sin(ph * Math.PI * 2);
    roll = 0.035 * w; yaw = 0.045 * w; lift += 0.012 * Math.abs(Math.cos(ph * Math.PI * 2));
  }
  // the pitcher winds up by raising his right fore leg and rearing a little
  const wind = !bat && !run && !cheer && !fall && aL < -0.5 ? clamp((-aL - 0.5) / 2, 0, 1) : 0;
  rear -= wind * 0.22;
  // reaching for a ball: lift the front toward it
  // Behind the plate he is crouched (drawn 0.22 low): head down, horn laid
  // forward along the ground. Raised, it stood straight up in the middle of
  // the batting camera's view, a black pole in front of the plate.
  const crouch = !fall && !bat && bob < -0.1;
  if (crouch) flex += 0.60;
  const reachY = bat || crouch ? null : p.handR ? p.handR[1] : p.handL ? p.handL[1] : null;
  if (reachY !== null && !fall) flex -= clamp((reachY - 0.5) / 1.6, 0, 0.32);

  const W = mTRS(_bm.W, x, 0, z, 0, ry, 0, 1, 1, 1), B = _bm.B, F = _bm.F;
  if (flip) {
    // over on his back, rocked a little onto one side, legs in the air
    mPiv(_bm.U, BEE_ROLL, 0, 0, Math.PI - 0.16);
    mTRS(_bm.V, 0, -0.035, 0, 0, 0, 0, 1, 1, 1);
    mMul(B, _bm.V, _bm.U);
  } else {
    mPiv(_bm.U, BEE_REAR, rear, 0, 0);
    mPiv(_bm.V, BEE_ROLL, 0, yaw, roll);
    mMul(_bm.T, _bm.U, _bm.V);
    mTRS(_bm.V, 0, lift, 0, 0, 0, 0, 1, 1, 1);
    mMul(B, _bm.V, _bm.T);
  }
  mPiv(_bm.U, BEE_NECK, flex, bat ? yaw * 0.35 : crouch ? 0.50 : 0, bat ? roll * 0.8 : 0);
  mMul(F, B, _bm.U);

  // the shadow follows the body, long and narrow under him
  const cz = flip ? -0.08 : -0.12;
  shadow(x + cz * sn, z + cz * cs, flip ? 0.50 : 0.46, 0.34, 1.80, ry);

  // ---- colours
  const ely = col(A.fur), pro = col(A.fur2), headC = col(A.headC), horn = col(A.horn);
  const legC = col(A.leg), ven = col(A.venter), eye = col('#06040A');

  // ---- legs, outlined at half weight: at a distance the full line doubled
  // their thickness and the six of them became a dark tangle
  const inkW = R.inkW;
  if (inkW > 0) R.ink(inkW * 0.5);
  const up = mDir(B, [0, 1, 0]);
  let hl = null, hr = null;
  for (let i = 0; i < 3; i++) {
    const L = BEE_LEG[i], base = i === 0 ? F : B;
    for (const s of [1, -1]) {
      const C = mPt(base, [s * L[0], L[1], L[2]]);
      const outw = mDir(B, [s, 0, 0]);
      const pole = v3unit([outw[0] + up[0] * 1.3, outw[1] + up[1] * 1.3, outw[2] + up[2] * 1.3]);
      let T, air = false;
      const fb = (slide ? BEE_SLIDE : BEE_FOOT)[i];
      if (flip) {
        // waving at the sky, each a little differently
        const kk = (s > 0 ? lg : p.legR || 0) * (i === 1 ? -0.6 : 1);
        T = mPt(B, [s * fb[0] * 0.70, -0.16 + 0.05 * i + kk * 0.10, fb[1] * 0.72 + kk * 0.12]);
        air = true;
      } else if (i === 0 && cheer) {
        T = mPt(F, [s * 0.36, 0.98 + bob * 0.5, 0.80]);
        air = true;
      } else if (i === 0 && !bat && (s > 0 ? p.handR : p.handL)) {
        const h = s > 0 ? p.handR : p.handL, dx = h[0] - x, dz = h[2] - z;
        T = [dx * cs - dz * sn, h[1], dx * sn + dz * cs];
        air = true;
      } else if (i === 0 && s < 0 && wind > 0) {
        const r0 = [-fb[0], 0, fb[1]], r1 = mPt(F, [-0.34, 0.80, 0.78]);
        T = [lerp(r0[0], r1[0], wind), lerp(r0[1], r1[1], wind), lerp(r0[2], r1[2], wind)];
        air = wind > 0.05;
      } else {
        let dz = 0, hgt = 0;
        if (ph !== null) {
          const tri = (i === 1) === (s > 0) ? 0.5 : 0;
          const u = ((ph + tri) % 1 + 1) % 1;
          if (u < 0.5) dz = BEE_STRIDE / 2 - (u / 0.5) * BEE_STRIDE;
          else { const v = (u - 0.5) / 0.5; dz = -BEE_STRIDE / 2 + v * BEE_STRIDE; hgt = Math.sin(Math.PI * v) * 0.15; }
        }
        T = [s * fb[0], hgt, fb[1] + dz];
      }
      // the tarsus: laid along the ground from the claws back toward the body,
      // rising to the ankle; in the air it simply carries on from the leg
      const Lf = L[3], Lt = L[4], Lr = L[5];
      let An;
      if (air) {
        const d = v3unit(v3sub(C, T));
        An = [T[0] + d[0] * Lr * 0.92, T[1] + d[1] * Lr * 0.92 + Lr * 0.25, T[2] + d[2] * Lr * 0.92];
      } else {
        const h = v3unit([C[0] - T[0], 0, C[2] - T[2]]);
        An = [T[0] + h[0] * Lr * 0.90, T[1] + Lr * 0.42, T[2] + h[2] * Lr * 0.90];
      }
      // two bones from the coxa to the ankle, the knee breaking up and out
      let d = v3sub(An, C), D = Math.hypot(d[0], d[1], d[2]);
      const reach = (Lf + Lt) * 0.998;
      if (D > reach) {
        An = [C[0] + d[0] / D * reach, C[1] + d[1] / D * reach, C[2] + d[2] / D * reach];
        const dt = v3unit(v3sub(T, An));
        T = [An[0] + dt[0] * Lr, An[1] + dt[1] * Lr, An[2] + dt[2] * Lr];
        d = v3sub(An, C); D = reach;
      }
      const u = [d[0] / D, d[1] / D, d[2] / D];
      const a = (Lf * Lf - Lt * Lt + D * D) / (2 * D), hk = Math.sqrt(Math.max(0, Lf * Lf - a * a));
      const pp = v3unit(v3sub(pole, u.map((q) => q * v3dot(pole, u))));
      const K = [C[0] + u[0] * a + pp[0] * hk, C[1] + u[1] * a + pp[1] * hk, C[2] + u[2] * a + pp[2] * hk];
      const across = v3unit(v3cross(v3sub(K, C), v3sub(An, C)));
      const ref = [outw[0] + up[0], outw[1] + up[1], outw[2] + up[2]];

      R.gloss = 0.45;
      mMul(_bm.T, base, mTRS(_bm.V, s * L[0], L[1], L[2], 0, 0, s * 0.35, 1, 1, 1));
      mMul(_bm.M, W, _bm.T);
      beeDraw('bee_coxa', _bm.M, legC);
      beeBone('bee_fem', C, K, BEE_BONE[0], ref, across, legC);
      beeBone(i === 0 ? 'bee_tibf' : 'bee_tib', K, An, BEE_BONE[1], ref, across, legC);
      beeBone('bee_tars', An, T, BEE_BONE[2], up, across, legC);
      for (const [q, r] of [[K, 0.068], [An, 0.046]]) {
        mTRS(_bm.T, q[0], q[1], q[2], 0, 0, 0, r, r, r);
        mMul(_bm.M, W, _bm.T);
        beeDraw('sphere', _bm.M, legC);
      }
      if (i === 0) {
        const wT = [x + T[0] * cs + T[2] * sn, T[1], z - T[0] * sn + T[2] * cs];
        if (s > 0) hr = wT; else hl = wT;
      }
    }
  }

  if (inkW > 0) R.ink(inkW);

  // ---- the body: three tagmata, three values. The wing cases are lacquered
  // chestnut; the pronotum and the head go nearly black, so the three parts
  // read apart even at a distance.
  R.gloss = 0.30;
  beeAt('bee_venter', B, ven);
  beeAt('bee_stern', B, shade(A.venter, 0.70));
  R.gloss = 0.55;
  beeAt('bee_elytra', B, ely);
  beeAt('bee_rim', B, shade(A.fur, 0.80));
  R.gloss = 0;
  beeAt('bee_suture', B, shade(A.fur, 0.42));
  beeAt('bee_scut', B, pro);
  R.gloss = 0.55;
  beeAt('bee_mark', B, col(look.uni));
  // the pronotum is satin, not lacquer: a smaller, softer highlight
  R.gloss = 0.35;
  beeAt('bee_prono', F, pro);
  R.gloss = 0.55;
  beeAt('bee_head', F, headC);
  beeAt('bee_horn', F, horn);
  beeAt('bee_mouth', F, headC);
  beeAt('bee_ant', F, legC);
  R.gloss = 0.95;
  beeAt('bee_eye', F, eye);
  R.gloss = 0;
  beeAt('bee_brush', F, col(A.brush));

  R.gloss = 0;
  return { f: yawFrame(x, z, ry), hl: hl || [x, 0.4, z], hr: hr || [x, 0.4, z], hy: 1.0, y: bob };
}

/* ---------- ペンギン ----------
   One soft egg with a round head on it. The legs are inside him: the hips stay
   at the rig's y+0.44 and only the feet come out from under the hem, so he
   waddles by construction. The arms are flippers, still driven by the shared
   pose (swung by `armL/armR`, or aimed at a grip with `handL/handR`), so the
   bat, the glove, the throw and the cheer all work as they do on everyone. */
const PEN_SH = [0.268, 0.865, -0.010];      // shoulder: out, up, back
const PEN_SPLAY = 0.50;

/* a local point to world, tilt and all — where part() would put it */
function penW(f, lx, ly, lz) {
  let Y = ly, Z = lz;
  if (f.t) {
    const dy = ly - f.pivot;
    Y = f.pivot + dy * f.ct - lz * f.st;
    Z = dy * f.st + lz * f.ct;
  }
  const [wx, wz] = L2W(f, lx, Z);
  return [wx, Y, wz];
}

/* a local direction to world */
function penDir(f, v) {
  let y = v[1], z = v[2];
  if (f.t) { const y2 = y * f.ct - z * f.st; z = y * f.st + z * f.ct; y = y2; }
  return [v[0] * f.c + z * f.s, y, -v[0] * f.s + z * f.c];
}

/* part() with a yaw of its own — the feet turn out a little */
function penPart(f, prim, lx, ly, lz, c, rx, rz, yaw) {
  const w = penW(f, lx, ly, lz);
  R.d(prim, w[0], w[1], w[2], (rx || 0) + f.t, f.ry + (yaw || 0), rz || 0, 1, 1, 1, c);
}

/* Draw a part that hangs along its own -y so that -y points along `d` and its
   +x (the flat face of a flipper) as near `n` as it can. Euler angles alone
   cannot roll a flipper about its own length, and a flipper that cannot roll
   goes edge-on — a stick — the moment it is raised. */
function penAim(prim, p, d, n, sy, c) {
  const Y = [-d[0], -d[1], -d[2]];
  const k = n[0] * Y[0] + n[1] * Y[1] + n[2] * Y[2];
  let X = [n[0] - k * Y[0], n[1] - k * Y[1], n[2] - k * Y[2]];
  let L = Math.hypot(X[0], X[1], X[2]);
  if (L < 1e-4) { X = [Y[1], -Y[0], 0]; L = Math.hypot(X[0], X[1]) || 1; }
  X = [X[0] / L, X[1] / L, X[2] / L];
  const Z = [X[1] * Y[2] - X[2] * Y[1], X[2] * Y[0] - X[0] * Y[2], X[0] * Y[1] - X[1] * Y[0]];
  R.d(prim, p[0], p[1], p[2], Math.asin(clamp(-Z[1], -1, 1)), Math.atan2(Z[0], Z[2]),
      Math.atan2(X[1], Y[1]), 1, sy || 1, 1, c);
}

function drawPenguin(x, z, ry, f, A, look, p, y, FC) {
  const fur = col(A.fur), white = col(A.fur2), orange = col(A.foot);
  const uni = col(look.uni), trim = col(look.trim), cap = col(look.cap);
  const sp = (p.spread || 0) * 0.5;
  // He leans as one piece, about a point just above his feet: tipping only
  // the egg about its middle swings the hem back and bares the legs.
  if (!f.t && p.lean) {
    f.t = p.lean * 0.75; f.ct = Math.cos(f.t); f.st = Math.sin(f.t); f.pivot = y + 0.12;
  }
  const lL = p.legL || 0, lR = p.legR || 0;
  // the waddle: he rocks onto whichever foot is under him
  const wad = (lL - lR) * 0.06;

  // legs: short fat orange stubs, nearly all inside the egg, and the feet.
  // Thick, because in a slide they come out and a thin one is a stick.
  for (const s of [-1, 1]) {
    const jx = s * (0.150 + sp), lr = s < 0 ? lL : lR;
    const e = limb(f, jx, y + 0.44, 0, lr, s * 0.04, 0.36, 0.088, orange, null, 0);
    penPart(f, 'penguin_foot', e[0], e[1], e[2], orange, lr * 0.7, s * 0.04, s * 0.26);
  }

  // the egg: dark below the hem with the white belly on it, the jersey above
  const B = (prim, c) => part(f, prim, 0, y + 0.74, 0, 1, 1, 1, c, 0, wad);
  B('penguin_body', fur);
  B('penguin_belly', white);
  B('penguin_jersey', uni);
  B('penguin_hem', trim);
  B('penguin_placket', trim);
  B('penguin_button', white);
  // a little point of a tail, low at the back
  part(f, 'cone', 0, y + 0.19, -0.290, 0.13, 0.12, 0.07, fur, 1.25);

  // flippers, each in a short sleeve that turns with it
  let hl, hr;
  const [shx, shy, shz] = PEN_SH, sy = y + shy;
  for (const s of [-1, 1]) {
    const tgt = s < 0 ? p.handL : p.handR;
    let e, d, n, w, sc = 1;
    if (tgt) {
      // reaching: straight at the grip from a shoulder pulled in a little. It
      // does not bend, so it stretches a little instead, as the cartoon arms do
      w = penW(f, s * (shx - 0.04), sy, shz + 0.04);
      d = [tgt[0] - w[0], tgt[1] - w[1], tgt[2] - w[2]];
      const dl = Math.hypot(d[0], d[1], d[2]) || 1e-4, L = clamp(dl, 0.26, 0.78);
      d = [d[0] / dl, d[1] / dl, d[2] / dl];
      n = penDir(f, [s, 0.2, 0.7]);
      sc = L / PEN.flip;
      e = [w[0] + d[0] * L, w[1] + d[1] * L, w[2] + d[2] * L];
    } else {
      const rx = (s < 0 ? p.armL : p.armR) || 0, rz = s * PEN_SPLAY;
      const t = limbTip(0, 0, 0, rx, rz, 1);
      // Hanging, the flat face looks out and a little forward; raised, it
      // turns to face front, so a cheer is two flippers and not two sticks
      const u = clamp(-rx / 2.2, 0, 1), th = 0.45 + u * 0.95;
      w = penW(f, s * shx, sy, shz);
      d = penDir(f, t);
      n = penDir(f, [s * Math.cos(th), 0, Math.sin(th)]);
      e = [s * shx + t[0] * PEN.flip, sy + t[1] * PEN.flip, shz + t[2] * PEN.flip];
    }
    penAim('penguin_flip', w, d, n, sc, fur);
    penAim('penguin_sleeve', w, d, n, 1, uni);
    penAim('penguin_cuff', w, d, n, 1, trim);
    if (s < 0) hl = e; else hr = e;
  }

  // the head: may turn on its own (a batter watching the pitcher)
  const fh = p.headRy ? yawFrame(x, z, ry + p.headRy) : f;
  if (fh !== f && f.t) Object.assign(fh, { t: f.t, ct: f.ct, st: f.st, pivot: f.pivot });
  const hy = y + 1.34;
  part(fh, 'penguin_head', 0, hy, 0, 1, 1, 1, fur);
  if (FC && R.atlas && R.inkW === 0) {
    // the white mask, the eyes and the blush, painted on the skull's own patch
    R.decal(faceRect(look.animal, p.face || 0, 0));
    part(fh, 'penguin_face', 0, hy, 0, 1, 1, 1, white);
    R.decal(null);
  }
  // The beak: one closed soft cone; only when he is pleased with himself does
  // it come apart into two halves, the lower one dropped open
  const [by, bz, bt] = PEN.beak, beak = col(A.beak);
  if (p.face === EXPR.happy) {
    const open = 0.55;
    part(fh, 'penguin_beak', 0, hy + by, bz, 1, 1, 1, beak, bt);
    part(fh, 'penguin_beak', 0, hy + by - 0.002, bz - 0.004, 0.94, 0.82, 0.94,
         shade(A.beak, 0.92), bt + open, Math.PI);
    if (R.inkW === 0)
      part(fh, 'sphere', 0, hy + by - 0.018, bz + 0.012, 0.11, 0.055, 0.135, col('#B4474A'), bt + open * 0.5);
  } else {
    part(fh, 'penguin_beakc', 0, hy + by, bz, 1, 1, 1, beak, bt);
  }

  // headwear: the shared crown and bill at his own (smaller) size, perched on
  // top and rocked back a little, so a low camera sees the top of the bill
  // and the bill never reaches the eyes
  if (!p.noHat) {
    const cy = A.capY || 0, cs = A.capS || 1, tip = A.capT || 0;
    // the bill a shade under the crown, not navy: a navy bill seen from below
    // is a headband across the forehead
    const brim = shade(look.cap, 0.80);
    if (p.helmet) {
      // A size up and sat lower. Big enough that its rim stands clear of the
      // skull all the way round: a rim that cuts into the head leaves a
      // ragged line where the two meet.
      const hs = 1.08, hy2 = hy - 0.060, hz = 0.015;
      part(fh, 'cap_crown', 0, hy2, hz, hs, hs, hs, cap, tip * 0.5);
      part(fh, 'cap_bill', 0, hy2, hz + 0.348 * hs * 0.45, hs * 0.74, hs, hs * 0.55, brim, tip * 0.5);
    } else {
      // The bill is scaled shorter in z, and a scale in z also pulls its root
      // back inside the crown — so it is slid forward by what the scale took.
      const k = 1.0, by2 = (0.222 + 0.026) * (cs - cs * k);
      part(fh, 'cap_crown', 0, hy + cy, 0, cs, cs, cs, cap, tip);
      part(fh, 'cap_bill', 0, hy + cy + by2, 0.348 * cs * 0.36, cs * 0.80, cs * k, cs * 0.64,
           brim, tip);
      part(fh, 'sphere', 0, hy + cy + 0.492 * cs, -0.06 * cs, 0.09 * cs, 0.09 * cs, 0.09 * cs, trim);
    }
  }
  return { f, hl, hr, hy, y };
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
  if (A.body === 'beetle') return drawBeetle(x, z, ry, A, look, p, y);
  if (p.fall) { f.t = p.fall; f.ct = Math.cos(p.fall); f.st = Math.sin(p.fall); f.pivot = y + 0.34; }
  const big = A.big ? 1.12 : 1;
  const fur = col(A.fur), fur2 = col(A.fur2), paw = A.paw ? col(A.paw) : fur, hs = A.handS || 0.27;
  const uni = col(look.uni), trim = col(look.trim), cap = col(look.cap);
  const trim2 = shade(look.trim, 0.72);

  shadow(x, z, (p.fall ? 0.72 : 0.44) * big * (A.shadow || 1), 0.34);
  if (A.form === 'penguin') return drawPenguin(x, z, ry, f, A, look, p, y, FC);

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
  } else if (A.legs === 'frog') {
    // a green stub and a flat webbed foot, turned out and laid on the ground
    // from the ankle the way the rabbit's is
    for (const s of [-1, 1]) {
      const rx = (s < 0 ? p.legL : p.legR) || 0, rz = s * 0.04;
      // a baked soft leg on the rig's own hip and length, not the plain
      // cylinder: spread at the plate, that was a bright green post
      // half the stance spread, as the penguin: the full one stood the back
      // leg out beside the jersey from the hip down
      const jx = s * (A.hipX * big + sp * 0.5), e = limbTip(jx, y + 0.44, 0, rx, rz, 0.36);
      part(f, 'frog_leg', jx, y + 0.44, 0, 1, 1, 1, fur, rx, rz);
      part(f, s < 0 ? 'frog_foot_r' : 'frog_foot_l', e[0], e[1], e[2], 1, 1, 1, col(A.foot), rx, rz);
    }
  } else if (!A.body) {             // the fish has none and the beetle has six
    // `legW` / `footS` let a species be stumpier without moving the hip: the
    // rig hangs every leg off y+0.44 and running, sliding and falling are all
    // built on that. How much leg you actually see is set by how low the
    // jersey comes; thickness and foot size do the rest of the work.
    const lw = A.legW || 0.12, fs = A.footS || 0.30;
    for (const s of [-1, 1]) {
      const rx = (s < 0 ? p.legL : p.legR) || 0, rz = s * 0.04;
      const e = limb(f, s * (0.155 * big + sp), y + 0.44, 0, rx, rz, 0.36, lw, pant,
                     A.sole ? pant : shoe, fs, 1);
      // just the sole dark, a slab under the foot the way the sketch shades it
      if (A.sole) part(f, 'rbox', e[0], e[1] - fs * 0.24, e[2] + fs * 0.16,
                       fs * 0.98, fs * 0.26, fs * 1.38, shoe, rx, rz);
    }
  }

  // torso
  if (A.body === 'fish') drawSalmon(f, A, look, p, y);
  else if (A.mesh) {
    // the kit is baked as slices of the same profile as the body: laying a
    // sphere over a shaped torso makes it bulge out rather than cover
    const M = A.mesh + '_', ln = p.lean || 0;
    part(f, M + 'body', 0, y + 0.74, 0, 1, 1, 1, uni, ln);
    if (!A.noStripe) part(f, M + 'stripe', 0, y + 0.74, 0, 1, 1, 1, look.pin ? col(look.pin) : shade(look.uni, 0.80), ln);
    part(f, M + 'placket', 0, y + 0.74, 0, 1, 1, 1, trim, ln);
    // the sketch's jersey has no collar: the head sits straight on it
    if (!A.noCollar) part(f, M + 'collar', 0, y + 0.74, 0, 1, 1, 1, trim, ln);
    part(f, M + 'belt', 0, y + 0.74, 0, 1, 1, 1, shade(look.cap, 0.85), ln);
    // The sleeve is a capped cylinder hung outside the jersey, so its cut end
    // sat in plain sight as a hard facet on each shoulder — most obvious from
    // a low camera, which is the one the game uses at the plate. The mesh
    // cannot reach it: the torso is tall enough there, just not wide enough,
    // and widening the whole ring only makes him square. A cap over the joint
    // is what a set-in sleeve looks like anyway.
    // (a baked `sleeve` has a dome of its own and needs none)
    if (!A.sleeve) for (const s of [-1, 1])
      part(f, 'sphere', s * 0.318 * big, y + 0.948, 0.004, 0.268, 0.248, 0.274, uni, ln);
  } else if (A.torso === 'rabbit') {
    // white jersey on white fur: the pink trim is what draws him
    const ln = p.lean || 0;
    part(f, 'rabbit_body', 0, y + 0.74, 0, 1, 1, 1, uni, ln);
    for (const m of ['rabbit_collar', 'rabbit_placket'])
      part(f, m, 0, y + 0.74, 0, 1, 1, 1, trim, ln);
    part(f, 'rabbit_button', 0, y + 0.74, 0, 1, 1, 1, col('#FFFFFF'), ln);
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
  const shY = y + (A.armY || 0.94);
  // `armX`/`armLen`/`armW` for a smaller body; with `sleeve` the arm is fur
  // and a baked sleeve, hung from the same joint, swings with it
  const AX = (A.armX || 0.33) * big, AL = A.armLen || 0.34, AW = A.armW || 0.112;
  const AZ = A.armRz || 0.30;
  const armC = A.sleeve ? fur : uni;
  const sleeve = (s, rx) => {
    if (!A.sleeve) return;
    part(f, A.sleeve + '_sleeve', s * AX, shY, 0, 1, 1, 1, uni, rx, s * AZ);
    part(f, A.sleeve + '_cuff', s * AX, shY, 0, 1, 1, 1, trim, rx, s * AZ);
  };
  const slv = A.sleeve ? { sleeve: A.sleeve + '_sleeve', cuff: A.sleeve + '_cuff', c: uni, trim }
                       : undefined;
  let hl, hr;
  if (A.body) { hl = [x, y + 0.9, z]; hr = [x, y + 0.9, z]; }
  else if (p.handL || p.handR) {
    // reaching arms hang off narrower shoulders and get a longer bone pair, so
    // the front arm can cross the chest to the knob without rubber-banding
    const SH = 0.17 * big, BONE = 0.32;
    const [slx, slz] = L2W(f, -SH, 0);
    const [srx, srz] = L2W(f, SH, 0);
    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    const hand = p.gloveC ? col(p.gloveC) : paw;
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.075, armC,
              p.noPawL ? null : hand, slv)
      : (sleeve(-1, p.armL || 0), limb(f, -AX, shY, 0, p.armL || 0, -AZ, AL, AW, armC, paw, hs));
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.075, armC,
              p.noPawR ? null : hand, slv)
      : (sleeve(1, p.armR || 0), limb(f, AX, shY, 0, p.armR || 0, AZ, AL, AW, armC,
             p.noPawR ? null : paw, hs));
  } else {
    sleeve(-1, p.armL || 0); sleeve(1, p.armR || 0);
    hl = limb(f, -AX, shY, 0, p.armL || 0, -AZ, AL, AW, armC,
              p.noPawL ? null : paw, hs);
    hr = limb(f, AX, shY, 0, p.armR || 0, AZ, AL, AW, armC,
              p.noPawR ? null : paw, hs);
  }

  // head — may be turned independently of the body (a batter watching the
  // ball). The fish and the beetle have no neck to turn it on: taking the
  // batter's head turn left the beetle's cap twisted 90 degrees on his shell.
  const fh = p.headRy && !A.body ? yawFrame(x, z, ry + p.headRy) : f;
  // `headS` scales the whole head (skull, face patch, ears, cap) uniformly
  // about its centre, and `headUp` lifts that centre so the chin stays put:
  // the drawn face lands on the same spot of a bigger ball
  const HS = A.headS || 1;
  const hy = y + 1.34 + (A.headUp || 0);
  const HW = (A.hw || 1) * HS, HH = (A.hh || 1) * HS, HD = (A.hd || 1) * HS;
  const hzF = 0.32 * HD + 0.02;                 // where the front of the face is
  if (A.mesh) part(fh, A.mesh + '_head', 0, hy, 0, 1, 1, 1, fur);   // ears included
  else if (!A.body)
    part(fh, A.head || 'sphere', 0, hy, 0.02 * HS, 0.68 * big * HW, 0.66 * HH, 0.64 * big * HD, fur);

  if (A.patch) {                                // panda mask
    for (const s of [-1, 1])
      part(fh, 'sphere', s * 0.17, hy + 0.08, hzF - 0.07, 0.27, 0.29, 0.16, fur2);
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
    } else {
      part(fh, A.head === 'rbox' ? 'facepr' : 'facep', 0, hy, 0.02 * HS,
           0.68 * big * HW * k, 0.66 * HH * k, 0.64 * big * HD * k, fur);
    }
    R.decal(null);
  }

  if (A.mesh) {
    part(fh, A.mesh + '_muz', 0, hy, 0, 1, 1, 1, fur2);     // the pale mask
    if (!(A.lidHappy && p.face === EXPR.happy))
      part(fh, A.mesh + '_earin', 0, hy, 0, 1, 1, 1, A.earIn ? col(A.earIn) : fur2);
    if (FC && !FC.onHead && R.atlas && R.inkW === 0) {
      R.decal(faceRect(look.animal, p.face || 0, 1));
      part(fh, A.mesh + '_snout', 0, hy, 0, 1, 1, 1, fur);
      R.decal(null);
    }
  } else if (A.muz) {
    const mz = A.muz, my = hy + (A.muzY === undefined ? -0.09 : A.muzY);
    const mzz = A.muzZ === undefined ? 0.26 : A.muzZ;
    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], A.muzC ? col(A.muzC) : fur2);
    if (FC && !FC.onHead && R.atlas && R.inkW === 0) {   // nose and mouth, as art
      R.decal(faceRect(look.animal, p.face || 0, 1));
      part(fh, 'facep', 0, my, mzz, mz[0] * 1.03, mz[1] * 1.03, mz[2] * 1.03, fur);
      R.decal(null);
    }
  }
  // Every mammal has a face cell, so its eyes, nose and mouth are art on the
  // decals above rather than spheres; the fish and the beetle carry theirs in
  // the mesh.

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
    const exx = (A.earX || 0.148) * HS, eyy = (A.earY || 0.18) * HS;
    const tl = A.earTilt === undefined ? 0.13 : A.earTilt;
    // and they lean back when the legs are going. Driven by the pose, not by
    // `clock` — that lives in 50-main.js, which the face lab does not load.
    const back = Math.min(0.30, (Math.abs(p.legL || 0) + Math.abs(p.legR || 0)) * 0.16);
    const inC = A.earIn ? col(A.earIn) : fur2;
    // and they say what the face says: they splay and sag when he is down,
    // stand up straight when he is happy. His left one always leans a little
    // further out than the right — a toy that has been hugged.
    const fc = p.face || 0;
    const sag = fc === 3 ? 0.36 : fc === 2 ? -0.05 : 0;
    for (const s of [-1, 1]) {
      const lean = s > 0 ? 0.07 : 0, bk = back + (s > 0 ? 0.05 : 0) + Math.max(0, sag) * 0.6;
      const rz = -s * (tl + lean + sag);
      part(fh, 'rabbit_ear', s * exx, hy + eyy, -0.02 * HS, HS, HS, HS, fur, -bk, rz);
      part(fh, 'rabbit_earin', s * exx, hy + eyy, -0.02 * HS, HS, HS, HS, inC, -bk, rz);
    }
  }
  // tail
  if (A.tail === 'cotton')
    part(f, 'rabbit_tail', 0, y + (A.tailY || 0.66), A.tailZ || -0.30, 1, 1, 1, fur2);
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
    // Same two shells as the cap, a size up and with the bill squashed to a
    // stub — a helmet is a cap that swallowed the head, not a different
    // object. The crest used to be a free-standing box above the dome and
    // read as a chimney; it is sunk into the shell now.
    // `helm` ({s, y, z}) lets a species whose cap is a toy wear a real helmet
    const H = A.helm || {};
    const cy = (H.y !== undefined ? H.y : A.capY || 0) * HS, cs = (H.s || A.capS || 1) * HS;
    const cz = (H.z || 0) * HS;
    // `capSY` keeps a shrunk cap's bill thick enough for the outline
    const sy = A.capSY ? A.capSY * HS : cs, shy = hy + cy - 0.014 * sy;
    part(fh, 'cap_crown', 0, shy, cz, 1.055 * big * cs, 1.05 * sy, 1.055 * big * cs, cap);
    part(fh, 'cap_bill', 0, shy, cz, 1.06 * big * cs * (A.billW || 1), 1.05 * sy, (H.bill || 0.70) * big * cs, cap);
    // the flap covers the ear turned toward the pitcher (local +x)
    part(fh, 'sphere', 0.345 * big * cs, hy + 0.10 * cs + cy, 0.01 + cz,
         0.15 * cs, 0.34 * cs, 0.42 * cs, cap);
    part(fh, 'rbox', 0, hy + 0.462 * sy + cy, 0.012 * cs + cz,
         0.082 * cs, 0.112 * cs, 0.54 * cs, trim);
  } else {
    // Baked at full size, so the scale is 1 and `capS` is the only shrink.
    // A dome and a box read as a plate with a plank on it; the crown has a
    // lip and a shoulder, and the bill curves down its length and up across
    // its width so it is still a bill when seen edge-on.
    // `capZ` sets it back on the crown, `billW` narrows the bill
    // and `capT` rocks it back about the skull so the bill shows its top
    const cy = (A.capY || 0) * HS, cs = (A.capS || 1) * HS, cz = (A.capZ || 0) * HS;
    // `capSY` keeps a shrunk cap's bill thick enough for the outline: at half
    // size it fell under 2 x A.ink and went solid black
    const bw = A.billW || 1, ct = A.capT || 0, sy = A.capSY ? A.capSY * HS : cs;
    part(fh, 'cap_crown', 0, hy + cy, cz, big * cs, sy, big * cs, cap, ct);
    part(fh, 'cap_bill', 0, hy + cy, cz, big * cs * bw, sy, big * cs, cap, ct);
    const by = 0.492 * sy, bz = 0.012 * cs;
    part(fh, 'sphere', 0, hy + cy + by * Math.cos(ct) - bz * Math.sin(ct),
         cz + by * Math.sin(ct) + bz * Math.cos(ct),
         0.082 * cs, 0.082 * cs, 0.082 * cs, trim);
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
  // a pinstripe on cream, as in the sketch — and a brown bear in a brown
  // jersey was one blob from the outfield
  { id: 'bears',    name: 'もりのクマーズ',   animal: 'bear',    uni: '#EFE6D2', trim: '#4E2F1C', cap: '#4E2F1C',
    pin: '#6E4A30',
    tag: 'POWER',   desc: 'とにかく長打。当たれば飛ぶが、確実性は低め。', pow: 5, con: 2, spd: 2, def: 3 },
  { id: 'rabbits',  name: 'はらっぱラビッツ', animal: 'rabbit',  uni: '#E8EDF2', trim: '#E86A8A', cap: '#D9527A',
    tag: 'SPEED',   desc: '足が速い。内野安打も盗塁もお手のもの。', pow: 2, con: 4, spd: 5, def: 4 },
  { id: 'salmons',  name: 'そじょうサーモンズ', animal: 'salmon', uni: '#2F5C7A', trim: '#F0B9A8', cap: '#22455C',
    tag: 'CONTACT', desc: 'バットは持たないが、当てるのはうまい。四球も選ぶ。', pow: 3, con: 5, spd: 3, def: 3 },
  // a cream jersey with deep green trim: a green frog in a green jersey was
  // one green blob from the outfield
  { id: 'frogs',    name: 'ぬまたフロッグス', animal: 'frog',    uni: '#F3E9B8', trim: '#2F6B3B', cap: '#2F6B3B',
    tag: 'BALANCE', desc: 'すべてが平均的。クセがなく扱いやすい。', pow: 3, con: 3, spd: 3, def: 3 },
  // ice blue with navy trim: a navy jersey on a navy bird was one dark lump
  { id: 'penguins', name: 'こおりやまペンギンズ', animal: 'penguin', uni: '#BFE0EE', trim: '#22395A', cap: '#BFE0EE',
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
      look: { animal: def.animal, uni: def.uni, trim: def.trim, cap: def.cap, pin: def.pin },
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
