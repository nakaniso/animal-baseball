/* 造形ラボ — contact sheet of one animal from several angles. Dev tool only. */
var clock = 0;
var SWING_LAG = 0.09;

const glc = document.getElementById('gl');
const sheet = document.getElementById('sheet');
const sctx = sheet.getContext('2d');

const LOOKS = {};
TEAMS.forEach((t) => { LOOKS[t.animal] = t; });
// species that no longer field a team still need to be viewable
for (const name in ANIMALS)
  if (!LOOKS[name]) LOOKS[name] = { animal: name, uni: '#E8EDF2', trim: '#8899AA', cap: '#5A6B7C' };

const ENV = { light: [0.35, 1, 0.28], skyTint: '#EAF2FA', gndTint: '#C9D2DC',
              fog: '#F2F4F6', fogDist: 4000 };

const POSE_IDLE = { armL: 0.12, armR: -0.12, legL: 0, legR: 0, lean: 0, bob: 0 };

function view(name, opt) {
  // `fr` is the half-height of what the frame covers, in metres: that, not
  // `dist`, is what zooms — dist only changes the perspective
  return Object.assign({ label: name, ry: Math.PI, dist: 3.4, ty: 0.85,
                         ey: 0.95, fr: 1.15, pose: POSE_IDLE }, opt || {});
}

const SETS = {
  a: [
    view('正面 front',    { ry: Math.PI }),
    view('斜め 3/4',      { ry: Math.PI * 0.72 }),
    view('横 side',       { ry: Math.PI * 0.5 }),
    view('背面 back',     { ry: 0 }),
  ],
  b: [
    view('真上 top',      { ry: Math.PI, ey: 3.2, ty: 0.7, dist: 1.7 }),
    view('低い 正面 low', { ry: Math.PI, ey: 0.28, ty: 0.72, dist: 3.0 }),
    view('走り run',      { ry: Math.PI * 0.78,
                            pose: { legL: 0.8, legR: -0.8, bob: 0.05, lean: 0.12 } }),
    view('走り 正面',     { ry: Math.PI,
                            pose: { legL: -0.6, legR: 0.6, bob: 0.03 } }),
  ],
  // the head on its own, which is where the face and the muzzle have to hold up
  c: [
    view('顔 face',       { ry: Math.PI, dist: 2.2, fr: 0.52, ty: 1.36, ey: 1.38 }),
    view('顔 3/4',        { ry: Math.PI * 0.74, dist: 2.2, fr: 0.52, ty: 1.36, ey: 1.38 }),
    view('顔 横',         { ry: Math.PI * 0.5, dist: 2.2, fr: 0.52, ty: 1.36, ey: 1.38 }),
    view('顔 後ろ斜め',   { ry: Math.PI * 0.26, dist: 2.2, fr: 0.52, ty: 1.36, ey: 1.44 }),
  ],
  // what the kit and the silhouette do when the body is turned or knocked over
  d: [
    view('打席 bat',      { ry: Math.PI * 0.62,
                            pose: { face: 1, lean: -0.12, spread: 0.10,
                                    armL: -0.9, armR: -1.1 } }),
    view('万歳 cheer',    { ry: Math.PI,
                            pose: { armL: -2.4, armR: -2.4, bob: 0.12, face: 2 } }),
    view('転倒 fall',     { ry: Math.PI * 0.7, pose: { fall: 1.35, face: 3 } }),
    view('帽子なし',      { ry: Math.PI * 0.76, pose: { noHat: 1 } }),
  ],
  // the beetle's own two: the horn is his whole identity and the front legs
  // are the pair that digs, so both get framed on their own
  e: [
    view('角 正面',       { ry: Math.PI, dist: 2.4, fr: 0.42, ty: 1.20, ey: 1.22 }),
    view('角 3/4',        { ry: Math.PI * 0.74, dist: 2.4, fr: 0.42, ty: 1.20, ey: 1.26 }),
    view('前脚 正面',     { ry: Math.PI, dist: 2.4, fr: 0.36, ty: 0.36, ey: 0.44 }),
    view('前脚 3/4',      { ry: Math.PI * 0.78, dist: 2.4, fr: 0.36, ty: 0.36, ey: 0.44 }),
  ],
  // headwear, which is shared by every species and so is easy to leave alone:
  // the cap and the helmet framed on their own, both from a camera low enough
  // to catch a bill hanging over the eyes
  f: [
    view('帽子 正面',     { ry: Math.PI, dist: 2.3, fr: 0.50, ty: 1.44, ey: 1.10 }),
    view('帽子 3/4',      { ry: Math.PI * 0.74, dist: 2.3, fr: 0.50, ty: 1.44, ey: 1.30 }),
    view('ヘル 正面',     { ry: Math.PI, dist: 2.3, fr: 0.50, ty: 1.44, ey: 1.10,
                            pose: { helmet: 1 } }),
    view('ヘル 3/4',      { ry: Math.PI * 0.74, dist: 2.3, fr: 0.50, ty: 1.44, ey: 1.30,
                            pose: { helmet: 1 } }),
  ],
};
let VIEWS = SETS.a;

const COLS = 2, TW = 520, TH = 520;

function renderAll(animal) {
  sheet.width = COLS * TW;
  sheet.height = Math.ceil(VIEWS.length / COLS) * TH;
  sctx.fillStyle = '#F2F4F6';
  sctx.fillRect(0, 0, sheet.width, sheet.height);
  VIEWS.forEach((v, i) => {
    const d = v.dist;
    const fov = 2 * Math.atan(v.fr / d) * 180 / Math.PI;
    R.begin({ ex: 0, ey: v.ey, ez: -d, tx: 0, ty: v.ty, tz: 0, fov: fov }, ENV);
    drawAnimal(0, 0, v.ry, LOOKS[animal], v.pose, 0);
    const x = (i % COLS) * TW, y = Math.floor(i / COLS) * TH;
    sctx.drawImage(glc, x, y, TW, TH);
    sctx.fillStyle = '#11202C';
    sctx.font = 'bold 17px system-ui,sans-serif';
    sctx.fillText(v.label, x + 12, y + 26);
    sctx.strokeStyle = '#C3CCD4';
    sctx.strokeRect(x + 0.5, y + 0.5, TW - 1, TH - 1);
  });
  const err = R.gl.getError();
  document.getElementById('info').textContent =
    'verts ' + (GEO.pos.length / 3) + '  glError ' + err;
}

if (!R.init(glc)) {
  document.body.innerHTML = '<p>WebGL unavailable</p>';
} else {
  R.upload(buildFaceAtlas());
  const q = new URLSearchParams(location.search);
  const animal = q.get('a') || window.LAB_ANIMAL || 'bear';
  VIEWS = SETS[q.get('v') || window.LAB_SET || 'a'] || SETS.a;
  R.resize();
  requestAnimationFrame(() => { renderAll(animal); });
  // so the page can be re-driven from the console without a reload
  window.LAB = (a, v) => { VIEWS = SETS[v || 'a'] || SETS.a; renderAll(a || animal); };
}
