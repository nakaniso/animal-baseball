# Card art: a rabbit's ears must clear the cap, and a penguin needs its beak.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

p = 'src/50-main.js'
s = io.open(p, encoding='utf-8').read()

a = """  g.fillStyle = A.fur;
  if (A.ear === 'round') { ear(-r * 0.82, -r * 0.72, r * 0.36); ear(r * 0.82, -r * 0.72, r * 0.36); }
  if (A.ear === 'long') {
    for (const s of [-1, 1]) { g.save(); g.translate(cx + s * r * 0.42, cy - r * 0.9); g.rotate(s * 0.3); g.beginPath(); g.ellipse(0, 0, r * 0.22, r * 0.62, 0, 0, 7); g.fill(); g.restore(); }
  }
  if (A.ear === 'point') {"""
b = """  g.fillStyle = A.fur;
  if (A.ear === 'round') { ear(-r * 0.82, -r * 0.72, r * 0.36); ear(r * 0.82, -r * 0.72, r * 0.36); }
  if (A.ear === 'point') {"""
assert a in s, 'miss ears'
s = s.replace(a, b)

a = """  g.fillStyle = team.trim; g.beginPath(); g.arc(cx, cy - r * 1.1, r * 0.12, 0, 7); g.fill();
  // muzzle + eyes
  g.fillStyle = A.fur2;
  g.beginPath(); g.ellipse(cx, cy + r * 0.36, r * 0.44, r * 0.32, 0, 0, 7); g.fill();"""
b = """  g.fillStyle = team.trim; g.beginPath(); g.arc(cx, cy - r * 1.1, r * 0.12, 0, 7); g.fill();
  // long ears sit on top of the cap, not under it
  if (A.ear === 'long') {
    for (const s of [-1, 1]) {
      g.save(); g.translate(cx + s * r * 0.46, cy - r * 1.16); g.rotate(s * 0.26);
      g.fillStyle = A.fur; g.beginPath(); g.ellipse(0, 0, r * 0.23, r * 0.66, 0, 0, 7); g.fill();
      g.fillStyle = A.fur2; g.beginPath(); g.ellipse(0, r * 0.06, r * 0.11, r * 0.44, 0, 0, 7); g.fill();
      g.restore();
    }
  }
  // muzzle + eyes
  g.fillStyle = A.fur2;
  g.beginPath(); g.ellipse(cx, cy + r * 0.36, r * 0.44, r * 0.32, 0, 0, 7); g.fill();
  if (A.beak) {
    g.fillStyle = A.beak;
    g.beginPath(); g.moveTo(cx - r * 0.20, cy + r * 0.26); g.lineTo(cx + r * 0.20, cy + r * 0.26);
    g.lineTo(cx, cy + r * 0.66); g.closePath(); g.fill();
  }"""
assert a in s, 'miss beak'
s = s.replace(a, b)

# the penguin has no muzzle nose dot under a beak
a = """  g.beginPath(); g.ellipse(cx, cy + r * 0.26, r * 0.13, r * 0.10, 0, 0, 7); g.fill();"""
b = """  if (!A.beak) { g.beginPath(); g.ellipse(cx, cy + r * 0.26, r * 0.13, r * 0.10, 0, 0, 7); g.fill(); }"""
assert a in s, 'miss nose'
s = s.replace(a, b)

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
