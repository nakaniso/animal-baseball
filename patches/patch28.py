# Every species gets the same treatment the bear got: a shaped head, a face
# built for that animal (fox snout, cat whiskers, rabbit's long ears and pink
# nose, frog's grin and eye domes, penguin's white face and bill, hippo's
# nostrils), and the ink outline, so the whole cast is drawn in one style.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

p = 'src/30-actors.js'
s = io.open(p, encoding='utf-8').read()

# ---------- species table ----------
i0 = s.index('const ANIMALS = {')
i1 = s.index('};', i0) + 2
TABLE = """const ANIMALS = {
  bear:    { ink: 0.022, ear: 'round', fur: '#96683F', fur2: '#DFC49B', tail: 'nub',
             head: 'rbox', hw: 1.16, hh: 1.08, hd: 1.00,
             muz: [0.56, 0.365, 0.33], muzY: -0.135, muzZ: 0.230, noseR: 0.105,
             brow: 1, earR: 0.245, earX: 0.325, earY: 0.315, earD: 0.60,
             eyeX: 0.152, eyeW: 0.132, eyeH: 0.104 },

  rabbit:  { ink: 0.022, ear: 'long', fur: '#F0EAE0', fur2: '#F6D7DA', tail: 'puff',
             head: 'rbox', hw: 0.99, hh: 1.10, hd: 0.94,
             muz: [0.34, 0.235, 0.24], muzY: -0.135, muzZ: 0.245,
             noseR: 0.082, noseC: '#D9808F', cheek: 0.19,
             earR: 0.165, earX: 0.145, earY: 0.50, earLen: 0.64, earIn: '#F6D7DA',
             eyeX: 0.166, eyeW: 0.124, eyeH: 0.124 },

  cat:     { ink: 0.022, ear: 'point', fur: '#E0A44F', fur2: '#F7EDDD', tail: 'long',
             head: 'rbox', hw: 1.10, hh: 0.98, hd: 0.94,
             muz: [0.46, 0.255, 0.26], muzY: -0.125, muzZ: 0.245,
             noseR: 0.085, noseC: '#C2705E', whisk: 1,
             earR: 0.255, earX: 0.235, earY: 0.36, earT: 0.26,
             eyeX: 0.156, eyeW: 0.145, eyeH: 0.100, eyeTilt: 0.16 },

  frog:    { ink: 0.022, ear: 'toad', fur: '#7DC163', fur2: '#E8F0C8', tail: 'none',
             head: 'rbox', hw: 1.24, hh: 0.86, hd: 1.02,
             noFaceEyes: 1, mouth: 1,
             earR: 0.30, earX: 0.255, earY: 0.28 },

  penguin: { ink: 0.022, ear: 'none', fur: '#2E3B4A', fur2: '#F4F1E6', tail: 'nub',
             beak: '#F2A93B', head: 'sphere', hw: 1.02, hh: 1.08, hd: 0.98,
             facePatch: [0.54, 0.58, 0.30],
             eyeX: 0.138, eyeW: 0.104, eyeH: 0.104 },

  fox:     { ink: 0.022, ear: 'point', fur: '#D96F3A', fur2: '#F6EFE2', tail: 'bushy',
             head: 'rbox', hw: 1.04, hh: 0.96, hd: 1.08,
             muz: [0.33, 0.235, 0.46], muzY: -0.115, muzZ: 0.30, noseR: 0.082,
             cheek: 0.21, cheekC: '#F6EFE2',
             earR: 0.275, earX: 0.255, earY: 0.38, earT: 0.22, earTip: '#3C2A20',
             eyeX: 0.156, eyeW: 0.140, eyeH: 0.098, eyeTilt: 0.20 },

  panda:   { ink: 0.022, ear: 'round', fur: '#F0EDE6', fur2: '#2C3138', tail: 'nub', patch: 1,
             head: 'rbox', hw: 1.12, hh: 1.04, hd: 0.98,
             muz: [0.44, 0.28, 0.28], muzY: -0.13, muzZ: 0.24, noseR: 0.10,
             earR: 0.25, earX: 0.32, earY: 0.315, earD: 0.60, earC: '#2C3138',
             eyeX: 0.166, eyeW: 0.135, eyeH: 0.110 },

  hippo:   { ink: 0.022, ear: 'round', fur: '#9E86C4', fur2: '#D8C9EC', tail: 'nub', big: 1,
             head: 'rbox', hw: 1.18, hh: 0.92, hd: 1.02,
             muz: [0.62, 0.36, 0.38], muzY: -0.115, muzZ: 0.24, noseR: 0.072, nostril: 1,
             earR: 0.165, earX: 0.34, earY: 0.30, earD: 0.60,
             eyeX: 0.186, eyeW: 0.115, eyeH: 0.095 },
};"""
s = s[:i0] + TABLE + s[i1:]

# ---------- head and face ----------
j0 = s.index('  // head — may be turned independently')
j1 = s.index('  // tail', j0)
FACE = """  // head — may be turned independently of the body (a batter watching the ball)
  const fh = p.headRy ? yawFrame(x, z, ry + p.headRy) : f;
  const hy = y + 1.34;
  const HW = A.hw || 1, HH = A.hh || 1, HD = A.hd || 1;
  const hzF = 0.32 * HD + 0.02;                 // where the front of the face is
  part(fh, A.head || 'sphere', 0, hy, 0.02, 0.68 * big * HW, 0.66 * HH, 0.64 * big * HD, fur);

  if (A.patch) {                                // panda mask
    for (const s of [-1, 1])
      part(fh, 'sphere', s * 0.17, hy + 0.08, hzF - 0.07, 0.27, 0.29, 0.16, fur2);
  }
  if (A.facePatch) {                            // the penguin's white face
    const fp = A.facePatch;
    part(fh, 'sphere', 0, hy - 0.02, hzF - 0.10, fp[0], fp[1], fp[2], fur2);
  }
  if (A.cheek) {                                // fluffy cheeks
    for (const s of [-1, 1])
      part(fh, 'sphere', s * 0.29, hy - 0.09, 0.09, A.cheek, A.cheek * 0.94, A.cheek * 0.88,
           A.cheekC ? col(A.cheekC) : fur2);
  }

  if (A.beak) {
    part(fh, 'cone', 0, hy - 0.045, hzF - 0.03, 0.27, 0.32, 0.27, col(A.beak), -Math.PI / 2);
    part(fh, 'box', 0, hy - 0.045, hzF + 0.07, 0.19, 0.022, 0.16, shade(A.beak, 0.62));
  } else if (A.muz) {
    const mz = A.muz, my = hy + (A.muzY === undefined ? -0.09 : A.muzY);
    const mzz = A.muzZ === undefined ? 0.26 : A.muzZ;
    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], fur2);
    const nr = A.noseR || 0.11;
    if (A.nostril) {
      for (const s of [-1, 1])
        part(fh, 'sphere', s * mz[0] * 0.24, my + mz[1] * 0.28, mzz + mz[2] * 0.40,
             nr, nr * 0.90, nr * 0.60, col('#3A3040'));
    } else {
      part(fh, 'sphere', 0, my + mz[1] * 0.40, mzz + mz[2] * 0.40,
           nr, nr * 0.74, nr * 0.72, col(A.noseC || '#33291F'));
    }
    if (A.whisk) for (const s of [-1, 1]) for (let i = 0; i < 3; i++)
      part(fh, 'box', s * (mz[0] * 0.60 + 0.13), my + 0.02 + (i - 1) * 0.05, mzz + 0.03,
           0.28, 0.017, 0.017, col('#6B5A48'), 0, s * ((i - 1) * 0.24 + 0.05));
  }
  if (A.mouth) {                                // the frog's wide grin
    for (const s of [-1, 1])
      part(fh, 'box', s * 0.17, hy - 0.16, hzF - 0.02, 0.36, 0.036, 0.07,
           shade(A.fur, 0.42), 0, s * -0.11);
  }

  // eyes, with the drawn brow line above them
  if (!A.noFaceEyes) {
    const ex = A.eyeX || 0.150, ew = A.eyeW || 0.140, eh = A.eyeH || 0.115;
    const et = A.eyeTilt || 0;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * ex, hy + 0.098, hzF - 0.025, ew, eh, 0.085, col('#F6F1E6'), 0, s * et);
      part(fh, 'sphere', s * ex - s * 0.008, hy + 0.094, hzF + 0.012,
           ew * 0.60, eh * 0.74, 0.058, col(EYE), 0, s * et);
      part(fh, 'sphere', s * ex + 0.024, hy + 0.118, hzF + 0.028, 0.034, 0.034, 0.028, col(SHINE));
      if (A.brow)
        part(fh, 'box', s * ex, hy + 0.205, hzF - 0.030, 0.215, 0.040, 0.085,
             shade(A.fur, 0.34), 0, s * 0.16);
    }
  }

  // ears
  const earC = A.earC ? col(A.earC) : fur;
  if (A.ear === 'round') {
    const er = A.earR || 0.26, exx = A.earX || 0.26, eyy = A.earY || 0.26, ed = A.earD || 0.77;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, -0.02, er, er, er * ed, earC);
      part(fh, 'sphere', s * exx, hy + eyy + 0.01, 0.04, er * 0.55, er * 0.55, er * 0.50, fur2);
    }
  }
  if (A.ear === 'point') {
    const er = A.earR || 0.26, exx = A.earX || 0.21, eyy = A.earY || 0.34, tl = A.earT || 0.22;
    for (const s of [-1, 1]) {
      part(fh, 'cone', s * exx, hy + eyy, -0.02, er, er * 1.30, er * 0.76, earC, 0, s * tl);
      part(fh, 'cone', s * exx, hy + eyy - 0.01, 0.035, er * 0.52, er * 0.86, er * 0.42, fur2, 0, s * tl);
      if (A.earTip)
        part(fh, 'cone', s * (exx + er * 0.32), hy + eyy + er * 0.46, -0.02,
             er * 0.60, er * 0.50, er * 0.46, col(A.earTip), 0, s * tl);
    }
  }
  if (A.ear === 'long') {
    const er = A.earR || 0.17, exx = A.earX || 0.15, eyy = A.earY || 0.44, el = A.earLen || 0.56;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, -0.03, er, el, er * 0.85, fur, 0, s * 0.20);
      part(fh, 'sphere', s * (exx + 0.012), hy + eyy + 0.01, 0.025,
           er * 0.54, el * 0.72, er * 0.50, A.earIn ? col(A.earIn) : fur2, 0, s * 0.20);
    }
  }
  if (A.ear === 'toad') {
    const er = A.earR || 0.28, exx = A.earX || 0.19, eyy = A.earY || 0.26;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, 0.05, er, er, er, fur);
      part(fh, 'sphere', s * exx, hy + eyy + 0.03, 0.17, er * 0.68, er * 0.68, er * 0.50, col('#F6F1E6'));
      part(fh, 'sphere', s * exx - s * 0.012, hy + eyy + 0.03, 0.21,
           er * 0.34, er * 0.42, er * 0.30, col(EYE));
      part(fh, 'sphere', s * exx + 0.05, hy + eyy + 0.10, 0.22, 0.036, 0.036, 0.030, col(SHINE));
    }
  }
"""
s = s[:j0] + FACE + s[j1:]
io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
