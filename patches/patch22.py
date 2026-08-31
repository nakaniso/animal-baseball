# Runners now cover the bases at a believable pace — home to first takes the
# same time the ruling gives them, so a throw that beats them looks like it —
# and the game length is selectable (3 / 6 / 9 innings, 6 by default).
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

# ---- innings setting ----
rep("  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null, traffic: null, carStall: 0,",
    "  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null, traffic: null, carStall: 0,\n  innings: 6,", 'innings field')
rep("    if (G.inning >= 9 && G.score[1] > G.score[0]) { endGame(); return; }",
    "    if (G.inning >= G.innings && G.score[1] > G.score[0]) { endGame(); return; }", 'no bottom')
rep("""    if (G.inning > 9 && G.score[0] !== G.score[1]) { endGame(); return; }
    if (G.inning > 12) { endGame(); return; }""",
"""    if (G.inning > G.innings && G.score[0] !== G.score[1]) { endGame(); return; }
    if (G.inning > G.innings + 3) { endGame(); return; }   // three extra, then a tie""", 'extra innings')
rep("  if (G.half === 1 && G.inning >= 9 && G.score[1] > G.score[0]) {",
    "  if (G.half === 1 && G.inning >= G.innings && G.score[1] > G.score[0]) {", 'walkoff')

# ---- runners run at a real pace ----
rep("""  const legs = Math.max(1, to - from);
  const pace = 0.86 + p.speed * 0.30;
  G.movers.push({
    p, from, to, pts, segs, total, t: -(delay || 0),
    dur: (0.95 + 0.62 * (legs - 1)) / pace,
    scored: to >= 3,
  });""",
"""  const legs = Math.max(1, to - from);
  // the first 90 feet take exactly as long as the ruling gives him, so a throw
  // that beats him is seen to beat him; later bases are compressed a little
  const first = 27.43 / (5.6 + p.speed * 1.7);
  const rest = 27.43 / (7.6 + p.speed * 2.2);
  let dur = first * (legs === 1 ? 1 : 0.72) + (legs - 1) * rest * 0.48;
  if (legs >= 4) dur = Math.min(dur, 6.0);
  G.movers.push({
    p, from, to, pts, segs, total, t: -(delay || 0), dur,
    scored: to >= 3, retired: !!retired,
  });""", 'runner pace')
rep("function moveRunner(p, from, to, delay) {",
    "function moveRunner(p, from, to, delay, retired) {", 'moveRunner sig')

# a man who is out does not need to finish his run before play resumes
rep("  for (const mv of G.movers) m = Math.max(m, mv.dur - mv.t + 0.5);",
    "  for (const mv of G.movers) if (!mv.retired) m = Math.max(m, Math.min(mv.dur - mv.t + 0.5, 6.6));", 'playLength movers')

rep("      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0);\n      if (o.canSac",
    "      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);\n      if (o.canSac", 'flyout retired')
rep("""    case 'groundout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0);""",
"""    case 'groundout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);""", 'groundout retired')
rep("""      moveRunner(bat, -1, 0);
      if (forced) moveRunner(forced, 0, 1);""",
"""      moveRunner(bat, -1, 0, 0, true);
      if (forced) moveRunner(forced, 0, 1, 0, true);""", 'dp retired')
rep("""    case 'bunt_out':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0);""",
"""    case 'bunt_out':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);""", 'bunt retired')
wr('src/40-game.js', box['s'])

# ============================================================
# 00-shell.html — the innings picker
# ============================================================
box, rep = mk('src/00-shell.html')
rep("""      <h2>どこで試合する？</h2>
      <div class="grid" id="stadium-grid"></div>""",
"""      <h2>どこで試合する？</h2>
      <div class="setrow" id="inn-pick"></div>
      <div class="grid" id="stadium-grid"></div>""", 'inn pick')
rep(""".stats{display:flex;gap:5px;margin-top:4px}""",
""".setrow{display:flex;gap:8px;align-items:center;pointer-events:auto;flex-wrap:wrap;justify-content:center}
.setrow>span{font-family:var(--dot);font-size:12px;letter-spacing:.18em;color:var(--dim)}
.setrow button{pointer-events:auto;padding:8px 18px;border-radius:999px;font-family:var(--body);
  font-weight:700;font-size:14px;color:var(--dim);box-shadow:inset 0 0 0 2px var(--line)}
.setrow button:hover{color:var(--cream)}
.setrow button.on{box-shadow:inset 0 0 0 2px var(--amber);color:var(--amber);background:rgba(255,196,77,.12)}
.stats{display:flex;gap:5px;margin-top:4px}""", 'setrow css')
rep("""        球場でも、道路のまんなかでも、スーパーの店内でも。9回まで、ちゃんと野球します。</p>""",
"""        球場でも、道路のまんなかでも、スーパーの店内でも。3回・6回・9回、ちゃんと野球します。</p>""", 'title sub')
wr('src/00-shell.html', box['s'])

# ============================================================
# 50-main.js — picker + result screen labels
# ============================================================
box, rep = mk('src/50-main.js')
rep("""function buildMenus() {
  const sg = $('#stadium-grid');""",
"""function paintInnings() {
  const ip = $('#inn-pick');
  ip.innerHTML = '<span>イニング</span>' + [3, 6, 9].map((n) =>
    `<button data-n="${n}" class="${G.innings === n ? 'on' : ''}">${n}回</button>`).join('');
  for (const el of ip.querySelectorAll('button'))
    el.onclick = () => { Snd.blip(); G.innings = +el.dataset.n; paintInnings(); };
}

function buildMenus() {
  paintInnings();
  const sg = $('#stadium-grid');""", 'paintInnings')

rep("  const innings = Math.max(9, G.lines[0].length, G.lines[1].length);",
    "  const innings = Math.max(G.innings, G.lines[0].length, G.lines[1].length);", 'linescore cols')
rep("    `<span class=\"pill\">${innings > 9 ? '延長' + innings + '回' : '9回'}</span>`,",
    "    `<span class=\"pill\">${innings > G.innings ? '延長' + innings + '回' : G.innings + '回'}</span>`,", 'result pill')
rep("""    ['ルール', '4ボールで四球、3ストライクで三振、3アウトでチェンジ。9回制で、同点なら12回まで延長。あなたは先攻。'],""",
"""    ['ルール', '4ボールで四球、3ストライクで三振、3アウトでチェンジ。イニング数は球場選択の画面で<b>3回・6回・9回</b>から選べる（初期設定は6回）。同点ならさらに3イニングまで延長し、それでも決まらなければ引き分け。あなたは先攻。'],""", 'rules card')
wr('src/50-main.js', box['s'])
print('patched ok')
