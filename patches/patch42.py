# The hook for scanned line art. Empty by default, so nothing changes until a
# cell is actually filled in — the art is baked by tools/face-lab.html.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s: raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)

edit('src/30-actors.js', [(
"""/* uv rect for one cell: [scaleU, scaleV, offsetU, offsetV] */""",
"""/* Hand-drawn cells, baked from a scan by tools/face-lab.html and pasted in
   here as PNG data URIs. The key is 'species:cell', where cell 0-3 is the head
   and 4-7 the muzzle, one per expression — the same numbering as the atlas.
   A cell listed here replaces the drawn-in-code one; everything else is
   untouched. */
const FACE_SCANS = {
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

/* uv rect for one cell: [scaleU, scaleV, offsetU, offsetV] */""", 'FACE_SCANS')])

edit('src/50-main.js', [(
"""  R.upload(buildFaceAtlas());""",
"""  const faceAtlas = buildFaceAtlas();
  R.upload(faceAtlas);
  applyFaceScans(faceAtlas, () => R.upload(faceAtlas));""", 'boot')])

# the tool only refreshed its readouts on a real input event
edit('tools/lab-main.js', [(
"""function rebuild() {
  atlas = buildFaceAtlas();""",
"""function rebuild() {
  refreshLabels();
  atlas = buildFaceAtlas();""", 'labels')])
print('patched ok')
