# Rabbit pass 2: the sketch has a plain face with just a nose and mouth (no
# pink snout), a wide round head that the cap actually sits down on, and
# buttons that read from the front.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
p = 'src/30-actors.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b)

rep("""             head: 'sphere', hw: 1.05, hh: 1.02, hd: 0.98,
             muz: [0.27, 0.185, 0.21], muzY: -0.150, muzZ: 0.250,
             noseR: 0.060, noseC: '#4A3438', smallMouth: 1, buttons: 1,""",
"""             head: 'sphere', hw: 1.08, hh: 1.06, hd: 0.98,
             muz: [0.20, 0.13, 0.16], muzY: -0.150, muzZ: 0.255, muzC: '#F0EBE1',
             noseR: 0.060, noseC: '#4A3438', smallMouth: 1, buttons: 1,""", 'head/muzzle')

# the snout can be fur-coloured while the ear lining and tail stay pink
rep("    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], fur2);",
    "    part(fh, 'sphere', 0, my, mzz, mz[0], mz[1], mz[2], A.muzC ? col(A.muzC) : fur2);", 'muzC')

# the torso sphere's front sits at z≈0.28; the buttons have to clear it
rep("    part(f, 'sphere', 0, y + 0.86 - i * 0.14, 0.215, 0.070, 0.070, 0.045, trim2);",
    "    part(f, 'sphere', 0, y + 0.86 - i * 0.145, 0.295 - i * 0.012, 0.075, 0.075, 0.060, trim2);", 'buttons z')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
