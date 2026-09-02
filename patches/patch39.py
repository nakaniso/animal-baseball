# Stage 2, part 2: hang the face cells on the head and the muzzle, and stop
# building faces out of spheres.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s: raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)

# --- a second patch shaped to the superellipsoid heads ---------------------
edit('src/10-core.js', [(
"""/* half sphere (dome) — caps, hats, hills */""",
"""/* the same patch on the |x|^4+|y|^4+|z|^4 = 1 head. A sphere patch scaled to
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
    t(a, b, a + 1); t(a + 1, b, b + 1);
  }
});

/* half sphere (dome) — caps, hats, hills */""", 'facepr'),
(
"""  upload(canvas) {
    const gl = this.gl;""",
"""  upload(canvas) {
    const gl = this.gl;
    this.atlas = true;""", 'atlas flag')])

# --- drawAnimal: decals in, sphere-faces out -------------------------------
edit('src/30-actors.js', [
# the muzzle keeps its bump; the nose moves onto the decal
("""    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], A.muzC ? col(A.muzC) : fur2);
    const nr = A.noseR || 0.11;
    if (A.nostril) {""",
 """    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], A.muzC ? col(A.muzC) : fur2);
    if (FC && R.atlas && R.inkW === 0) {           // nose and mouth, as art
      R.decal(faceRect(look.animal, p.face || 0, 1));
      part(fh, 'facep', 0, my, mzz, mz[0] * 1.03, mz[1] * 1.03, mz[2] * 1.03, fur);
      R.decal(null);
    }
    const nr = A.noseR || 0.11;
    if (!FC && A.nostril) {""", 'muzzle decal'),
("""    } else {
      if (!(A.dotEyes && R.inkW > 0))
        part(fh, 'sphere', 0, my + mz[1] * 0.40, mzz + mz[2] * 0.40,
             nr, nr * 0.74, nr * 0.72, col(A.noseC || '#33291F'));
    }
    if (A.whisk) for (const s of [-1, 1]) for (let i = 0; i < 3; i++)""",
 """    } else if (!FC) {
      part(fh, 'sphere', 0, my + mz[1] * 0.40, mzz + mz[2] * 0.40,
           nr, nr * 0.74, nr * 0.72, col(A.noseC || '#33291F'));
    }
    if (!FC && A.whisk) for (const s of [-1, 1]) for (let i = 0; i < 3; i++)""", 'nose/whisk'),
("  if (A.mouth) {                                // the frog's wide grin",
 "  if (A.mouth && !FC) {                         // the frog's wide grin", 'frog mouth'),
("  if (A.smallMouth && R.inkW === 0) {           // a little mouth under the nose",
 "  if (A.smallMouth && !FC && R.inkW === 0) {    // a little mouth under the nose", 'small mouth'),
("  if (!A.noFaceEyes && A.dotEyes) {              // simple dots, as drawn",
 "  if (FC) { /* the eyes live in the face cell */ }\n  else if (!A.noFaceEyes && A.dotEyes) {         // simple dots, as drawn", 'eye gate'),
# the head decal goes on after the head and any mask/patch on it
("""  if (A.beak) {""",
 """  if (FC && R.atlas && R.inkW === 0) {            // eyes and brows, as art
    R.decal(faceRect(look.animal, p.face || 0, 0));
    const k = 1.015;
    part(fh, A.head === 'rbox' ? 'facepr' : 'facep', 0, hy, 0.02,
         0.68 * big * HW * k, 0.66 * HH * k, 0.64 * big * HD * k, fur);
    R.decal(null);
  }

  if (A.beak) {""", 'head decal'),
("""  const p = pose || IDLE;
  const f = yawFrame(x, z, ry);""",
 """  const p = pose || IDLE;
  const FC = FACES[look.animal] || null;
  const f = yawFrame(x, z, ry);""", 'FC')])

# --- build the atlas at boot ----------------------------------------------
edit('src/50-main.js', [("""  buildMenus();
  bindInput();""",
"""  R.upload(buildFaceAtlas());
  buildMenus();
  bindInput();""", 'boot upload')])

print('patched ok')
