# 1. The mitt had a big pale panel across its face that read as a white blob.
#    Rebuilt with finger ridges, a thumb and a web instead.
# 2. The glove was on the character's right hand (local -x is his right, since
#    forward is +z). It moves to the left; the right hand stays free to throw.
# 3. More time before a pitch, especially the first one to a new batter.
# 4. Runners hold their base on a fly ball instead of drifting off it.
# 5. A tag-up starts when the catch is made, not at contact.
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
# 30-actors.js — a mitt that looks like a mitt
# ============================================================
box, rep = mk('src/30-actors.js')
rep("""/* a leather mitt with a darker rim and a pale pocket, turned to face `ry` */
function drawGlove(pt, ry) {
  if (!pt) return;
  const a = ry || 0, fx = Math.sin(a), fz = Math.cos(a);
  const x = pt[0] + fx * 0.05, y = pt[1], z = pt[2] + fz * 0.05;
  const hide = col('#7A3F16'), dark = col('#43220C'), pocket = col('#F0DCB2');
  R.d('rbox', x, y, z, 0, a, 0, 0.40, 0.42, 0.20, hide);
  // the pocket faces whichever way the mitt is turned
  R.d('rbox', x + fx * 0.075, y - 0.01, z + fz * 0.075, 0, a, 0, 0.27, 0.29, 0.09, pocket);
  R.d('sphere', x - fz * 0.19, y + 0.11, z + fx * 0.19, 0, a, 0, 0.13, 0.26, 0.15, hide);
  R.d('sphere', x + fz * 0.19, y + 0.13, z - fx * 0.19, 0, a, 0, 0.13, 0.24, 0.15, hide);
  R.d('rbox', x, y - 0.22, z, 0, a, 0, 0.32, 0.10, 0.17, dark);
}""",
"""/* A fielder's mitt: palm, four finger ridges, a thumb and the web between
   them. All one leather; the shape does the work, not a painted pocket. */
function drawGlove(pt, ry) {
  if (!pt) return;
  const a = ry || 0, fx = Math.sin(a), fz = Math.cos(a);
  const sx = fz, sz = -fx;                       // across the mitt
  const x = pt[0] + fx * 0.05, y = pt[1], z = pt[2] + fz * 0.05;
  const hide = col('#7A4A22'), dark = col('#46280F'), web = col('#9A6B38');
  R.d('rbox', x, y - 0.02, z, 0, a, 0, 0.38, 0.36, 0.20, hide);          // palm
  for (let i = -1; i <= 2; i++)                                          // fingers
    R.d('rbox', x + sx * i * 0.083, y + 0.20, z + sz * i * 0.083, 0, a, 0,
        0.072, 0.22, 0.18, hide);
  R.d('rbox', x - sx * 0.235, y - 0.03, z - sz * 0.235, 0, a, 0, 0.11, 0.30, 0.19, hide);
  R.d('rbox', x - sx * 0.145, y + 0.18, z - sz * 0.145, 0, a, 0, 0.11, 0.20, 0.16, web);
  R.d('rbox', x + fx * 0.075, y - 0.05, z + fz * 0.075, 0, a, 0, 0.20, 0.18, 0.05, dark);
  R.d('rbox', x, y - 0.22, z, 0, a, 0, 0.32, 0.10, 0.18, dark);          // heel
}""", 'mitt')
wr('src/30-actors.js', box['s'])

# ============================================================
# 40-game.js
# ============================================================
box, rep = mk('src/40-game.js')

# (3) let the batter get set
rep("  setPhase('ready', G.firstPitch ? 2.4 : 0.75);",
    "  setPhase('ready', G.firstPitch ? 3.0 : 1.5);", 'ready len')
rep("    banner('ボール');\n    uiScore(); setPhase('result', 0.55);",
    "    banner('ボール');\n    uiScore(); setPhase('result', 0.70);", 'ball pause')
rep("if (kind === 'foul' && G.strikes >= 2) { banner('ファウル'); uiScore(); setPhase('result', 0.55); return; }",
    "if (kind === 'foul' && G.strikes >= 2) { banner('ファウル'); uiScore(); setPhase('result', 0.70); return; }", 'foul pause')
rep("    if (kind === 'whiff') Snd.miss();\n    uiScore(); setPhase('result', 0.55);",
    "    if (kind === 'whiff') Snd.miss();\n    uiScore(); setPhase('result', 0.70);", 'strike pause')

# (5) a tag-up waits for the catch
rep("""    case 'flyout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);
      if (o.canSac && G.outs < 2 && G.bases[2]) {
        runs++; scoreRun(G.bases[2], bat); moveRunner(G.bases[2], 2, 3); G.bases[2] = null;
        o.text = '犠牲フライ！\\n1点';
      } else if (G.outs < 2 && G.bases[1] && o.canSac && chance(0.62)) {
        G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null;
      }
      Snd.mitt();
      break;""",
"""    case 'flyout': {
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);
      // a runner tagging up cannot leave until the ball is caught
      const held = o.play ? o.play.cutT + 0.12 : 1.2;
      if (o.canSac && G.outs < 2 && G.bases[2]) {
        runs++; scoreRun(G.bases[2], bat); moveRunner(G.bases[2], 2, 3, held); G.bases[2] = null;
        o.text = '犠牲フライ！\\n1点';
      } else if (G.outs < 2 && G.bases[1] && o.canSac && chance(0.62)) {
        G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2, held); G.bases[1] = null;
      }
      Snd.mitt();
      break;
    }""", 'tag up delay')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js
# ============================================================
box, rep = mk('src/50-main.js')

# (2) glove on the left hand (local +x), throwing hand free
rep("""    // any fielder puts his glove out when the ball comes near him
    if (!isP && G.ball.vis && !pose.handL) {
      const shy = 0.94 + (f.st.k === 'C' ? -0.22 : 0);
      const shx = f.x - 0.17 * Math.cos(f.ry), shz = f.z + 0.17 * Math.sin(f.ry);
      if (Math.hypot(G.ball.x - shx, G.ball.y - shy, G.ball.z - shz) < 2.3) {
        pose.handL = reachFrom(shx, shy, shz, G.ball.x,
                               clamp(G.ball.y, 0.15, 2.1), G.ball.z, 0.62);
        pose.pole = [0, -0.7, 0.5];
      }
    }
    if (!isP) pose.noPawL = 1;              // that hand is inside the mitt
    // the glove hand: the throwing hand for a pitcher, the left for everyone else
    if (isP) pose.noPawR = 1; else pose.noPawL = 1;
    if (f.fumbling) {                       // arms up — it got away from him
      pose.handL = null; pose.armL = -2.3; pose.armR = -2.2; pose.lean = -0.20;
    }""",
"""    // The glove goes on the left hand — which is the local +x arm, since a
    // character faces its local +z and so its right is local -x.
    pose.noPawR = 1;
    if (!isP && G.ball.vis) {
      const shy = 0.94 + (f.st.k === 'C' ? -0.22 : 0);
      const shx = f.x + 0.17 * Math.cos(f.ry), shz = f.z - 0.17 * Math.sin(f.ry);
      if (Math.hypot(G.ball.x - shx, G.ball.y - shy, G.ball.z - shz) < 2.3) {
        pose.handR = reachFrom(shx, shy, shz, G.ball.x,
                               clamp(G.ball.y, 0.15, 2.1), G.ball.z, 0.62);
        pose.pole = [0, -0.7, 0.5];
      }
    }
    if (f.fumbling) {                       // arms up — it got away from him
      pose.handR = null; pose.armL = -2.3; pose.armR = -2.2; pose.lean = -0.20;
    }""", 'glove hand')

rep("""    if (isC && G.phase === 'pitch') {
      // the mitt sits up in front of him and only moves the last little bit to
      // meet the ball — it never chases it out toward the mound
      const shy = 0.94 - 0.22;
      let tx = f.x * 0.4, ty = 0.78, tz = f.z + 0.62;
      if (G.ball.vis && G.ball.z < f.z + 2.6) {
        tx = G.ball.x; ty = clamp(G.ball.y, 0.28, 1.75); tz = Math.max(G.ball.z, f.z + 0.42);
      }
      pose.handL = reachFrom(f.x, shy, f.z, tx, ty, tz, 0.60);
      pose.pole = [0, -0.7, 0.7];
    }""",
"""    if (isC && G.phase === 'pitch') {
      // the mitt sits up in front of him and only moves the last little bit to
      // meet the ball — it never chases it out toward the mound
      const shy = 0.94 - 0.22;
      let tx = f.x * 0.4, ty = 0.78, tz = f.z + 0.62;
      if (G.ball.vis && G.ball.z < f.z + 2.6) {
        tx = G.ball.x; ty = clamp(G.ball.y, 0.28, 1.75); tz = Math.max(G.ball.z, f.z + 0.42);
      }
      pose.handR = reachFrom(f.x, shy, f.z, tx, ty, tz, 0.60);
      pose.pole = [0, -0.7, 0.7];
    }""", 'catcher mitt')

rep("""    const a = drawAnimal(f.x, f.z, ry, pl.look, pose, y0);
    const gp = L2W(a.f, a.hl[0], a.hl[2]);
    if (isP) {
      const gr = L2W(a.f, a.hr[0], a.hr[2]);
      inked(pl.look, () => drawGlove([gr[0], a.hr[1], gr[1]], f.ry));
    } else if (!f.fumbling) {
      inked(pl.look, () => drawGlove(pose.handL
        ? [pose.handL[0], pose.handL[1], pose.handL[2]]
        : [gp[0], a.hl[1], gp[1]], f.ry));
    }""",
"""    const a = drawAnimal(f.x, f.z, ry, pl.look, pose, y0);
    if (!f.fumbling) {
      const gp = L2W(a.f, a.hr[0], a.hr[2]);
      inked(pl.look, () => drawGlove(pose.handR
        ? [pose.handR[0], pose.handR[1], pose.handR[2]]
        : [gp[0], a.hr[1], gp[1]], f.ry));
    }""", 'glove draw')

# (4) with the ball in play a runner holds his bag
rep("""    const off = LEAD_OFF + Math.sin(clock * 1.7 + i * 2) * 0.34;""",
"""    // he only takes his lead before the pitch — once the ball is hit he is
    // back on the bag, watching the fly
    const off = G.phase === 'play' ? 0.25
      : LEAD_OFF + Math.sin(clock * 1.7 + i * 2) * 0.34;""", 'hold bag')
wr('src/50-main.js', box['s'])
print('patched ok')
