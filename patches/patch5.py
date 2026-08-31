# Keep the ball readable at any distance, tighten the fly camera, and give the
# riverside ground some contrast against its infield.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def rep(s, a, b, label):
    if a not in s: raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

# --- ball keeps a usable on-screen size as it flies away ---
p = 'src/30-actors.js'; s = rd(p)
s = rep(s, """const BALL_R = 0.14;
function drawBall(x, y, z, spin) {
  R.b('sphere', x, y, z, BALL_R * 2, BALL_R * 2, BALL_R * 2, col('#FBF7EC'));
  R.d('cyl', x, y, z, Math.PI / 2, spin || 0, 0, BALL_R * 1.55, BALL_R * 0.5, BALL_R * 1.55, col('#D9402E'));
}
function drawTrail(tr) {
  for (let i = 0; i < tr.length; i += 3) {
    const k = 1 - i / tr.length;
    const s = BALL_R * 1.5 * k * k;
    if (s < 0.012) continue;
    R.b('sphere', tr[i], tr[i + 1], tr[i + 2], s, s, s, col('#FFE9B0'));
  }
}""",
"""const BALL_R = 0.14;
/* a real ball is a speck at 80m — grow it with distance so the player can
   always follow the flight */
function ballScale(x, y, z) {
  const d = Math.hypot(x - R.eye[0], y - R.eye[1], z - R.eye[2]);
  return BALL_R * 2 * clamp(d / 13, 1, 4.2);
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
}""", 'ball scale')
wr(p, s)

# --- fly camera tracks a little tighter ---
p = 'src/50-main.js'; s = rd(p)
s = rep(s, "tx = b.x * 0.9; ty = b.y * 0.85 + 0.6; tz = b.z * 0.96; fov = 48; sp = 2.4;",
           "tx = b.x * 0.9; ty = b.y * 0.85 + 0.6; tz = b.z * 0.96; fov = 48; sp = 3.4;", 'fly cam')
wr(p, s)

# --- riverside: grassier ground so the infield reads separately ---
p = 'src/20-world.js'; s = rd(p)
s = rep(s, "      S.plate(0, 0, 40, 460, 460, '#9C9464');",
           "      S.plate(0, 0, 40, 460, 460, '#8B9455');", 'river ground')
s = rep(s, "      for (let i = -5; i <= 8; i++) S.plate(rnd(-60, 60), 0.006, i * 18, rnd(14, 34), rnd(8, 16), '#8E9A5E');",
           "      for (let i = -5; i <= 8; i++) S.plate(rnd(-60, 60), 0.006, i * 18, rnd(14, 34), rnd(8, 16), '#7C8A4C');", 'river patches')
s = rep(s, "      addDiamond(S, { dirt: '#A8865C', chalk: '#EFEDE0', fill: 1 });",
           "      addDiamond(S, { dirt: '#B08A56', chalk: '#EFEDE0', fill: 1 });", 'river dirt')
wr(p, s)
print('patched ok')
