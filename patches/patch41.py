# Expressions, driven by what just happened on the field.
import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s: raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)

edit('src/40-game.js', [
("""  G.inningRuns += runs;
  G.lastText = o.text;""",
 """  G.inningRuns += runs;
  // whoever got something out of the play wears it on their face until the
  // next pitch. Runs, or the batter reaching, counts as the batting side's.
  const forBat = runs > 0 || outsAdded === 0;
  G.faceBat = forBat ? EXPR.happy : EXPR.down;
  G.faceFld = forBat ? EXPR.down : EXPR.happy;
  G.lastText = o.text;""", 'mood'),
("""function afterPitch(kind) {
  const bat = curBatter();""",
 """function afterPitch(kind) {
  const bat = curBatter();
  G.faceBat = G.faceFld = EXPR.idle;   // finishAtBat overrides if the PA ends""", 'reset mood')])

edit('src/50-main.js', [
# --- shared for the whole frame ---
("""  const bt = batTeam(), ft = fldTeam();
  const bob = Math.sin(clock * 2.2) * 0.03;""",
 """  const bt = batTeam(), ft = fldTeam();
  const bob = Math.sin(clock * 2.2) * 0.03;
  // moods only show while the play is being read out; before the pitch the
  // batter and the pitcher are bearing down instead
  const mood = G.phase === 'result' || G.phase === 'halfend' || G.phase === 'walkoff';
  const faceBat = mood ? (G.faceBat || EXPR.idle) : EXPR.focus;
  const faceFld = mood ? (G.faceFld || EXPR.idle) : EXPR.idle;""", 'mood vars'),
# --- fielders ---
("""    const pose = {
      armL: running ? swing * 0.7 : 0.2 + bob, armR: running ? -swing * 0.7 : -0.2 - bob,
      legL: swing, legR: -swing, bob: running ? Math.abs(Math.sin(clock * 13)) * 0.06 : bob * 0.5,
    };""",
 """    const pose = {
      armL: running ? swing * 0.7 : 0.2 + bob, armR: running ? -swing * 0.7 : -0.2 - bob,
      legL: swing, legR: -swing, bob: running ? Math.abs(Math.sin(clock * 13)) * 0.06 : bob * 0.5,
      face: f.st.k === 'P' && (G.phase === 'ready' || G.phase === 'pitch') ? EXPR.focus : faceFld,
    };""", 'fielder face'),
("""        fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4,
        armL: -1.1, armR: 1.1, bob: -0.30,
      }, 0);""",
 """        fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4,
        armL: -1.1, armR: 1.1, bob: -0.30, face: EXPR.down,
      }, 0);""", 'downed fielder'),
# --- batter ---
("""        { fall: -0.62, spread: 0.20, legL: -0.35, legR: 0.30,
          armL: -1.7, armR: -1.6, bob: -0.12, helmet: 1 }, 0);""",
 """        { fall: -0.62, spread: 0.20, legL: -0.35, legR: 0.30,
          armL: -1.7, armR: -1.6, bob: -0.12, helmet: 1, face: EXPR.down }, 0);""", 'hbp batter'),
("""      helmet: 1, gloveC: bt.trim,
      bob: G.batSwingT < 0 ? bob * 0.5 : 0.015,
    }, 0);""",
 """      helmet: 1, gloveC: bt.trim, face: faceBat,
      bob: G.batSwingT < 0 ? bob * 0.5 : 0.015,
    }, 0);""", 'batter face'),
# --- runners ---
("""        { fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4, armL: -1.1, armR: 1.1,
          bob: -0.30, helmet: 1 }, 0);""",
 """        { fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4, armL: -1.1, armR: 1.1,
          bob: -0.30, helmet: 1, face: EXPR.down }, 0);""", 'downed runner'),
("""      armL: sw * 0.8, armR: -sw * 0.8, legL: sw, legR: -sw, helmet: 1,
      bob: r.done ? 0 : Math.abs(Math.sin(clock * 15)) * 0.07, lean: 0.16,
    }, 0);""",
 """      armL: sw * 0.8, armR: -sw * 0.8, legL: sw, legR: -sw, helmet: 1, face: faceBat,
      bob: r.done ? 0 : Math.abs(Math.sin(clock * 15)) * 0.07, lean: 0.16,
    }, 0);""", 'running runner'),
("""               { armL: 0.42, armR: 0.42, legL: 0.10, legR: -0.10, spread: 0.19,
                 lean: 0.17, bob: bob * 0.6, helmet: 1 }, 0);""",
 """               { armL: 0.42, armR: 0.42, legL: 0.10, legR: -0.10, spread: 0.19,
                 lean: 0.17, bob: bob * 0.6, helmet: 1, face: faceBat }, 0);""", 'leading runner')])

print('patched ok')
