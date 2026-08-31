# Face pass 2: almond eyes with whites and a small pupil (the sketch draws them
# as outlined ovals, not black beads), the brow line moved clear of the cap
# brim, the nose sitting high on the muzzle, and the cap lifted off the forehead.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
box = {'s': rd('src/30-actors.js')}
def rep(a, b, label):
    if a not in box['s']: raise SystemExit('MISS: ' + label)
    box['s'] = box['s'].replace(a, b)

rep("""             muz: [0.50, 0.40, 0.32], muzY: -0.11, muzZ: 0.24, noseR: 0.13,
             brow: 1, earR: 0.25, earX: 0.325, earY: 0.30, earD: 0.62,
             eyeX: 0.165, eyeW: 0.175, eyeH: 0.155 },""",
"""             muz: [0.53, 0.355, 0.32], muzY: -0.115, muzZ: 0.235, noseR: 0.115,
             brow: 1, earR: 0.25, earX: 0.325, earY: 0.31, earD: 0.62,
             eyeX: 0.168, eyeW: 0.155, eyeH: 0.125 },""", 'bear spec')
rep("  bear:    { ear: 'round',  fur: '#9A7150', fur2: '#CDA87E', belly: 1, tail: 'nub',",
    "  bear:    { ear: 'round',  fur: '#96683F', fur2: '#DFC49B', belly: 1, tail: 'nub',", 'bear colours')

rep("""    const nr = A.noseR || 0.11;
    part(fh, 'sphere', 0, my + mz[1] * 0.24, mzz + mz[2] * 0.42,
         nr, nr * 0.80, nr * 0.80, col('#33291F'));""",
"""    const nr = A.noseR || 0.11;
    part(fh, 'sphere', 0, my + mz[1] * 0.40, mzz + mz[2] * 0.40,
         nr, nr * 0.74, nr * 0.72, col('#33291F'));""", 'nose')

rep("""  const ex = A.eyeX || 0.145, ew = A.eyeW || 0.115, eh = A.eyeH || 0.13;
  for (const s of [-1, 1]) {
    part(fh, 'sphere', s * ex, hy + 0.07, hzF - 0.03, ew, eh, 0.10, col(EYE));
    part(fh, 'sphere', s * ex + 0.035, hy + 0.105, hzF + 0.005, 0.05, 0.05, 0.04, col(SHINE));
    if (A.brow)
      part(fh, 'box', s * ex, hy + 0.215, hzF - 0.035, 0.215, 0.048, 0.07,
           shade(A.fur, 0.48), 0, s * 0.13);
  }""",
"""  const ex = A.eyeX || 0.150, ew = A.eyeW || 0.140, eh = A.eyeH || 0.115;
  for (const s of [-1, 1]) {
    // an outlined oval with a pupil in it, as drawn
    part(fh, 'sphere', s * ex, hy + 0.075, hzF - 0.045, ew, eh, 0.075, col('#F6F1E6'));
    part(fh, 'sphere', s * ex + s * 0.012, hy + 0.068, hzF - 0.018,
         ew * 0.50, eh * 0.66, 0.055, col(EYE));
    part(fh, 'sphere', s * ex + 0.030, hy + 0.100, hzF + 0.002, 0.040, 0.040, 0.032, col(SHINE));
    if (A.brow)
      part(fh, 'box', s * ex, hy + 0.192, hzF - 0.055, 0.235, 0.052, 0.075,
           shade(A.fur, 0.40), 0, s * 0.15);
  }""", 'eyes')

rep("""    part(fh, 'dome', 0, hy + 0.22, 0.01, 0.80 * big, 0.50, 0.78 * big, cap);
    part(fh, 'sphere', 0, hy + 0.235, 0.01, 0.80 * big, 0.24, 0.78 * big, cap);
    part(fh, 'box', 0, hy + 0.215, 0.33, 0.50, 0.075, 0.26, cap);
    // the flap covers the ear turned toward the pitcher (local +x)
    part(fh, 'sphere', 0.335 * big, hy + 0.08, 0.02, 0.14, 0.34, 0.40, cap);
    part(fh, 'box', 0, hy + 0.35, 0.10, 0.09, 0.06, 0.60, trim);""",
"""    part(fh, 'dome', 0, hy + 0.27, 0.01, 0.80 * big, 0.44, 0.78 * big, cap);
    part(fh, 'sphere', 0, hy + 0.285, 0.01, 0.80 * big, 0.22, 0.78 * big, cap);
    part(fh, 'box', 0, hy + 0.265, 0.34, 0.50, 0.075, 0.26, cap);
    // the flap covers the ear turned toward the pitcher (local +x)
    part(fh, 'sphere', 0.335 * big, hy + 0.12, 0.02, 0.14, 0.32, 0.40, cap);
    part(fh, 'box', 0, hy + 0.40, 0.10, 0.09, 0.06, 0.60, trim);""", 'helmet')
rep("""    part(fh, 'dome', 0, hy + 0.24, 0.01, 0.70 * big, 0.42, 0.66 * big, cap);
    part(fh, 'box', 0, hy + 0.235, 0.30, 0.44, 0.07, 0.30, cap);
    part(fh, 'sphere', 0, hy + 0.44, 0.01, 0.09, 0.09, 0.09, trim);""",
"""    part(fh, 'dome', 0, hy + 0.29, 0.01, 0.74 * big, 0.38, 0.70 * big, cap);
    part(fh, 'box', 0, hy + 0.283, 0.31, 0.46, 0.07, 0.30, cap);
    part(fh, 'sphere', 0, hy + 0.46, 0.01, 0.09, 0.09, 0.09, trim);""", 'cap')
wr('src/30-actors.js', box['s'])
print('patched ok')
