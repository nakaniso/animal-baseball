# Face tuning: the snout art belongs on the head for a species whose muzzle is
# barely a bump (the rabbit), and on the white face patch for the penguin,
# whose patch stands proud of the skull and was hiding its eyes.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s: raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)

edit('src/30-actors.js', [
# --- species art params ---
("""  rabbit:  { eye: 'dot',    eyeX: 0.185, eyeY: 0.345, eyeR: 0.062,
             nose: 'dot',   noseC: '#4A3438', noseY: 0.290, noseR: 0.115, mouth: 'w',
             mouthC: '#4A3438', mouthY: 0.560, mouthW: 0.230 },""",
 """  // the rabbit's muzzle is a flush bump, so its nose and mouth go on the head
  rabbit:  { eye: 'dot',    eyeX: 0.200, eyeY: 0.355, eyeR: 0.062, onHead: 1,
             nose: 'dot',   noseC: '#4A3438', noseY: 0.655, noseR: 0.050, mouth: 'w',
             mouthC: '#4A3438', mouthY: 0.745, mouthW: 0.085 },""", 'rabbit face'),
("  penguin: { eye: 'bead',   eyeX: 0.170, eyeY: 0.360, eyeR: 0.058 },",
 "  penguin: { eye: 'bead',   eyeX: 0.250, eyeY: 0.300, eyeR: 0.076, onPatch: 1 },", 'penguin face'),
("""             nose: 'tri',   noseC: '#3C2A20', noseY: 0.285, noseR: 0.135, mouth: 'w' },""",
 """             nose: 'tri',   noseC: '#3C2A20', noseY: 0.300, noseR: 0.175, mouth: 'w',
             mouthY: 0.560, mouthW: 0.200 },""", 'fox face'),

# --- the snout art becomes reusable so the head cell can carry it too ---
("""function drawMuzCell(g, F, exp) {
  if (!F.nose) return;
  const nx = 0.5, ny = F.noseY, nr = F.noseR;""",
 """function drawSnout(g, F, exp) {
  const nx = 0.5, ny = F.noseY, nr = F.noseR;""", 'drawSnout rename'),
("""function buildFaceAtlas() {""",
 """function drawMuzCell(g, F, exp) { if (F.nose && !F.onHead) drawSnout(g, F, exp); }

function buildFaceAtlas() {""", 'drawMuzCell'),
("""  if (F.headMouth === 'wide') {                   // the frog's grin spans the head""",
 """  if (F.nose && F.onHead) drawSnout(g, F, exp);
  if (F.headMouth === 'wide') {                   // the frog's grin spans the head""", 'head snout'),

# --- the penguin's decal rides on its face patch, not the skull ---
("""  if (FC && R.atlas && R.inkW === 0) {            // eyes and brows, as art
    R.decal(faceRect(look.animal, p.face || 0, 0));
    const k = 1.015;
    part(fh, A.head === 'rbox' ? 'facepr' : 'facep', 0, hy, 0.02,
         0.68 * big * HW * k, 0.66 * HH * k, 0.64 * big * HD * k, fur);
    R.decal(null);
  }""",
 """  if (FC && R.atlas && R.inkW === 0) {            // eyes and brows, as art
    R.decal(faceRect(look.animal, p.face || 0, 0));
    const k = 1.015;
    if (FC.onPatch && A.facePatch) {
      const fp = A.facePatch;                      // the patch stands proud of
      part(fh, 'facep', 0, hy - 0.02, hzF - 0.10,  // the skull, so sit on that
           fp[0] * k, fp[1] * k, fp[2] * k, fur);
    } else {
      part(fh, A.head === 'rbox' ? 'facepr' : 'facep', 0, hy, 0.02,
           0.68 * big * HW * k, 0.66 * HH * k, 0.64 * big * HD * k, fur);
    }
    R.decal(null);
  }""", 'penguin decal'),

# a species whose snout art lives on the head skips the muzzle decal entirely
("""    if (FC && R.atlas && R.inkW === 0) {           // nose and mouth, as art""",
 """    if (FC && !FC.onHead && R.atlas && R.inkW === 0) {   // nose and mouth, as art""", 'skip muz decal')])

print('patched ok')
