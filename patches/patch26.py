# The reference is pen line-art, so the thing that makes it read as "that
# drawing" is the ink contour, not the volume. This adds a toon outline pass
# (inverted hull, displaced along the world normal) and turns it on for the bear
# only, so he becomes a drawn character among shaded ones.
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
# 10-core.js — outline pass
# ============================================================
box, rep = mk('src/10-core.js')
rep("""const VS = `
attribute vec3 aPos; attribute vec3 aNor;
uniform mat4 uVP, uM;
varying vec3 vN, vW;
void main(){
  vec4 w = uM * vec4(aPos,1.0);
  vW = w.xyz;
  vN = (uM * vec4(aNor,0.0)).xyz;
  gl_Position = uVP * w;
}`;""",
"""const VS = `
attribute vec3 aPos; attribute vec3 aNor;
uniform mat4 uVP, uM;
uniform float uOutline;
varying vec3 vN, vW;
void main(){
  vec4 w = uM * vec4(aPos,1.0);
  vec3 n = (uM * vec4(aNor,0.0)).xyz;
  float l = length(n);
  vN = n;
  // inverted hull: push the shell out along the world normal, draw back faces
  if (uOutline > 0.0 && l > 0.0001) w.xyz += (n / l) * uOutline;
  vW = w.xyz;
  gl_Position = uVP * w;
}`;""", 'VS outline')

rep("    for (const n of ['uVP', 'uM', 'uColor', 'uLight', 'uSky', 'uGnd', 'uFog', 'uEye', 'uFogD', 'uUnlit', 'uAlpha'])",
    "    for (const n of ['uVP', 'uM', 'uColor', 'uLight', 'uSky', 'uGnd', 'uFog', 'uEye', 'uFogD', 'uUnlit', 'uAlpha', 'uOutline'])", 'uniform list')

rep("""  eye: [0, 0, 0], w: 1, h: 1, dpr: 1,""",
"""  eye: [0, 0, 0], w: 1, h: 1, dpr: 1, inkW: 0,""", 'inkW field')

rep("""    gl.uniform1f(this.u.uUnlit, 0);
    gl.uniform1f(this.u.uAlpha, 1);
  },""",
"""    gl.uniform1f(this.u.uUnlit, 0);
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
  },""", 'R.ink')

rep("""  /* draw one primitive with a full transform */
  d(prim, x, y, z, rx, ry, rz, sx, sy, sz, c) {
    const gl = this.gl, part = GEO.parts[prim];
    mTRS(this._m, x, y, z, rx, ry, rz, sx, sy, sz);
    gl.uniformMatrix4fv(this.u.uM, false, this._m);
    gl.uniform3fv(this.u.uColor, c);""",
"""  /* draw one primitive with a full transform */
  d(prim, x, y, z, rx, ry, rz, sx, sy, sz, c) {
    const gl = this.gl, part = GEO.parts[prim];
    mTRS(this._m, x, y, z, rx, ry, rz, sx, sy, sz);
    gl.uniformMatrix4fv(this.u.uM, false, this._m);
    gl.uniform3fv(this.u.uColor, this.inkW > 0 ? INK_COL : c);""", 'd ink color')

rep("""/* soft contact shadow — a flat disc, drawn in a blended pass */
const SHADOWS = [];
function shadow(x, z, r, a) { SHADOWS.push(x, z, r, a === undefined ? 0.3 : a); }""",
"""const INK_COL = [0.09, 0.07, 0.06];

/* soft contact shadow — a flat disc, drawn in a blended pass */
const SHADOWS = [];
function shadow(x, z, r, a) {
  if (R.inkW > 0) return;                       // not during the outline pass
  SHADOWS.push(x, z, r, a === undefined ? 0.3 : a);
}""", 'shadow guard')
wr('src/10-core.js', box['s'])

# ============================================================
# 30-actors.js — the bear is drawn twice: ink, then fill
# ============================================================
box, rep = mk('src/30-actors.js')
rep("""             head: 'rbox', hw: 1.16, hh: 1.08, hd: 1.00,""",
"""             ink: 0.023, head: 'rbox', hw: 1.16, hh: 1.08, hd: 1.00,""", 'bear ink')

rep("""function drawAnimal(x, z, ry, look, pose, y0) {
  const A = ANIMALS[look.animal];""",
"""/* run `draw` once as an ink shell and once as the fill, for species drawn in
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
  }""", 'inked helper')

# face features stand a little further off the head so their line reads
rep("""    part(fh, 'sphere', s * ex, hy + 0.075, hzF - 0.045, ew, eh, 0.075, col('#F6F1E6'));
    part(fh, 'sphere', s * ex + s * 0.012, hy + 0.068, hzF - 0.018,
         ew * 0.50, eh * 0.66, 0.055, col(EYE));
    part(fh, 'sphere', s * ex + 0.030, hy + 0.100, hzF + 0.002, 0.040, 0.040, 0.032, col(SHINE));
    if (A.brow)
      part(fh, 'box', s * ex, hy + 0.188, hzF - 0.055, 0.215, 0.040, 0.075,
           shade(A.fur, 0.38), 0, s * 0.16);""",
"""    part(fh, 'sphere', s * ex, hy + 0.075, hzF - 0.025, ew, eh, 0.085, col('#F6F1E6'));
    part(fh, 'sphere', s * ex + s * 0.012, hy + 0.068, hzF + 0.010,
         ew * 0.50, eh * 0.66, 0.060, col(EYE));
    part(fh, 'sphere', s * ex + 0.030, hy + 0.100, hzF + 0.028, 0.040, 0.040, 0.032, col(SHINE));
    if (A.brow)
      part(fh, 'box', s * ex, hy + 0.192, hzF - 0.030, 0.225, 0.042, 0.085,
           shade(A.fur, 0.34), 0, s * 0.16);""", 'face proud')
wr('src/30-actors.js', box['s'])

# ============================================================
# 50-main.js — the bat and glove get the same treatment
# ============================================================
box, rep = mk('src/50-main.js')
rep("""    drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');
    drawGrip(rig.grip, rig.dir, rig.botAt, bt.trim);
    drawGrip(rig.grip, rig.dir, rig.topAt, bt.trim);""",
"""    inked(b.look, () => {
      drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');
      drawGrip(rig.grip, rig.dir, rig.botAt, bt.trim);
      drawGrip(rig.grip, rig.dir, rig.topAt, bt.trim);
    });""", 'bat ink')
rep("""    if (!isP) drawGlove(pose.handL ? [pose.handL[0], pose.handL[1], pose.handL[2]]
                                   : [gp[0], a.hl[1], gp[1]], ft.trim);""",
"""    if (!isP) inked(pl.look, () => drawGlove(pose.handL
      ? [pose.handL[0], pose.handL[1], pose.handL[2]]
      : [gp[0], a.hl[1], gp[1]], ft.trim));""", 'glove ink')
wr('src/50-main.js', box['s'])
print('patched ok')
