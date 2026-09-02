# (a) Screen-space outline weight and (b) finer tessellation.
#
# (a) The inverted hull pushed every shell out by a fixed number of METRES, so
#     the ink line was ~10x heavier on the batter than on a right fielder, and
#     on anything smaller than 0.022m across it swallowed the part whole (the
#     rabbit's dot eyes). Scaling the push with camera distance makes the line
#     a roughly constant width on screen instead.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
p = 'src/10-core.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b, 1)

rep("""attribute vec3 aPos; attribute vec3 aNor;
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
}""",
"""attribute vec3 aPos; attribute vec3 aNor;
uniform mat4 uVP, uM;
uniform float uOutline;
uniform vec3 uEye;
varying vec3 vN, vW;
void main(){
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
    float k = clamp(distance(uEye, w.xyz) / 11.0, 0.30, 3.6);
    w.xyz += (n / l) * uOutline * k;
  }
  vW = w.xyz;
  gl_Position = uVP * w;
}""", 'vs outline')

# (b) finer tessellation. Costs vertices only - the draw-call count per
#     character is unchanged, and the whole buffer stays far under the 65535
#     that the Uint16 index type allows.
rep("  const RN = 8, SN = 14;", "  const RN = 16, SN = 24;", 'sphere tess')
rep("  const RN = 10, SN = 16, e = 0.5;", "  const RN = 16, SN = 24, e = 0.5;", 'rbox tess')
rep("  const RN = 5, SN = 14;", "  const RN = 9, SN = 24;", 'dome tess')
rep("function tube(v, t, rTop, rBot, capped) {\n  const N = 16;",
    "function tube(v, t, rTop, rBot, capped) {\n  const N = 24;", 'tube tess')
rep("geoPart('disc', (v, t) => {\n  const N = 22;",
    "geoPart('disc', (v, t) => {\n  const N = 32;", 'disc tess')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
