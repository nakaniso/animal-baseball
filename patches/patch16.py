# Two-player mode and quitting mid-game.
#   G.mode: 'cpu' (one player vs the computer), 'vs' (two players sharing the
#   keyboard: one pitches, the other bats), 'auto' (both sides computer, used
#   for balance measurement).
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
# 00-shell.html — mode buttons, quit button, pause screen
# ============================================================
box, rep = mk('src/00-shell.html')
rep("""      <div class="row">
        <button class="btn" id="btn-start">試合をはじめる</button>
        <button class="btn ghost" id="btn-rules">あそびかた</button>
      </div>""",
"""      <div class="row">
        <button class="btn" id="btn-start">ひとりで遊ぶ</button>
        <button class="btn" id="btn-vs">ふたりで対戦</button>
      </div>
      <div class="row">
        <button class="btn ghost" id="btn-rules">あそびかた</button>
      </div>""", 'title buttons')

rep("""      <h2>どのチームを使う？</h2>
      <p class="sub">あなたは<b>先攻</b>。1回表からいきなり打席に立ちます。</p>""",
"""      <h2 id="team-head">どのチームを使う？</h2>
      <p class="sub" id="team-sub">あなたは<b>先攻</b>。1回表からいきなり打席に立ちます。</p>""", 'team head')

rep("""      <div id="banner"></div>""",
"""      <button id="btn-quit">やめる</button>
      <div id="banner"></div>""", 'quit button')

rep("""    <section id="s-result" class="screen hidden">""",
"""    <section id="s-pause" class="screen hidden">
      <div class="eyebrow">PAUSED</div>
      <h2>試合を中断中</h2>
      <p class="sub" id="pause-score"></p>
      <div class="row">
        <button class="btn" id="btn-resume">試合をつづける</button>
        <button class="btn ghost" id="btn-abandon">やめてタイトルへ</button>
      </div>
    </section>

    <section id="s-result" class="screen hidden">""", 'pause screen')

rep("""#banner{position:absolute;top:42%;left:50%;""",
"""#btn-quit{position:absolute;top:14px;right:14px;pointer-events:auto;
  font-family:var(--dot);font-size:12px;letter-spacing:.12em;color:var(--dim);
  background:var(--ink2);padding:9px 14px;border-radius:10px;
  box-shadow:inset 0 0 0 2px var(--line),0 8px 22px rgba(0,0,0,.5)}
#btn-quit:hover{color:var(--amber);box-shadow:inset 0 0 0 2px var(--amber),0 8px 22px rgba(0,0,0,.5)}
#banner{position:absolute;top:42%;left:50%;""", 'quit css')

rep("""  #log{display:none} .countbox{transform:scale(.86);transform-origin:top left}""",
"""  #log{display:none;} .countbox{transform:scale(.86);transform-origin:top left}
  #btn-quit{top:auto;bottom:14px;right:12px;padding:7px 11px;font-size:11px}""", 'quit mobile')
wr('src/00-shell.html', box['s'])

# ============================================================
# 40-game.js — mode plumbing
# ============================================================
box, rep = mk('src/40-game.js')
rep("""const batTeam = () => (G.half === 0 ? G.away : G.home);
const fldTeam = () => (G.half === 0 ? G.home : G.away);
const userBatting = () => (G.half === 0 ? 0 : 1) === G.userSide;""",
"""const batTeam = () => (G.half === 0 ? G.away : G.home);
const fldTeam = () => (G.half === 0 ? G.home : G.away);
const userBatting = () => (G.half === 0 ? 0 : 1) === G.userSide;
/* who is at the controls right now */
const humanBats = () => (G.mode === 'vs' ? true : G.mode === 'auto' ? false : userBatting());
const humanPitches = () => (G.mode === 'vs' ? true : G.mode === 'auto' ? false : !userBatting());
/* 1P is always the away side */
const battingPlayer = () => (G.half === 0 ? '1P' : '2P');
const pitchingPlayer = () => (G.half === 0 ? '2P' : '1P');""", 'mode helpers')

rep("  camMode: 'bat', lastText: '',",
    "  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null,", 'mode field')

rep("""function startGame(stadiumId, userTeamId) {
  const st = stadiumById(stadiumId);
  G.st = st;
  G.stations = stationsFor(st);
  G.scene = st.build();
  const others = TEAMS.filter((t) => t.id !== userTeamId);
  G.away = makeTeam(teamById(userTeamId));
  G.home = makeTeam(pick(others));""",
"""function startGame(stadiumId, awayTeamId, homeTeamId) {
  const st = stadiumById(stadiumId);
  G.st = st;
  G.stations = stationsFor(st);
  G.scene = st.build();
  const others = TEAMS.filter((t) => t.id !== awayTeamId);
  G.away = makeTeam(teamById(awayTeamId));
  G.home = makeTeam(homeTeamId ? teamById(homeTeamId) : pick(others));""", 'startGame sig')
rep("  G.over = false; G.active = true; G.movers = []; G.flight = null;",
    "  G.over = false; G.active = true; G.paused = false; G.movers = []; G.flight = null; G.playScript = null;", 'startGame reset')

rep("  // CPU batter makes up its mind now\n  if (!userBatting()) cpuBatterDecide();",
    "  // in two-player games the hitter re-aims from scratch each pitch\n  if (G.mode === 'vs') { G.reticle.x = 0; G.reticle.y = 0.88; }\n  if (!humanBats()) cpuBatterDecide();", 'throwPitch cpu')

rep("  if (G.phase !== 'pitch' || G.swingT >= 0 || !userBatting()) return;",
    "  if (G.phase !== 'pitch' || G.swingT >= 0 || !humanBats()) return;", 'playerSwing')
rep("  const aim = userBatting() ? G.reticle : G.cpuAim;",
    "  const aim = humanBats() ? G.reticle : G.cpuAim;", 'judgeSwing aim')
wr('src/40-game.js', box['s'])

# ============================================================
# 50-main.js — flow, UI, pause
# ============================================================
box, rep = mk('src/50-main.js')
rep("    dir = clamp(-d.dt * 330 + (pc.ax - (userBatting() ? G.reticle.x : G.cpuAim.x)) * 18 + gauss(9), -58, 58);",
    "    dir = clamp(-d.dt * 330 + (pc.ax - (humanBats() ? G.reticle.x : G.cpuAim.x)) * 18 + gauss(9), -58, 58);", 'doContact aim')
rep("""      if (G.pt >= G.phaseLen) {
        if (userBatting()) { const c = cpuPitchChoice(); throwPitch(c.ti, c.ax, c.ay); }
        else { setPhase('aim'); uiHint(); }
      }""",
"""      if (G.pt >= G.phaseLen) {
        if (humanPitches()) { setPhase('aim'); uiHint(); }
        else { const c = cpuPitchChoice(); throwPitch(c.ti, c.ax, c.ay); }
      }""", 'ready phase')
rep("      if (!userBatting() && G.swingT >= 0 && !G.decided && pc.t >= G.swingT) {",
    "      if (!humanBats() && G.swingT >= 0 && !G.decided && pc.t >= G.swingT) {", 'cpu swing')
rep("function update(dt) {\n  if (!G.active) return;",
    "function update(dt) {\n  if (!G.active || G.paused) return;", 'pause update')

# --- input ---
rep("""    if (e.code === 'Space') {
      e.preventDefault();
      Snd.boot();
      if (userBatting()) playerSwing(e.shiftKey || KEYS.ShiftLeft || KEYS.ShiftRight);
      else if (G.phase === 'aim') throwPitch(G.pitchType, G.reticle.x, G.reticle.y);
    }
    if (!userBatting() && e.code >= 'Digit1' && e.code <= 'Digit5') {
      G.pitchType = +e.code.slice(5) - 1; uiHint();
    }""",
"""    if (e.code === 'Escape') { togglePause(); return; }
    if (G.paused) return;
    if (e.code === 'Space') {
      e.preventDefault();
      Snd.boot();
      if (G.phase === 'aim' && humanPitches()) throwPitch(G.pitchType, G.reticle.x, G.reticle.y);
      else if (G.phase === 'pitch' && humanBats()) playerSwing(e.shiftKey || KEYS.ShiftLeft || KEYS.ShiftRight);
    }
    if (G.phase === 'aim' && humanPitches() && e.code >= 'Digit1' && e.code <= 'Digit5') {
      G.pitchType = +e.code.slice(5) - 1; uiHint();
    }""", 'keydown')
rep("""    track(e); Snd.boot();
    if (!G.active) return;
    if (userBatting()) playerSwing(KEYS.ShiftLeft || KEYS.ShiftRight);
    else if (G.phase === 'aim') throwPitch(G.pitchType, G.reticle.x, G.reticle.y);""",
"""    track(e); Snd.boot();
    if (!G.active || G.paused) return;
    if (G.phase === 'aim' && humanPitches()) throwPitch(G.pitchType, G.reticle.x, G.reticle.y);
    else if (G.phase === 'pitch' && humanBats()) playerSwing(KEYS.ShiftLeft || KEYS.ShiftRight);""", 'pointerdown')

# --- HUD text ---
rep("""function uiBatter() {
  const b = curBatter(), p = curPitcher();
  const mine = userBatting();
  $('#batter .role').textContent = mine ? `${G.inning}回${G.half === 0 ? 'オモテ' : 'ウラ'} ${G.order[G.half] + 1}番` : 'PITCHING';
  $('#batter .who').textContent = mine ? b.name : p.name;
  $('#batter .meta').textContent = mine
    ? `${batTeam().name}  P${'★'.repeat(Math.round(b.power * 5)) || '-'}`
    : `対 ${b.name}（${batTeam().name}）`;
  uiHint();
}""",
"""function uiBatter() {
  const b = curBatter(), p = curPitcher();
  const vs = G.mode === 'vs';
  const half = `${G.inning}回${G.half === 0 ? 'オモテ' : 'ウラ'}`;
  if (vs) {
    $('#batter .role').textContent = `${half}  ${G.order[G.half] + 1}番`;
    $('#batter .who').textContent = `${battingPlayer()} ${b.name}`;
    $('#batter .meta').textContent = `投 ${pitchingPlayer()} ${p.name}`;
  } else if (userBatting()) {
    $('#batter .role').textContent = `${half} ${G.order[G.half] + 1}番`;
    $('#batter .who').textContent = b.name;
    $('#batter .meta').textContent = `${batTeam().name}  P${'★'.repeat(Math.round(b.power * 5)) || '-'}`;
  } else {
    $('#batter .role').textContent = 'PITCHING';
    $('#batter .who').textContent = p.name;
    $('#batter .meta').textContent = `対 ${b.name}（${batTeam().name}）`;
  }
  uiHint();
}""", 'uiBatter')

rep("""function uiHint() {
  const mine = userBatting();
  const touch = matchMedia('(pointer:coarse)').matches;
  const keys = mine
    ? (touch ? [['ドラッグ', 'ねらう'], ['タップ', 'スイング']]
             : [['矢印 / マウス', 'ねらう'], ['SPACE', 'スイング'], ['SHIFT+SPACE', 'バント']])
    : (touch ? [['球種ボタン', 'えらぶ'], ['ドラッグ', 'コース'], ['タップ', '投げる']]
             : [['1〜5', '球種'], ['矢印 / マウス', 'コース'], ['SPACE', '投げる']]);
  $('#hint').innerHTML = keys.map(([k, d]) => `<span class="key"><kbd>${k}</kbd>${d}</span>`).join('');
  const pp = $('#pitchpick');
  pp.classList.toggle('hidden', mine || !G.active);
  if (!mine) {""",
"""function uiHint() {
  // during 'aim' the pitcher has the controls; once the ball is away the hitter does
  const pitching = G.phase === 'aim' && humanPitches();
  const touch = matchMedia('(pointer:coarse)').matches;
  const who = G.mode === 'vs' ? (pitching ? `${pitchingPlayer()} ` : `${battingPlayer()} `) : '';
  const keys = !pitching
    ? (touch ? [['ドラッグ', 'ねらう'], ['タップ', 'スイング']]
             : [['矢印 / マウス', 'ねらう'], ['SPACE', 'スイング'], ['SHIFT+SPACE', 'バント']])
    : (touch ? [['球種ボタン', 'えらぶ'], ['ドラッグ', 'コース'], ['タップ', '投げる']]
             : [['1〜5', '球種'], ['矢印 / マウス', 'コース'], ['SPACE', '投げる']]);
  $('#hint').innerHTML = (who ? `<span class="key act"><kbd>${who.trim()}</kbd>${pitching ? 'が投げる' : 'が打つ'}</span>` : '')
    + keys.map(([k, d]) => `<span class="key"><kbd>${k}</kbd>${d}</span>`).join('');
  const pp = $('#pitchpick');
  pp.classList.toggle('hidden', !pitching || !G.active);
  if (pitching) {""", 'uiHint')

rep("""function uiTeams() {
  $('#sb-away .sb-nm').textContent = G.away.name;
  $('#sb-home .sb-nm').textContent = G.home.name;""",
"""function uiTeams() {
  const tag = G.mode === 'vs' ? ['1P ', '2P '] : G.mode === 'auto' ? ['', ''] : ['', 'CPU '];
  $('#sb-away .sb-nm').textContent = tag[0] + G.away.name;
  $('#sb-home .sb-nm').textContent = tag[1] + G.home.name;""", 'uiTeams')

rep("""  const w = G.score[0] === G.score[1] ? null : (G.score[0] > G.score[1] ? 0 : 1);
  const youWon = w === G.userSide;
  $('#res-head').textContent = w === null ? '引き分け' : (youWon ? 'あなたの勝ち！' : `${(w === 0 ? G.away : G.home).name}の勝ち`);""",
"""  const w = G.score[0] === G.score[1] ? null : (G.score[0] > G.score[1] ? 0 : 1);
  $('#res-head').textContent = w === null ? '引き分け'
    : G.mode === 'vs' ? `${w === 0 ? '1P' : '2P'}の勝ち！ — ${(w === 0 ? G.away : G.home).name}`
    : w === G.userSide ? 'あなたの勝ち！'
    : `${(w === 0 ? G.away : G.home).name}の勝ち`;""", 'result head')

# --- flow: mode -> stadium -> team(s) ---
rep("""    b.onclick = () => { Snd.boot(); chosenStadium = st.id; show('#s-team'); };""",
"""    b.onclick = () => { Snd.boot(); chosenStadium = st.id; teamPick = 0; showTeamPick(); };""", 'stadium click')
rep("""    b.onclick = () => { Snd.boot(); show(null); startGame(chosenStadium, t.id); };""",
"""    b.onclick = () => {
      Snd.boot();
      if (G.mode === 'vs' && teamPick === 0) { team1 = t.id; teamPick = 1; showTeamPick(); return; }
      show(null);
      startGame(chosenStadium, G.mode === 'vs' ? team1 : t.id, G.mode === 'vs' ? t.id : null);
    };""", 'team click')

rep("""const KEYS = Object.create(null);
let chosenStadium = null;""",
"""const KEYS = Object.create(null);
let chosenStadium = null, teamPick = 0, team1 = null;

function showTeamPick() {
  const vs = G.mode === 'vs';
  $('#team-head').textContent = vs
    ? (teamPick === 0 ? '1P（先攻）のチームは？' : '2P（後攻）のチームは？')
    : 'どのチームを使う？';
  $('#team-sub').innerHTML = vs
    ? (teamPick === 0
        ? '1Pは<b>先攻</b>。1回表に打って、裏は投げます。'
        : '2Pは<b>後攻</b>。1回表は投げて、裏に打ちます。')
    : 'あなたは<b>先攻</b>。1回表からいきなり打席に立ちます。';
  show('#s-team');
}

function togglePause() {
  if (!G.active || G.over) return;
  G.paused = !G.paused;
  if (G.paused) {
    $('#pause-score').textContent =
      `${G.inning}回${G.half === 0 ? '表' : '裏'}  ${G.away.name} ${G.score[0]} - ${G.score[1]} ${G.home.name}`;
    show('#s-pause');
  } else show(null);
}""", 'flow helpers')

rep("""  $('#btn-start').onclick = () => { Snd.boot(); show('#s-stadium'); };""",
"""  $('#btn-start').onclick = () => { Snd.boot(); G.mode = 'cpu'; show('#s-stadium'); };
  $('#btn-vs').onclick = () => { Snd.boot(); G.mode = 'vs'; show('#s-stadium'); };
  $('#btn-quit').onclick = () => togglePause();
  $('#btn-resume').onclick = () => togglePause();
  $('#btn-abandon').onclick = () => {
    G.paused = false; G.active = false; G.over = false; G.st = null;
    show('#s-title');
  };""", 'boot buttons')
rep("""  $('#btn-again').onclick = () => { G.st = null; show('#s-stadium'); };""",
"""  $('#btn-again').onclick = () => { G.st = null; teamPick = 0; show('#s-stadium'); };""", 'again')
wr('src/50-main.js', box['s'])
print('patched ok')
