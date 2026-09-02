# Rabbit pass 3: seat the cap on the rounder skull, lose the visible seam
# around the snout, and shrink the mouth back to the little mark in the sketch.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
p = 'src/30-actors.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b)

# a rounder head needs the cap to sit lower, so make the offset per-species
rep("""    part(fh, 'dome', 0, hy + 0.29, 0.01, 0.74 * big, 0.38, 0.70 * big, cap);
    part(fh, 'box', 0, hy + 0.283, 0.31, 0.46, 0.07, 0.30, cap);
    part(fh, 'sphere', 0, hy + 0.46, 0.01, 0.09, 0.09, 0.09, trim);""",
"""    const cy = A.capY || 0;
    part(fh, 'dome', 0, hy + 0.29 + cy, 0.01, 0.74 * big, 0.38, 0.70 * big, cap);
    part(fh, 'box', 0, hy + 0.283 + cy, 0.31, 0.46, 0.07, 0.30, cap);
    part(fh, 'sphere', 0, hy + 0.46 + cy, 0.01, 0.09, 0.09, 0.09, trim);""", 'capY')
rep("""    part(fh, 'dome', 0, hy + 0.27, 0.01, 0.80 * big, 0.44, 0.78 * big, cap);
    part(fh, 'sphere', 0, hy + 0.285, 0.01, 0.80 * big, 0.22, 0.78 * big, cap);
    part(fh, 'box', 0, hy + 0.265, 0.34, 0.50, 0.075, 0.26, cap);""",
"""    const cy = A.capY || 0;
    part(fh, 'dome', 0, hy + 0.27 + cy, 0.01, 0.80 * big, 0.44, 0.78 * big, cap);
    part(fh, 'sphere', 0, hy + 0.285 + cy, 0.01, 0.80 * big, 0.22, 0.78 * big, cap);
    part(fh, 'box', 0, hy + 0.265 + cy, 0.34, 0.50, 0.075, 0.26, cap);""", 'capY helmet')
rep("""    part(fh, 'sphere', 0.335 * big, hy + 0.12, 0.02, 0.14, 0.32, 0.40, cap);
    part(fh, 'box', 0, hy + 0.40, 0.10, 0.09, 0.06, 0.60, trim);""",
"""    part(fh, 'sphere', 0.335 * big, hy + 0.12 + cy, 0.02, 0.14, 0.32, 0.40, cap);
    part(fh, 'box', 0, hy + 0.40 + cy, 0.10, 0.09, 0.06, 0.60, trim);""", 'capY flap')

# the mouth belongs just under the nose, and it is a small mark, not a wedge
rep("""  if (A.smallMouth && R.inkW === 0) {           // a little mouth under the nose
    const my2 = hy + (A.muzY === undefined ? -0.09 : A.muzY) - 0.060;
    for (const s of [-1, 1])
      part(fh, 'box', s * 0.046, my2, hzF - 0.050, 0.092, 0.028, 0.06,
           col('#4A3438'), 0, s * 0.52);
  }""",
"""  if (A.smallMouth && R.inkW === 0) {           // a little mouth under the nose
    const mz = A.muz || [0.2, 0.13, 0.16];
    const my2 = hy + (A.muzY === undefined ? -0.09 : A.muzY) + mz[1] * 0.40 - 0.078;
    for (const s of [-1, 1])
      part(fh, 'box', s * 0.038, my2, hzF - 0.062, 0.074, 0.024, 0.05,
           col('#4A3438'), 0, s * 0.30);
  }""", 'mouth')

rep("""             head: 'sphere', hw: 1.08, hh: 1.06, hd: 0.98,
             muz: [0.20, 0.13, 0.16], muzY: -0.150, muzZ: 0.255, muzC: '#F0EBE1',""",
"""             head: 'sphere', hw: 1.08, hh: 1.06, hd: 0.98, capY: -0.075,
             muz: [0.17, 0.11, 0.13], muzY: -0.145, muzZ: 0.260, muzC: '#F4F0E8',""", 'head tweak')

rep("    part(f, 'sphere', 0, y + 0.86 - i * 0.145, 0.295 - i * 0.012, 0.075, 0.075, 0.060, trim2);",
    "    part(f, 'sphere', 0, y + 0.86 - i * 0.145, 0.292 - i * 0.012, 0.058, 0.058, 0.050, trim2);", 'button size')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
