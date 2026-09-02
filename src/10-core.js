/* ============================================================
   10-core.js — math, tiny WebGL cel-shaded renderer, audio
   No external libraries: everything below is hand-rolled.
   ============================================================ */
'use strict';

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const rnd = (a, b) => a + Math.random() * (b - a);
const rint = (a, b) => Math.floor(a + Math.random() * (b - a + 1));
const pick = (a) => a[Math.floor(Math.random() * a.length)];
const chance = (p) => Math.random() < p;
const DEG = Math.PI / 180;
const dist2 = (ax, az, bx, bz) => Math.hypot(ax - bx, az - bz);

/* ---------- 4x4 matrices (column-major, WebGL order) ---------- */
function m4() { return new Float32Array(16); }

function mMul(o, a, b) {
  for (let c = 0; c < 4; c++) {
    const b0 = b[c * 4], b1 = b[c * 4 + 1], b2 = b[c * 4 + 2], b3 = b[c * 4 + 3];
    o[c * 4]     = a[0] * b0 + a[4] * b1 + a[8]  * b2 + a[12] * b3;
    o[c * 4 + 1] = a[1] * b0 + a[5] * b1 + a[9]  * b2 + a[13] * b3;
    o[c * 4 + 2] = a[2] * b0 + a[6] * b1 + a[10] * b2 + a[14] * b3;
    o[c * 4 + 3] = a[3] * b0 + a[7] * b1 + a[11] * b2 + a[15] * b3;
  }
  return o;
}

function mPerspective(o, fovy, aspect, near, far) {
  const f = 1 / Math.tan(fovy / 2), nf = 1 / (near - far);
  o.fill(0);
  o[0] = f / aspect; o[5] = f; o[10] = (far + near) * nf;
  o[11] = -1; o[14] = 2 * far * near * nf;
  return o;
}

function mLookAt(o, ex, ey, ez, cx, cy, cz) {
  let zx = ex - cx, zy = ey - cy, zz = ez - cz;
  let l = Math.hypot(zx, zy, zz) || 1; zx /= l; zy /= l; zz /= l;
  // x = normalize(cross(up, z)) with up = (0,1,0)
  let xx = zz, xy = 0, xz = -zx;
  l = Math.hypot(xx, xy, xz);
  if (l < 1e-5) { xx = 1; xy = 0; xz = 0; } else { xx /= l; xy /= l; xz /= l; }
  const yx = zy * xz - zz * xy, yy = zz * xx - zx * xz, yz = zx * xy - zy * xx;
  o[0] = xx; o[1] = yx; o[2] = zx; o[3] = 0;
  o[4] = xy; o[5] = yy; o[6] = zy; o[7] = 0;
  o[8] = xz; o[9] = yz; o[10] = zz; o[11] = 0;
  o[12] = -(xx * ex + xy * ey + xz * ez);
  o[13] = -(yx * ex + yy * ey + yz * ez);
  o[14] = -(zx * ex + zy * ey + zz * ez);
  o[15] = 1;
  return o;
}

/* model matrix from translate / euler(Y*X*Z) / scale */
function mTRS(o, px, py, pz, rx, ry, rz, sx, sy, sz) {
  const cx = Math.cos(rx), snx = Math.sin(rx);
  const cy = Math.cos(ry), sny = Math.sin(ry);
  const cz = Math.cos(rz), snz = Math.sin(rz);
  const r00 = cy * cz + sny * snx * snz, r01 = -cy * snz + sny * snx * cz, r02 = sny * cx;
  const r10 = cx * snz,                  r11 = cx * cz,                    r12 = -snx;
  const r20 = -sny * cz + cy * snx * snz, r21 = sny * snz + cy * snx * cz, r22 = cy * cx;
  o[0] = r00 * sx; o[1] = r10 * sx; o[2] = r20 * sx; o[3] = 0;
  o[4] = r01 * sy; o[5] = r11 * sy; o[6] = r21 * sy; o[7] = 0;
  o[8] = r02 * sz; o[9] = r12 * sz; o[10] = r22 * sz; o[11] = 0;
  o[12] = px; o[13] = py; o[14] = pz; o[15] = 1;
  return o;
}

/* ---------- colors ---------- */
const _colCache = new Map();
function col(hex) {
  let c = _colCache.get(hex);
  if (c) return c;
  const n = parseInt(hex.slice(1), 16);
  c = [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
  _colCache.set(hex, c);
  return c;
}
function shade(hex, k) { // k<1 darker, k>1 lighter
  const c = col(hex);
  return [clamp(c[0] * k, 0, 1), clamp(c[1] * k, 0, 1), clamp(c[2] * k, 0, 1)];
}

/* ============================================================
   Geometry — a handful of primitives packed into one buffer
   ============================================================ */
const GEO = { pos: [], nor: [], uv: [], idx: [], parts: {} };

function geoPart(name, build) {
  const start = GEO.idx.length, base = GEO.pos.length / 3;
  build((x, y, z, nx, ny, nz, u, w) => {
    GEO.pos.push(x, y, z); GEO.nor.push(nx, ny, nz);
    GEO.uv.push(u || 0, w || 0);
    return GEO.pos.length / 3 - 1 - base;
  }, (a, b, c) => GEO.idx.push(base + a, base + b, base + c));
  GEO.parts[name] = { offset: start * 2, count: GEO.idx.length - start };
}

geoPart('box', (v, t) => {
  const F = [
    [[ .5, -.5, .5], [ .5, .5, .5], [-.5, .5, .5], [-.5, -.5, .5], [0, 0, 1]],
    [[-.5, -.5, -.5], [-.5, .5, -.5], [ .5, .5, -.5], [ .5, -.5, -.5], [0, 0, -1]],
    [[ .5, -.5, -.5], [ .5, .5, -.5], [ .5, .5, .5], [ .5, -.5, .5], [1, 0, 0]],
    [[-.5, -.5, .5], [-.5, .5, .5], [-.5, .5, -.5], [-.5, -.5, -.5], [-1, 0, 0]],
    [[-.5, .5, .5], [ .5, .5, .5], [ .5, .5, -.5], [-.5, .5, -.5], [0, 1, 0]],
    [[-.5, -.5, -.5], [ .5, -.5, -.5], [ .5, -.5, .5], [-.5, -.5, .5], [0, -1, 0]],
  ];
  let i = 0;
  for (const f of F) {
    const n = f[4];
    for (let k = 0; k < 4; k++) v(f[k][0], f[k][1], f[k][2], n[0], n[1], n[2]);
    t(i, i + 1, i + 2); t(i, i + 2, i + 3); i += 4;
  }
});

geoPart('sphere', (v, t) => {
  const RN = 16, SN = 24;
  for (let r = 0; r <= RN; r++) {
    const phi = (r / RN) * Math.PI, sp = Math.sin(phi), cp = Math.cos(phi);
    for (let s = 0; s <= SN; s++) {
      const th = (s / SN) * Math.PI * 2;
      const x = sp * Math.cos(th), y = cp, z = sp * Math.sin(th);
      v(x * .5, y * .5, z * .5, x, y, z);
    }
  }
  for (let r = 0; r < RN; r++) for (let s = 0; s < SN; s++) {
    const a = r * (SN + 1) + s, b = a + SN + 1;
    t(a, a + 1, b); t(a + 1, b + 1, b);   // wound outward
  }
});

function tube(v, t, rTop, rBot, capped) {
  const N = 24;
  let i = 0;
  for (let s = 0; s <= N; s++) {
    const th = (s / N) * Math.PI * 2, cx = Math.cos(th), sz = Math.sin(th);
    v(cx * rTop, .5, sz * rTop, cx, .35, sz);
    v(cx * rBot, -.5, sz * rBot, cx, .35, sz);
  }
  for (let s = 0; s < N; s++) { const a = s * 2; t(a, a + 2, a + 1); t(a + 1, a + 2, a + 3); }
  i = (N + 1) * 2;
  if (capped) {
    for (const [y, r, ny] of [[.5, rTop, 1], [-.5, rBot, -1]]) {
      if (r <= 0) continue;
      const c = i; v(0, y, 0, 0, ny, 0); i++;
      for (let s = 0; s <= N; s++) {
        const th = (s / N) * Math.PI * 2;
        v(Math.cos(th) * r, y, Math.sin(th) * r, 0, ny, 0); i++;
      }
      for (let s = 0; s < N; s++) {
        if (ny > 0) t(c, c + 2 + s, c + 1 + s); else t(c, c + 1 + s, c + 2 + s);
      }
    }
  }
}
geoPart('cyl',  (v, t) => tube(v, t, .5, .5, true));
geoPart('cone', (v, t) => tube(v, t, .001, .5, true));
geoPart('taper',(v, t) => tube(v, t, .26, .5, true));

geoPart('disc', (v, t) => {
  const N = 32;
  v(0, 0, 0, 0, 1, 0);
  for (let s = 0; s <= N; s++) {
    const th = (s / N) * Math.PI * 2;
    v(Math.cos(th) * .5, 0, Math.sin(th) * .5, 0, 1, 0);
  }
  // wound so the face points +y — otherwise every disc is back-face culled
  for (let s = 0; s < N; s++) t(0, s + 2, s + 1);
});

geoPart('quad', (v, t) => {
  v(-.5, 0, -.5, 0, 1, 0); v(.5, 0, -.5, 0, 1, 0);
  v(.5, 0, .5, 0, 1, 0); v(-.5, 0, .5, 0, 1, 0);
  t(0, 2, 1); t(0, 3, 2);
});

/* Rounded box — a superellipsoid with |x|^4+|y|^4+|z|^4 = 1. Heads drawn as a
   soft square read far more like a drawn character than a plain sphere does. */
geoPart('rbox', (v, t) => {
  const RN = 16, SN = 24, e = 0.5;
  const pw = (a, k) => (a < 0 ? -Math.pow(-a, k) : Math.pow(a, k));
  for (let r = 0; r <= RN; r++) {
    const phi = (r / RN) * Math.PI, sp = Math.sin(phi), cp = Math.cos(phi);
    for (let s = 0; s <= SN; s++) {
      const th = (s / SN) * Math.PI * 2;
      const x = pw(sp, e) * pw(Math.cos(th), e);
      const y = pw(cp, e);
      const z = pw(sp, e) * pw(Math.sin(th), e);
      const nx = x * x * x, ny = y * y * y, nz = z * z * z;
      const l = Math.hypot(nx, ny, nz) || 1;
      v(x * 0.5, y * 0.5, z * 0.5, nx / l, ny / l, nz / l);
    }
  }
  for (let r = 0; r < RN; r++) for (let s = 0; s < SN; s++) {
    const a = r * (SN + 1) + s, b = a + SN + 1;
    t(a, a + 1, b); t(a + 1, b + 1, b);   // wound outward
  }
});

/* extruded polygon: pts are [x,z] wound counter-clockwise seen from above,
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

/* A patch of the unit sphere with uv across it. Scaled with the same numbers
   as the head it sits on, it lies exactly on that surface, so a face drawn
   into a texture wraps instead of floating. u runs from the character's own
   -x to +x, which is left-to-right as the reader sees the face. */
const FACE_AZ = 60 * DEG, FACE_EL = 50 * DEG;
geoPart('facep', (v, t) => {
  const N = 16, M = 16;
  for (let i = 0; i <= M; i++) {
    const el = ((i / M) * 2 - 1) * FACE_EL, ce = Math.cos(el), se = Math.sin(el);
    for (let j = 0; j <= N; j++) {
      const az = ((j / N) * 2 - 1) * FACE_AZ;
      const x = ce * Math.sin(az), y = se, z = ce * Math.cos(az);
      v(x * .5, y * .5, z * .5, x, y, z, j / N, 1 - i / M);
    }
  }
  for (let i = 0; i < M; i++) for (let j = 0; j < N; j++) {
    const a = i * (N + 1) + j, b = a + N + 1;
    t(a, a + 1, b); t(a + 1, b + 1, b);   // wound outward
  }
});

/* the same patch on the |x|^4+|y|^4+|z|^4 = 1 head. A sphere patch scaled to
   an rbox head sinks ~0.02m inside it away from the centre and the face gets
   buried, so the surface has to be the one it is actually sitting on. */
geoPart('facepr', (v, t) => {
  const N = 16, M = 16;
  for (let i = 0; i <= M; i++) {
    const el = ((i / M) * 2 - 1) * FACE_EL, ce = Math.cos(el), se = Math.sin(el);
    for (let j = 0; j <= N; j++) {
      const az = ((j / N) * 2 - 1) * FACE_AZ;
      const dx = ce * Math.sin(az), dy = se, dz = ce * Math.cos(az);
      const k = 1 / Math.pow(dx * dx * dx * dx + dy * dy * dy * dy + dz * dz * dz * dz, 0.25);
      const x = dx * k, y = dy * k, z = dz * k;
      const nx = x * x * x, ny = y * y * y, nz = z * z * z;
      const l = Math.hypot(nx, ny, nz) || 1;
      v(x * .5, y * .5, z * .5, nx / l, ny / l, nz / l, j / N, 1 - i / M);
    }
  }
  for (let i = 0; i < M; i++) for (let j = 0; j < N; j++) {
    const a = i * (N + 1) + j, b = a + N + 1;
    t(a, a + 1, b); t(a + 1, b + 1, b);   // wound outward
  }
});

/* half sphere (dome) — caps, hats, hills */
geoPart('dome', (v, t) => {
  const RN = 9, SN = 24;
  for (let r = 0; r <= RN; r++) {
    const phi = (r / RN) * (Math.PI / 2), sp = Math.sin(phi), cp = Math.cos(phi);
    for (let s = 0; s <= SN; s++) {
      const th = (s / SN) * Math.PI * 2;
      const x = sp * Math.cos(th), y = cp, z = sp * Math.sin(th);
      v(x * .5, y * .5, z * .5, x, y, z);
    }
  }
  for (let r = 0; r < RN; r++) for (let s = 0; s < SN; s++) {
    const a = r * (SN + 1) + s, b = a + SN + 1;
    t(a, a + 1, b); t(a + 1, b + 1, b);   // wound outward
  }
});

/* ============================================================
   Renderer
   ============================================================ */
const VS = `
attribute vec3 aPos; attribute vec3 aNor; attribute vec2 aUV;
uniform mat4 uVP, uM;
uniform float uOutline;
uniform vec3 uCam;
uniform vec4 uUVRect;
varying vec3 vN, vW;
varying vec2 vUV;
void main(){
  vUV = aUV * uUVRect.xy + uUVRect.zw;
  vec4 w = uM * vec4(aPos,1.0);
  vec3 n = (uM * vec4(aNor,0.0)).xyz;
  float l = length(n);
  vN = n;
  // Inverted hull: push the shell out along the world normal, draw back faces.
  // The push is in metres, so it has to grow with distance or the line weight
  // is ~10x heavier on the batter (10m) than on a right fielder (100m).
  // uOutline is tuned at INK_REF; the clamp stops close-ups from going to
  // hairlines and distant players from turning into ink blobs.
  if (uOutline > 0.0 && l > 0.0001) {
    float k = clamp(distance(uCam, w.xyz) / 11.0, 0.30, 3.6);
    w.xyz += (n / l) * uOutline * k;
  }
  vW = w.xyz;
  gl_Position = uVP * w;
}`;

const FS = `
precision mediump float;
varying vec3 vN, vW;
varying vec2 vUV;
uniform vec3 uColor, uLight, uSky, uGnd, uFog, uEye;
uniform float uFogD, uUnlit, uAlpha, uUseTex;
uniform sampler2D uTex;
void main(){
  vec3 base = uColor;
  float a = uAlpha;
  if (uUseTex > 0.5) {
    vec4 t = texture2D(uTex, vUV);
    if (t.a < 0.02) discard;          // the blank part of a face cell
    base = t.rgb; a = t.a * uAlpha;
  }
  if (uUnlit > 0.5) { gl_FragColor = vec4(base, a); return; }
  vec3 n = normalize(vN);
  float d = dot(n, uLight);
  // three soft cel bands keeps forms readable without looking flat
  float s = smoothstep(-0.35, -0.05, d) * 0.22
          + smoothstep(0.10, 0.30, d) * 0.30
          + smoothstep(0.55, 0.75, d) * 0.22 + 0.52;
  vec3 hemi = mix(uGnd, uSky, n.y * 0.5 + 0.5);
  vec3 c = base * s * (0.80 + 0.42 * hemi);
  float f = clamp(length(vW - uEye) / uFogD, 0.0, 1.0);
  c = mix(c, uFog, f * f * 0.85);
  gl_FragColor = vec4(c, a);
}`;

const R = {
  gl: null, prog: null, u: {}, vp: m4(), _m: m4(), _t: m4(),
  eye: [0, 0, 0], w: 1, h: 1, dpr: 1, inkW: 0,

  init(canvas) {
    const gl = canvas.getContext('webgl', { antialias: true, alpha: false });
    if (!gl) return false;
    this.gl = gl; this.canvas = canvas;
    const mk = (type, src) => {
      const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) console.error(gl.getShaderInfoLog(s));
      return s;
    };
    const p = gl.createProgram();
    gl.attachShader(p, mk(gl.VERTEX_SHADER, VS));
    gl.attachShader(p, mk(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) {
      console.error('shader link failed: ' + gl.getProgramInfoLog(p));
      return false;
    }
    gl.useProgram(p);
    this.prog = p;
    for (const n of ['uVP', 'uM', 'uColor', 'uLight', 'uSky', 'uGnd', 'uFog', 'uEye', 'uFogD', 'uUnlit', 'uAlpha', 'uOutline', 'uCam', 'uUseTex', 'uUVRect', 'uTex'])
      this.u[n] = gl.getUniformLocation(p, n);

    const vb = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vb);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(GEO.pos), gl.STATIC_DRAW);
    const ap = gl.getAttribLocation(p, 'aPos');
    gl.enableVertexAttribArray(ap); gl.vertexAttribPointer(ap, 3, gl.FLOAT, false, 0, 0);

    const nb = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, nb);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(GEO.nor), gl.STATIC_DRAW);
    const an = gl.getAttribLocation(p, 'aNor');
    gl.enableVertexAttribArray(an); gl.vertexAttribPointer(an, 3, gl.FLOAT, false, 0, 0);

    const ub = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, ub);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(GEO.uv), gl.STATIC_DRAW);
    const au = gl.getAttribLocation(p, 'aUV');
    gl.enableVertexAttribArray(au); gl.vertexAttribPointer(au, 2, gl.FLOAT, false, 0, 0);

    const ib = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(GEO.idx), gl.STATIC_DRAW);

    // unit 0 always holds a valid texture, so sampling is defined even on the
    // draws that ignore it
    this.tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE,
                  new Uint8Array([0, 0, 0, 0]));
    gl.activeTexture(gl.TEXTURE0);
    gl.uniform1i(this.u.uTex, 0);
    gl.uniform1f(this.u.uUseTex, 0);
    gl.uniform4f(this.u.uUVRect, 1, 1, 0, 0);

    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.clearColor(0.05, 0.08, 0.11, 1);
    return true;
  },

  /* upload the face atlas (a canvas). Power-of-two, so it can be mipmapped —
     without mips a distant fielder's face crawls with aliasing. */
  upload(canvas) {
    const gl = this.gl;
    this.atlas = true;
    gl.bindTexture(gl.TEXTURE_2D, this.tex);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, canvas);
    gl.generateMipmap(gl.TEXTURE_2D);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
  },

  /* a textured decal: blended, and it does not write depth because it sits a
     hair in front of a surface that already did */
  decal(rect) {
    const gl = this.gl;
    if (rect) {
      gl.uniform1f(this.u.uUseTex, 1);
      gl.uniform4f(this.u.uUVRect, rect[0], rect[1], rect[2], rect[3]);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.depthMask(false);
    } else {
      gl.uniform1f(this.u.uUseTex, 0);
      gl.uniform4f(this.u.uUVRect, 1, 1, 0, 0);
      gl.disable(gl.BLEND);
      gl.depthMask(true);
    }
  },

  resize() {
    const c = this.canvas;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.round(c.clientWidth * dpr), h = Math.round(c.clientHeight * dpr);
    if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    this.w = w; this.h = h; this.dpr = dpr;
    this.gl.viewport(0, 0, w, h);
  },

  begin(cam, env) {
    const gl = this.gl;
    this.resize();
    // on a tall screen a fixed vertical fov leaves almost no horizontal view,
    // so widen it as the aspect ratio narrows
    const aspect = this.w / this.h;
    const fov = (cam.fov || 46) * clamp(1.12 / aspect, 1, 1.75);
    const proj = mPerspective(m4(), fov * DEG, aspect, 0.35, 1100);
    const view = mLookAt(m4(), cam.ex, cam.ey, cam.ez, cam.tx, cam.ty, cam.tz);
    mMul(this.vp, proj, view);
    this.eye = [cam.ex, cam.ey, cam.ez];
    const bg = col(env.fog);
    gl.clearColor(bg[0], bg[1], bg[2], 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.disable(gl.BLEND);
    gl.depthMask(true);
    gl.uniformMatrix4fv(this.u.uVP, false, this.vp);
    gl.uniform3fv(this.u.uLight, env.light);
    gl.uniform3fv(this.u.uSky, col(env.skyTint));
    gl.uniform3fv(this.u.uGnd, col(env.gndTint));
    gl.uniform3fv(this.u.uFog, bg);
    gl.uniform3fv(this.u.uEye, this.eye);
    gl.uniform3fv(this.u.uCam, this.eye);
    gl.uniform1f(this.u.uFogD, env.fogDist);
    gl.uniform1f(this.u.uUnlit, 0);
    gl.uniform1f(this.u.uAlpha, 1);
    gl.uniform1f(this.u.uOutline, 0);
    this.inkW = 0;
  },

  /* ink line pass: call R.ink(w), draw the same parts again, then R.ink(0) */
  ink(w) {
    const gl = this.gl;
    this.inkW = w || 0;
    gl.uniform1f(this.u.uOutline, this.inkW);
    gl.uniform1f(this.u.uUnlit, this.inkW > 0 ? 1 : 0);
    gl.uniform1f(this.u.uAlpha, 1);
    gl.cullFace(this.inkW > 0 ? gl.FRONT : gl.BACK);
  },

  /* draw one primitive with a full transform */
  d(prim, x, y, z, rx, ry, rz, sx, sy, sz, c) {
    const gl = this.gl, part = GEO.parts[prim];
    mTRS(this._m, x, y, z, rx, ry, rz, sx, sy, sz);
    gl.uniformMatrix4fv(this.u.uM, false, this._m);
    gl.uniform3fv(this.u.uColor, this.inkW > 0 ? INK_COL : c);
    gl.drawElements(gl.TRIANGLES, part.count, gl.UNSIGNED_SHORT, part.offset);
  },

  /* no rotation — the common case */
  b(prim, x, y, z, sx, sy, sz, c) { this.d(prim, x, y, z, 0, 0, 0, sx, sy, sz, c); },

  /* a primitive stretched between two points — limbs, bats, rails */
  seg(prim, ax, ay, az, bx, by, bz, r, c) {
    const dx = bx - ax, dy = by - ay, dz = bz - az;
    const len = Math.hypot(dx, dy, dz) || 1e-4;
    const rx = Math.acos(clamp(dy / len, -1, 1));
    const ry = Math.atan2(dx, dz);
    this.d(prim, (ax + bx) / 2, (ay + by) / 2, (az + bz) / 2, rx, ry, 0, r * 2, len, r * 2, c);
  },

  /* pre-baked matrix (static scenery) */
  m(prim, mat, c) {
    const gl = this.gl, part = GEO.parts[prim];
    gl.uniformMatrix4fv(this.u.uM, false, mat);
    gl.uniform3fv(this.u.uColor, c);
    gl.drawElements(gl.TRIANGLES, part.count, gl.UNSIGNED_SHORT, part.offset);
  },

  unlit(on, alpha) {
    const gl = this.gl;
    gl.uniform1f(this.u.uUnlit, on ? 1 : 0);
    gl.uniform1f(this.u.uAlpha, alpha === undefined ? 1 : alpha);
    if (alpha !== undefined && alpha < 1) {
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.depthMask(false);
    } else {
      gl.disable(gl.BLEND); gl.depthMask(true);
    }
  },
};

const INK_COL = [0.09, 0.07, 0.06];

/* soft contact shadow — a flat disc, drawn in a blended pass */
const SHADOWS = [];
function shadow(x, z, r, a) {
  if (R.inkW > 0) return;                       // not during the outline pass
  SHADOWS.push(x, z, r, a === undefined ? 0.3 : a);
}
function flushShadows(groundY) {
  if (!SHADOWS.length) return;
  R.unlit(true, 0.34);
  const c = [0.05, 0.09, 0.06];
  for (let i = 0; i < SHADOWS.length; i += 4) {
    R.gl.uniform1f(R.u.uAlpha, SHADOWS[i + 3]);
    R.b('disc', SHADOWS[i], groundY + 0.055, SHADOWS[i + 1], SHADOWS[i + 2] * 2, 1, SHADOWS[i + 2] * 2, c);
  }
  SHADOWS.length = 0;
  R.unlit(false);
}

/* ============================================================
   Audio — short synthesised blips, built on first user gesture
   ============================================================ */
const Snd = {
  ctx: null, on: true,
  boot() { if (!this.ctx) { try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { this.on = false; } } },
  tone(freq, dur, type, gain, slideTo) {
    if (!this.on || !this.ctx) return;
    const t = this.ctx.currentTime;
    const o = this.ctx.createOscillator(), g = this.ctx.createGain();
    o.type = type || 'sine'; o.frequency.setValueAtTime(freq, t);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(gain || 0.16, t + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g); g.connect(this.ctx.destination);
    o.start(t); o.stop(t + dur + 0.02);
  },
  noise(dur, gain, hz) {
    if (!this.on || !this.ctx) return;
    const t = this.ctx.currentTime, n = Math.floor(this.ctx.sampleRate * dur);
    const buf = this.ctx.createBuffer(1, n, this.ctx.sampleRate), d = buf.getChannelData(0);
    for (let i = 0; i < n; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / n);
    const s = this.ctx.createBufferSource(); s.buffer = buf;
    const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = hz || 900;
    const g = this.ctx.createGain(); g.gain.value = gain || 0.1;
    s.connect(f); f.connect(g); g.connect(this.ctx.destination); s.start(t);
  },
  hit(power) { this.tone(300 + power * 480, 0.11, 'square', 0.13, 120); this.noise(0.09, 0.1, 1800); },
  miss() { this.noise(0.09, 0.06, 500); },
  mitt() { this.noise(0.07, 0.09, 420); },
  blip() { this.tone(760, 0.06, 'square', 0.05); },
  good() { this.tone(660, 0.1, 'triangle', 0.11); setTimeout(() => this.tone(990, 0.16, 'triangle', 0.11), 95); },
  bad()  { this.tone(300, 0.16, 'sawtooth', 0.07, 150); },
  cheer(){ this.noise(0.9, 0.07, 700); this.tone(520, 0.5, 'triangle', 0.05, 780); },
  horn() { this.tone(392, 0.30, 'square', 0.05); setTimeout(() => this.tone(330, 0.34, 'square', 0.05), 120); },
  crash(){ this.noise(0.30, 0.14, 260); this.tone(150, 0.28, 'sawtooth', 0.10, 60); },
  clang(){ this.tone(880, 0.16, 'square', 0.10, 320); this.noise(0.12, 0.09, 2400); },
};
