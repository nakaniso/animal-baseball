# Six fixes:
#  1. after a foul the camera stayed out at the ball, so the next pitch arrived
#     before it was back behind the plate
#  2/3. the catcher's glove was aimed at the ball wherever it was, stretching
#     the arm several metres and reading as the ball going through him
#  4. TOP/BTM -> 表/裏
#  5. foul balls flew and rolled a hundred metres out of the park; they now stop
#     where they land, and mishits are pushed further outside the line
#  6. the coach's box was open on the wrong side
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
# 30-actors.js — an arm can no longer stretch without limit
# ============================================================
box, rep = mk('src/30-actors.js')
rep("  if (d > (L1 + L2) * 0.995) { const k = (d / (L1 + L2)) * 1.02; L1 *= k; L2 *= k; }",
"""  if (d > (L1 + L2) * 0.995) {
    // cartoon arms give a little, but never more than a third of their length;
    // past that the hand is pulled in rather than the limb turned into a pole
    const need = d / (L1 + L2);
    const give = Math.min(need, 1.32);
    L1 *= give * 1.02; L2 *= give * 1.02;
    if (need > 1.32) {
      const k = ((L1 + L2) * 0.995) / d;
      hx = sx + dx * k; hy = sy + dy * k; hz = sz + dz * k;
      dx *= k; dy *= k; dz *= k; d *= k;
    }
  }""", 'ik clamp')
wr('src/30-actors.js', box['s'])

# ============================================================
# 20-world.js — coach's box opens away from the field
# ============================================================
box, rep = mk('src/20-world.js')
rep("""    const inA = P(-hw, -hl), inB = P(-hw, hl), outB = P(hw, hl), outA = P(hw, -hl);
    chalkLine(S, inB[0], inB[1], outB[0], outB[1], chalk);   // far end
    chalkLine(S, outB[0], outB[1], outA[0], outA[1], chalk); // outer side
    chalkLine(S, outA[0], outA[1], inA[0], inA[1], chalk);   // near end""",
"""    const inA = P(-hw, -hl), inB = P(-hw, hl), outB = P(hw, hl), outA = P(hw, -hl);
    // the line the coach must stay behind is the one next to the foul line, so
    // that side is always chalked; the box is left open away from the field
    chalkLine(S, inA[0], inA[1], inB[0], inB[1], chalk);     // field side
    chalkLine(S, inB[0], inB[1], outB[0], outB[1], chalk);   // far end
    chalkLine(S, outA[0], outA[1], inA[0], inA[1], chalk);   // near end""", 'coach box')
wr('src/20-world.js', box['s'])

# ============================================================
# 40-game.js — mishits are pushed clearly foul; contact point nearer the plate
# ============================================================
box, rep = mk('src/40-game.js')
rep("  let x = BAT_X - 0.7, y = 1.05, z = BAT_Z + 0.25;",
    "  let x = BAT_X - 0.80, y = 1.05, z = BAT_Z + 0.17;", 'contact point')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js
# ============================================================
box, rep = mk('src/50-main.js')

# --- (4) Japanese half-inning label ---
rep("  $('#sb-half').textContent = G.half === 0 ? 'TOP' : 'BTM';",
    "  $('#sb-half').textContent = G.half === 0 ? '表' : '裏';", 'half label')

# --- (5) mishits go unambiguously foul ---
rep("""      dir = (chance(0.5) ? 1 : -1) * rnd(47, 80);
      la = clamp(la + rnd(6, 34), 8, 78);
      v0 *= rnd(0.58, 0.94);""",
"""      dir = (chance(0.5) ? 1 : -1) * rnd(55, 88);
      la = clamp(la + rnd(10, 38), 12, 80);
      v0 *= rnd(0.50, 0.86);""", 'foul angle')

# --- (5) a foul ball stops where it lands instead of rolling out of the park ---
rep("""  if (o.kind === 'foul') {
    G.playScript = null;
    G.pendingCount = 'foul';
    setPhase('play', Math.min(G.flight.total, 1.9) + 0.5);
    banner('ファウル');
    return;
  }""",
"""  if (o.kind === 'foul') {
    // freeze it a beat after it first lands, so it does not roll into the next
    // county with the camera chasing it
    const fl2 = G.flight;
    const gi = Math.min(fl2.groundIdx + 14, fl2.path.length - 1);
    const q = fl2.path[gi];
    G.playScript = { fidx: -1, coverIdx: -1, cutIdx: gi, cutT: q.t,
                     pt: { x: q.x, y: q.y, z: q.z }, air: false, throwTo: null, throwDur: 0 };
    G.pendingCount = 'foul';
    setPhase('play', Math.min(q.t, 2.0) + 0.55);
    banner('ファウル');
    return;
  }""", 'foul script')

# the play phase must tolerate a script with no fielder
rep("""        if (pl) {
          // the fielder runs to the ball and arrives with it
          const f = G.fielders[pl.fidx];
          f.scripted = true;""",
"""        if (pl && pl.fidx >= 0) {
          // the fielder runs to the ball and arrives with it
          const f = G.fielders[pl.fidx];
          f.scripted = true;""", 'play guard a')
rep("""          if (G.flightT > pl.cutT) {
            live = false;""",
"""        }
        if (pl && G.flightT > pl.cutT) {
          {
            live = false;""", 'play guard b')
rep("""            } else {
              bx = pl.pt.x; by = Math.max(pl.pt.y, 0.95); bz = pl.pt.z;
            }
          }
        }""",
"""            } else {
              bx = pl.pt.x; by = Math.max(pl.pt.y, 0.14); bz = pl.pt.z;
            }
          }
        }""", 'play guard c')

# --- (1) the camera comes home before the next pitch ---
rep("""function endPlay() {
  G.carStall = 0;
  G.ball.vis = false;""",
"""function endPlay() {
  G.carStall = 0;
  G.camMode = 'bat';        // back behind the plate before anything else
  G.ball.vis = false;""", 'endPlay cam')
rep("""      if (G.pt >= G.phaseLen) {
        if (humanPitches()) { setPhase('aim'); uiHint(); }
        else { const c = cpuPitchChoice(); throwPitch(c.ti, c.ax, c.ay); }
      }""",
"""      // never deliver until the camera is actually back behind the plate
      if (G.pt >= G.phaseLen && (camSettled() || G.pt > G.phaseLen + 2.2)) {
        if (humanPitches()) { setPhase('aim'); uiHint(); }
        else { const c = cpuPitchChoice(); throwPitch(c.ti, c.ax, c.ay); }
      }""", 'ready gate')
rep("""  const k = Math.min(1, dt * sp);
  CAM.ex += (ex - CAM.ex) * k; CAM.ey += (ey - CAM.ey) * k; CAM.ez += (ez - CAM.ez) * k;""",
"""  CAM.wx = ex; CAM.wy = ey; CAM.wz = ez;
  const k = Math.min(1, dt * sp);
  CAM.ex += (ex - CAM.ex) * k; CAM.ey += (ey - CAM.ey) * k; CAM.ez += (ez - CAM.ez) * k;""", 'cam target')
rep("""function updateCamera(dt) {""",
"""const camSettled = () =>
  CAM.wx === undefined ||
  Math.hypot(CAM.ex - CAM.wx, CAM.ey - CAM.wy, CAM.ez - CAM.wz) < 0.9;

function updateCamera(dt) {""", 'camSettled')

# --- (2)(3) the catcher receives the ball instead of reaching across the field ---
rep("""      const mitt = -2.3;                       // the ball is caught, not flown past
      G.ball.x = p.x; G.ball.y = Math.max(p.y, 0.35); G.ball.z = Math.max(p.z, mitt);""",
"""      // the ball dies in the mitt rather than carrying on through the catcher
      const cst = G.stations[1];
      const mitt = cst.z + 0.62;
      G.ball.x = p.x; G.ball.y = Math.max(p.y, 0.42); G.ball.z = Math.max(p.z, mitt);""", 'mitt')

rep("""    if (isC && G.ball.vis && G.phase === 'pitch' && G.ball.z < 5) {
      pose.handL = [clamp(G.ball.x, -1.1, 1.1), clamp(G.ball.y, 0.3, 1.7),
                    Math.max(G.ball.z, f.z + 0.55)];
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
      pose.handL = reachFrom(f.x, shy, f.z, tx, ty, tz, 0.60);
      pose.pole = [0, -0.7, 0.7];
    }""", 'catcher glove')
rep("""        if (t < 0.16 && G.ball.vis) {             // the ball is still in his hand
          pose.handL = [G.ball.x, G.ball.y, G.ball.z];
          pose.pole = [0.4, -0.6, 0.2];
        }""",
"""        if (t < 0.10 && G.ball.vis) {             // the ball is still in his hand
          pose.handL = reachFrom(f.x, 0.94, f.z, G.ball.x, G.ball.y, G.ball.z, 0.60);
          pose.pole = [0.4, -0.6, 0.2];
        }""", 'pitcher hand')
rep("""function drawScene() {""",
"""/* a hand target, pulled back so it stays within `max` of the shoulder */
function reachFrom(sx, sy, sz, tx, ty, tz, max) {
  const dx = tx - sx, dy = ty - sy, dz = tz - sz;
  const d = Math.hypot(dx, dy, dz) || 1;
  const k = Math.min(1, max / d);
  return [sx + dx * k, sy + dy * k, sz + dz * k];
}

function drawScene() {""", 'reachFrom')
wr('src/50-main.js', box['s'])
print('patched ok')
