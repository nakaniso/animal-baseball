# The first hand-drawn cell, and the 3D nose bump it replaces.
#
# The rabbit's muzzle was a fur-coloured sphere sitting just under the drawn
# nose. With the nose now part of the artwork the bump only adds a shading
# ridge across the middle of the face, so it goes.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s:
            raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)


b64 = io.open('patches/scan-rabbit-0.b64', encoding='utf-8').read().strip()
assert b64.startswith('iVBORw0KGgo'), 'not a PNG'
assert "'" not in b64 and chr(92) not in b64, 'base64 must be safe inside a JS string'

edit('src/30-actors.js', [
    ("""  // the rabbit's muzzle is a flush bump, so its nose and mouth go on the head
  rabbit:  { eye: 'dot',    eyeX: 0.200, eyeY: 0.355, eyeR: 0.062, onHead: 1,""",
     """  // the rabbit has no muzzle at all, so its nose and mouth go on the head
  rabbit:  { eye: 'dot',    eyeX: 0.200, eyeY: 0.355, eyeR: 0.062, onHead: 1,""",
     'comment'),
    ("""             head: 'sphere', hw: 1.08, hh: 1.06, hd: 0.98, capY: -0.075,
             muz: [0.17, 0.11, 0.13], muzY: -0.145, muzZ: 0.260, muzC: '#F4F0E8',
             noseR: 0.060, noseC: '#4A3438', smallMouth: 1, buttons: 1,""",
     """             head: 'sphere', hw: 1.08, hh: 1.06, hd: 0.98, capY: -0.075,
             buttons: 1,                   // no muzzle — the nose is drawn on""",
     'drop muzzle'),
    ("""const FACE_SCANS = {
};""",
     "const FACE_SCANS = {\n  'rabbit:0': 'data:image/png;base64," + b64 + "',\n};",
     'scan'),
])

print('patched ok')
