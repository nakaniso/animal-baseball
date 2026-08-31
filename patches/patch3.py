# Visual pass: raise/pull the batting camera off the catcher, rebuild the
# infield so each park uses its own surface (no dirt inside a supermarket),
# and stop the play-by-play log from covering the control hints.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def rep(s, a, b, label):
    if a not in s: raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

# ================= 20-world.js : infield =================
p = 'src/20-world.js'; s = rd(p)
s = rep(s, """function addDiamond(S, dirt, chalk, grassMound) {
  // infield dirt: a quad rotated 45deg is exactly a diamond
  S.plate(0, 0.012, 19.4, 40, 40, dirt, 45 * DEG);
  S.ring(0, 0.02, 18.44, 5.6, grassMound || dirt);           // mound circle
  S.ring(0, 0.022, 18.44, 2.6, shade(dirt, 1.08));
  S.ring(0, 0.02, 0, 4.2, dirt);                              // home circle""",
"""/* opt = { dirt, chalk, fill (skinned infield?), grass (grass inside the paths) } */
function addDiamond(S, opt) {
  const dirt = opt.dirt, chalk = opt.chalk;
  if (opt.fill) {
    // a quad rotated 45deg is exactly the shape of a skinned infield
    S.plate(0, 0.012, 19.4, 40, 40, dirt, 45 * DEG);
    if (opt.grass) S.plate(0, 0.016, 19.4, 24, 24, opt.grass, 45 * DEG);
  }
  // base paths, drawn whether or not the infield is skinned
  const pts = [HOME_POS, BASE_POS[0], BASE_POS[1], BASE_POS[2]];
  for (let i = 0; i < 4; i++) {
    const a = pts[i], b = pts[(i + 1) % 4];
    S.plate((a[0] + b[0]) / 2, 0.018, (a[1] + b[1]) / 2, 2.6,
            Math.hypot(b[0] - a[0], b[1] - a[1]), dirt,
            Math.atan2(b[0] - a[0], b[1] - a[1]));
  }
  S.ring(0, 0.02, 18.44, 5.6, dirt);                          // mound circle
  S.ring(0, 0.022, 18.44, 2.6, shade(dirt, 1.08));
  S.ring(0, 0.02, 0, 4.2, dirt);                              // home circle""", 'addDiamond')

s = rep(s, "      addDiamond(S, '#C08551', '#F4EFE2', '#C08551');",
           "      addDiamond(S, { dirt: '#C08551', chalk: '#F4EFE2', fill: 1, grass: '#42964F' });", 'dome diamond')
s = rep(s, "      addDiamond(S, '#B98A5E', '#F0EDE4', '#B98A5E');",
           "      addDiamond(S, { dirt: '#6C7177', chalk: '#F0EDE4' });", 'road diamond')
s = rep(s, "      addDiamond(S, '#C7B79C', '#FFFFFF', '#C7B79C');",
           "      addDiamond(S, { dirt: '#C6BCA6', chalk: '#FFFFFF' });", 'market diamond')
s = rep(s, "      addDiamond(S, '#A8865C', '#EFEDE0', '#A8865C');",
           "      addDiamond(S, { dirt: '#A8865C', chalk: '#EFEDE0', fill: 1 });", 'river diamond')
s = rep(s, "      addDiamond(S, '#9A9AA2', '#E8ECF4', '#9A9AA2');",
           "      addDiamond(S, { dirt: '#9A9AA2', chalk: '#E8ECF4', fill: 1 });", 'moon diamond')
# the catcher sets up a touch deeper now
s = rep(s, "{ k: 'C',  a: 0,   d: () => -2.9,           nm: '捕手' }",
           "{ k: 'C',  a: 0,   d: () => -3.4,           nm: '捕手' }", 'catcher depth')
wr(p, s)

# ================= 50-main.js : camera =================
p = 'src/50-main.js'; s = rd(p)
s = rep(s, """    ex = 0.55; ey = 5.4; ez = -13.0;
    tx = -0.05; ty = 1.45; tz = 13; fov = 44; sp = 5;""",
"""    ex = 0.55; ey = 6.4; ez = -11.5;
    tx = -0.05; ty = 1.05; tz = 8.5; fov = 40; sp = 5;""", 'bat cam')
s = rep(s, """  drawAnimal(-1.45, -4.35, 0, { animal: 'hippo', uni: '#2B3138', trim: '#4A525C', cap: '#1E242A' },
    { armL: 0.5, armR: -0.5, bob: bob * 0.4 }, -0.30);""",
"""  drawAnimal(-1.55, -4.9, 0, { animal: 'hippo', uni: '#2B3138', trim: '#4A525C', cap: '#1E242A' },
    { armL: 0.5, armR: -0.5, bob: bob * 0.4 }, -0.30);""", 'umpire')
s = rep(s, "  while (box.children.length > 9) box.removeChild(box.firstChild);",
           "  while (box.children.length > 6) box.removeChild(box.firstChild);", 'log cap')
wr(p, s)

# ================= 00-shell.html : log placement =================
p = 'src/00-shell.html'; s = rd(p)
s = rep(s, "#log{position:absolute;bottom:16px;right:14px;width:272px;",
           "#log{position:absolute;bottom:70px;right:14px;width:262px;", 'log pos')
s = rep(s, "@media (max-width:660px){\n  #log{display:none}",
           "@media (max-width:900px){\n  #log{display:none}", 'log hide')
wr(p, s)
print('patched ok')
