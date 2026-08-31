# Fielding: a double play is now turned through second — one middle infielder
# covers the bag, the other converges to back it up — and outfielders relay to
# a cut-off man instead of throwing to the bag ahead of the runner, which on a
# triple would just open up home plate.
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

box, rep = mk('src/40-game.js')

# --- who takes a bag, allowing for the man who fielded it being busy ---
rep("""/* which fielder covers a bag for the throw */
function coverFor(tx, tz) {
  const want = dist2(tx, tz, BASE_POS[0][0], BASE_POS[0][1]) < 1 ? '1B'
    : dist2(tx, tz, BASE_POS[1][0], BASE_POS[1][1]) < 1 ? '2B'
    : dist2(tx, tz, BASE_POS[2][0], BASE_POS[2][1]) < 1 ? '3B' : 'C';
  return G.stations.findIndex((s) => s.k === want);
}""",
"""/* which fielder covers a bag for the throw; if he is the one who fielded the
   ball, the usual back-up takes it instead */
const BACKUP = { '1B': 'P', '2B': 'SS', '3B': 'P', C: 'P', SS: '2B' };
function coverFor(tx, tz, busy) {
  let want = dist2(tx, tz, BASE_POS[0][0], BASE_POS[0][1]) < 1 ? '1B'
    : dist2(tx, tz, BASE_POS[1][0], BASE_POS[1][1]) < 1 ? '2B'
    : dist2(tx, tz, BASE_POS[2][0], BASE_POS[2][1]) < 1 ? '3B' : 'C';
  let i = G.stations.findIndex((s) => s.k === want);
  if (i === busy && BACKUP[want]) i = G.stations.findIndex((s) => s.k === BACKUP[want]);
  return i;
}
const stationIdx = (k) => G.stations.findIndex((s) => s.k === k);""", 'coverFor')

rep("""  const play = { fidx: best.i, cutIdx: best.it.i, cutT: best.it.t,
                 pt: { x: P.x, y: P.y, z: P.z }, air: best.it.air };
  const aimAt = (bx, bz) => {
    play.throwTo = [bx, bz];
    play.throwDur = throwTime(P, bx, bz, best.pl.arm);
    play.coverIdx = coverFor(bx, bz);
  };""",
"""  const play = { fidx: best.i, cutIdx: best.it.i, cutT: best.it.t,
                 pt: { x: P.x, y: P.y, z: P.z }, air: best.it.air, moves: [] };
  /* someone has to be standing on the bag when the throw gets there */
  const sendTo = (bx, bz, fromPt, arm, after) => {
    const dur = throwTime(fromPt, bx, bz, arm);
    const ci = coverFor(bx, bz, play.fidx);
    if (ci >= 0 && ci !== play.fidx)
      play.moves.push({ idx: ci, x: bx, z: bz, byT: (after || play.cutT) + dur });
    return dur;
  };
  const aimAt = (bx, bz) => {
    play.throwTo = [bx, bz];
    play.throwDur = sendTo(bx, bz, P, best.pl.arm);
  };""", 'aimAt')

# --- the double play goes through second ---
rep("""    if (G.bases[0] && G.outs < 2 && infield && fl.v0 > 17
        && chance(0.34 + best.pl.defense * 0.28)) {
      aimAt(BASE_POS[0][0], BASE_POS[0][1]);
      play.via = BASE_POS[1];
      return { kind: 'dp', outs: 2, fielder: best.s, play,
               text: `${best.s.sn}→セカンド→ファースト\\nゲッツー！` };
    }""",
"""    if (G.bases[0] && G.outs < 2 && infield && fl.v0 > 17
        && chance(0.34 + best.pl.defense * 0.28)) {
      // ball to the third-base side: the second baseman takes the bag and the
      // shortstop backs him up; to the first-base side it is the other way round
      const leftSide = fl.ang > 0;
      let pivotK = leftSide ? '2B' : 'SS', backK = leftSide ? 'SS' : '2B';
      if (stationIdx(pivotK) === best.i) { const t2 = pivotK; pivotK = backK; backK = t2; }
      const pivotI = stationIdx(pivotK), backI = stationIdx(backK);
      const pivotP = fielderOf(def, pivotK);
      const bag2 = BASE_POS[1], bag1 = BASE_POS[0];

      play.via = bag2;
      play.viaDur = throwTime(P, bag2[0], bag2[1], best.pl.arm);
      play.moves.push({ idx: pivotI, x: bag2[0], z: bag2[1], byT: play.cutT + play.viaDur });
      if (backI >= 0 && backI !== best.i)     // the other one converges as back-up
        play.moves.push({ idx: backI, x: bag2[0] + (leftSide ? 2.6 : -2.6), z: bag2[1] + 3.4,
                          byT: play.cutT + play.viaDur });
      play.throwTo = bag1;
      play.throwDur = throwTime({ x: bag2[0], z: bag2[1] }, bag1[0], bag1[1], pivotP.arm);
      const fbI = coverFor(bag1[0], bag1[1], best.i);
      if (fbI >= 0 && fbI !== best.i && fbI !== pivotI)
        play.moves.push({ idx: fbI, x: bag1[0], z: bag1[1],
                          byT: play.cutT + play.viaDur + play.throwDur });
      return { kind: 'dp', outs: 2, fielder: best.s, play,
               text: `${best.s.sn}→${pivotK === '2B' ? 'セカンド' : 'ショート'}→ファースト\\nゲッツー！` };
    }""", 'dp pivot')

# --- outfield hits: relay to the cut-off man, or throw home ---
rep("""  /* ---- a base hit ---- */
  const ahead = basePt(Math.min(safeTo, 2));
  aimAt(ahead[0], ahead[1]);""",
"""  /* ---- a base hit ---- */
  if (infield) {
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
  } else if (G.bases[1] || G.bases[2]) {
    aimAt(HOME_POS[0], HOME_POS[1]);        // a runner is coming round: back home
  } else {
    // never throw to the bag ahead of the runner from the outfield — a throw to
    // third on a triple only opens up the plate. It goes to the cut-off man.
    const d0 = Math.hypot(P.x, P.z) || 1;
    const rx = (P.x / d0) * 36, rz = (P.z / d0) * 36;
    let cutK = fl.ang > 0 ? 'SS' : '2B';
    if (stationIdx(cutK) === best.i) cutK = cutK === 'SS' ? '2B' : 'SS';
    const ci = stationIdx(cutK);
    play.throwTo = [rx, rz];
    play.throwDur = throwTime(P, rx, rz, best.pl.arm);
    if (ci >= 0 && ci !== best.i)
      play.moves.push({ idx: ci, x: rx, z: rz, byT: play.cutT + play.throwDur });
  }""", 'relay')

# --- the play must last long enough for a relay ---
rep("""  const pl = G.playScript;
  if (pl) m = Math.max(m, pl.cutT + (pl.throwDur || 0) + 0.7);""",
"""  const pl = G.playScript;
  if (pl) m = Math.max(m, pl.cutT + (pl.viaDur || 0) + (pl.via ? 0.28 : 0)
                          + (pl.throwDur || 0) + 0.7);""", 'playLength')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js — animate the extra fielders and the relay leg
# ============================================================
box, rep = mk('src/50-main.js')
rep("""          // and a team-mate covers the bag the throw is going to
          if (pl.throwTo && pl.coverIdx >= 0 && pl.coverIdx !== pl.fidx) {
            const c = G.fielders[pl.coverIdx];
            c.scripted = true;
            const cu = clamp(G.flightT / Math.max(0.5, pl.cutT + 0.25), 0, 1);
            const ce = cu * cu * (3 - 2 * cu);
            c.x = lerp(c.st.x, pl.throwTo[0], ce); c.z = lerp(c.st.z, pl.throwTo[1], ce);
            c.run = cu < 1 ? 1.2 : 0;
          }""",
"""          // team-mates cover the bags and back up the play
          for (const mv of pl.moves || []) {
            const c = G.fielders[mv.idx];
            if (!c || mv.idx === pl.fidx) continue;
            c.scripted = true;
            const cu = clamp(G.flightT / Math.max(0.5, mv.byT), 0, 1);
            const ce = cu * cu * (3 - 2 * cu);
            c.x = lerp(c.st.x, mv.x, ce); c.z = lerp(c.st.z, mv.z, ce);
            c.run = cu < 1 ? 1.2 : 0;
          }""", 'moves anim')

rep("""            live = false;
            const tt = G.flightT - pl.cutT;
            if (pl.throwTo && pl.throwDur > 0) {
              const u2 = clamp(tt / pl.throwDur, 0, 1);
              bx = lerp(pl.pt.x, pl.throwTo[0], u2);
              bz = lerp(pl.pt.z, pl.throwTo[1], u2);
              by = lerp(Math.max(pl.pt.y, 1.0), 1.0, u2) + Math.sin(u2 * Math.PI) * 2.4;
              if (u2 >= 1) by = 1.0;
            } else {
              bx = pl.pt.x; by = Math.max(pl.pt.y, 0.14); bz = pl.pt.z;
            }""",
"""            live = false;
            let tt = G.flightT - pl.cutT;
            let fromX = pl.pt.x, fromZ = pl.pt.z, fromY = Math.max(pl.pt.y, 1.0);
            const arc = (ax, az, ay, bx2, bz2, u) => {
              bx = lerp(ax, bx2, u); bz = lerp(az, bz2, u);
              by = lerp(ay, 1.0, u) + Math.sin(u * Math.PI) * 2.4;
              if (u >= 1) by = 1.0;
            };
            if (pl.via) {                       // the relay through second
              if (tt <= pl.viaDur) {
                arc(fromX, fromZ, fromY, pl.via[0], pl.via[1], clamp(tt / pl.viaDur, 0, 1));
              } else {
                bx = pl.via[0]; bz = pl.via[1]; by = 1.0;
                tt -= pl.viaDur + 0.28;         // a beat on the bag, then away
                if (tt > 0 && pl.throwTo && pl.throwDur > 0)
                  arc(pl.via[0], pl.via[1], 1.0, pl.throwTo[0], pl.throwTo[1],
                      clamp(tt / pl.throwDur, 0, 1));
              }
            } else if (pl.throwTo && pl.throwDur > 0) {
              arc(fromX, fromZ, fromY, pl.throwTo[0], pl.throwTo[1], clamp(tt / pl.throwDur, 0, 1));
            } else {
              bx = pl.pt.x; by = Math.max(pl.pt.y, 0.14); bz = pl.pt.z;
            }""", 'relay anim')
wr('src/50-main.js', box['s'])
print('patched ok')
