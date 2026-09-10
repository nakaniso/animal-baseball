# Presentation side of the same six:
#  - a man not running takes his lead off the bag with the ball in the air:
#    halfway on a high fly, nowhere at all on a liner, and back the moment it
#    is caught
#  - three out gets its own beat: the call, the wide shot, everybody jogging in
#  - a foul pop that is caught keeps the camera down at the plate
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))


def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s:
            raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)


edit('src/50-main.js', [
    # ---- a caught foul pop stays on the plate camera ----------------------
    ("""  G.camMode = o.kind === 'foul' ? 'foul' : 'fly';
  G.ballBoost = o.kind === 'foul' ? 1.7 : 1;""",
     """  const nearPlate = o.kind === 'foul' || o.foulFly;
  G.camMode = nearPlate ? 'foul' : 'fly';
  G.ballBoost = nearPlate ? 1.7 : 1;""",
     'foul fly camera'),

    # ---- how far off the bag a stationary runner stands -------------------
    ("""function runnerAt(m) {""",
     """/* How far down the line a man who is not running stands. Before the pitch it
   is his lead. Once the ball is up he goes as far as he dares — halfway to the
   next bag on a high fly, not a step on a liner — and comes back the moment it
   is caught. */
function leadOff(i) {
  if (G.phase !== 'play') return LEAD_OFF + Math.sin(clock * 1.7 + i * 2) * 0.34;
  const pl = G.playScript;
  if (!pl || !pl.air) return 0.6;               // on the ground: back on the bag
  const hang = Math.max(0.4, pl.cutT);
  // hang time is what buys him the room to go and still get back
  const far = LEAD_OFF + clamp((hang - 1.6) / 1.5, 0, 1) * (i === 0 ? 11.0 : 7.5);
  if (G.flightT < hang) {
    const u = clamp(G.flightT / hang, 0, 1);
    return lerp(LEAD_OFF, far, u * u * (3 - 2 * u));
  }
  const k = clamp((G.flightT - hang) / 0.85, 0, 1);
  return lerp(far, 0.4, k * k * (3 - 2 * k));
}

function runnerAt(m) {""",
     'leadOff'),

    ("""    const off = G.phase === 'play' ? 0.25
      : LEAD_OFF + Math.sin(clock * 1.7 + i * 2) * 0.34;
    const lx = b[0] + (ux / ul) * off, lz = b[1] + (uz / ul) * off;
    // he edges down the line but stays squared up to the pitcher
    drawAnimal(lx, lz, Math.atan2(MOUND_POS[0] - lx, MOUND_POS[1] - lz), p.look,""",
     """    const off = leadOff(i);
    const lx = b[0] + (ux / ul) * off, lz = b[1] + (uz / ul) * off;
    // he watches the ball while it is up, and the pitcher the rest of the time
    const up = G.phase === 'play' && G.ball.vis;
    const wx = up ? G.ball.x : MOUND_POS[0], wz = up ? G.ball.z : MOUND_POS[1];
    drawAnimal(lx, lz, Math.atan2(wx - lx, wz - lz), p.look,""",
     'use leadOff'),

    # ---- three out ---------------------------------------------------------
    ("""  if (G.outs >= 3) { endHalfInning(); return; }
  nextBatter();""",
     """  if (G.outs >= 3) {
    // the half-inning does not just cut away: it gets called, and they run in
    G.camMode = 'field';
    banner('スリーアウト\\nチェンジ', true);
    Snd.good();
    setPhase('change', 1.9);
    return;
  }
  nextBatter();""",
     'three out'),

    ("""    case 'halfend':
      if (G.pt >= G.phaseLen) nextBatter();
      break;""",
     """    case 'change':
      if (G.pt >= G.phaseLen) endHalfInning();
      break;

    case 'halfend':
      if (G.pt >= G.phaseLen) nextBatter();
      break;""",
     'change phase'),

    ("""  // fielders drift back / converge
  for (const f of G.fielders) {
    if (!f.scripted) {
      const k = Math.min(1, dt * 3.4);         // get back to your position
      f.x += (f.tx - f.x) * k; f.z += (f.tz - f.z) * k;
      f.run = Math.hypot(f.tx - f.x, f.tz - f.z);
    }
    // a fielder making a play watches the ball; otherwise he faces the plate
    if (f.scripted && G.ball.vis) f.ry = Math.atan2(G.ball.x - f.x, G.ball.z - f.z);
    else f.ry = Math.atan2(-f.x, -f.z);
  }""",
     """  // fielders drift back / converge, or head for the bench on the third out
  const off3 = G.phase === 'change';
  for (const f of G.fielders) {
    const tx = off3 ? DUGOUT[0] : f.tx, tz = off3 ? DUGOUT[1] : f.tz;
    if (!f.scripted || off3) {
      const k = Math.min(1, dt * (off3 ? 1.5 : 3.4));
      f.x += (tx - f.x) * k; f.z += (tz - f.z) * k;
      f.run = Math.hypot(tx - f.x, tz - f.z);
    }
    // a fielder making a play watches the ball; otherwise he faces the plate
    if (off3) f.ry = Math.atan2(tx - f.x, tz - f.z);
    else if (f.scripted && G.ball.vis) f.ry = Math.atan2(G.ball.x - f.x, G.ball.z - f.z);
    else f.ry = Math.atan2(-f.x, -f.z);
  }""",
     'jog in'),

    ("""  const mood = G.phase === 'result' || G.phase === 'halfend' || G.phase === 'walkoff';""",
     """  const mood = G.phase === 'result' || G.phase === 'halfend'
            || G.phase === 'walkoff' || G.phase === 'change';""",
     'mood on change'),
])

# the bench they run to, on the first-base side in foul ground
edit('src/40-game.js', [
    ("const basePt = (i) => (i < 0 || i >= 3 ? HOME_POS : BASE_POS[i]);",
     "const basePt = (i) => (i < 0 || i >= 3 ? HOME_POS : BASE_POS[i]);\nconst DUGOUT = [-25.5, 2.0];   // first-base side, in foul ground"),
])

print('patched ok')
