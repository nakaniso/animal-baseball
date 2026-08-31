# The ruling and the ball now come from the same physics. Previously fieldBall
# picked a fielder by angle while the ball flew its own path, so a "pitcher's
# grounder" could roll to centre field. Now: simulate the ball, work out which
# fielder can actually get a glove on it and when, then race the throw against
# the runner. The animation is handed the same numbers as a play script.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

p = 'src/40-game.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b)

# ---------- rolling physics: a grounder should keep rolling, not stop dead ----------
rep("""    if (y <= BALL_R) {
      if (!hang) hang = t;
      y = BALL_R;
      if (bounced < 3 && Math.abs(vy) > 1.2) { vy = -vy * 0.34; vx *= 0.66; vz *= 0.66; bounced++; }
      else { vy = 0; vx *= 0.965; vz *= 0.965; }
      if (Math.hypot(vx, vz) < 1.2) { path.push({ x, y, z, t }); break; }
    }""",
"""    if (y <= BALL_R) {
      if (!hang) hang = t;
      if (groundIdx < 0) groundIdx = path.length;
      y = BALL_R;
      if (bounced < 6 && Math.abs(vy) > 0.9) { vy = -vy * 0.36; vx *= 0.82; vz *= 0.82; bounced++; }
      else { vy = 0; vx -= vx * 1.15 * dt; vz -= vz * 1.15 * dt; }  // rolling friction
      if (Math.hypot(vx, vz) < 0.6) { path.push({ x, y, z, t }); break; }
    }""", 'roll')
rep("  let t = 0, hr = false, ceilHit = false, apex = y, hang = 0, bounced = 0;",
    "  let t = 0, hr = false, ceilHit = false, apex = y, hang = 0, bounced = 0, groundIdx = -1;", 'groundIdx var')
rep("""    path, hang: landT, apex, hr, ceilHit, la: laDeg, dir: dirDeg, v0,""",
    """    path, hang: landT, apex, hr, ceilHit, la: laDeg, dir: dirDeg, v0,
    groundIdx: groundIdx < 0 ? path.length : groundIdx,""", 'groundIdx out')

# ---------- new fielding model ----------
old = s[s.index("/* ============================================================\n   turning a batted ball into a baseball outcome"):s.index("/* ============================================================\n   base running")]
new = """/* ============================================================
   turning a batted ball into a baseball outcome
   ============================================================ */
const fielderOf = (team, k) => team.roster.find((r) => r.pos === k) || team.roster[0];

/* The first moment a fielder starting at (sx,sz) can put a glove on the ball.
   Only points below jumping height count, and he needs time to get there. */
function interceptOn(fl, sx, sz, spd) {
  const path = fl.path;
  for (let i = 0; i < path.length; i++) {
    const q = path[i];
    if (q.y > 2.6) continue;                       // still over his head
    const reach = 1.0 + spd * Math.max(0, q.t - 0.30) * 0.88;
    if (Math.hypot(q.x - sx, q.z - sz) <= reach)
      return { i, t: q.t, p: q, air: i < fl.groundIdx };
  }
  const i = path.length - 1;
  return { i, t: path[i].t, p: path[i], air: false, late: true };
}

/* transfer + throw, with a cut-off man on anything long */
function throwTime(from, tx, tz, arm) {
  const d = Math.hypot(from.x - tx, from.z - tz);
  return 0.38 + d / (27 + (arm || 0.6) * 13) + (d > 46 ? 0.55 : 0);
}

/* seconds from contact for a runner to reach base n (1 = first) */
function baseTime(p, n) {
  const first = 27.43 / (5.9 + p.speed * 2.0);
  const rest = 27.43 / (7.6 + p.speed * 2.2);
  return first + (n - 1) * rest + (n > 1 ? 0.25 : 0);
}

/* which fielder covers a bag for the throw */
function coverFor(tx, tz) {
  const want = dist2(tx, tz, BASE_POS[0][0], BASE_POS[0][1]) < 1 ? '1B'
    : dist2(tx, tz, BASE_POS[1][0], BASE_POS[1][1]) < 1 ? '2B'
    : dist2(tx, tz, BASE_POS[2][0], BASE_POS[2][1]) < 1 ? '3B' : 'C';
  return G.stations.findIndex((s) => s.k === want);
}

function fieldBall(fl) {
  const st = G.st, bat = curBatter(), def = fldTeam();

  if (fl.foul) return { kind: 'foul', text: 'ファウル' };
  if (fl.hr) {
    const far = fl.finalDist > fenceAt(st, fl.ang) * 1.22;
    return { kind: 'hr', bases: 4, big: true,
      text: far ? 'ホームラン！\\n特大の一発だ' : 'ホームラン！' };
  }
  if (fl.ceilHit && st.ceiling && fl.dist >= fenceAt(st, fl.ang) * 0.94)
    return { kind: 'ground_rule', bases: 2, hit: true, text: '天井に当たった！\\nエンタイトルツーベース' };
  if (st.fenceH === 0 && fl.dist >= fenceAt(st, fl.ang) && fl.la >= 14)
    return { kind: 'hr', bases: 4, big: true, text: 'ホームラン！\\n川まで届いた' };

  /* who actually gets to it first */
  let best = null;
  for (let i = 0; i < G.stations.length; i++) {
    const s = G.stations[i], pl = fielderOf(def, s.k);
    const spd = 6.8 * st.fielderSpeed * (0.86 + pl.defense * 0.28);
    const it = interceptOn(fl, s.x, s.z, spd);
    if (!best || it.t < best.it.t) best = { i, s, pl, spd, it };
  }
  const P = best.it.p;
  const errP = clamp((1 - best.pl.defense) * 0.05
    + (st.id === 'market' ? 0.03 : 0) + (st.id === 'road' ? 0.025 : 0), 0, 0.13);
  const play = { fidx: best.i, cutIdx: best.it.i, cutT: best.it.t,
                 pt: { x: P.x, y: P.y, z: P.z }, air: best.it.air };
  const aimAt = (bx, bz) => {
    play.throwTo = [bx, bz];
    play.throwDur = throwTime(P, bx, bz, best.pl.arm);
    play.coverIdx = coverFor(bx, bz);
  };

  /* ---- caught on the fly ---- */
  if (best.it.air) {
    if (chance(errP * 0.55)) {
      G.errs[1 - G.half]++;
      aimAt(BASE_POS[1][0], BASE_POS[1][1]);
      return { kind: 'error', bases: fl.dist > 62 ? 2 : 1, err: true, play,
               text: `${best.s.nm}が落球！\\nエラー` };
    }
    const liner = fl.la < 24 && fl.hang < 1.7;
    const tight = best.it.t > fl.hang - 0.45;
    aimAt(MOUND_POS[0], MOUND_POS[1]);           // lob it back in
    return { kind: 'flyout', outs: 1, fielder: best.s, play,
      canSac: !liner && Math.hypot(P.x, P.z) > 48,
      text: liner ? `${best.s.nm}ライナー\\nアウト`
        : (tight ? `${best.s.nm}が好捕！\\nアウト` : `${best.s.nm}フライ\\nアウト`) };
  }

  /* ---- played off the ground: race the throw to the bag ---- */
  let safeTo = 0;
  for (let n = 1; n <= 3; n++) {
    const arrives = best.it.t + throwTime(P, basePt(n - 1)[0], basePt(n - 1)[1], best.pl.arm);
    if (arrives > baseTime(bat, n) + 0.12) safeTo = n; else break;
  }
  const infield = best.s.infield;

  if (chance(errP)) {
    G.errs[1 - G.half]++;
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
    return { kind: 'error', bases: Math.max(1, safeTo), err: true, play,
             text: `${best.s.nm}がはじいた！\\nエラー` };
  }

  if (safeTo === 0) {
    if (G.bases[0] && G.outs < 2 && infield && fl.v0 > 17
        && chance(0.34 + best.pl.defense * 0.28)) {
      aimAt(BASE_POS[0][0], BASE_POS[0][1]);
      play.via = BASE_POS[1];
      return { kind: 'dp', outs: 2, fielder: best.s, play,
               text: `${best.s.nm}→二塁→一塁\\nゲッツー！` };
    }
    if (G.bases[0] && G.outs < 2 && chance(0.22)) {
      aimAt(BASE_POS[1][0], BASE_POS[1][1]);
      return { kind: 'fc', outs: 1, fielder: best.s, play,
               text: `${best.s.nm}\\nフィルダースチョイス` };
    }
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
    return { kind: 'groundout', outs: 1, fielder: best.s, play,
             text: `${best.s.nm}ゴロ\\nアウト` };
  }

  /* ---- a base hit ---- */
  const ahead = basePt(Math.min(safeTo, 2));
  aimAt(ahead[0], ahead[1]);
  if (st.fenceH === 0 && safeTo === 3 && bat.speed > 0.72 && chance(0.22))
    return { kind: 'ihr', bases: 4, hit: true, big: true, play, text: 'ランニングホームラン！' };
  const text = safeTo === 3 ? 'スリーベースヒット！'
    : safeTo === 2 ? 'ツーベースヒット！'
    : infield ? '内野安打！'
    : Math.hypot(P.x, P.z) < 46 ? 'ポテンヒット！' : 'ヒット！';
  return { kind: 'hit', bases: safeTo, hit: true, play, text };
}

"""
s = s.replace(old, new)

# ---------- retired runners still run it out ----------
rep("""    case 'flyout':
      bat.ab++; outsAdded = 1;""",
"""    case 'flyout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0);""", 'flyout run')
rep("""    case 'groundout':
      bat.ab++; outsAdded = 1;""",
"""    case 'groundout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0);""", 'groundout run')
rep("""    case 'dp':
      bat.ab++; outsAdded = Math.min(2, 3 - G.outs);
      G.bases[0] = null;""",
"""    case 'dp': {
      bat.ab++; outsAdded = Math.min(2, 3 - G.outs);
      const forced = G.bases[0];
      G.bases[0] = null;
      moveRunner(bat, -1, 0);
      if (forced) moveRunner(forced, 0, 1);""", 'dp run')
rep("""      if (G.bases[1]) { G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null; }
      Snd.mitt();
      break;
    case 'strikeout':""",
"""      if (G.bases[1]) { G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null; }
      Snd.mitt();
      break;
    }
    case 'strikeout':""", 'dp close')
rep("""    case 'bunt_out':
      bat.ab++; outsAdded = 1;""",
"""    case 'bunt_out':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0);""", 'bunt run')

# ---------- the play length must cover the throw ----------
rep("""function playLength() {
  let m = 1.4;
  for (const mv of G.movers) m = Math.max(m, mv.dur - mv.t + 0.5);
  if (G.flight) m = Math.max(m, Math.min(G.flight.total, 5.0) + 0.8);
  return m;
}""",
"""function playLength() {
  let m = 1.4;
  for (const mv of G.movers) m = Math.max(m, mv.dur - mv.t + 0.5);
  const pl = G.playScript;
  if (pl) m = Math.max(m, pl.cutT + (pl.throwDur || 0) + 0.7);
  else if (G.flight) m = Math.max(m, Math.min(G.flight.total, 5.0) + 0.8);
  return m;
}""", 'playLength')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
