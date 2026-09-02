# Stage 2, part 1: give the renderer UVs and a texture unit so faces can be
# authored as art instead of assembled from spheres.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
p = 'src/10-core.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b, 1)

# --- geometry: vertices gain an optional uv ---
rep("""const GEO = { pos: [], nor: [], idx: [], parts: {} };

function geoPart(name, build) {
  const start = GEO.idx.length, base = GEO.pos.length / 3;
  build((x, y, z, nx, ny, nz) => {
    GEO.pos.push(x, y, z); GEO.nor.push(nx, ny, nz);
    return GEO.pos.length / 3 - 1 - base;
  }, (a, b, c) => GEO.idx.push(base + a, base + b, base + c));
  GEO.parts[name] = { offset: start * 2, count: GEO.idx.length - start };
}""",
"""const GEO = { pos: [], nor: [], uv: [], idx: [], parts: {} };

function geoPart(name, build) {
  const start = GEO.idx.length, base = GEO.pos.length / 3;
  build((x, y, z, nx, ny, nz, u, w) => {
    GEO.pos.push(x, y, z); GEO.nor.push(nx, ny, nz);
    GEO.uv.push(u || 0, w || 0);
    return GEO.pos.length / 3 - 1 - base;
  }, (a, b, c) => GEO.idx.push(base + a, base + b, base + c));
  GEO.parts[name] = { offset: start * 2, count: GEO.idx.length - start };
}""", 'geoPart uv')

# --- the face decal: a patch of the unit sphere, so scaling it exactly like the
#     head (or the muzzle) lays it flat on that surface ---
rep("""/* half sphere (dome) — caps, hats, hills */""",
"""/* A patch of the unit sphere with uv across it. Scaled with the same numbers
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
    t(a, b, a + 1); t(a + 1, b, b + 1);
  }
});

/* half sphere (dome) — caps, hats, hills */""", 'facep')

# --- shaders ---
rep("""attribute vec3 aPos; attribute vec3 aNor;
uniform mat4 uVP, uM;
uniform float uOutline;
uniform vec3 uCam;
varying vec3 vN, vW;
void main(){""",
"""attribute vec3 aPos; attribute vec3 aNor; attribute vec2 aUV;
uniform mat4 uVP, uM;
uniform float uOutline;
uniform vec3 uCam;
uniform vec4 uUVRect;
varying vec3 vN, vW;
varying vec2 vUV;
void main(){
  vUV = aUV * uUVRect.xy + uUVRect.zw;""", 'vs uv')

rep("""precision mediump float;
varying vec3 vN, vW;
uniform vec3 uColor, uLight, uSky, uGnd, uFog, uEye;
uniform float uFogD, uUnlit, uAlpha;
void main(){
  if (uUnlit > 0.5) { gl_FragColor = vec4(uColor, uAlpha); return; }
  vec3 n = normalize(vN);""",
"""precision mediump float;
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
  vec3 n = normalize(vN);""", 'fs tex')

rep("""  vec3 c = uColor * s * (0.80 + 0.42 * hemi);
  float f = clamp(length(vW - uEye) / uFogD, 0.0, 1.0);
  c = mix(c, uFog, f * f * 0.85);
  gl_FragColor = vec4(c, uAlpha);""",
"""  vec3 c = base * s * (0.80 + 0.42 * hemi);
  float f = clamp(length(vW - uEye) / uFogD, 0.0, 1.0);
  c = mix(c, uFog, f * f * 0.85);
  gl_FragColor = vec4(c, a);""", 'fs out')

# --- uniforms, buffers, texture ---
rep("'uFogD', 'uUnlit', 'uAlpha', 'uOutline', 'uCam'])",
    "'uFogD', 'uUnlit', 'uAlpha', 'uOutline', 'uCam', 'uUseTex', 'uUVRect', 'uTex'])", 'uniform list')

rep("""    const ib = gl.createBuffer();""",
"""    const ub = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, ub);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(GEO.uv), gl.STATIC_DRAW);
    const au = gl.getAttribLocation(p, 'aUV');
    gl.enableVertexAttribArray(au); gl.vertexAttribPointer(au, 2, gl.FLOAT, false, 0, 0);

    const ib = gl.createBuffer();""", 'uv buffer')

rep("""    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.clearColor(0.05, 0.08, 0.11, 1);
    return true;
  },""",
"""    // unit 0 always holds a valid texture, so sampling is defined even on the
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
  },""", 'texture api')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
