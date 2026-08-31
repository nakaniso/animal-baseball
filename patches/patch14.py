# Animation now replays the play script the ruling was made from: the ball stops
# where the fielder actually gets it, that fielder runs there and arrives with
# it, a team-mate covers the bag, and the throw goes to that bag. Also puts the
# pitcher's hand on the ball at release and the catcher's mitt on the pitch.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

p = 'src/50-main.js'
s = io.open(p, encoding='utf-8').read()
def rep(a, b, label):
    global s
    if a not in s: raise SystemExit('MISS: ' + label)
    s = s.replace(a, b)

# ---------- contact hands off the script ----------
rep("""  const o = fieldBall(G.flight);
  G.flightT = 0;
  G.throwArc = null;
  G.camMode = 'fly';

  if (o.kind === 'foul') {
    G.pendingCount = 'foul';
    setPhase('play', Math.min(G.flight.total, 1.9) + 0.5);
    banner('ファウル');
    return;
  }
  G.pendingCount = null;
  if (o.fielder && (o.kind === 'groundout' || o.kind === 'dp' || o.kind === 'fc')) {
    G.throwArc = { from: null, to: BASE_POS[0], t: 0, dur: 0.5 };
  }
  finishAtBat(o);""",
"""  const o = fieldBall(G.flight);
  G.flightT = 0;
  G.playScript = o.play || null;
  G.camMode = 'fly';

  if (o.kind === 'foul') {
    G.playScript = null;
    G.pendingCount = 'foul';
    setPhase('play', Math.min(G.flight.total, 1.9) + 0.5);
    banner('ファウル');
    return;
  }
  G.pendingCount = null;
  finishAtBat(o);""", 'doContact')

# ---------- the play phase follows the script ----------
rep("""    case 'play': {
      // ball along its simulated path
      if (G.flight) {
        G.flightT += dt;
        const path = G.flight.path;
        let i = Math.min(path.length - 1, Math.floor(G.flightT / (1 / 90)));
        const p = path[i];
        G.ball.x = p.x; G.ball.y = p.y; G.ball.z = p.z;
        G.trail.unshift(p.x, p.y, p.z);
        if (G.trail.length > 60) G.trail.length = 60;
        if (G.flightT > G.flight.total * 0.62 || G.flightT > 2.6) G.camMode = 'field';
        // the nearest fielder converges on the ball
        let bi = 0, bd = 1e9;
        for (let k = 0; k < G.fielders.length; k++) {
          const f = G.fielders[k], d = dist2(f.st.x, f.st.z, G.flight.land.x, G.flight.land.z);
          if (d < bd) { bd = d; bi = k; }
        }
        G.fielders[bi].tx = G.flight.land.x; G.fielders[bi].tz = G.flight.land.z;
        if (G.throwArc && G.flightT > Math.min(G.flight.total, 1.2)) {
          G.throwArc.t += dt;
          const u = clamp(G.throwArc.t / G.throwArc.dur, 0, 1);
          G.ball.x = lerp(p.x, G.throwArc.to[0], u);
          G.ball.z = lerp(p.z, G.throwArc.to[1], u);
          G.ball.y = 1.0 + Math.sin(u * Math.PI) * 3.2;
        }
      }
      if (G.pt >= G.phaseLen) endPlay();
      break;
    }""",
"""    case 'play': {
      if (G.flight) {
        G.flightT += dt;
        const fl = G.flight, pl = G.playScript, path = fl.path;
        const stop = pl ? Math.min(pl.cutIdx, path.length - 1) : path.length - 1;
        const p = path[Math.min(stop, Math.floor(G.flightT / (1 / 90)))];
        let bx = p.x, by = p.y, bz = p.z, live = true;

        if (pl) {
          // the fielder runs to the ball and arrives with it
          const f = G.fielders[pl.fidx];
          f.scripted = true;
          const u = clamp((G.flightT - 0.22) / Math.max(0.25, pl.cutT - 0.22), 0, 1);
          const e = u * u * (3 - 2 * u);
          f.x = lerp(f.st.x, pl.pt.x, e); f.z = lerp(f.st.z, pl.pt.z, e);
          f.run = u < 1 ? 1.2 : 0;
          // and a team-mate covers the bag the throw is going to
          if (pl.throwTo && pl.coverIdx >= 0 && pl.coverIdx !== pl.fidx) {
            const c = G.fielders[pl.coverIdx];
            c.scripted = true;
            const cu = clamp(G.flightT / Math.max(0.5, pl.cutT + 0.25), 0, 1);
            const ce = cu * cu * (3 - 2 * cu);
            c.x = lerp(c.st.x, pl.throwTo[0], ce); c.z = lerp(c.st.z, pl.throwTo[1], ce);
            c.run = cu < 1 ? 1.2 : 0;
          }
          if (G.flightT > pl.cutT) {
            live = false;
            const tt = G.flightT - pl.cutT;
            if (pl.throwTo && pl.throwDur > 0) {
              const u2 = clamp(tt / pl.throwDur, 0, 1);
              bx = lerp(pl.pt.x, pl.throwTo[0], u2);
              bz = lerp(pl.pt.z, pl.throwTo[1], u2);
              by = lerp(Math.max(pl.pt.y, 1.0), 1.0, u2) + Math.sin(u2 * Math.PI) * 2.4;
              if (u2 >= 1) by = 1.0;
            } else {
              bx = pl.pt.x; by = Math.max(pl.pt.y, 0.95); bz = pl.pt.z;
            }
          }
        }
        G.ball.x = bx; G.ball.y = by; G.ball.z = bz;
        if (live) {
          G.trail.unshift(bx, by, bz);
          if (G.trail.length > 60) G.trail.length = 60;
        } else if (G.trail.length) {
          G.trail.length = Math.max(0, G.trail.length - 6);
        }
        const wide = pl ? pl.cutT * 0.72 : fl.total * 0.62;
        if (G.flightT > wide || G.flightT > 2.8) G.camMode = 'field';
      }
      if (G.pt >= G.phaseLen) endPlay();
      break;
    }""", 'play phase')

# ---------- scripted fielders are not dragged back to their stations ----------
rep("""  for (const f of G.fielders) {
    const k = Math.min(1, dt * 2.2);
    f.x += (f.tx - f.x) * k; f.z += (f.tz - f.z) * k;
    f.run = Math.hypot(f.tx - f.x, f.tz - f.z);
    const dx = -f.x, dz = -f.z;
    f.ry = Math.atan2(dx, dz);
  }""",
"""  for (const f of G.fielders) {
    if (!f.scripted) {
      const k = Math.min(1, dt * 2.2);
      f.x += (f.tx - f.x) * k; f.z += (f.tz - f.z) * k;
      f.run = Math.hypot(f.tx - f.x, f.tz - f.z);
    }
    // a fielder making a play watches the ball; otherwise he faces the plate
    if (f.scripted && G.ball.vis) f.ry = Math.atan2(G.ball.x - f.x, G.ball.z - f.z);
    else f.ry = Math.atan2(-f.x, -f.z);
  }""", 'fielder update')

rep("""function endPlay() {
  G.ball.vis = false;
  G.flight = null;""",
"""function endPlay() {
  G.ball.vis = false;
  G.flight = null;
  G.playScript = null;
  for (const f of G.fielders) f.scripted = false;""", 'endPlay')

# ---------- the pitch dies in the catcher's mitt ----------
rep("""      const p = pitchPos(pc, pc.t);
      G.ball.x = p.x; G.ball.y = p.y; G.ball.z = p.z;""",
"""      const p = pitchPos(pc, pc.t);
      const mitt = -2.3;                       // the ball is caught, not flown past
      G.ball.x = p.x; G.ball.y = Math.max(p.y, 0.35); G.ball.z = Math.max(p.z, mitt);""", 'mitt')

# ---------- pitcher and catcher hands ----------
rep("""    const isP = f.st.k === 'P', isC = f.st.k === 'C';
    let ry = f.ry;
    if (isP && G.phase === 'pitch') pose.armR = -2.2 + clamp(G.pitch.t * 6, 0, 2.4);
    const y0 = isC ? -0.22 : 0;
    const a = drawAnimal(f.x, f.z, ry, pl.look, pose, y0);
    const gp = L2W(a.f, a.hl[0], a.hl[2]);
    if (!isP) drawGlove([gp[0], a.hl[1], gp[1]], ft.trim);""",
"""    const isP = f.st.k === 'P', isC = f.st.k === 'C';
    let ry = f.ry;
    if (isP) {
      if (G.phase === 'ready') {                 // wind up
        const u = clamp(G.pt / Math.max(0.3, G.phaseLen), 0, 1);
        pose.armL = -0.5 - u * 2.0; pose.armR = -0.4 - u * 0.8; pose.legR = -u * 0.45;
      } else if (G.phase === 'pitch') {
        const t = G.pitch.t;
        if (t < 0.16 && G.ball.vis) {             // the ball is still in his hand
          pose.handL = [G.ball.x, G.ball.y, G.ball.z];
          pose.pole = [0.4, -0.6, 0.2];
        }
        pose.armR = -1.6 + clamp(t * 5, 0, 2.0);
      }
    }
    if (isC && G.ball.vis && G.phase === 'pitch' && G.ball.z < 5) {
      pose.handL = [clamp(G.ball.x, -1.1, 1.1), clamp(G.ball.y, 0.3, 1.7),
                    Math.max(G.ball.z, f.z + 0.55)];
      pose.pole = [0, -0.7, 0.7];
    }
    const y0 = isC ? -0.22 : 0;
    const a = drawAnimal(f.x, f.z, ry, pl.look, pose, y0);
    const gp = L2W(a.f, a.hl[0], a.hl[2]);
    if (!isP) drawGlove(pose.handL ? [pose.handL[0], pose.handL[1], pose.handL[2]]
                                   : [gp[0], a.hl[1], gp[1]], ft.trim);""", 'pitcher catcher')

io.open(p, 'w', encoding='utf-8').write(s)
print('patched ok')
