# Calibration and detail pass:
#  - an outfielder cannot throw the batter out at first from 60m away
#  - realistic home-to-first times and a slower transfer on throws
#  - a wider spray angle, so not everything goes up the middle
#  - Japanese position names in the play-by-play (ショートゴロ, センターフライ)
#  - coach's boxes drawn open on the field side, as they are chalked for real
#  - on-deck circles at their real 37ft, and runners round the bags
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def mk(path):
    s = rd(path)
    def rep(a, b, label):
        nonlocal s
        if a not in s: raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b)
    return (lambda: s), rep

# ============================================================
# 20-world.js — markings + short position names
# ============================================================
get, rep = mk('src/20-world.js')
rep("""  // coach's boxes, 20ft x 10ft, set back from the baselines
  for (const sgn of [-1, 1]) {
    const dx = sgn * SQ2, dz = SQ2;            // along that foul line
    const nx = sgn * SQ2, nz = -SQ2;           // out into foul territory
    chalkRect(S, dx * 20.5 + nx * 5.6, dz * 20.5 + nz * 5.6,
              3.05, 6.1, sgn * 45 * DEG, chalk);
  }
  // on-deck circles, 5ft across, back in foul ground
  for (const sgn of [-1, 1]) chalkCircle(S, sgn * 7.6, -3.6, 0.76, chalk);""",
"""  // coach's boxes, 20ft x 10ft. They are chalked as three lines: the side
  // facing the field is left open so the coach can step out of it.
  for (const sgn of [-1, 1]) {
    const dx = sgn * SQ2, dz = SQ2;            // along that foul line
    const nx = sgn * SQ2, nz = -SQ2;           // out into foul territory
    const cx = dx * 20.5 + nx * 5.6, cz = dz * 20.5 + nz * 5.6;
    const hw = 1.525, hl = 3.05;
    const P = (u, v) => [cx + nx * u + dx * v, cz + nz * u + dz * v];
    const inA = P(-hw, -hl), inB = P(-hw, hl), outB = P(hw, hl), outA = P(hw, -hl);
    chalkLine(S, inB[0], inB[1], outB[0], outB[1], chalk);   // far end
    chalkLine(S, outB[0], outB[1], outA[0], outA[1], chalk); // outer side
    chalkLine(S, outA[0], outA[1], inA[0], inA[1], chalk);   // near end
  }
  // on-deck circles, 5ft across, 37ft from home in foul ground
  for (const sgn of [-1, 1]) chalkCircle(S, sgn * 9.0, -6.8, 0.76, chalk);""", 'coach boxes')

rep("""const POS_DEF = [
  { k: 'P',  a: 0,   d: () => 18.44,          nm: '投手' },
  { k: 'C',  a: 0,   d: () => -3.4,           nm: '捕手' },
  { k: '1B', a: -38, d: () => 27,             nm: '一塁手' },
  { k: '2B', a: -20, d: () => 36,             nm: '二塁手' },
  { k: 'SS', a: 20,  d: () => 36,             nm: '遊撃手' },
  { k: '3B', a: 38,  d: () => 27,             nm: '三塁手' },
  { k: 'LF', a: 30,  d: (st) => fenceAt(st, 30) * 0.76,  nm: '左翼手' },
  { k: 'CF', a: 0,   d: (st) => fenceAt(st, 0) * 0.78,   nm: '中堅手' },
  { k: 'RF', a: -30, d: (st) => fenceAt(st, -30) * 0.76, nm: '右翼手' },
];""",
"""const POS_DEF = [
  { k: 'P',  a: 0,   d: () => 18.44,          nm: '投手',   sn: 'ピッチャー' },
  { k: 'C',  a: 0,   d: () => -3.4,           nm: '捕手',   sn: 'キャッチャー' },
  { k: '1B', a: -38, d: () => 27,             nm: '一塁手', sn: 'ファースト' },
  { k: '2B', a: -20, d: () => 36,             nm: '二塁手', sn: 'セカンド' },
  { k: 'SS', a: 20,  d: () => 36,             nm: '遊撃手', sn: 'ショート' },
  { k: '3B', a: 38,  d: () => 27,             nm: '三塁手', sn: 'サード' },
  { k: 'LF', a: 30,  d: (st) => fenceAt(st, 30) * 0.76,  nm: '左翼手', sn: 'レフト' },
  { k: 'CF', a: 0,   d: (st) => fenceAt(st, 0) * 0.78,   nm: '中堅手', sn: 'センター' },
  { k: 'RF', a: -30, d: (st) => fenceAt(st, -30) * 0.76, nm: '右翼手', sn: 'ライト' },
];""", 'pos names')
rep("    return { k: p.k, nm: p.nm, x, z: d < 0 ? d : z, infield:",
    "    return { k: p.k, nm: p.nm, sn: p.sn, x, z: d < 0 ? d : z, infield:", 'station sn')
wr('src/20-world.js', get())

# ============================================================
# 40-game.js — calibration + names + rounded base paths
# ============================================================
get, rep = mk('src/40-game.js')
rep("""function throwTime(from, tx, tz, arm) {
  const d = Math.hypot(from.x - tx, from.z - tz);
  return 0.38 + d / (27 + (arm || 0.6) * 13) + (d > 46 ? 0.55 : 0);
}""",
"""function throwTime(from, tx, tz, arm) {
  const d = Math.hypot(from.x - tx, from.z - tz);
  return 0.55 + d / (27 + (arm || 0.6) * 13) + (d > 42 ? 0.70 : 0);
}""", 'throwTime')
rep("""function baseTime(p, n) {
  const first = 27.43 / (5.9 + p.speed * 2.0);
  const rest = 27.43 / (7.6 + p.speed * 2.2);
  return first + (n - 1) * rest + (n > 1 ? 0.25 : 0);
}""",
"""function baseTime(p, n) {
  const first = 27.43 / (5.6 + p.speed * 1.7);   // 4.9s slow .. 3.8s quick
  const rest = 27.43 / (7.6 + p.speed * 2.2);
  return first + (n - 1) * rest + (n > 1 ? 0.25 : 0);
}""", 'baseTime')

rep("""  const infield = best.s.infield;

  if (chance(errP)) {""",
"""  const infield = best.s.infield;
  const outDist = Math.hypot(P.x, P.z);
  // nobody throws the batter out at first from deep in the outfield
  if (safeTo === 0 && !infield && outDist > 40) safeTo = 1;

  if (chance(errP)) {""", 'no OF putout')

# short position names throughout the play-by-play
rep("""      return { kind: 'error', bases: fl.dist > 62 ? 2 : 1, err: true, play,
               text: `${best.s.nm}が落球！\\nエラー` };""",
"""      return { kind: 'error', bases: fl.dist > 62 ? 2 : 1, err: true, play,
               text: `${best.s.sn}が落球！\\nエラー` };""", 'err1')
rep("""      text: liner ? `${best.s.nm}ライナー\\nアウト`
        : (tight ? `${best.s.nm}が好捕！\\nアウト` : `${best.s.nm}フライ\\nアウト`) };""",
"""      text: liner ? `${best.s.sn}ライナー\\nアウト`
        : (tight ? `${best.s.sn}が好捕！\\nアウト` : `${best.s.sn}フライ\\nアウト`) };""", 'fly text')
rep("""    return { kind: 'error', bases: Math.max(1, safeTo), err: true, play,
             text: `${best.s.nm}がはじいた！\\nエラー` };""",
"""    return { kind: 'error', bases: Math.max(1, safeTo), err: true, play,
             text: `${best.s.sn}がはじいた！\\nエラー` };""", 'err2')
rep("""      return { kind: 'dp', outs: 2, fielder: best.s, play,
               text: `${best.s.nm}→二塁→一塁\\nゲッツー！` };""",
"""      return { kind: 'dp', outs: 2, fielder: best.s, play,
               text: `${best.s.sn}→セカンド→ファースト\\nゲッツー！` };""", 'dp text')
rep("""      return { kind: 'fc', outs: 1, fielder: best.s, play,
               text: `${best.s.nm}\\nフィルダースチョイス` };""",
"""      return { kind: 'fc', outs: 1, fielder: best.s, play,
               text: `${best.s.sn}\\nフィルダースチョイス` };""", 'fc text')
rep("""    return { kind: 'groundout', outs: 1, fielder: best.s, play,
             text: `${best.s.nm}ゴロ\\nアウト` };""",
"""    return { kind: 'groundout', outs: 1, fielder: best.s, play,
             text: `${best.s.sn}ゴロ\\nアウト` };""", 'go text')
rep("""  const text = safeTo === 3 ? 'スリーベースヒット！'
    : safeTo === 2 ? 'ツーベースヒット！'
    : infield ? '内野安打！'
    : Math.hypot(P.x, P.z) < 46 ? 'ポテンヒット！' : 'ヒット！';""",
"""  const text = safeTo === 3 ? `${best.s.sn}へ\\nスリーベースヒット！`
    : safeTo === 2 ? `${best.s.sn}へ\\nツーベースヒット！`
    : infield ? '内野安打！'
    : outDist < 46 ? 'ポテンヒット！' : `${best.s.sn}前ヒット！`;""", 'hit text')

# runners take a rounded turn at the bags they pass through
rep("""  const pts = [];
  for (let b = from; b <= to; b++) pts.push(basePt(b));
  if (pts.length < 2) pts.push(basePt(to));""",
"""  const pts = [];
  for (let b = from; b <= to; b++) {
    const q = basePt(b);
    // bags he only rounds are taken a little wide, as a runner actually does
    if (b > from && b < to && b >= 0 && b <= 2) {
      const ox = q[0] - 0, oz = q[1] - 19.4, l = Math.hypot(ox, oz) || 1;
      pts.push([q[0] + (ox / l) * 1.7, q[1] + (oz / l) * 1.7]);
    } else pts.push([q[0], q[1]]);
  }
  if (pts.length < 2) pts.push(basePt(to));""", 'rounded path')
wr('src/40-game.js', get())

# ============================================================
# 50-main.js — spray angle
# ============================================================
get, rep = mk('src/50-main.js')
rep("    dir = clamp(-d.dt * 245 + (pc.ax - (userBatting() ? G.reticle.x : G.cpuAim.x)) * 18 + gauss(4), -54, 54);",
    "    dir = clamp(-d.dt * 245 + (pc.ax - (userBatting() ? G.reticle.x : G.cpuAim.x)) * 18 + gauss(9), -54, 54);", 'spray')
wr('src/50-main.js', get())
print('patched ok')
