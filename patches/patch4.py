# Readability pass: a strike zone that reads on any surface, a supermarket that
# is not washed out white-on-white, more moon character near the plate, and a
# play-by-play log that resets with each new game.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def rep(s, a, b, label):
    if a not in s: raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

# ---------------- strike zone: dark backing + light face ----------------
p = 'src/50-main.js'; s = rd(p)
s = rep(s, """function drawZone() {
  const z = 0.30;
  R.unlit(true, 0.55);
  const c = col('#FFFFFF');
  const seg = (x, y, w, h) => R.b('box', x, y, z, w, h, 0.02, c);
  const t = 0.035;
  seg(0, ZY0, ZX * 2 + t, t); seg(0, ZY1, ZX * 2 + t, t);
  seg(-ZX, (ZY0 + ZY1) / 2, t, ZY1 - ZY0); seg(ZX, (ZY0 + ZY1) / 2, t, ZY1 - ZY0);""",
"""function drawZone() {
  const z = 0.30;
  R.unlit(true, 0.55);
  // two passes: a dark backing then a light face, so the zone reads on grass,
  // asphalt, a white tiled floor and grey regolith alike
  const frame = (c, t, dz, a) => {
    R.gl.uniform1f(R.u.uAlpha, a);
    const seg = (x, y, w, h) => R.b('box', x, y, z + dz, w, h, 0.02, c);
    seg(0, ZY0, ZX * 2 + t, t); seg(0, ZY1, ZX * 2 + t, t);
    seg(-ZX, (ZY0 + ZY1) / 2, t, ZY1 - ZY0); seg(ZX, (ZY0 + ZY1) / 2, t, ZY1 - ZY0);
  };
  frame(col('#141C26'), 0.075, 0.012, 0.5);
  frame(col('#FFFFFF'), 0.035, 0, 0.9);""", 'zone frame')
s = rep(s, """  // meet cursor
  const a = col('#FFC44D');
  const rx = G.reticle.x, ry = G.reticle.y;
  R.gl.uniform1f(R.u.uAlpha, 0.92);
  for (let i = 0; i < 8; i++) {
    const th = (i / 8) * Math.PI * 2;
    R.b('box', rx + Math.cos(th) * 0.2, ry + Math.sin(th) * 0.2, z - 0.02, 0.07, 0.07, 0.02, a);
  }
  R.b('box', rx, ry, z - 0.02, 0.05, 0.05, 0.02, a);""",
"""  // meet cursor
  const a = col('#FFC44D'), ao = col('#5A3B06');
  const rx = G.reticle.x, ry = G.reticle.y;
  for (let i = 0; i < 8; i++) {
    const th = (i / 8) * Math.PI * 2;
    const px = rx + Math.cos(th) * 0.2, py = ry + Math.sin(th) * 0.2;
    R.gl.uniform1f(R.u.uAlpha, 0.55);
    R.b('box', px, py, z - 0.01, 0.105, 0.105, 0.02, ao);
    R.gl.uniform1f(R.u.uAlpha, 0.95);
    R.b('box', px, py, z - 0.03, 0.07, 0.07, 0.02, a);
  }
  R.b('box', rx, ry, z - 0.03, 0.05, 0.05, 0.02, a);""", 'zone cursor')
wr(p, s)

# ---------------- supermarket: contrast ----------------
p = 'src/20-world.js'; s = rd(p)
s = rep(s, "    fog: '#D9DCD2', skyTint: '#F2F3EC', gndTint: '#B9BCB2', fogDist: 190,",
           "    fog: '#B9C0BA', skyTint: '#E4E8E0', gndTint: '#8E958E', fogDist: 300,", 'market fog')
s = rep(s, """      for (let x = -5; x <= 5; x++) for (let z = -2; z <= 10; z++)
        S.plate(x * 9, 0, z * 9, 9, 9, (x + z) % 2 ? '#DCDDD4' : '#D0D2C8');""",
"""      for (let x = -6; x <= 6; x++) for (let z = -2; z <= 10; z++)
        S.plate(x * 8, 0, z * 8, 8, 8, (x + z) % 2 ? '#D2D6CC' : '#B6BCB2');
      // vinyl guide stripes, like a real shop floor
      for (let z = -16; z < 100; z += 24) S.plate(0, 0.008, z, 104, 1.2, '#8FA8A2');""", 'market floor')
s = rep(s, "        S.box(s * 54, 5.25, 40, 1.0, 10.5, 160, '#E6E7DF');",
           "        S.box(s * 54, 5.25, 40, 1.0, 10.5, 160, '#C9CEC4');", 'market walls')
s = rep(s, "      S.plate(0, 10.5, 40, 230, 230, '#C4C7BE');",
           "      S.plate(0, 10.5, 40, 230, 230, '#9BA29B');", 'market ceiling')
s = rep(s, "          S.box(sx + dx, 1.1, sz + dz, rot ? 2.0 : 3.0, 2.2, rot ? 3.0 : 2.0, '#9EA6A2');",
           "          S.box(sx + dx, 1.1, sz + dz, rot ? 2.0 : 3.0, 2.2, rot ? 3.0 : 2.0, '#77807C');", 'market shelves')

# ---------------- moon: surface character near the plate ----------------
s = rep(s, """      for (let i = 0; i < 70; i++) {
        const x = rnd(-280, 280), z = rnd(-60, 320);
        if (dist2(x, z, 0, 40) < 58) continue;
        const r = rnd(3, 16);
        S.ring(x, 0.02, z, r, '#6E6E76'); S.ring(x, 0.03, z, r * 0.7, '#8A8A92');
      }""",
"""      for (let i = 0; i < 110; i++) {
        const x = rnd(-280, 280), z = rnd(-70, 320);
        if (dist2(x, z, 0, 19.4) < 30) continue;    // keep the diamond clear
        const r = rnd(2.5, 16);
        S.ring(x, 0.02, z, r, '#63636B'); S.ring(x, 0.03, z, r * 0.7, '#8E8E97');
      }
      for (let i = 0; i < 70; i++) {                 // scattered rocks
        const x = rnd(-160, 160), z = rnd(-40, 220);
        if (dist2(x, z, 0, 19.4) < 26) continue;
        const r = rnd(0.5, 2.2);
        S.sph(x, r * 0.4, z, r, i % 3 ? '#72727A' : '#8A8A93');
      }""", 'moon craters')
s = rep(s, "      S.plate(0, 0, 40, 620, 620, '#7E7E86');",
           "      S.plate(0, 0, 40, 700, 700, '#83838C');", 'moon ground')
wr(p, s)

# ---------------- log resets with the game ----------------
p = 'src/40-game.js'; s = rd(p)
s = rep(s, "  uiTeams();\n  logLine(", "  uiTeams();\n  clearLog();\n  logLine(", 'clear log')
wr(p, s)

p = 'src/50-main.js'; s = rd(p)
s = rep(s, "function logLine(text, hi) {", "function clearLog() { $('#log').innerHTML = ''; }\n\nfunction logLine(text, hi) {", 'clearLog fn')
s = rep(s, "    b.onclick = () => { Snd.boot(); show(null); $('#log').innerHTML = ''; startGame(chosenStadium, t.id); };",
           "    b.onclick = () => { Snd.boot(); show(null); startGame(chosenStadium, t.id); };", 'team click')
wr(p, s)
print('patched ok')
