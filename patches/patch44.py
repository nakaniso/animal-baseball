# Three things:
#  1. the result banner (and its sound) waited for nobody — "センターがはじいた"
#     appeared while the ball was still in the air. Hold each one until the
#     moment on screen that it describes.
#  2. with two out there is nothing to tag up for, so runners go on contact.
#  3. base running: the batter-runner runs through first or takes his turn and
#     pulls up, and anyone racing a throw to a bag goes in sliding.
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
    # --- the play script records where the ball was played ---------------
    ("""  const play = { fidx: best.i, cutIdx: best.it.i, cutT: best.it.t,
                 pt: { x: P.x, y: P.y, z: P.z }, air: best.it.air, moves: [] };""",
     """  const play = { fidx: best.i, cutIdx: best.it.i, cutT: best.it.t,
                 pt: { x: P.x, y: P.y, z: P.z }, air: best.it.air,
                 infield: !!best.s.infield, moves: [] };""",
     'play.infield'),
    ("""             play: { fidx: 0, cutIdx: fl.path.length - 1, cutT: q.t,
                     pt: { x: q.x, y: q.y, z: q.z }, air: false, coverIdx: -1 } };""",
     """             play: { fidx: 0, cutIdx: fl.path.length - 1, cutT: q.t,
                     pt: { x: q.x, y: q.y, z: q.z }, air: false, infield: false,
                     coverIdx: -1 } };""",
     'triple play.infield'),

    # --- moveRunner hands the mover back so the caller can style it ------
    ("""  G.movers.push({
    p, from, to, pts, segs, total, t: -(delay || 0), dur,
    scored: to >= 3, retired: !!retired,
    rbiOwner: to >= 3 ? curBatter() : null,
  });""",
     """  const mv = {
    p, from, to, pts, segs, total, t: -(delay || 0), dur,
    scored: to >= 3, retired: !!retired,
    rbiOwner: to >= 3 ? curBatter() : null,
  };
  G.movers.push(mv);
  return mv;""",
     'moveRunner returns'),

    # --- how each runner finishes ----------------------------------------
    ("""/* everyone still on base moves up one, lead runner first */""",
     """/* How the runners finish. The batter-runner never stops on first: on a play
   in the infield he runs straight through the bag, and on a ball through to
   the outfield he takes his turn toward second and pulls up. Anyone arriving
   at a bag the ball is also arriving at goes in sliding. */
function styleBaseRunning(o) {
  const pl = o.play;
  const targets = [];
  if (pl && pl.throwTo) targets.push(pl.throwTo);
  if (pl && pl.via) targets.push(pl.via);
  for (const mv of G.movers) {
    if (mv.from === -1 && mv.to === 0) {
      const b = basePt(0);
      if (pl && !pl.infield) {                 // rounding, looking at second
        const n = basePt(1);
        const ux = n[0] - b[0], uz = n[1] - b[1], ul = Math.hypot(ux, uz) || 1;
        mv.over = { x: b[0] + (ux / ul) * 3.6, z: b[1] + (uz / ul) * 3.6,
                    dur: 0.62, ret: false };
      } else {                                 // straight through, then back
        const ul = Math.hypot(b[0], b[1]) || 1;      // home plate is the origin
        mv.over = { x: b[0] + (b[0] / ul) * 5.4, z: b[1] + (b[1] / ul) * 5.4,
                    dur: 0.55, ret: true };
      }
    }
    if (mv.to >= 1 && mv.to <= 3) {
      const b = basePt(mv.to);
      for (const t of targets)
        if (Math.hypot(t[0] - b[0], t[1] - b[1]) < 5.0) { mv.slide = 1; break; }
    }
  }
}

/* everyone still on base moves up one, lead runner first */""",
     'styleBaseRunning'),

    # --- two out: nobody waits on a fly ball ------------------------------
    ("""      } else if (G.outs < 2 && G.bases[1] && o.canSac && chance(0.62)) {
        G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2, held); G.bases[1] = null;
      }
      Snd.mitt();
      break;
    }""",
     """      } else if (G.outs < 2 && G.bases[1] && o.canSac && chance(0.62)) {
        G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2, held); G.bases[1] = null;
      } else if (G.outs >= 2) {
        // two out — he is running on contact, and the catch ends the inning
        // anyway, so show him going rather than standing on the bag
        for (let i = 2; i >= 0; i--)
          if (G.bases[i]) moveRunner(G.bases[i], i, i + 1, 0, true);
      }
      o.snd = 'mitt';
      break;
    }""",
     'two-out fly'),

    # --- the sounds move with the banner ---------------------------------
    ("      Snd.cheer();\n      break;", "      o.snd = 'cheer';\n      break;", 'hr snd'),
    ("      Snd.good();\n      break;", "      o.snd = 'good';\n      break;", 'hit snd'),
    ("      Snd.bad();\n      break;", "      o.snd = 'bad';\n      break;", 'error snd'),
    ("""      if (chance(0.86)) runs += advanceOneAll(bat, G.outs < 2 && chance(0.85));
      Snd.mitt();""",
     """      if (chance(0.86)) runs += advanceOneAll(bat, G.outs < 2 && chance(0.85));
      o.snd = 'mitt';""", 'groundout snd'),
    ("""      G.bases[0] = bat; moveRunner(bat, -1, 0);
      Snd.mitt();""",
     """      G.bases[0] = bat; moveRunner(bat, -1, 0);
      o.snd = 'mitt';""", 'fc snd'),
    ("""      if (G.bases[1]) { G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null; }
      Snd.mitt();""",
     """      if (G.bases[1]) { G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null; }
      o.snd = 'mitt';""", 'dp snd'),
    ("      bat.ab++; bat.k++; outsAdded = 1;\n      Snd.miss();",
     "      bat.ab++; bat.k++; outsAdded = 1;\n      o.snd = 'miss';", 'k snd'),
    ("      G.hbpT = 1.05;\n      Snd.crash();",
     "      G.hbpT = 1.05;\n      o.snd = 'crash';", 'hbp snd'),

    ("""  G.outs += outsAdded;
  if (runs > 0) {""",
     """  styleBaseRunning(o);
  G.outs += outsAdded;
  if (runs > 0) {""", 'call styleBaseRunning'),

    # --- hold the banner until the play reaches its point -----------------
    ("""  G.lastText = o.text;
  banner(o.text, o.big);
  uiScore();""",
     """  G.lastText = o.text;
  uiScore();""", 'drop immediate banner'),

    ("""function finishAtBat(o) {
  applyOutcome(o);
  logLine(`${G.inning}回${G.half === 0 ? '表' : '裏'} ${curBatter().name}：${o.text.replace('\\n', ' ')}`);
  G.order[G.half] = (G.order[G.half] + 1) % 9;
  if (!G.flight) G.ball.vis = false;   // a batted ball stays on screen
  setPhase('play', Math.max(1.5, playLength()));
}""",
     """/* When the words should land: as the ball is booted, as it hits the mitt, as
   the throw beats him to the bag. Measured on the same clock the play script
   runs on (`G.flightT`), so it stays glued to what is on screen. */
function resultDelay(o) {
  const pl = o.play;
  if (!pl) return G.flight ? Math.min(G.flight.total * 0.72, 2.4) : 0;
  const caught = pl.cutT;
  if (o.err) return caught + (pl.air ? 0.16 : 0.26);
  if (o.kind === 'flyout') return caught + 0.10;
  if (o.kind === 'groundout' || o.kind === 'dp' || o.kind === 'fc' || o.kind === 'bunt_out')
    return caught + (pl.viaDur || 0) + (pl.throwDur || 0) + 0.06;
  return caught + 0.14;                       // a base hit, as it is played
}

function flushResult() {
  const q = G.pending;
  if (!q) return;
  G.pending = null;
  banner(q.text, q.big);
  if (q.snd && Snd[q.snd]) Snd[q.snd]();
}

function finishAtBat(o) {
  applyOutcome(o);
  logLine(`${G.inning}回${G.half === 0 ? '表' : '裏'} ${curBatter().name}：${o.text.replace('\\n', ' ')}`);
  G.order[G.half] = (G.order[G.half] + 1) % 9;
  if (!G.flight) G.ball.vis = false;   // a batted ball stays on screen
  const len = Math.max(1.5, playLength());
  G.pending = { text: o.text, big: o.big, snd: o.snd,
                at: Math.min(resultDelay(o), len - 0.25) };
  setPhase('play', len);
}""",
     'deferred banner'),

    # nothing may leave the play phase with the result still unsaid
    ("function setPhase(p, len) { G.phase = p; G.pt = 0; G.phaseLen = len || 0; }",
     """function setPhase(p, len) {
  if (G.phase === 'play' && p !== 'play') flushResult();
  G.phase = p; G.pt = 0; G.phaseLen = len || 0;
}""", 'setPhase flush'),

    # the run-through has to fit inside the play phase to be seen
    ("""  for (const mv of G.movers) if (!mv.retired) m = Math.max(m, Math.min(mv.dur - mv.t + 0.5, 6.6));""",
     """  for (const mv of G.movers) {
    if (!mv.retired) m = Math.max(m, Math.min(mv.dur - mv.t + 0.5, 6.6));
    if (mv.over) m = Math.max(m, Math.min(mv.dur - mv.t + mv.over.dur + 0.4, 6.6));
  }""", 'playLength overrun'),
])

edit('src/50-main.js', [
    # --- fire the held result on the play clock ---------------------------
    ("""    case 'play': {
      if (G.flight) {""",
     """    case 'play': {
      if (G.pending && (G.flight ? G.flightT : G.pt) >= G.pending.at) flushResult();
      if (G.flight) {""", 'fire pending'),

    # --- the overrun past first ------------------------------------------
    ("""function runnerAt(m) {
  const u = clamp(m.t / m.dur, 0, 1);
  const e = u * u * (3 - 2 * u);
  let d = e * m.total;
  const n = m.segs.length;
  for (let i = 0; i < n; i++) {
    if (d <= m.segs[i] || i === n - 1) {
      const k = m.segs[i] > 1e-6 ? clamp(d / m.segs[i], 0, 1) : 1;
      const a = m.pts[i], b = m.pts[i + 1];
      return { x: lerp(a[0], b[0], k), z: lerp(a[1], b[1], k), done: u >= 1, u,
               ry: Math.atan2(b[0] - a[0], b[1] - a[1]) };
    }
    d -= m.segs[i];
  }
  return { x: m.pts[0][0], z: m.pts[0][1], done: u >= 1, u, ry: 0 };
}""",
     """function runnerAt(m) {
  const u = clamp(m.t / m.dur, 0, 1);
  const e = u * u * (3 - 2 * u);
  let d = e * m.total;
  const n = m.segs.length;
  let r = { x: m.pts[0][0], z: m.pts[0][1], done: u >= 1, u, ry: 0 };
  for (let i = 0; i < n; i++) {
    if (d <= m.segs[i] || i === n - 1) {
      const k = m.segs[i] > 1e-6 ? clamp(d / m.segs[i], 0, 1) : 1;
      const a = m.pts[i], b = m.pts[i + 1];
      r = { x: lerp(a[0], b[0], k), z: lerp(a[1], b[1], k), done: u >= 1, u,
            ry: Math.atan2(b[0] - a[0], b[1] - a[1]) };
      break;
    }
    d -= m.segs[i];
  }
  // he does not stop dead on the bag
  if (m.over && u >= 1) {
    const o = m.over, s = m.t - m.dur, bx = r.x, bz = r.z;
    if (s < o.dur) {                              // carrying past it, slowing
      const q = s / o.dur, k = 1 - (1 - q) * (1 - q);
      r.x = lerp(bx, o.x, k); r.z = lerp(bz, o.z, k);
      r.ry = Math.atan2(o.x - bx, o.z - bz);
      r.done = false;
    } else if (o.ret && s < o.dur * 2.6) {        // and walking back to it
      const k = clamp((s - o.dur) / (o.dur * 1.6), 0, 1);
      r.x = lerp(o.x, bx, k); r.z = lerp(o.z, bz, k);
      r.ry = Math.atan2(bx - o.x, bz - o.z);
      r.done = false;
    } else if (!o.ret) { r.x = o.x; r.z = o.z; }
  }
  return r;
}""", 'runnerAt overrun'),

    # --- going in sliding -------------------------------------------------
    ("""    const sw = r.done ? 0 : Math.sin(clock * 15) * 0.9;
    drawAnimal(r.x, r.z, r.ry, m.p.look, {""",
     """    if (m.slide && r.u > 0.80) {          // a throw is coming: get down
      const k = clamp((r.u - 0.80) / 0.13, 0, 1);
      drawAnimal(r.x, r.z, r.ry, m.p.look, {
        fall: -1.00 * k, spread: 0.24, legL: -0.85, legR: -0.30,
        armL: -1.45, armR: -1.10, bob: -0.30 * k, helmet: 1, face: EXPR.focus,
      }, 0);
      continue;
    }
    const sw = r.done ? 0 : Math.sin(clock * 15) * 0.9;
    drawAnimal(r.x, r.z, r.ry, m.p.look, {""", 'slide pose'),
])

print('patched ok')
