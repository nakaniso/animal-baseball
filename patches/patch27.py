# 1. The pitch could start before the pitcher was back on the rubber, so the
#    ball appeared out of thin air. The delivery now waits for him, and the
#    release point follows his actual hand.
# 2. A pop-up or grounder taken by the pitcher was still "thrown back to the
#    mound", and coverFor excluded him as the receiver (he was busy), so the
#    first baseman ran to the mound to take it. An infielder who catches a ball
#    simply holds it.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def mk(path):
    box = {'s': rd(path)}
    def rep(a, b, label):
        if a not in box['s']: raise SystemExit('MISS %s: %s' % (path, label))
        box['s'] = box['s'].replace(a, b)
    return box, rep

# ============================================================
# 40-game.js
# ============================================================
box, rep = mk('src/40-game.js')

# the ball leaves the pitcher's hand, wherever he is standing
rep("""  G.pitch = {
    P, T, t: 0, ti,
    x0: 0.5, y0: 1.92, z0: 18.3,""",
"""  const pf = G.fielders[0];
  G.pitch = {
    P, T, t: 0, ti,
    x0: (pf ? pf.x : 0) + 0.46, y0: 1.92, z0: (pf ? pf.z : MOUND_POS[1]) - 0.16,""", 'release point')

# a fly ball caught by an infielder is not thrown anywhere
rep("""    const liner = fl.la < 24 && fl.hang < 1.7;
    const tight = best.it.t > fl.hang - 0.45;
    aimAt(MOUND_POS[0], MOUND_POS[1]);           // lob it back in""",
"""    const liner = fl.la < 24 && fl.hang < 1.7;
    const tight = best.it.t > fl.hang - 0.45;
    // an infielder just holds it; only an outfielder lobs the ball back in
    if (best.s.infield) { play.throwTo = null; play.throwDur = 0; }
    else aimAt(MOUND_POS[0], MOUND_POS[1]);""", 'flyout hold')

# nobody is sent to a spot they are already standing on
rep("""    const ci = coverFor(bx, bz, play.fidx);
    if (ci >= 0 && ci !== play.fidx) {
      const isC = G.stations[ci].k === 'C';   // he sets up just behind the plate
      play.moves.push({ idx: ci, x: isC ? 0 : bx, z: isC ? -1.1 : bz,
                        byT: (after || play.cutT) + dur });
    }""",
"""    const ci = coverFor(bx, bz, play.fidx);
    if (ci >= 0 && ci !== play.fidx) {
      const st2 = G.stations[ci];
      const isC = st2.k === 'C';               // he sets up just behind the plate
      const tx2 = isC ? 0 : bx, tz2 = isC ? -1.1 : bz;
      // never drag someone clear across the diamond to take a routine lob
      if (dist2(st2.x, st2.z, tx2, tz2) < 34)
        play.moves.push({ idx: ci, x: tx2, z: tz2, byT: (after || play.cutT) + dur });
    }""", 'sendTo guard')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js — hold the delivery until the pitcher is set
# ============================================================
box, rep = mk('src/50-main.js')
rep("""const camSettled = () =>
  CAM.wx === undefined ||
  Math.hypot(CAM.ex - CAM.wx, CAM.ey - CAM.wy, CAM.ez - CAM.wz) < 0.9;""",
"""const camSettled = () =>
  CAM.wx === undefined ||
  Math.hypot(CAM.ex - CAM.wx, CAM.ey - CAM.wy, CAM.ez - CAM.wz) < 0.9;

/* the pitcher has to be back on the rubber before he can deliver */
const pitcherSet = () => {
  const f = G.fielders[0];
  return !f || (f.down <= 0 && Math.hypot(f.x - f.st.x, f.z - f.st.z) < 0.7);
};""", 'pitcherSet')
rep("""      // never deliver until the camera is actually back behind the plate
      if (G.pt >= G.phaseLen && (camSettled() || G.pt > G.phaseLen + 2.2)) {""",
"""      // never deliver until the camera is back behind the plate and the
      // pitcher has actually returned to the mound
      if (G.pt >= G.phaseLen
          && (camSettled() || G.pt > G.phaseLen + 2.2)
          && (pitcherSet() || G.pt > G.phaseLen + 3.2)) {""", 'ready gate')
rep("""    if (!f.scripted) {
      const k = Math.min(1, dt * 2.2);""",
"""    if (!f.scripted) {
      const k = Math.min(1, dt * 3.4);         // get back to your position""", 'return speed')
wr('src/50-main.js', box['s'])
print('patched ok')
