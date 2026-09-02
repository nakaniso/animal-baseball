# The inverted-hull outline expands every part by A.ink (0.022). On the small
# drawn features of the rabbit's face that halo is wider than the feature
# itself, so a dot eye came out as a fat dark ring. Draw those in the colour
# pass only.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
p = 'src/30-actors.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b)

rep("""  if (A.smallMouth) {                           // a little mouth under the nose
    const my2 = hy + (A.muzY === undefined ? -0.09 : A.muzY) - 0.055;
    for (const s of [-1, 1])
      part(fh, 'box', s * 0.043, my2, hzF - 0.055, 0.085, 0.026, 0.06,
           col('#4A3438'), 0, s * 0.55);
  }
  if (!A.noFaceEyes && A.dotEyes) {              // simple dots, as drawn
    const ex = A.eyeX || 0.150, ew = A.eyeW || 0.078, eh = A.eyeH || 0.086;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * ex, hy + 0.085, hzF - 0.030, ew, eh, 0.070, col(EYE));
      part(fh, 'sphere', s * ex + 0.018, hy + 0.105, hzF - 0.008, 0.026, 0.026, 0.022, col(SHINE));
    }
  } else if (!A.noFaceEyes) {""",
"""  if (A.smallMouth && R.inkW === 0) {           // a little mouth under the nose
    const my2 = hy + (A.muzY === undefined ? -0.09 : A.muzY) - 0.060;
    for (const s of [-1, 1])
      part(fh, 'box', s * 0.046, my2, hzF - 0.050, 0.092, 0.028, 0.06,
           col('#4A3438'), 0, s * 0.52);
  }
  if (!A.noFaceEyes && A.dotEyes) {              // simple dots, as drawn
    const ex = A.eyeX || 0.150, ew = A.eyeW || 0.078, eh = A.eyeH || 0.086;
    if (R.inkW === 0) for (const s of [-1, 1]) {
      part(fh, 'sphere', s * ex, hy + 0.085, hzF - 0.028, ew, eh, 0.070, col(EYE));
      part(fh, 'sphere', s * ex + 0.016, hy + 0.102, hzF - 0.006, 0.021, 0.021, 0.018, col(SHINE));
    }
  } else if (!A.noFaceEyes) {""", 'no ink on dot face')

# the nose is small too — let it keep its own edge instead of a halo
rep("""      part(fh, 'sphere', 0, my + mz[1] * 0.40, mzz + mz[2] * 0.40,
           nr, nr * 0.74, nr * 0.72, col(A.noseC || '#33291F'));""",
"""      if (!(A.dotEyes && R.inkW > 0))
        part(fh, 'sphere', 0, my + mz[1] * 0.40, mzz + mz[2] * 0.40,
             nr, nr * 0.74, nr * 0.72, col(A.noseC || '#33291F'));""", 'nose ink')

rep("             dotEyes: 1, eyeX: 0.152, eyeW: 0.074, eyeH: 0.084 },",
    "             dotEyes: 1, eyeX: 0.150, eyeW: 0.086, eyeH: 0.098 },", 'eye size')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
