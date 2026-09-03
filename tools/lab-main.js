/* ============================================================
   顔ラボ — scanned line art into a face cell, previewed in 3D.
   A development tool; none of this ships in the game.
   ============================================================ */
const $$ = (s) => document.querySelector(s);
const UI = {};
for (const id of ['file', 'drop', 'animal', 'part', 'expr', 'thr', 'soft', 'ink', 'keep',
                  'scale', 'x', 'y', 'rot', 'emit', 'out', 'copy', 'mode', 'spin', 'dist'])
  UI[id] = $$('#' + id);

let srcImg = null;          // the loaded scan
let atlas = null;           // the canvas uploaded to the GPU
let dirty = true;

FACE_ORDER.forEach((name) => {
  const o = document.createElement('option');
  o.value = name; o.textContent = name;
  UI.animal.appendChild(o);
});
UI.animal.value = 'rabbit';

/* ---------- loading ---------- */
function loadFile(f) {
  if (!f || !/^image\//.test(f.type)) return;
  const fr = new FileReader();
  fr.onload = () => {
    const img = new Image();
    img.onload = () => { srcImg = img; fitToCell(); dirty = true; };
    img.src = fr.result;
  };
  fr.readAsDataURL(f);
}
UI.file.onchange = (e) => loadFile(e.target.files[0]);
for (const ev of ['dragenter', 'dragover']) {
  document.addEventListener(ev, (e) => { e.preventDefault(); UI.drop.classList.add('hot'); });
}
for (const ev of ['dragleave', 'drop']) {
  document.addEventListener(ev, (e) => { e.preventDefault(); UI.drop.classList.remove('hot'); });
}
document.addEventListener('drop', (e) => loadFile(e.dataTransfer.files[0]));
UI.drop.onclick = () => UI.file.click();

/* a fresh image starts filling the cell, so there is something to see at once */
function fitToCell() { UI.scale.value = 1; UI.x.value = 0; UI.y.value = 0; UI.rot.value = 0; }

/* ---------- baking one cell ---------- */
function opts() {
  return {
    thr: +UI.thr.value, soft: +UI.soft.value, ink: UI.ink.value, keep: UI.keep.value === '1',
    scale: +UI.scale.value, x: +UI.x.value, y: +UI.y.value, rot: +UI.rot.value,
  };
}

function hexRGB(h) {
  return [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
}

/* Paper becomes transparent and the pencil becomes ink: alpha is driven by how
   dark the pixel is, between `thr` (paper, gone) and `thr - soft` (line, solid). */
function bakeCell(img, o) {
  const S = FACE_PX, cv = document.createElement('canvas');
  cv.width = cv.height = S;
  const g = cv.getContext('2d', { willReadFrequently: true });
  if (!img) return cv;

  const sc = o.scale * S / Math.max(img.width, img.height);
  g.save();
  g.translate(S / 2 + o.x * S, S / 2 + o.y * S);
  g.rotate(o.rot);
  g.drawImage(img, -img.width * sc / 2, -img.height * sc / 2, img.width * sc, img.height * sc);
  g.restore();

  const d = g.getImageData(0, 0, S, S), p = d.data;
  const hi = o.thr, lo = Math.max(0, o.thr - o.soft), span = Math.max(1e-4, hi - lo);
  const ink = hexRGB(o.ink);
  for (let i = 0; i < p.length; i += 4) {
    if (p[i + 3] === 0) continue;               // never drawn on — leave it clear
    const L = (p[i] * 0.299 + p[i + 1] * 0.587 + p[i + 2] * 0.114) / 255;
    const a = Math.max(0, Math.min(1, 1 - (L - lo) / span));
    if (!o.keep) { p[i] = ink[0]; p[i + 1] = ink[1]; p[i + 2] = ink[2]; }
    p[i + 3] = Math.round(a * 255 * (p[i + 3] / 255));
  }
  g.putImageData(d, 0, 0);
  return cv;
}

/* ---------- the atlas the preview renders with ---------- */
function cellIndex() { return +UI.part.value + +UI.expr.value; }

function rebuild() {
  refreshLabels();
  atlas = buildFaceAtlas();
  const S = FACE_PX, row = FACE_ORDER.indexOf(UI.animal.value), col = cellIndex();
  const proc = document.createElement('canvas');
  proc.width = proc.height = S;
  proc.getContext('2d').drawImage(atlas, col * S, row * S, S, S, 0, 0, S, S);

  const baked = bakeCell(srcImg, opts());
  if (UI.mode.value === 'scan' && srcImg) {
    const g = atlas.getContext('2d');
    g.clearRect(col * S, row * S, S, S);
    g.drawImage(baked, col * S, row * S);
  }
  R.upload(atlas);

  // the three thumbnails under the viewport
  const put = (id, from) => {
    const c = $$('#' + id), g2 = c.getContext('2d');
    g2.clearRect(0, 0, S, S);
    if (from) g2.drawImage(from, 0, 0, S, S);
  };
  put('baked', baked);
  put('proc', proc);
  const sc2 = $$('#src').getContext('2d');
  sc2.clearRect(0, 0, S, S);
  if (srcImg) {
    const k = Math.min(S / srcImg.width, S / srcImg.height);
    sc2.drawImage(srcImg, (S - srcImg.width * k) / 2, (S - srcImg.height * k) / 2,
                  srcImg.width * k, srcImg.height * k);
  }
}

/* ---------- 3D preview ---------- */
let yaw = Math.PI, spinning = true, drag = null;
const view = $$('#view');
view.addEventListener('pointerdown', (e) => { drag = e.clientX; view.setPointerCapture(e.pointerId); });
view.addEventListener('pointermove', (e) => {
  if (drag === null) return;
  yaw -= (e.clientX - drag) * 0.011; drag = e.clientX;
});
view.addEventListener('pointerup', () => { drag = null; });

const LOOK = {};
FACE_ORDER.forEach((a) => {
  const t = TEAMS.filter((x) => x.animal === a)[0];
  LOOK[a] = t || { animal: a, uni: '#E8EDF2', trim: '#8899AA', cap: '#5A6B7C' };
});

function frame() {
  if (dirty) { rebuild(); dirty = false; }
  spinning = UI.spin.value === '1';
  if (spinning && drag === null) yaw += 0.004;

  const d = +UI.dist.value;
  // frame head and shoulders the same at every distance, so the only thing
  // that changes is how many pixels the face actually gets
  const fov = 2 * Math.atan(0.80 / d) * 180 / Math.PI;
  R.begin({ ex: 0, ey: 1.52, ez: -d, tx: 0, ty: 1.52, tz: 0, fov: fov },
    { light: [0.35, 1, 0.28], skyTint: '#EAF2FA', gndTint: '#C9D2DC',
      fog: '#111820', fogDist: 4000 });
  drawAnimal(0, 0, yaw, LOOK[UI.animal.value], { face: +UI.expr.value }, 0);
  requestAnimationFrame(frame);
}

/* ---------- output ---------- */
UI.emit.onclick = () => {
  if (!srcImg) { UI.out.value = '// 先に画像を読み込んでください'; return; }
  const url = bakeCell(srcImg, opts()).toDataURL('image/png');
  const key = UI.animal.value + ':' + cellIndex();
  const kb = Math.round(url.length * 0.75 / 1024);
  UI.out.value = "  '" + key + "': '" + url + "',   // " + kb + 'KB';
};
UI.copy.onclick = () => { UI.out.select(); document.execCommand('copy'); };

/* ---------- wiring ---------- */
const SHOW = { thr: 2, soft: 2, scale: 2, x: 3, y: 3, rot: 3 };
function refreshLabels() {
  for (const k in SHOW) $$('#v-' + k).textContent = (+UI[k].value).toFixed(SHOW[k]);
}
for (const id of ['animal', 'part', 'expr', 'thr', 'soft', 'ink', 'keep',
                  'scale', 'x', 'y', 'rot', 'mode']) {
  UI[id].addEventListener('input', () => { refreshLabels(); dirty = true; });
}
refreshLabels();

if (!R.init($$('#gl'))) {
  document.body.innerHTML = '<p style="padding:40px">WebGLが使えません。</p>';
} else {
  addEventListener('resize', () => R.resize());
  requestAnimationFrame(frame);
}
