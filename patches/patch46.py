# Game-side work:
#  - a foul pop-up somebody can camp under is an out, not a plain foul
#  - an outfielder throws to the cut-off man, never straight at the pitcher
#  - the sacrifice-fly banner waits for the run to actually touch the plate
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s:
            raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)


edit('src/40-game.js', [
    # ---- the ball comes in through an infielder --------------------------
    ("""function fieldBall(fl) {""",
     """/* An outfielder never throws straight at the pitcher: the ball comes in
   through the cut-off man, who meets it on the line the ball came down on. */
function relayIn(play, fl, P, arm, fidx) {
  const d0 = Math.hypot(P.x, P.z) || 1;
  const rr = clamp(d0 * 0.55, 20, 40);
  const rx = (P.x / d0) * rr, rz = (P.z / d0) * rr;
  let cutK = fl.ang > 0 ? 'SS' : '2B';
  if (stationIdx(cutK) === fidx) cutK = cutK === 'SS' ? '2B' : 'SS';
  const ci = stationIdx(cutK);
  play.throwTo = [rx, rz];
  play.throwDur = throwTime(P, rx, rz, arm);
  if (ci >= 0 && ci !== fidx)
    play.moves.push({ idx: ci, x: rx, z: rz, byT: play.cutT + play.throwDur });
}

/* A pop-up into foul ground is an out if somebody can camp under it. Anything
   hit flat down the line, or hooking back into the seats, stays a plain foul.
   The middle infielders and the centre fielder never get there. */
function foulCatch(fl) {
  if (fl.la < 32 || fl.hang < 1.5) return null;
  const d = Math.hypot(fl.land.x, fl.land.z);
  if (d > 30) return null;                        // into the crowd
  if (Math.abs(fl.ang) > 95 && d > 15) return null;   // over the backstop
  const st = G.st, def = fldTeam();
  let best = null;
  for (let i = 0; i < G.stations.length; i++) {
    if (G.fielders[i] && G.fielders[i].down > 0) continue;
    const s = G.stations[i];
    if (s.k === '2B' || s.k === 'SS' || s.k === 'CF') continue;
    const pl = fielderOf(def, s.k);
    const spd = 6.0 * st.fielderSpeed * (0.86 + pl.defense * 0.28) * (s.k === 'C' ? 1.10 : 1);
    const fx = G.fielders[i] ? G.fielders[i].x : s.x;
    const fz = G.fielders[i] ? G.fielders[i].z : s.z;
    const it = interceptOn(fl, fx, fz, spd);
    if (!it.air) continue;                        // he has to get under it
    if (!best || it.t < best.it.t) best = { i, s, pl, it };
  }
  if (!best) return null;
  // it is a harder play than a routine fly: on the run, near the screen
  if (!chance(0.66)) return null;
  const P = best.it.p;
  const play = { fidx: best.i, cutIdx: best.it.i, cutT: best.it.t,
                 pt: { x: P.x, y: P.y, z: P.z }, air: true,
                 infield: !!best.s.infield, moves: [] };
  if (best.s.infield) { play.throwTo = null; play.throwDur = 0; }
  else relayIn(play, fl, P, best.pl.arm, best.i);
  return { kind: 'flyout', outs: 1, fielder: best.s, play, canSac: false, foulFly: 1,
           text: `ファウルフライ\\n${best.s.sn}がつかんだ！` };
}

function fieldBall(fl) {""",
     'relayIn + foulCatch'),

    ("  if (fl.foul) return { kind: 'foul', text: 'ファウル' };",
     "  if (fl.foul) return foulCatch(fl) || { kind: 'foul', text: 'ファウル' };",
     'hook foulCatch'),

    ("    else aimAt(MOUND_POS[0], MOUND_POS[1]);",
     "    else relayIn(play, fl, P, best.pl.arm, best.i);",
     'outfield relay'),

    # ---- the sacrifice fly is called when the run scores ------------------
    ("""  if (o.kind === 'flyout') return caught + 0.10;""",
     """  if (o.kind === 'flyout') {
    // on a sacrifice fly the words belong to the run, not to the catch. The
    // mover clock and G.flightT share an origin, and `t` still holds its
    // creation value here, so `dur - t` is when he touches the plate.
    let home = 0;
    for (const mv of G.movers)
      if (mv.to === 3 && !mv.retired) home = Math.max(home, mv.dur - mv.t);
    return Math.max(caught + 0.10, home ? home + 0.06 : 0);
  }""",
     'sac fly timing'),
])

print('patched ok')
