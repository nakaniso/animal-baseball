# Follow-ups on the base running:
#  - the movers advance every frame regardless of phase, so the run-through
#    plays out during `result` on its own. Stretching the play phase for it
#    only made every ground ball a second and a half slower.
#  - a batter-runner does not round first on a caught fly, and a man who is
#    out does not take his turn toward second.
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
    ("""  for (const mv of G.movers) {
    if (!mv.retired) m = Math.max(m, Math.min(mv.dur - mv.t + 0.5, 6.6));
    if (mv.over) m = Math.max(m, Math.min(mv.dur - mv.t + mv.over.dur + 0.4, 6.6));
  }""",
     """  for (const mv of G.movers) if (!mv.retired) m = Math.max(m, Math.min(mv.dur - mv.t + 0.5, 6.6));""",
     'revert playLength'),

    ("""    if (mv.from === -1 && mv.to === 0) {
      const b = basePt(0);
      if (pl && !pl.infield) {                 // rounding, looking at second""",
     """    // on a caught fly he peels off rather than running it out
    if (mv.from === -1 && mv.to === 0 && o.kind !== 'flyout') {
      const b = basePt(0);
      if (!mv.retired && pl && !pl.infield) {  // rounding, looking at second""",
     'flyout / retired'),
])

print('patched ok')
