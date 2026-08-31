# 1. The catcher was the fall-through receiver in coverFor, so a fly ball lobbed
#    back to the mound sent him charging out to it. Anything that is not a bag
#    now goes to the nearest infielder, and the catcher only ever moves to just
#    behind the plate.
# 2. Count/bases move to the bottom right; the play-by-play log moves to the
#    left; the batter card goes to the top left.
# 3. Hit by pitch.
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

# ---- (1) the catcher stays home ----
rep("""const BACKUP = { '1B': 'P', '2B': 'SS', '3B': 'P', C: 'P', SS: '2B' };
function coverFor(tx, tz, busy) {
  let want = dist2(tx, tz, BASE_POS[0][0], BASE_POS[0][1]) < 1 ? '1B'
    : dist2(tx, tz, BASE_POS[1][0], BASE_POS[1][1]) < 1 ? '2B'
    : dist2(tx, tz, BASE_POS[2][0], BASE_POS[2][1]) < 1 ? '3B' : 'C';
  let i = G.stations.findIndex((s) => s.k === want);
  if (i === busy && BACKUP[want]) i = G.stations.findIndex((s) => s.k === BACKUP[want]);
  return i;
}""",
"""const BACKUP = { '1B': 'P', '2B': 'SS', '3B': 'P', C: 'P', SS: '2B' };
function coverFor(tx, tz, busy) {
  const near = (b) => dist2(tx, tz, b[0], b[1]) < 1.5;
  const want = near(BASE_POS[0]) ? '1B' : near(BASE_POS[1]) ? '2B'
    : near(BASE_POS[2]) ? '3B'
    : dist2(tx, tz, HOME_POS[0], HOME_POS[1]) < 2.5 ? 'C' : null;
  if (!want) {
    // not a bag — a lob back to the mound, a cut-off. The nearest infielder
    // takes it; the catcher never leaves the plate to chase a throw.
    let bi = -1, bd = 1e9;
    for (let i = 0; i < G.stations.length; i++) {
      const s = G.stations[i];
      if (s.k === 'C' || !s.infield || i === busy) continue;
      const d = dist2(tx, tz, s.x, s.z);
      if (d < bd) { bd = d; bi = i; }
    }
    return bi;
  }
  let i = G.stations.findIndex((s) => s.k === want);
  if (i === busy && BACKUP[want]) i = G.stations.findIndex((s) => s.k === BACKUP[want]);
  return i;
}""", 'coverFor')
rep("""    const ci = coverFor(bx, bz, play.fidx);
    if (ci >= 0 && ci !== play.fidx)
      play.moves.push({ idx: ci, x: bx, z: bz, byT: (after || play.cutT) + dur });""",
"""    const ci = coverFor(bx, bz, play.fidx);
    if (ci >= 0 && ci !== play.fidx) {
      const isC = G.stations[ci].k === 'C';   // he sets up just behind the plate
      play.moves.push({ idx: ci, x: isC ? 0 : bx, z: isC ? -1.1 : bz,
                        byT: (after || play.cutT) + dur });
    }""", 'catcher target')

# ---- (3) hit by pitch ----
rep("""    inZone: Math.abs(arrive.x) <= ZX + 0.05 && arrive.y >= ZY0 - 0.05 && arrive.y <= ZY1 + 0.05,
  };""",
"""    inZone: Math.abs(arrive.x) <= ZX + 0.05 && arrive.y >= ZY0 - 0.05 && arrive.y <= ZY1 + 0.05,
    // way inside and at body height: it is going to hit him unless he spins away
    hbp: arrive.x > 0.80 && arrive.y > 0.18 && arrive.y < 1.58 && chance(0.45),
  };""", 'hbp flag')

rep("""function afterPitch(kind) {
  const bat = curBatter();
  if (kind === 'ball') {""",
"""function afterPitch(kind) {
  const bat = curBatter();
  if (kind === 'hbp') {
    finishAtBat({ kind: 'hbp', text: 'デッドボール！' });
    return;
  }
  if (kind === 'ball') {""", 'afterPitch hbp')

rep("""    case 'walk':
      bat.bb++;
      runs = advanceOnWalk(bat);
      break;""",
"""    case 'walk':
      bat.bb++;
      runs = advanceOnWalk(bat);
      break;
    case 'hbp':
      bat.hbp++;
      runs = advanceOnWalk(bat);
      // he takes a moment to shake it off before trotting down
      for (const mv of G.movers) mv.t = -0.65;
      G.hbpT = 1.05;
      Snd.crash();
      logLine(`${bat.name}にデッドボール！`, true);
      break;""", 'applyOutcome hbp')
rep("  innings: 6,", "  innings: 6, hbpT: 0,", 'hbpT field')
wr('src/40-game.js', box['s'])

box2, rep2 = mk('src/30-actors.js')
rep2("      ab: 0, h: 0, hr: 0, rbi: 0, k: 0, bb: 0,",
     "      ab: 0, h: 0, hr: 0, rbi: 0, k: 0, bb: 0, hbp: 0,", 'stat field')
wr('src/30-actors.js', box2['s'])

# ============================================================
# 50-main.js
# ============================================================
box, rep = mk('src/50-main.js')

# fire the hit-by-pitch the moment the ball reaches him
rep("""      if (pc.t > pc.T + 0.42) {
        if (G.decided && G.decided.miss) afterPitch('whiff');""",
"""      if (pc.hbp && G.swingT < 0 && pc.t >= pc.T + 0.02) {
        G.ball.vis = false;
        afterPitch('hbp');
        break;
      }
      if (pc.t > pc.T + 0.42) {
        if (G.decided && G.decided.miss) afterPitch('whiff');""", 'hbp trigger')

rep("  updateTraffic(dt);", "  if (G.hbpT > 0) G.hbpT -= dt;\n  updateTraffic(dt);", 'hbpT tick')

# the batter is still at the plate while his mover is delayed
rep("  const batterRunning = G.movers.some((m) => m.from === -1);",
    "  const batterRunning = G.movers.some((m) => m.from === -1 && m.t >= 0);", 'batter running')
rep("""    const b = curBatter();
    const rig = batterRig(G.batSwingT, clock);""",
"""    const b = curBatter();
    if (G.hbpT > 0) {                       // just wore one — no bat, on the deck
      drawAnimal(BAT_X + 0.25, BAT_Z - 0.2, -Math.PI / 2, b.look,
        { fall: -0.62, spread: 0.20, legL: -0.35, legR: 0.30,
          armL: -1.7, armR: -1.6, bob: -0.12, helmet: 1 }, 0);
      for (let s2 = 0; s2 < 3; s2++) {
        const a2 = clock * 5 + s2 * 2.1;
        R.b('sphere', BAT_X + 0.25 + Math.cos(a2) * 0.34, 1.05 + Math.sin(clock * 6 + s2) * 0.05,
            BAT_Z - 0.2 + Math.sin(a2) * 0.34, 0.13, 0.13, 0.13, col('#FFE04A'));
      }
    } else {
    const rig = batterRig(G.batSwingT, clock);""", 'hbp batter draw')
rep("""    drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');
    drawGrip(rig.grip, rig.dir, rig.botAt, bt.trim);
    drawGrip(rig.grip, rig.dir, rig.topAt, bt.trim);
  }""",
"""    drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');
    drawGrip(rig.grip, rig.dir, rig.botAt, bt.trim);
    drawGrip(rig.grip, rig.dir, rig.topAt, bt.trim);
    }
  }""", 'hbp batter close')

rep("""    ['ルール', '4ボールで四球、3ストライクで三振、3アウトでチェンジ。""",
"""    ['ルール', '4ボールで四球、3ストライクで三振、当たればデッドボール、3アウトでチェンジ。""", 'rules text')
wr('src/50-main.js', box['s'])

# ============================================================
# 00-shell.html — HUD layout
# ============================================================
box, rep = mk('src/00-shell.html')
rep(""".countbox{position:absolute;top:14px;left:14px;background:var(--ink2);border-radius:12px;padding:11px 13px;""",
""".countbox{position:absolute;bottom:60px;right:14px;background:var(--ink2);border-radius:12px;padding:11px 13px;""", 'countbox pos')
rep("""#batter{position:absolute;bottom:16px;left:14px;background:var(--ink2);border-radius:12px;padding:10px 14px;""",
"""#batter{position:absolute;top:14px;left:14px;background:var(--ink2);border-radius:12px;padding:10px 14px;""", 'batter pos')
rep("""#log{position:absolute;bottom:70px;right:14px;width:262px;display:flex;flex-direction:column-reverse;""",
"""#log{position:absolute;bottom:16px;left:14px;width:262px;display:flex;flex-direction:column-reverse;""", 'log pos')
rep("""#log p{background:rgba(14,20,28,.82);border-left:3px solid var(--line);padding:6px 10px;border-radius:0 8px 8px 0;
  line-height:1.55;animation:slide .3s ease}
#log p.hi{border-left-color:var(--amber);color:var(--cream)}
@keyframes slide{from{opacity:0;transform:translateX(16px)}}""",
"""#log p{background:rgba(14,20,28,.82);border-left:3px solid var(--line);padding:6px 10px;border-radius:0 8px 8px 0;
  line-height:1.55;animation:slide .3s ease}
#log p.hi{border-left-color:var(--amber);color:var(--cream)}
@keyframes slide{from{opacity:0;transform:translateX(-16px)}}""", 'log anim')
rep("""@media (max-width:900px){
  #log{display:none;} .countbox{transform:scale(.86);transform-origin:top left}
  #btn-quit{top:auto;bottom:14px;right:12px;padding:7px 11px;font-size:11px}
  .scorebug{font-size:13px} .sb-team{min-width:100px} .sb-nm{font-size:11px}
  #hint{max-width:94vw} #batter{transform:scale(.9);transform-origin:bottom left}
}""",
"""@media (max-width:900px){
  #log{display:none;} .countbox{transform:scale(.86);transform-origin:bottom right}
  .scorebug{font-size:13px} .sb-team{min-width:100px} .sb-nm{font-size:11px}
  #hint{max-width:94vw} #batter{transform:scale(.9);transform-origin:top left}
}""", 'mobile 900')
rep("""  /* the batter card moves under the count so the hints keep the bottom row */
  #batter{top:56px;left:auto;right:10px;bottom:auto;transform:none;min-width:0;
    max-width:44vw;padding:8px 10px}
  #batter .who{font-size:14px} #batter .meta{display:none}
  #hint{bottom:10px;gap:5px;max-width:96vw}""",
"""  #batter{top:56px;left:10px;right:auto;bottom:auto;transform:none;min-width:0;
    max-width:46vw;padding:8px 10px}
  #batter .who{font-size:14px} #batter .meta{display:none}
  /* count bottom right, hints beside it on the left */
  .countbox{bottom:10px;right:10px;top:auto;left:auto;padding:8px 10px;gap:10px}
  #hint{bottom:10px;left:10px;transform:none;justify-content:flex-start;
    gap:5px;max-width:calc(100vw - 140px)}""", 'mobile 560')
rep("""  .countbox{top:56px;left:10px;padding:8px 10px;gap:10px;transform:none}
  .diamond{width:44px;height:44px} .diamond span{width:14px;height:14px}""",
"""  .diamond{width:44px;height:44px} .diamond span{width:14px;height:14px}""", 'mobile countbox old')
wr('src/00-shell.html', box['s'])
print('patched ok')
