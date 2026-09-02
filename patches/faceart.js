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
  rabbit:  { eye: 'dot',    eyeX: 0.185, eyeY: 0.345, eyeR: 0.062,
             nose: 'dot',   noseC: '#4A3438', noseY: 0.290, noseR: 0.115, mouth: 'w',
             mouthC: '#4A3438', mouthY: 0.560, mouthW: 0.230 },
  cat:     { eye: 'almond', eyeX: 0.205, eyeY: 0.355, eyeR: 0.092, tilt: 0.16, whisk: '#B0895A',
             nose: 'tri',   noseC: '#C2705E', noseY: 0.295, noseR: 0.140, mouth: 'w' },
  frog:    { eye: 'none',   headMouth: 'wide', mouthC: '#3E6B33' },
  penguin: { eye: 'bead',   eyeX: 0.170, eyeY: 0.360, eyeR: 0.058 },
  fox:     { eye: 'almond', eyeX: 0.205, eyeY: 0.350, eyeR: 0.084, tilt: 0.20,
             nose: 'tri',   noseC: '#3C2A20', noseY: 0.285, noseR: 0.135, mouth: 'w' },
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

function drawMuzCell(g, F, exp) {
  if (!F.nose) return;
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

/* uv rect for one cell: [scaleU, scaleV, offsetU, offsetV] */
function faceRect(animal, exp, muz) {
  const row = FACE_ORDER.indexOf(animal);
  if (row < 0) return null;
  const col = (exp || 0) + (muz ? 4 : 0), k = 1 / FACE_N;
  return [k, k, col * k, row * k];
}
