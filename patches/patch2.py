# Mirror the world so that, from the camera behind home plate, first base is on
# the RIGHT (matching the HUD diamond). Screen-right is world -x, so first base
# moves to -x and the right-handed batter's box to +x. Also lifts the camera so
# the catcher and umpire stop covering the strike zone.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def rep(s, a, b, label):
    if a not in s: raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

# ================= 20-world.js =================
p = '20-world.js'; s = rd(p)
s = rep(s, "const BASE_POS = [[19.4, 19.4], [0, 38.8], [-19.4, 19.4]]; // 1st, 2nd, 3rd",
           "const BASE_POS = [[-19.4, 19.4], [0, 38.8], [19.4, 19.4]]; // 1st, 2nd, 3rd", 'bases')
s = rep(s, "/* polar helper: angle 0 = straight to centre field (+z), + = right field (+x) */",
           "/* polar helper: angle 0 = straight to centre field (+z), + = LEFT field (+x,\n   third-base side). Screen-right is world -x, so +x draws on the left. */", 'polar note')
s = rep(s, """  { k: '1B', a: 38,  d: () => 27,             nm: '一塁手' },
  { k: '2B', a: 20,  d: () => 36,             nm: '二塁手' },
  { k: 'SS', a: -20, d: () => 36,             nm: '遊撃手' },
  { k: '3B', a: -38, d: () => 27,             nm: '三塁手' },
  { k: 'LF', a: -30, d: (st) => fenceAt(st, -30) * 0.76, nm: '左翼手' },
  { k: 'CF', a: 0,   d: (st) => fenceAt(st, 0) * 0.78,   nm: '中堅手' },
  { k: 'RF', a: 30,  d: (st) => fenceAt(st, 30) * 0.76,  nm: '右翼手' },""",
"""  { k: '1B', a: -38, d: () => 27,             nm: '一塁手' },
  { k: '2B', a: -20, d: () => 36,             nm: '二塁手' },
  { k: 'SS', a: 20,  d: () => 36,             nm: '遊撃手' },
  { k: '3B', a: 38,  d: () => 27,             nm: '三塁手' },
  { k: 'LF', a: 30,  d: (st) => fenceAt(st, 30) * 0.76,  nm: '左翼手' },
  { k: 'CF', a: 0,   d: (st) => fenceAt(st, 0) * 0.78,   nm: '中堅手' },
  { k: 'RF', a: -30, d: (st) => fenceAt(st, -30) * 0.76, nm: '右翼手' },""", 'stations')
wr(p, s)

# ================= 40-game.js =================
p = '40-game.js'; s = rd(p)
s = rep(s, "const BAT_X = -0.95, BAT_Z = 0.25;             // right-handed batter's box",
           "const BAT_X = 0.95, BAT_Z = 0.25;              // right-handed batter's box (+x = 3B side)", 'bat x')
# pitch break directions mirror with the world
s = rep(s, """  { k: 'curve',    nm: 'カーブ',     en: 'CURVE',    spd: 24.5, bx: 0.20,  by: -0.55, pw: 2.0 },
  { k: 'slider',   nm: 'スライダー', en: 'SLIDER',   spd: 29.0, bx: 0.44,  by: -0.18, pw: 2.6 },
  { k: 'fork',     nm: 'フォーク',   en: 'SPLITTER', spd: 27.5, bx: 0,     by: -0.80, pw: 3.4 },
  { k: 'shoot',    nm: 'シュート',   en: 'SHOOT',    spd: 30.0, bx: -0.38, by: -0.12, pw: 2.2 },""",
"""  { k: 'curve',    nm: 'カーブ',     en: 'CURVE',    spd: 24.5, bx: -0.20, by: -0.55, pw: 2.0 },
  { k: 'slider',   nm: 'スライダー', en: 'SLIDER',   spd: 29.0, bx: -0.44, by: -0.18, pw: 2.6 },
  { k: 'fork',     nm: 'フォーク',   en: 'SPLITTER', spd: 27.5, bx: 0,     by: -0.80, pw: 3.4 },
  { k: 'shoot',    nm: 'シュート',   en: 'SHOOT',    spd: 30.0, bx: 0.38,  by: -0.12, pw: 2.2 },""", 'break dirs')
s = rep(s, "    x0: -0.5, y0: 1.92, z0: 18.3,", "    x0: 0.5, y0: 1.92, z0: 18.3,", 'release point')
s = rep(s, "  let x = BAT_X + 0.7, y = 1.05, z = BAT_Z + 0.25;",
           "  let x = BAT_X - 0.7, y = 1.05, z = BAT_Z + 0.25;", 'contact point')
wr(p, s)

# ================= 50-main.js =================
p = '50-main.js'; s = rd(p)
# pull now goes to +x (left field), so an early swing yields a positive angle
s = rep(s, "    dir = clamp(d.dt * 245 + (pc.ax - (userBatting() ? G.reticle.x : G.cpuAim.x)) * 18 + gauss(4), -54, 54);",
           "    dir = clamp(-d.dt * 245 + (pc.ax - (userBatting() ? G.reticle.x : G.cpuAim.x)) * 18 + gauss(4), -54, 54);", 'pull dir')
# aiming: moving right on screen means moving toward -x
s = rep(s, """  if (KEYS.ArrowLeft || KEYS.KeyA) { G.reticle.x -= k; moved = true; }
  if (KEYS.ArrowRight || KEYS.KeyD) { G.reticle.x += k; moved = true; }""",
"""  if (KEYS.ArrowLeft || KEYS.KeyA) { G.reticle.x += k; moved = true; }
  if (KEYS.ArrowRight || KEYS.KeyD) { G.reticle.x -= k; moved = true; }""", 'aim keys')
s = rep(s, "    const tx = lerp(-1.05, 1.05, clamp((pointer.x - 0.22) / 0.56, 0, 1));",
           "    const tx = lerp(1.05, -1.05, clamp((pointer.x - 0.22) / 0.56, 0, 1));", 'aim pointer')
# batter faces the plate from the +x side; the bat sweeps the other way now
s = rep(s, """  if (t < 0) return { ang: 215 * DEG, tilt: 0.85 };
  const p = clamp(t / 0.36, 0, 1);
  if (p < 0.265) return { ang: lerp(215, 90, p / 0.265) * DEG, tilt: lerp(0.85, 0, p / 0.265) };
  return { ang: lerp(90, 2, (p - 0.265) / 0.735) * DEG, tilt: lerp(0, -0.25, (p - 0.265) / 0.735) };""",
"""  if (t < 0) return { ang: -215 * DEG, tilt: 0.85 };
  const p = clamp(t / 0.36, 0, 1);
  if (p < 0.265) return { ang: lerp(-215, -90, p / 0.265) * DEG, tilt: lerp(0.85, 0, p / 0.265) };
  return { ang: lerp(-90, -2, (p - 0.265) / 0.735) * DEG, tilt: lerp(0, -0.25, (p - 0.265) / 0.735) };""", 'bat arc')
s = rep(s, """    drawAnimal(BAT_X, BAT_Z, Math.PI / 2, b.look, pose, 0);
    drawBat(BAT_X + 0.42, BAT_Z + 0.05, Math.PI / 2, sw.ang, sw.tilt, '#C99A5E', '#7A5A34');""",
"""    drawAnimal(BAT_X, BAT_Z, -Math.PI / 2, b.look, pose, 0);
    drawBat(BAT_X - 0.42, BAT_Z + 0.05, -Math.PI / 2, sw.ang, sw.tilt, '#C99A5E', '#7A5A34');""", 'batter draw')
# lift the batting camera so catcher + umpire stop covering the zone
s = rep(s, """    ex = -0.55; ey = 3.95; ez = -11.6;
    tx = 0.05; ty = 1.35; tz = 12; fov = 42; sp = 5;""",
"""    ex = 0.55; ey = 5.4; ez = -13.0;
    tx = -0.05; ty = 1.45; tz = 13; fov = 44; sp = 5;""", 'bat cam')
s = rep(s, """  drawAnimal(0, -3.7, 0, { animal: 'hippo', uni: '#2B3138', trim: '#4A525C', cap: '#1E242A' },
    { armL: 0.5, armR: -0.5, bob: bob * 0.4 }, -0.18);""",
"""  drawAnimal(-1.45, -4.35, 0, { animal: 'hippo', uni: '#2B3138', trim: '#4A525C', cap: '#1E242A' },
    { armL: 0.5, armR: -0.5, bob: bob * 0.4 }, -0.30);""", 'umpire')
# runners wait just outside the diamond, whichever side their base is on
s = rep(s, "    drawAnimal(b[0] + 1.1, b[1] - 0.8, Math.PI, p.look, { armL: 0.3, armR: -0.3, bob }, 0);",
           "    drawAnimal(b[0] * 1.06, b[1] - 1.15, Math.PI, p.look, { armL: 0.3, armR: -0.3, bob }, 0);", 'onbase')
wr(p, s)
print('patched ok')
