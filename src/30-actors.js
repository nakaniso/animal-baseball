/* ============================================================
   30-actors.js — deformed animal players, bats, gloves, the ball
   ============================================================ */
'use strict';

/* local(character) -> world, given a yaw frame */
function yawFrame(x, z, ry) { return { x, z, ry, c: Math.cos(ry), s: Math.sin(ry), t: 0 }; }
function L2W(f, lx, lz) { return [f.x + lx * f.c + lz * f.s, f.z - lx * f.s + lz * f.c]; }

/* f.t tips the whole body about its hips — used when a car flattens someone */
function part(f, prim, lx, ly, lz, sx, sy, sz, c, rx, rz) {
  let Y = ly, Z = lz;
  if (f.t) {
    const dy = ly - f.pivot;
    Y = f.pivot + dy * f.ct - lz * f.st;
    Z = dy * f.st + lz * f.ct;
  }
  const [wx, wz] = L2W(f, lx, Z);
  R.d(prim, wx, Y, wz, (rx || 0) + f.t, f.ry, rz || 0, sx, sy, sz, c);
}

/* a limb hanging from a joint, rotated by rx (swing) and rz (splay) */
function limb(f, jx, jy, jz, rx, rz, len, rad, c, endC, endS, flat) {
  const cz = Math.cos(rz), sz = Math.sin(rz), cx = Math.cos(rx), sx = Math.sin(rx);
  const dx = sz, dy = -cx * cz, dz = -sx * cz;
  part(f, 'cyl', jx + dx * len * 0.5, jy + dy * len * 0.5, jz + dz * len * 0.5,
       rad * 2, len, rad * 2, c, rx, rz);
  if (endC === null) return [jx + dx * len, jy + dy * len, jz + dz * len];
  if (endC) {
    const s = endS || rad * 2.5;
    if (flat) part(f, 'rbox', jx + dx * len, jy + dy * len - s * 0.08, jz + dz * len + s * 0.16,
                   s * 0.92, s * 0.66, s * 1.34, endC, rx, rz);
    else part(f, 'sphere', jx + dx * len, jy + dy * len, jz + dz * len, s, s * 0.9, s, endC);
  }
  return [jx + dx * len, jy + dy * len, jz + dz * len];
}

/* Two-bone IK in world space: the hand lands exactly on the target, so whatever
   it is holding stays held. Cartoon arms stretch rather than fall short. */
function armIK(sx, sy, sz, hx, hy, hz, L1, L2, pole, rad, c, handC) {
  let dx = hx - sx, dy = hy - sy, dz = hz - sz;
  let d = Math.hypot(dx, dy, dz) || 1e-4;
  if (d > (L1 + L2) * 0.995) {
    // cartoon arms give a little, but never more than a third of their length;
    // past that the hand is pulled in rather than the limb turned into a pole
    const need = d / (L1 + L2);
    const give = Math.min(need, 1.32);
    L1 *= give * 1.02; L2 *= give * 1.02;
    if (need > 1.32) {
      const k = ((L1 + L2) * 0.995) / d;
      hx = sx + dx * k; hy = sy + dy * k; hz = sz + dz * k;
      dx *= k; dy *= k; dz *= k; d *= k;
    }
  }
  const ux = dx / d, uy = dy / d, uz = dz / d;
  const a = clamp((d * d + L1 * L1 - L2 * L2) / (2 * d), -L1, L1);
  const h = Math.sqrt(Math.max(0, L1 * L1 - a * a));
  // project the pole hint onto the plane perpendicular to the shoulder->hand axis
  let px = pole[0], py = pole[1], pz = pole[2];
  const dot = px * ux + py * uy + pz * uz;
  px -= ux * dot; py -= uy * dot; pz -= uz * dot;
  let pl = Math.hypot(px, py, pz);
  if (pl < 1e-4) { px = -ux * uy; py = 1 - uy * uy; pz = -uz * uy; pl = Math.hypot(px, py, pz) || 1; }
  px /= pl; py /= pl; pz /= pl;
  const ex = sx + ux * a + px * h, ey = sy + uy * a + py * h, ez = sz + uz * a + pz * h;
  R.seg('cyl', sx, sy, sz, ex, ey, ez, rad, c);
  R.seg('cyl', ex, ey, ez, hx, hy, hz, rad * 0.9, c);
  R.b('sphere', ex, ey, ez, rad * 2, rad * 2, rad * 2, c);
  if (handC !== null) R.b('sphere', hx, hy, hz, rad * 2.2, rad * 2.1, rad * 2.2, handC || c);
  return [hx, hy, hz];
}

/* ---------- animal species ---------- */
/* hw/hh/hd scale the head; muz is the size of the muzzle; brow adds the drawn
   eyebrow strokes; earR/earX/earY place the ears. */
const ANIMALS = {
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
             earR: 0.285, earX: 0.275, earY: 0.13, earZ: 0.24 },

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
};

const EYE = '#22282F', SHINE = '#FFFFFF';

/* pose: { armL, armR, legL, legR, lean, bob, ry } — all radians */
const IDLE = { armL: 0.12, armR: -0.12, legL: 0, legR: 0, lean: 0, bob: 0 };

/* run `draw` once as an ink shell and once as the fill, for species drawn in
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
  }
  const p = pose || IDLE;
  const f = yawFrame(x, z, ry);
  const y = (y0 || 0) + (p.bob || 0);
  if (p.fall) { f.t = p.fall; f.ct = Math.cos(p.fall); f.st = Math.sin(p.fall); f.pivot = y + 0.34; }
  const big = A.big ? 1.12 : 1;
  const fur = col(A.fur), fur2 = col(A.fur2);
  const uni = col(look.uni), trim = col(look.trim), cap = col(look.cap);

  shadow(x, z, (p.fall ? 0.72 : 0.44) * big, 0.34);

  // legs (local -x is the character's right side, +x their left)
  const sp = p.spread || 0;
  const pant = shade(look.uni, 0.93), shoe = shade(look.cap, 0.66);
  limb(f, -(0.155 * big + sp), y + 0.44, 0, p.legL || 0, -0.04, 0.36, 0.12, pant, shoe, 0.30, 1);
  limb(f, 0.155 * big + sp, y + 0.44, 0, p.legR || 0, 0.04, 0.36, 0.12, pant, shoe, 0.30, 1);

  // torso
  part(f, 'sphere', 0, y + 0.74, 0, 0.66 * big, 0.70, 0.56 * big, uni, p.lean || 0);
  part(f, 'sphere', 0, y + 0.97, 0.01, 0.50, 0.14, 0.45, trim);   // jersey collar
  part(f, 'box', 0, y + 0.72, 0.185, 0.075, 0.42, 0.05, trim);  // button placket
  // pinstripes down the front, and the belt at the waist
  const stripe = shade(look.uni, 0.80);
  for (const i of [-2, -1, 1, 2]) {
    const px = i * 0.098 * big;
    const k = Math.max(0, 1 - (px / (0.34 * big)) ** 2);
    part(f, 'box', px, y + 0.74, 0.28 * big * Math.sqrt(k) - 0.01, 0.026, 0.34, 0.035, stripe);
  }
  part(f, 'sphere', 0, y + 0.515, 0.02, 0.60 * big, 0.10, 0.50 * big, shade(look.cap, 0.85));

  // arms — either swung by rotation, or aimed at a world-space grip
  const shY = y + 0.94;
  let hl, hr;
  if (p.handL || p.handR) {
    // reaching arms hang off narrower shoulders and get a longer bone pair, so
    // the front arm can cross the chest to the knob without rubber-banding
    const SH = 0.17 * big, BONE = 0.32;
    const [slx, slz] = L2W(f, -SH, 0);
    const [srx, srz] = L2W(f, SH, 0);
    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    const hand = p.gloveC ? col(p.gloveC) : fur;
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.075, uni,
              p.noPawL ? null : hand)
      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.34, 0.112, uni, fur, 0.27);
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.075, uni,
              p.noPawR ? null : hand)
      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.34, 0.112, uni,
             p.noPawR ? null : fur, 0.27);
  } else {
    hl = limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.34, 0.112, uni,
              p.noPawL ? null : fur, 0.27);
    hr = limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.34, 0.112, uni,
              p.noPawR ? null : fur, 0.27);
  }

  // head — may be turned independently of the body (a batter watching the ball)
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
    const ez = A.earZ === undefined ? 0.05 : A.earZ;
    for (const s of [-1, 1]) {
      part(fh, 'sphere', s * exx, hy + eyy, ez, er, er, er * 0.92, fur);
      part(fh, 'sphere', s * exx, hy + eyy + 0.02, ez + 0.11, er * 0.66, er * 0.66, er * 0.46, col('#F6F1E6'));
      part(fh, 'sphere', s * exx - s * 0.014, hy + eyy + 0.02, ez + 0.15,
           er * 0.34, er * 0.42, er * 0.28, col(EYE));
      part(fh, 'sphere', s * exx + 0.05, hy + eyy + 0.09, ez + 0.17, 0.036, 0.036, 0.030, col(SHINE));
    }
  }
  // tail
  if (A.tail === 'puff') part(f, 'sphere', 0, y + 0.66, -0.30, 0.24, 0.24, 0.24, fur2);
  if (A.tail === 'nub') part(f, 'sphere', 0, y + 0.60, -0.30, 0.16, 0.16, 0.16, fur);
  if (A.tail === 'long') part(f, 'sphere', 0, y + 0.78, -0.36, 0.14, 0.44, 0.14, fur, 0.5);
  if (A.tail === 'bushy') {
    part(f, 'sphere', 0, y + 0.72, -0.38, 0.26, 0.46, 0.26, fur, 0.6);
    part(f, 'sphere', 0, y + 0.94, -0.50, 0.20, 0.20, 0.20, fur2);
  }
  // headwear: a batting helmet at the plate and on the bases, otherwise a cap
  if (p.noHat) { /* a shopper, not a ballplayer */ }
  else if (p.helmet) {
    part(fh, 'dome', 0, hy + 0.27, 0.01, 0.80 * big, 0.44, 0.78 * big, cap);
    part(fh, 'sphere', 0, hy + 0.285, 0.01, 0.80 * big, 0.22, 0.78 * big, cap);
    part(fh, 'box', 0, hy + 0.265, 0.34, 0.50, 0.075, 0.26, cap);
    // the flap covers the ear turned toward the pitcher (local +x)
    part(fh, 'sphere', 0.335 * big, hy + 0.12, 0.02, 0.14, 0.32, 0.40, cap);
    part(fh, 'box', 0, hy + 0.40, 0.10, 0.09, 0.06, 0.60, trim);
  } else {
    part(fh, 'dome', 0, hy + 0.29, 0.01, 0.74 * big, 0.38, 0.70 * big, cap);
    part(fh, 'box', 0, hy + 0.283, 0.31, 0.46, 0.07, 0.30, cap);
    part(fh, 'sphere', 0, hy + 0.46, 0.01, 0.09, 0.09, 0.09, trim);
  }

  return { f, hl, hr, hy, y };
}

/* A bat to real proportions: 2.5cm handle, a taper, a 6.5cm barrel, knob at the
   bottom. `grip` is where the bottom hand sits, `dir` points at the barrel. */
function drawBatRig(grip, dir, len, wood, tape) {
  const P = (t) => [grip[0] + dir[0] * t, grip[1] + dir[1] * t, grip[2] + dir[2] * t];
  const w = col(wood), g = col(tape);
  const knob = P(-0.055), hEnd = P(0.34), taper = P(0.60), tip = P(len);
  R.seg('cyl', knob[0], knob[1], knob[2], hEnd[0], hEnd[1], hEnd[2], 0.017, g);
  R.seg('taper', taper[0], taper[1], taper[2], hEnd[0], hEnd[1], hEnd[2], 0.033, w);
  R.seg('cyl', taper[0], taper[1], taper[2], tip[0], tip[1], tip[2], 0.033, w);
  R.b('sphere', tip[0], tip[1], tip[2], 0.070, 0.070, 0.070, w);
  const k2 = P(-0.02);
  R.seg('cyl', knob[0], knob[1], knob[2], k2[0], k2[1], k2[2], 0.031, g);
}

/* the two fists wrapped around the handle */
function drawGrip(grip, dir, at, c) {
  const P = (t) => [grip[0] + dir[0] * t, grip[1] + dir[1] * t, grip[2] + dir[2] * t];
  const a = P(at - 0.055), b = P(at + 0.055);
  R.seg('sphere', a[0], a[1], a[2], b[0], b[1], b[2], 0.082, col(c));
}

/* A fielder's mitt: palm, four finger ridges, a thumb and the web between
   them. All one leather; the shape does the work, not a painted pocket. */
function drawGlove(pt, ry) {
  if (!pt) return;
  const a = ry || 0, fx = Math.sin(a), fz = Math.cos(a);
  const sx = fz, sz = -fx;                       // across the mitt
  const x = pt[0] + fx * 0.05, y = pt[1], z = pt[2] + fz * 0.05;
  const hide = col('#7A4A22'), dark = col('#46280F'), web = col('#9A6B38');
  R.d('rbox', x, y - 0.02, z, 0, a, 0, 0.38, 0.36, 0.20, hide);          // palm
  for (let i = -1; i <= 2; i++)                                          // fingers
    R.d('rbox', x + sx * i * 0.083, y + 0.20, z + sz * i * 0.083, 0, a, 0,
        0.072, 0.22, 0.18, hide);
  R.d('rbox', x - sx * 0.235, y - 0.03, z - sz * 0.235, 0, a, 0, 0.11, 0.30, 0.19, hide);
  R.d('rbox', x - sx * 0.145, y + 0.18, z - sz * 0.145, 0, a, 0, 0.11, 0.20, 0.16, web);
  R.d('rbox', x + fx * 0.075, y - 0.05, z + fz * 0.075, 0, a, 0, 0.20, 0.18, 0.05, dark);
  R.d('rbox', x, y - 0.22, z, 0, a, 0, 0.32, 0.10, 0.18, dark);          // heel
}

/* ---------- the ball ---------- */
const BALL_R = 0.14;
/* a real ball is a speck at 80m — grow it with distance so the player can
   always follow the flight */
function ballScale(x, y, z) {
  const d = Math.hypot(x - R.eye[0], y - R.eye[1], z - R.eye[2]);
  // Nearly true perspective: the compensation is small enough that the ball
  // visibly shrinks as it flies away, which is the whole depth cue.
  return BALL_R * 2 * clamp(Math.pow(d / 12, 0.15), 1, 1.5) * (G.ballBoost || 1);
}
function drawBall(x, y, z, spin) {
  const s = ballScale(x, y, z);
  R.b('sphere', x, y, z, s, s, s, col('#FBF7EC'));
  R.d('cyl', x, y, z, Math.PI / 2, spin || 0, 0, s * 0.78, s * 0.25, s * 0.78, col('#D9402E'));
}
function drawTrail(tr) {
  for (let i = 0; i < tr.length; i += 3) {
    const k = 1 - i / tr.length;
    const s = ballScale(tr[i], tr[i + 1], tr[i + 2]) * 0.72 * k * k;
    if (s < 0.012) continue;
    R.b('sphere', tr[i], tr[i + 1], tr[i + 2], s, s, s, col('#FFE9B0'));
  }
}

/* ============================================================
   Teams
   ============================================================ */
const NAME_POOL = {
  bear:    ['ゴロー', 'ブンタ', 'クマキチ', 'ドスコイ', 'ハチベエ', 'テツ', 'モリオ', 'ガンタ', 'ノボル'],
  rabbit:  ['ミミ', 'ピョン', 'ラビ', 'シロタ', 'ハネダ', 'ツキノ', 'コハネ', 'トビオ', 'ユキ'],
  cat:     ['タマ', 'ミケ', 'ニャン太', 'トラキチ', 'クロベエ', 'シッポ', 'モモ', 'ヒゲオ', 'コタツ'],
  frog:    ['ケロ', 'ゲコタ', 'アマガエル', 'ピョンジ', 'ヌマオ', 'ハスオ', 'グエコ', 'ミズキ', 'カジカ'],
  penguin: ['ペンタ', 'コオリ', 'フブキ', 'ヨチヨチ', 'シラス', 'アデリー', 'ヒレタ', 'ナンキョク', 'ツララ'],
  fox:     ['コン', 'キツネビ', 'アカネ', 'シッポリ', 'イナリ', 'ゴンタ', 'ヒノ', 'ミミナガ', 'ユウ'],
  panda:   ['パンダ丸', 'シャンシャン', 'ササオ', 'モウソウ', 'クロシロ', 'マルオ', 'ゴロゴロ', 'タケゾウ', 'リンリン'],
  hippo:   ['カバオ', 'ドロン', 'ヌマヅ', 'オオクチ', 'ブクブク', 'ミズベ', 'ズッシリ', 'アグリ', 'ハナ'],
};

const TEAMS = [
  { id: 'bears',    name: 'もりのクマーズ',   animal: 'bear',    uni: '#7B4B2A', trim: '#F0D9A8', cap: '#5E3620',
    tag: 'POWER',   desc: 'とにかく長打。当たれば飛ぶが、確実性は低め。', pow: 5, con: 2, spd: 2, def: 3 },
  { id: 'rabbits',  name: 'はらっぱラビッツ', animal: 'rabbit',  uni: '#E8EDF2', trim: '#E86A8A', cap: '#D9527A',
    tag: 'SPEED',   desc: '足が速い。内野安打も盗塁もお手のもの。', pow: 2, con: 4, spd: 5, def: 4 },
  { id: 'cats',     name: 'ねこじゃらしキャッツ', animal: 'cat', uni: '#F2C14E', trim: '#3A3630', cap: '#2E2A24',
    tag: 'CONTACT', desc: 'バットに当てるのがうまい。四球も選ぶ。', pow: 3, con: 5, spd: 3, def: 3 },
  { id: 'frogs',    name: 'ぬまたフロッグス', animal: 'frog',    uni: '#4E8A4E', trim: '#E8F0C8', cap: '#2E5E34',
    tag: 'BALANCE', desc: 'すべてが平均的。クセがなく扱いやすい。', pow: 3, con: 3, spd: 3, def: 3 },
  { id: 'penguins', name: 'こおりやまペンギンズ', animal: 'penguin', uni: '#28405E', trim: '#F4F1E6', cap: '#1B2C42',
    tag: 'DEFENSE', desc: '守備が堅い。相手の打球をよく捕る。', pow: 3, con: 3, spd: 2, def: 5 },
  { id: 'foxes',    name: 'あかやまフォクシーズ', animal: 'fox',  uni: '#C4502E', trim: '#F6EFE2', cap: '#8E3A20',
    tag: 'PITCHING',desc: '投手陣が強力。変化球のキレがちがう。', pow: 3, con: 3, spd: 3, def: 4, arm: 5 },
];

const teamById = (id) => TEAMS.find((t) => t.id === id);

/* Build a 9-man roster with a batting order and fielding positions. */
function makeTeam(def) {
  const names = NAME_POOL[def.animal].slice();
  const order = ['CF', 'SS', 'RF', '1B', 'LF', '3B', 'C', '2B', 'P'];
  const roster = order.map((posK, i) => {
    const v = (s, spread) => clamp(s / 5 + rnd(-spread, spread), 0.12, 1.0);
    return {
      name: names[i], no: i + 1, pos: posK,
      look: { animal: def.animal, uni: def.uni, trim: def.trim, cap: def.cap },
      power: v(def.pow, 0.14), contact: v(def.con, 0.14), speed: v(def.spd, 0.12), defense: v(def.def, 0.12),
      arm: (def.arm || 3) / 5,
      ab: 0, h: 0, hr: 0, rbi: 0, k: 0, bb: 0, hbp: 0,
    };
  });
  // the pitcher bats ninth but is the best arm
  roster[8].arm = clamp((def.arm || 3) / 5 + 0.18, 0, 1);
  roster[8].power = clamp(roster[8].power - 0.22, 0.1, 1);
  roster[8].contact = clamp(roster[8].contact - 0.18, 0.1, 1);
  return { def, name: def.name, roster, animal: def.animal, uni: def.uni, trim: def.trim, cap: def.cap };
}
