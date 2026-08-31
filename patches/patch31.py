# 1. A ball nobody can cut off made every fielder return "too late", and the tie
#    went to index 0 — the pitcher. Balls to the wall were being credited to him.
#    Late retrievals now go to whoever is nearest where the ball stops, and the
#    pitcher covers less ground than the position players.
# 2. A double draws a throw to second base.
# 3. Errors get a bobble: the ball squirts loose and he has to chase it.
# 4. Fielders wear a proper mitt.
# 5. And they reach out with it to take the ball.
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
# 30-actors.js — a real mitt
# ============================================================
box, rep = mk('src/30-actors.js')
rep("""function drawGlove(pt, c) {
  if (!pt) return;
  R.b('sphere', pt[0], pt[1], pt[2], 0.34, 0.32, 0.26, col(c));
}""",
"""/* a leather mitt with a darker rim and a pale pocket, turned to face `ry` */
function drawGlove(pt, ry) {
  if (!pt) return;
  const x = pt[0], y = pt[1], z = pt[2], a = ry || 0;
  const hide = col('#8A5A32'), dark = col('#5E3B20'), pocket = col('#C89B64');
  R.d('rbox', x, y, z, 0, a, 0, 0.36, 0.38, 0.17, hide);
  R.d('rbox', x, y - 0.015, z + 0.045, 0, a, 0, 0.25, 0.27, 0.10, pocket);
  R.d('sphere', x, y + 0.20, z, 0, a, 0, 0.15, 0.16, 0.14, hide);
  R.d('sphere', x - 0.17, y + 0.09, z, 0, a, 0, 0.11, 0.24, 0.13, hide);
  R.d('rbox', x, y - 0.20, z, 0, a, 0, 0.30, 0.09, 0.15, dark);
}""", 'mitt')
wr('src/30-actors.js', box['s'])

# ============================================================
# 40-game.js
# ============================================================
box, rep = mk('src/40-game.js')

rep("""  let best = null;
  for (let i = 0; i < G.stations.length; i++) {
    if (G.fielders[i] && G.fielders[i].down > 0) continue;   // flattened by a car
    const s = G.stations[i], pl = fielderOf(def, s.k);
    const spd = 6.0 * st.fielderSpeed * (0.86 + pl.defense * 0.28);
    const it = interceptOn(fl, G.fielders[i] ? G.fielders[i].x : s.x,
                               G.fielders[i] ? G.fielders[i].z : s.z, spd);
    if (!best || it.t < best.it.t) best = { i, s, pl, spd, it };
  }""",
"""  let best = null;
  const rest = fl.path[fl.path.length - 1];
  for (let i = 0; i < G.stations.length; i++) {
    if (G.fielders[i] && G.fielders[i].down > 0) continue;   // flattened by a car
    const s = G.stations[i], pl = fielderOf(def, s.k);
    // a pitcher fields comebackers and bunts, not gaps
    const spd = 6.0 * st.fielderSpeed * (0.86 + pl.defense * 0.28) * (s.k === 'P' ? 0.72 : 1);
    const fx = G.fielders[i] ? G.fielders[i].x : s.x;
    const fz = G.fielders[i] ? G.fielders[i].z : s.z;
    const it = interceptOn(fl, fx, fz, spd);
    // if nobody could cut it off, whoever is nearest where it stops goes and
    // gets it — otherwise the tie always fell to the pitcher
    const key = it.late ? 1e5 + dist2(fx, fz, rest.x, rest.z) : it.t;
    if (!best || key < best.key) best = { i, s, pl, spd, it, key };
  }""", 'fielder pick')

rep("""  } else if (G.bases[1] || G.bases[2]) {
    aimAt(HOME_POS[0], HOME_POS[1]);        // a runner is coming round: back home
  } else {""",
"""  } else if (G.bases[1] || G.bases[2]) {
    aimAt(HOME_POS[0], HOME_POS[1]);        // a runner is coming round: back home
  } else if (safeTo === 2) {
    aimAt(BASE_POS[1][0], BASE_POS[1][1]);  // he is pulling into second: throw there
  } else {""", 'double to second')

rep("""    if (chance(errP * 0.55)) {
      G.errs[1 - G.half]++;
      aimAt(BASE_POS[1][0], BASE_POS[1][1]);
      return { kind: 'error', bases: fl.dist > 62 ? 2 : 1, err: true, play,
               text: `${best.s.sn}が落球！\\nエラー` };
    }""",
"""    if (chance(errP * 0.55)) {
      G.errs[1 - G.half]++;
      fumble(play, P);
      aimAt(BASE_POS[1][0], BASE_POS[1][1]);
      return { kind: 'error', bases: fl.dist > 62 ? 2 : 1, err: true, play,
               text: `${best.s.sn}が落球！\\nエラー` };
    }""", 'fly error')
rep("""  if (chance(errP)) {
    G.errs[1 - G.half]++;
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
    return { kind: 'error', bases: Math.max(1, safeTo), err: true, play,
             text: `${best.s.sn}がはじいた！\\nエラー` };
  }""",
"""  if (chance(errP)) {
    G.errs[1 - G.half]++;
    fumble(play, P);
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
    return { kind: 'error', bases: Math.max(1, safeTo), err: true, play,
             text: `${best.s.sn}がはじいた！\\nエラー` };
  }""", 'ground error')
rep("""function fieldBall(fl) {""",
"""/* the ball squirts out of the glove and he has to go and get it */
const FUMBLE_T = 0.66;
function fumble(play, P) {
  const a = rnd(0, Math.PI * 2), d = rnd(2.2, 3.6);
  play.fumble = 1;
  play.fumbleTo = [P.x + Math.cos(a) * d, P.z + Math.sin(a) * d];
}

function fieldBall(fl) {""", 'fumble helper')

rep("""  if (pl) m = Math.max(m, pl.cutT + (pl.viaDur || 0) + (pl.via ? 0.28 : 0)
                          + (pl.throwDur || 0) + 0.7);""",
"""  if (pl) m = Math.max(m, pl.cutT + (pl.fumble ? FUMBLE_T + 0.45 : 0)
                          + (pl.viaDur || 0) + (pl.via ? 0.28 : 0)
                          + (pl.throwDur || 0) + 0.7);""", 'playLength fumble')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js
# ============================================================
box, rep = mk('src/50-main.js')

# --- (3) the bobble ---
rep("""            live = false;
            let tt = G.flightT - pl.cutT;
            let fromX = pl.pt.x, fromZ = pl.pt.z, fromY = Math.max(pl.pt.y, 1.0);""",
"""            live = false;
            let tt = G.flightT - pl.cutT;
            let fromX = pl.pt.x, fromZ = pl.pt.z, fromY = Math.max(pl.pt.y, 1.0);
            let loose = false;
            if (pl.fumble) {                  // it pops out of the glove first
              if (tt <= FUMBLE_T + 0.45) {
                const u = clamp(tt / FUMBLE_T, 0, 1);
                bx = lerp(pl.pt.x, pl.fumbleTo[0], u);
                bz = lerp(pl.pt.z, pl.fumbleTo[1], u);
                by = lerp(Math.max(pl.pt.y, 0.95), 0.14, u) + Math.sin(u * Math.PI) * 0.85;
                loose = true;
              } else {
                tt -= FUMBLE_T + 0.45;
                fromX = pl.fumbleTo[0]; fromZ = pl.fumbleTo[1]; fromY = 0.7;
              }
            }""", 'fumble head')
rep("""            if (pl.via) {                       // the relay through second""",
"""            if (loose) { /* still skipping away from him */ }
            else if (pl.via) {                  // the relay through second""", 'fumble guard')

rep("""          const u = clamp((G.flightT - 0.22) / Math.max(0.25, pl.cutT - 0.22), 0, 1);
          const e = u * u * (3 - 2 * u);
          f.x = lerp(f.st.x, pl.pt.x, e); f.z = lerp(f.st.z, pl.pt.z, e);
          f.run = u < 1 ? 1.2 : 0;""",
"""          const u = clamp((G.flightT - 0.22) / Math.max(0.25, pl.cutT - 0.22), 0, 1);
          const e = u * u * (3 - 2 * u);
          f.x = lerp(f.st.x, pl.pt.x, e); f.z = lerp(f.st.z, pl.pt.z, e);
          f.run = u < 1 ? 1.2 : 0;
          f.fumbling = false;
          if (pl.fumble && G.flightT > pl.cutT + 0.16) {     // go and pick it up
            const fu = clamp((G.flightT - pl.cutT - 0.16) / (FUMBLE_T + 0.25), 0, 1);
            const fe = fu * fu * (3 - 2 * fu);
            f.x = lerp(pl.pt.x, pl.fumbleTo[0], fe); f.z = lerp(pl.pt.z, pl.fumbleTo[1], fe);
            f.run = fu < 1 ? 1.2 : 0;
            f.fumbling = G.flightT < pl.cutT + 0.46;
          }""", 'fumble chase')

# --- (4)(5) the mitt, and reaching with it ---
rep("""    if (isC && G.phase === 'pitch') {""",
"""    // any fielder puts his glove out when the ball comes near him
    if (!isP && G.ball.vis && !pose.handL) {
      const shy = 0.94 + (f.st.k === 'C' ? -0.22 : 0);
      const shx = f.x - 0.17 * Math.cos(f.ry), shz = f.z + 0.17 * Math.sin(f.ry);
      if (Math.hypot(G.ball.x - shx, G.ball.y - shy, G.ball.z - shz) < 2.3) {
        pose.handL = reachFrom(shx, shy, shz, G.ball.x,
                               clamp(G.ball.y, 0.15, 2.1), G.ball.z, 0.62);
        pose.pole = [0, -0.7, 0.5];
      }
    }
    if (f.fumbling) {                       // arms up — it got away from him
      pose.handL = null; pose.armL = -2.3; pose.armR = -2.2; pose.lean = -0.20;
    }
    if (isC && G.phase === 'pitch') {""", 'reach')
rep("""    if (!isP) inked(pl.look, () => drawGlove(pose.handL
      ? [pose.handL[0], pose.handL[1], pose.handL[2]]
      : [gp[0], a.hl[1], gp[1]], ft.trim));""",
"""    if (!f.fumbling) inked(pl.look, () => drawGlove(pose.handL
      ? [pose.handL[0], pose.handL[1], pose.handL[2]]
      : [gp[0], a.hl[1], gp[1]], f.ry));""", 'mitt call')
wr('src/50-main.js', box['s'])
print('patched ok')
