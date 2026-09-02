# The rabbit, redrawn from a child's reference sketch: long straight ears, a
# round head, simple dot eyes (not the white-and-pupil almonds the others have),
# a small nose with a little mouth under it, and buttons down the jersey.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

p = 'src/30-actors.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b)

# ---- species entry ----
rep("""  rabbit:  { ink: 0.022, ear: 'long', fur: '#F0EAE0', fur2: '#F6D7DA', tail: 'puff',
             head: 'rbox', hw: 0.99, hh: 1.10, hd: 0.94,
             muz: [0.34, 0.235, 0.24], muzY: -0.135, muzZ: 0.245,
             noseR: 0.082, noseC: '#D9808F', cheek: 0.19,
             earR: 0.165, earX: 0.145, earY: 0.50, earLen: 0.64, earIn: '#F6D7DA',
             eyeX: 0.166, eyeW: 0.124, eyeH: 0.124 },""",
"""  // drawn from the reference sketch: tall straight ears, round head, dot eyes
  rabbit:  { ink: 0.022, ear: 'long', fur: '#F4F0E8', fur2: '#F6D7DA', tail: 'puff',
             head: 'sphere', hw: 1.05, hh: 1.02, hd: 0.98,
             muz: [0.27, 0.185, 0.21], muzY: -0.150, muzZ: 0.250,
             noseR: 0.060, noseC: '#4A3438', smallMouth: 1, buttons: 1,
             earR: 0.150, earX: 0.128, earY: 0.62, earLen: 0.86, earTilt: 0.10,
             earIn: '#F6D7DA',
             dotEyes: 1, eyeX: 0.152, eyeW: 0.074, eyeH: 0.084 },""", 'rabbit spec')

# ---- dot eyes, and a small mouth under the nose ----
rep("""  if (!A.noFaceEyes) {
    const ex = A.eyeX || 0.150, ew = A.eyeW || 0.140, eh = A.eyeH || 0.115;
    const et = A.eyeTilt || 0;
    for (const s of [-1, 1]) {""",
"""  if (A.smallMouth) {                           // a little mouth under the nose
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
  } else if (!A.noFaceEyes) {
    const ex = A.eyeX || 0.150, ew = A.eyeW || 0.140, eh = A.eyeH || 0.115;
    const et = A.eyeTilt || 0;
    for (const s of [-1, 1]) {""", 'dot eyes')

# ---- ears take a per-species lean ----
rep("""  if (A.ear === 'long') {
    const er = A.earR || 0.17, exx = A.earX || 0.15, eyy = A.earY || 0.44, el = A.earLen || 0.56;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, -0.03, er, el, er * 0.85, fur, 0, s * 0.20);
      part(fh, 'sphere', s * (exx + 0.012), hy + eyy + 0.01, 0.025,
           er * 0.54, el * 0.72, er * 0.50, A.earIn ? col(A.earIn) : fur2, 0, s * 0.20);
    }
  }""",
"""  if (A.ear === 'long') {
    const er = A.earR || 0.17, exx = A.earX || 0.15, eyy = A.earY || 0.44;
    const el = A.earLen || 0.56, tl = A.earTilt === undefined ? 0.20 : A.earTilt;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, -0.03, er, el, er * 0.82, fur, 0, s * tl);
      part(fh, 'sphere', s * (exx + 0.010), hy + eyy + 0.02, 0.020,
           er * 0.50, el * 0.74, er * 0.46, A.earIn ? col(A.earIn) : fur2, 0, s * tl);
    }
  }""", 'long ears')

# ---- buttons down the jersey ----
rep("""  part(f, 'box', 0, y + 0.72, 0.185, 0.075, 0.42, 0.05, trim);  // button placket""",
"""  part(f, 'box', 0, y + 0.72, 0.185, 0.075, 0.42, 0.05, trim);  // button placket
  if (A.buttons) for (let i = 0; i < 3; i++)                     // ...and its buttons
    part(f, 'sphere', 0, y + 0.86 - i * 0.14, 0.215, 0.070, 0.070, 0.045, trim2);""", 'buttons')
rep("  const uni = col(look.uni), trim = col(look.trim), cap = col(look.cap);",
    "  const uni = col(look.uni), trim = col(look.trim), cap = col(look.cap);\n  const trim2 = shade(look.trim, 0.72);", 'trim2')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
