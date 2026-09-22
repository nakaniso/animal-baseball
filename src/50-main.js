/* ============================================================
   50-main.js — screens, input, the frame loop, and drawing
   ============================================================ */
'use strict';

const $ = (s) => document.querySelector(s);
const $$ = (s) => Array.from(document.querySelectorAll(s));

const CAM = { ex: 0, ey: 4, ez: -14, tx: 0, ty: 1.4, tz: 14, fov: 46 };
const KEYS = Object.create(null);
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
}

/* ============================================================
   card art — 2D sketches so the menus show what you are picking
   ============================================================ */
function faceCanvas(team, w, h) {
  const c = document.createElement('canvas');
  c.width = w * 2; c.height = h * 2;
  const g = c.getContext('2d'); g.scale(2, 2);
  const A = ANIMALS[team.animal];
  g.fillStyle = '#20303F'; g.fillRect(0, 0, w, h);
  // pennant stripes behind the face
  g.fillStyle = team.uni;
  for (let i = -2; i < 10; i++) { g.beginPath(); g.moveTo(i * 22, h); g.lineTo(i * 22 + 26, 0); g.lineTo(i * 22 + 38, 0); g.lineTo(i * 22 + 12, h); g.fill(); }
  g.globalAlpha = 0.22; g.fillStyle = '#000'; g.fillRect(0, 0, w, h); g.globalAlpha = 1;

  const cx = w / 2, cy = h * 0.60, r = h * 0.34;
  const ear = (dx, dy, rr) => { g.beginPath(); g.arc(cx + dx, cy + dy, rr, 0, 7); g.fill(); };
  g.fillStyle = A.fur;
  if (A.ear === 'round') { ear(-r * 0.82, -r * 0.72, r * 0.36); ear(r * 0.82, -r * 0.72, r * 0.36); }
  if (A.ear === 'point') {
    for (const s of [-1, 1]) { g.beginPath(); g.moveTo(cx + s * r * 0.3, cy - r * 0.8); g.lineTo(cx + s * r * 0.95, cy - r * 1.35); g.lineTo(cx + s * r * 1.0, cy - r * 0.5); g.fill(); }
  }
  if (A.ear === 'toad') { ear(-r * 0.72, -r * 0.66, r * 0.34); ear(r * 0.72, -r * 0.66, r * 0.34); }
  g.beginPath(); g.arc(cx, cy, r, 0, 7); g.fill();
  // cap
  g.fillStyle = team.cap;
  g.beginPath(); g.arc(cx, cy - r * 0.16, r * 1.0, Math.PI, 0); g.fill();
  g.fillRect(cx - r * 1.05, cy - r * 0.2, r * 2.1, r * 0.16);
  g.beginPath(); g.ellipse(cx, cy - r * 0.16, r * 1.25, r * 0.2, 0, Math.PI, 0); g.fill();
  g.fillStyle = team.trim; g.beginPath(); g.arc(cx, cy - r * 1.1, r * 0.12, 0, 7); g.fill();
  // long ears sit on top of the cap, not under it
  if (A.ear === 'long') {
    for (const s of [-1, 1]) {
      g.save(); g.translate(cx + s * r * 0.46, cy - r * 1.16); g.rotate(s * 0.26);
      g.fillStyle = A.fur; g.beginPath(); g.ellipse(0, 0, r * 0.23, r * 0.66, 0, 0, 7); g.fill();
      g.fillStyle = A.fur2; g.beginPath(); g.ellipse(0, r * 0.06, r * 0.11, r * 0.44, 0, 0, 7); g.fill();
      g.restore();
    }
  }
  // muzzle + eyes
  g.fillStyle = A.fur2;
  g.beginPath(); g.ellipse(cx, cy + r * 0.36, r * 0.44, r * 0.32, 0, 0, 7); g.fill();
  if (A.beak) {
    g.fillStyle = A.beak;
    g.beginPath(); g.moveTo(cx - r * 0.20, cy + r * 0.26); g.lineTo(cx + r * 0.20, cy + r * 0.26);
    g.lineTo(cx, cy + r * 0.66); g.closePath(); g.fill();
  }
  g.fillStyle = '#22282F';
  if (A.ear === 'toad') { g.fillStyle = A.fur; ear(-r * 0.72, -r * 0.66, r * 0.34); ear(r * 0.72, -r * 0.66, r * 0.34); g.fillStyle = '#22282F'; ear(-r * 0.72, -r * 0.72, r * 0.15); ear(r * 0.72, -r * 0.72, r * 0.15); }
  g.beginPath(); g.ellipse(cx - r * 0.34, cy + r * 0.02, r * 0.11, r * 0.14, 0, 0, 7); g.fill();
  g.beginPath(); g.ellipse(cx + r * 0.34, cy + r * 0.02, r * 0.11, r * 0.14, 0, 0, 7); g.fill();
  if (!A.beak) { g.beginPath(); g.ellipse(cx, cy + r * 0.26, r * 0.13, r * 0.10, 0, 0, 7); g.fill(); }
  g.fillStyle = '#fff';
  g.beginPath(); g.arc(cx - r * 0.30, cy - r * 0.04, r * 0.045, 0, 7); g.fill();
  g.beginPath(); g.arc(cx + r * 0.38, cy - r * 0.04, r * 0.045, 0, 7); g.fill();
  if (A.brow) {                      // the drawn brow line, as on the model
    g.strokeStyle = '#3A2A1A'; g.lineWidth = r * 0.11; g.lineCap = 'round';
    for (const s of [-1, 1]) {
      g.beginPath();
      g.moveTo(cx + s * r * 0.16, cy - r * 0.30);
      g.lineTo(cx + s * r * 0.52, cy - r * 0.24);
      g.stroke();
    }
  }
  return c;
}

function parkCanvas(st, w, h) {
  const c = document.createElement('canvas');
  c.width = w * 2; c.height = h * 2;
  const g = c.getContext('2d'); g.scale(2, 2);
  const [a, b, sky] = st.cardColors;
  const horizon = h * 0.52;
  g.fillStyle = sky; g.fillRect(0, 0, w, horizon);
  g.fillStyle = a; g.fillRect(0, horizon, w, h - horizon);
  const rect = (x, y, ww, hh, f) => { g.fillStyle = f; g.fillRect(x, y, ww, hh); };
  if (st.id === 'dome') {
    rect(0, horizon - 12, w, 12, '#2F6C57');
    for (let i = 0; i < 5; i++) rect(6 + i * 26, horizon - 30, 4, 30, '#5A6A78');
    g.fillStyle = b; g.beginPath(); g.moveTo(w / 2, h); g.lineTo(w / 2 - 46, horizon + 4); g.lineTo(w / 2 + 46, horizon + 4); g.fill();
    g.fillStyle = '#F4EFE2'; g.beginPath(); g.arc(w / 2, h - 8, 4, 0, 7); g.fill();
  }
  if (st.id === 'road') {
    for (let i = 0; i < 4; i++) { rect(2 + i * 16, horizon - 34 - i * 4, 13, 34 + i * 4, i % 2 ? '#8C7F72' : '#7A8A93'); rect(w - 15 - i * 16, horizon - 30 - i * 5, 13, 30 + i * 5, i % 2 ? '#9A8577' : '#6F7C86'); }
    rect(w / 2 - 34, horizon - 16, 68, 16, '#7E8489');
    for (let i = 0; i < 4; i++) rect(w / 2 - 2, horizon + 6 + i * 12, 4, 7, b);
    rect(w / 2 - 26, h - 16, 16, 9, '#D9483B'); rect(w / 2 + 12, h - 20, 16, 9, '#3E6FBF');
  }
  if (st.id === 'market') {
    rect(0, 0, w, 14, '#C4C7BE');
    for (let i = 0; i < 5; i++) rect(8 + i * 24, 4, 16, 4, '#FFF8DC');
    for (let i = 0; i < 4; i++) { rect(10 + i * 30, horizon - 22, 22, 22, '#9EA6A2'); for (let j = 0; j < 3; j++) rect(12 + i * 30, horizon - 20 + j * 7, 18, 4, [b, '#F2C14E', '#7FB3D5'][j]); }
    for (let x = 0; x < w; x += 14) for (let y = horizon; y < h; y += 14) rect(x, y, 13, 13, ((x + y) / 14) % 2 ? '#DCDDD4' : '#D0D2C8');
  }
  if (st.id === 'river') {
    rect(0, horizon - 10, w, 10, '#6FA8C4');
    for (let i = 0; i < 6; i++) { g.fillStyle = '#5E8A3E'; g.beginPath(); g.arc(10 + i * 34, horizon - 12, 9, 0, 7); g.fill(); g.fillStyle = '#6B4A32'; g.fillRect(9 + i * 34, horizon - 12, 3, 12); }
    g.fillStyle = b; g.beginPath(); g.moveTo(w / 2, h); g.lineTo(w / 2 - 40, horizon + 6); g.lineTo(w / 2 + 40, horizon + 6); g.fill();
  }
  if (st.id === 'moon') {
    g.fillStyle = '#E8EEFA';
    for (let i = 0; i < 40; i++) { const x = Math.random() * w, y = Math.random() * horizon; g.fillRect(x, y, 1.5, 1.5); }
    g.fillStyle = '#3E6FA8'; g.beginPath(); g.arc(w * 0.78, horizon * 0.42, 16, 0, 7); g.fill();
    g.fillStyle = '#5E9A5E'; g.beginPath(); g.arc(w * 0.74, horizon * 0.36, 6, 0, 7); g.fill();
    g.fillStyle = '#6E6E76';
    for (let i = 0; i < 6; i++) { g.beginPath(); g.ellipse(Math.random() * w, horizon + 8 + Math.random() * (h - horizon - 8), 8 + Math.random() * 12, 4, 0, 0, 7); g.fill(); }
  }
  return c;
}

/* ============================================================
   screens
   ============================================================ */
function show(id) {
  for (const s of $$('.screen')) s.classList.add('hidden');
  if (id) $(id).classList.remove('hidden');
  $('#hud').classList.toggle('hidden', id !== null);
}

function statBar(label, v) {
  return `<i title="${label}"><b style="width:${v * 20}%"></b></i>`;
}

function paintInnings() {
  const ip = $('#inn-pick');
  ip.innerHTML = '<span>イニング</span>' + [3, 6, 9].map((n) =>
    `<button data-n="${n}" class="${G.innings === n ? 'on' : ''}">${n}回</button>`).join('');
  for (const el of ip.querySelectorAll('button'))
    el.onclick = () => { Snd.blip(); G.innings = +el.dataset.n; paintInnings(); };
}

function buildMenus() {
  paintInnings();
  const sg = $('#stadium-grid');
  sg.innerHTML = '';
  for (const st of STADIUMS) {
    const b = document.createElement('button');
    b.className = 'card';
    b.innerHTML = `<div class="art"></div><div class="bd">
      <div class="tag">${st.tag}</div><div class="nm">${st.name}</div>
      <div class="ds">${st.desc}</div></div>`;
    b.querySelector('.art').appendChild(parkCanvas(st, 240, 104));
    b.onclick = () => { Snd.boot(); chosenStadium = st.id; teamPick = 0; showTeamPick(); };
    sg.appendChild(b);
  }
  const tg = $('#team-grid');
  tg.innerHTML = '';
  for (const t of TEAMS) {
    const b = document.createElement('button');
    b.className = 'card';
    b.innerHTML = `<div class="art"></div><div class="bd">
      <div class="tag">${t.tag}</div><div class="nm">${t.name}</div>
      <div class="ds">${t.desc}</div>
      <div class="stats">${statBar('パワー', t.pow)}${statBar('ミート', t.con)}${statBar('走力', t.spd)}${statBar('守備', t.def)}</div>
      <div class="statrow"><span>パワー</span><span>ミート</span><span>走力</span><span>守備</span></div></div>`;
    b.querySelector('.art').appendChild(faceCanvas(t, 240, 104));
    b.onclick = () => {
      Snd.boot();
      if (G.mode === 'vs' && teamPick === 0) { team1 = t.id; teamPick = 1; showTeamPick(); return; }
      show(null);
      startGame(chosenStadium, G.mode === 'vs' ? team1 : t.id, G.mode === 'vs' ? t.id : null);
    };
    tg.appendChild(b);
  }
  $('#rules-grid').innerHTML = [
    ['打つ', '球が来たら <b>スペース</b> でスイング。<b>矢印キー</b>（またはマウス）でミートカーソルを動かし、ボールに重ねてから振る。カーソルより上のボールを打つとフライ、下だとゴロになる。'],
    ['投げる', '守るイニングでは <b>1〜5</b> で球種、<b>矢印キー</b>でコース、<b>スペース</b>で投球。ストライクゾーンの外に外して振らせるのも手。'],
    ['バント', '<b>Shift＋スペース</b>でバント。転がして走者を進める。'],
    ['ルール', '4ボールで四球、3ストライクで三振、当たればデッドボール、3アウトでチェンジ。イニング数は球場選択の画面で<b>3回・6回・9回</b>から選べる（初期設定は6回）。同点ならさらに3イニングまで延長し、それでも決まらなければ引き分け。あなたは先攻。'],
    ['球場のクセ', '球場ごとに重力・フェンス距離・障害物がちがう。月面は1/6重力、スーパーは天井直撃でエンタイトルツーベース。'],
    ['勝ち方', '打球の質は「タイミング」と「カーソルの位置」で決まる。芯を外すとファウルになって粘れるので、追い込まれても諦めないこと。'],
    ['ふたりで対戦', 'キーボードひとつを交代で使う。投手（<b>1〜5</b>で球種、<b>矢印</b>でコース、<b>スペース</b>で投球）が投げたら、そのまま打者（<b>矢印</b>でねらう、<b>スペース</b>でスイング）の番。1Pが先攻、2Pが後攻。'],
    ['中断する', '右上の<b>やめる</b>、または<b>Escキー</b>でいつでも中断できる。そのまま続けるか、タイトルに戻るかを選べる。'],
  ].map(([h, d]) => `<div class="card"><div class="bd"><div class="nm">${h}</div><div class="ds">${d}</div></div></div>`).join('');
}

/* ============================================================
   HUD
   ============================================================ */
function uiTeams() {
  const tag = G.mode === 'vs' ? ['1P ', '2P '] : G.mode === 'auto' ? ['', ''] : ['', 'CPU '];
  $('#sb-away .sb-nm').textContent = tag[0] + G.away.name;
  $('#sb-home .sb-nm').textContent = tag[1] + G.home.name;
  $('#sb-away .sb-dot').style.background = G.away.uni;
  $('#sb-home .sb-dot').style.background = G.home.uni;
  uiScore();
}

function uiScore() {
  $('#sb-away .sb-run').textContent = G.score[0];
  $('#sb-home .sb-run').textContent = G.score[1];
  $('#sb-num').textContent = G.inning;
  $('#sb-half').textContent = G.half === 0 ? '表' : '裏';
  $('#sb-away').classList.toggle('bat', G.half === 0);
  $('#sb-home').classList.toggle('bat', G.half === 1);
  for (let i = 0; i < 3; i++) $('#b' + i).className = 'pip' + (G.balls > i ? ' b' : '');
  for (let i = 0; i < 2; i++) $('#s' + i).className = 'pip' + (G.strikes > i ? ' s' : '');
  for (let i = 0; i < 2; i++) $('#o' + i).className = 'pip' + (G.outs > i ? ' o' : '');
  for (let i = 0; i < 3; i++) $('#bs' + (i + 1)).classList.toggle('on', !!G.bases[i]);
}

function uiBatter() {
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
}

function uiHint() {
  // in a two-player game the controls hand over at the release; against the
  // computer the side you are on does not change mid-pitch
  const pitching = G.mode === 'vs' ? (G.phase === 'aim' || G.phase === 'ready') : !userBatting();
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
  if (pitching) {
    pp.innerHTML = PITCHES.map((p, i) =>
      `<button class="pc${i === G.pitchType ? ' sel' : ''}" data-i="${i}">${p.nm}<small>${i + 1} · ${p.en}</small></button>`).join('');
    for (const el of pp.querySelectorAll('.pc'))
      el.onclick = () => { G.pitchType = +el.dataset.i; uiHint(); };
  }
}

let bannerTimer = null;
function banner(text, big) {
  const el = $('#banner');
  el.textContent = text;
  el.style.color = big ? 'var(--amber)' : 'var(--cream)';
  el.classList.remove('show');
  void el.offsetWidth;
  el.classList.add('show');
}

function clearLog() { $('#log').innerHTML = ''; }

function logLine(text, hi) {
  const el = document.createElement('p');
  if (hi) el.className = 'hi';
  el.textContent = text;
  const box = $('#log');
  box.appendChild(el);
  while (box.children.length > 6) box.removeChild(box.firstChild);
}

function showResult() {
  const innings = Math.max(G.innings, G.lines[0].length, G.lines[1].length);
  const head = ['<tr><th></th>'];
  for (let i = 0; i < innings; i++) head.push(`<th>${i + 1}</th>`);
  head.push('<th>R</th><th>H</th><th>E</th></tr>');
  const row = (side, team) => {
    const cells = [`<td class="nm">${team.name}</td>`];
    for (let i = 0; i < innings; i++) {
      const v = G.lines[side][i];
      cells.push(`<td>${v === null || v === undefined ? '&ndash;' : v}</td>`);
    }
    cells.push(`<td class="tot">${G.score[side]}</td><td>${G.hits[side]}</td><td>${G.errs[side]}</td>`);
    return `<tr>${cells.join('')}</tr>`;
  };
  $('#res-line').innerHTML = head.join('') + row(0, G.away) + row(1, G.home);

  const w = G.score[0] === G.score[1] ? null : (G.score[0] > G.score[1] ? 0 : 1);
  $('#res-head').textContent = w === null ? '引き分け'
    : G.mode === 'vs' ? `${w === 0 ? '1P' : '2P'}の勝ち！ — ${(w === 0 ? G.away : G.home).name}`
    : w === G.userSide ? 'あなたの勝ち！'
    : `${(w === 0 ? G.away : G.home).name}の勝ち`;

  // best hitter of the game
  let star = null;
  for (const t of [G.away, G.home]) for (const p of t.roster) {
    const s = p.h * 2 + p.hr * 3 + p.rbi;
    if (!star || s > star.s) star = { s, p, t };
  }
  $('#res-stats').innerHTML = [
    `<span class="pill">球場 <b>${G.st.name}</b></span>`,
    `<span class="pill">${innings > G.innings ? '延長' + innings + '回' : G.innings + '回'}</span>`,
    star ? `<span class="pill">お手柄 <b>${star.p.name}</b> ${star.p.h}安打 ${star.p.rbi}打点</span>` : '',
  ].join('');
  show('#s-result');
}

/* ============================================================
   input
   ============================================================ */
const pointer = { x: 0.5, y: 0.5, has: false };

function bindInput() {
  addEventListener('keydown', (e) => {
    if (e.repeat) return;
    KEYS[e.code] = true;
    if (!G.active) return;
    if (e.code === 'Escape') { togglePause(); return; }
    if (G.paused) return;
    if (e.code === 'Space') {
      e.preventDefault();
      Snd.boot();
      if (G.phase === 'aim' && humanPitches()) throwPitch(G.pitchType, G.reticle.x, G.reticle.y);
      else if (G.phase === 'pitch' && humanBats()) playerSwing(e.shiftKey || KEYS.ShiftLeft || KEYS.ShiftRight);
    }
    if (G.phase === 'aim' && humanPitches() && e.code >= 'Digit1' && e.code <= 'Digit5') {
      G.pitchType = +e.code.slice(5) - 1; uiHint();
    }
  });
  addEventListener('keyup', (e) => { KEYS[e.code] = false; });

  const cv = $('#gl');
  const track = (e) => {
    const r = cv.getBoundingClientRect();
    pointer.x = (e.clientX - r.left) / r.width;
    pointer.y = (e.clientY - r.top) / r.height;
    pointer.has = true;
  };
  cv.addEventListener('pointermove', track);
  cv.addEventListener('pointerdown', (e) => {
    track(e); Snd.boot();
    if (!G.active || G.paused) return;
    if (G.phase === 'aim' && humanPitches()) throwPitch(G.pitchType, G.reticle.x, G.reticle.y);
    else if (G.phase === 'pitch' && humanBats()) playerSwing(KEYS.ShiftLeft || KEYS.ShiftRight);
  });
  addEventListener('blur', () => { for (const k in KEYS) KEYS[k] = false; });
}

function updateAim(dt) {
  const k = 1.55 * dt;
  let moved = false;
  if (KEYS.ArrowLeft || KEYS.KeyA) { G.reticle.x += k; moved = true; }
  if (KEYS.ArrowRight || KEYS.KeyD) { G.reticle.x -= k; moved = true; }
  if (KEYS.ArrowUp || KEYS.KeyW) { G.reticle.y += k; moved = true; }
  if (KEYS.ArrowDown || KEYS.KeyS) { G.reticle.y -= k; moved = true; }
  if (!moved && pointer.has) {
    const tx = lerp(1.05, -1.05, clamp((pointer.x - 0.22) / 0.56, 0, 1));
    const ty = lerp(1.72, 0.16, clamp((pointer.y - 0.20) / 0.58, 0, 1));
    G.reticle.x += (tx - G.reticle.x) * Math.min(1, dt * 12);
    G.reticle.y += (ty - G.reticle.y) * Math.min(1, dt * 12);
  }
  G.reticle.x = clamp(G.reticle.x, -1.05, 1.05);
  G.reticle.y = clamp(G.reticle.y, 0.16, 1.72);
}

/* ============================================================
   contact -> flight
   ============================================================ */
function doContact() {
  const d = G.decided, bat = curBatter(), pc = G.pitch;
  let la, v0, dir;
  if (G.bunting) {
    la = rnd(-5, 9);
    v0 = rnd(6.5, 11) * (0.9 + bat.contact * 0.2);
    dir = rnd(-40, 40);
  } else {
    la = clamp(13 + d.dy * 96 + gauss(6), -22, 62);
    v0 = lerp(13, 43, d.q) * (0.90 + bat.power * 0.22);
    dir = clamp(-d.dt * 330 + (pc.ax - (humanBats() ? G.reticle.x : G.cpuAim.x)) * 18 + gauss(9), -58, 58);
    // catching it off the end, under it, off the handle: poor contact is fouled
    // off far more often than it is put in play
    if (chance(clamp(0.70 - d.q * 0.62, 0, 0.70))) {
      dir = (chance(0.5) ? 1 : -1) * rnd(55, 88);
      la = clamp(la + rnd(10, 38), 12, 80);
      v0 *= rnd(0.50, 0.86);
    }
  }
  G.flight = simFlight(v0, la, dir, G.st);
  G.ball.vis = true;
  G.trail.length = 0;
  Snd.hit(clamp(d.q, 0, 1));

  const o = fieldBall(G.flight);
  G.flightT = 0;
  G.playScript = o.play || null;
  const nearPlate = o.kind === 'foul' || o.foulFly;
  G.camMode = nearPlate ? 'foul' : 'fly';
  G.ballBoost = nearPlate ? 1.7 : 1;

  if (o.kind === 'foul') {
    // freeze it a beat after it first lands, so it does not roll into the next
    // county with the camera chasing it
    const fl2 = G.flight;
    const gi = Math.min(fl2.groundIdx + 14, fl2.path.length - 1);
    const q = fl2.path[gi];
    G.playScript = { fidx: -1, coverIdx: -1, cutIdx: gi, cutT: q.t,
                     pt: { x: q.x, y: q.y, z: q.z }, air: false, throwTo: null, throwDur: 0 };
    G.pendingCount = 'foul';
    stealReturn();
    setPhase('play', Math.min(q.t, 1.5) + 0.45);
    banner('ファウル');
    return;
  }
  G.pendingCount = null;
  G.carStall = 0;
  if (G.flight.carHit) Snd.clang();
  finishAtBat(o);
}

/* ============================================================
   per-frame update
   ============================================================ */
function update(dt) {
  if (!G.active || G.paused) return;
  G.pt += dt;
  if (G.phase === 'pitch' || G.phase === 'aim') updateAim(dt);
  if (G.batSwingT >= 0) G.batSwingT += dt;

  switch (G.phase) {
    case 'ready':
      // never deliver until the camera is back behind the plate and the
      // pitcher has actually returned to the mound
      if (G.pt >= G.phaseLen
          && (camSettled() || G.pt > G.phaseLen + 2.2)
          && (pitcherSet() || G.pt > G.phaseLen + 3.2)) {
        if (humanPitches()) { setPhase('aim'); uiHint(); }
        else { const c = cpuPitchChoice(); throwPitch(c.ti, c.ax, c.ay); }
      }
      break;

    case 'aim':
      break;

    case 'pitch': {
      const pc = G.pitch;
      pc.t += dt;
      const p = pitchPos(pc, pc.t);
      // the ball dies in the mitt rather than carrying on through the catcher
      const cst = G.stations[1];
      const mitt = cst.z + 0.62;
      G.ball.x = p.x; G.ball.y = Math.max(p.y, 0.42); G.ball.z = Math.max(p.z, mitt);
      G.trail.unshift(p.x, p.y, p.z);
      if (G.trail.length > 42) G.trail.length = 42;
      if (!humanBats() && G.swingT >= 0 && !G.decided && pc.t >= G.swingT) {
        G.batSwingT = 0; judgeSwing();
      }
      if (G.contactAt >= 0 && pc.t >= G.contactAt) { doContact(); break; }
      if (pc.hbp && G.swingT < 0 && pc.t >= pc.T + 0.02) {
        G.ball.vis = false;
        afterPitch('hbp');
        break;
      }
      if (pc.t > pc.T + 0.42) {
        G.ball.vis = false;
        pitchPast(G.swingT >= 0 ? 'whiff' : pc.inZone ? 'strike' : 'ball');
      }
      break;
    }

    case 'result':
      if (G.pt >= G.phaseLen) { G.swingT = -1; G.decided = null; G.contactAt = -1; G.batSwingT = -1; G.bunting = false; setPhase('ready', 0.42); }
      break;

    case 'play': {
      if (G.pending && (G.flight ? G.flightT : G.pt) >= G.pending.at) flushResult();
      if (G.flight) {
        G.flightT += dt;
        const fl = G.flight, pl = G.playScript, path = fl.path;
        const stop = pl ? Math.min(pl.cutIdx, path.length - 1) : path.length - 1;
        const p = path[Math.min(stop, Math.floor(G.flightT / (1 / 90)))];
        let bx = p.x, by = p.y, bz = p.z, live = true;

        if (pl && pl.fidx >= 0) {
          // the fielder runs to the ball and arrives with it
          const f = G.fielders[pl.fidx];
          f.scripted = true;
          const u = clamp((G.flightT - 0.22) / Math.max(0.25, pl.cutT - 0.22), 0, 1);
          const e = u * u * (3 - 2 * u);
          f.x = lerp(f.st.x, pl.pt.x, e); f.z = lerp(f.st.z, pl.pt.z, e);
          f.run = u < 1 ? 1.2 : 0;
          f.fumbling = false;
          if (pl.fumble && G.flightT > pl.cutT + 0.16) {     // go and pick it up
            const fu = clamp((G.flightT - pl.cutT - 0.16) / (FUMBLE_T + 0.25), 0, 1);
            const fe = fu * fu * (3 - 2 * fu);
            f.x = lerp(pl.pt.x, pl.fumbleTo[0], fe); f.z = lerp(pl.pt.z, pl.fumbleTo[1], fe);
            f.run = fu < 1 ? 1.2 : 0;
            f.fumbling = G.flightT < pl.cutT + 0.46;
          }
          // team-mates cover the bags and back up the play
          for (const mv of pl.moves || []) {
            const c = G.fielders[mv.idx];
            if (!c || mv.idx === pl.fidx) continue;
            c.scripted = true;
            const cu = clamp(G.flightT / Math.max(0.5, mv.byT), 0, 1);
            const ce = cu * cu * (3 - 2 * cu);
            c.x = lerp(c.st.x, mv.x, ce); c.z = lerp(c.st.z, mv.z, ce);
            c.run = cu < 1 ? 1.2 : 0;
          }
        }
        if (pl && G.flightT > pl.cutT) {
          {
            live = false;
            let tt = G.flightT - pl.cutT;
            let fromX = pl.pt.x, fromZ = pl.pt.z, fromY = Math.max(pl.pt.y, 1.0);
            let loose = false;
            if (pl.fumble) {                  // it pops out of the glove first
              if (tt <= FUMBLE_T + 0.45) {
                const u = clamp(tt / FUMBLE_T, 0, 1);
                bx = lerp(pl.pt.x, pl.fumbleTo[0], u);
                bz = lerp(pl.pt.z, pl.fumbleTo[1], u);
                by = lerp(Math.max(pl.pt.y, 0.95), 0.14, u) + Math.sin(u * Math.PI) * 0.85;
                loose = true;
              } else {
                tt -= FUMBLE_T + 0.45;
                fromX = pl.fumbleTo[0]; fromZ = pl.fumbleTo[1]; fromY = 0.7;
              }
            }
            const arc = (ax, az, ay, bx2, bz2, u) => {
              bx = lerp(ax, bx2, u); bz = lerp(az, bz2, u);
              by = lerp(ay, 1.0, u) + Math.sin(u * Math.PI) * 2.4;
              if (u >= 1) by = 1.0;
            };
            if (loose) { /* still skipping away from him */ }
            else if (pl.via) {                  // the relay through second
              if (tt <= pl.viaDur) {
                arc(fromX, fromZ, fromY, pl.via[0], pl.via[1], clamp(tt / pl.viaDur, 0, 1));
              } else {
                bx = pl.via[0]; bz = pl.via[1]; by = 1.0;
                tt -= pl.viaDur + 0.28;         // a beat on the bag, then away
                if (tt > 0 && pl.throwTo && pl.throwDur > 0)
                  arc(pl.via[0], pl.via[1], 1.0, pl.throwTo[0], pl.throwTo[1],
                      clamp(tt / pl.throwDur, 0, 1));
              }
            } else if (pl.throwTo && pl.throwDur > 0) {
              arc(fromX, fromZ, fromY, pl.throwTo[0], pl.throwTo[1], clamp(tt / pl.throwDur, 0, 1));
            } else {
              bx = pl.pt.x; by = Math.max(pl.pt.y, 0.14); bz = pl.pt.z;
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
        // a foul stays on the close camera so it can snap back for the next pitch
        const foulPlay = pl && pl.fidx < 0;
        const wide = pl ? pl.cutT * 0.72 : fl.total * 0.62;
        if (!foulPlay && (G.flightT > wide || G.flightT > 2.8)) G.camMode = 'field';
      }
      if (G.pt >= G.phaseLen) endPlay();
      break;
    }

    case 'change':
      if (G.pt >= G.phaseLen) endHalfInning();
      break;

    case 'halfend':
      if (G.pt >= G.phaseLen) nextBatter();
      break;

    case 'walkoff':
      if (G.pt >= G.phaseLen) endGame();
      break;
  }

  if (G.hbpT > 0) G.hbpT -= dt;
  updateTraffic(dt);
  // runners (a flattened one lies there until he can get up)
  let stalled = false;
  for (const m of G.movers) {
    if (m.down > 0) { m.down -= dt; stalled = true; continue; }
    m.t += dt;
    if (G.traffic && !m.retired && m.t > 0 && m.t < m.dur) {
      if (m.dodge > 0) m.dodge -= dt;
      else {
        const r = runnerAt(m);
        for (const c of G.traffic) {
          if (carHits(c, r.x, 0.6, r.z, 0.30)) {
            if (!chance(c.walk ? 0.13 : 0.09)) { m.dodge = 1.3; break; }
            m.down = c.walk ? 1.3 : 1.6;
            Snd.crash();
            runOverRunner(m, !!c.walk);    // he is out where he stands
            stalled = true;
            break;
          }
        }
      }
    }
  }
  if (stalled && G.phase === 'play' && G.carStall < 2.6) { G.phaseLen += dt; G.carStall += dt; }
  // fielders drift back / converge, or head for the bench on the third out
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
  }
  updateCamera(dt);
}

function endPlay() {
  G.carStall = 0;
  G.ballBoost = 1;
  G.camMode = 'bat';        // back behind the plate before anything else
  G.ball.vis = false;
  G.flight = null;
  G.playScript = null;
  for (const f of G.fielders) f.scripted = false;
  G.movers = [];
  G.trail.length = 0;
  // a run can come in on a wild pitch or a balk too, and the third out can be
  // made on the bases in the middle of an at-bat — so both are asked before
  // the count carries on
  const count = G.pendingCount;
  G.pendingCount = null;
  if (checkWalkoff()) return;
  if (G.outs >= 3) {
    // the half-inning does not just cut away: it gets called, and they run in
    G.camMode = 'field';
    banner('スリーアウト\nチェンジ', true);
    Snd.good();
    setPhase('change', 1.9);
    return;
  }
  if (count) afterPitch(count, true);
  else nextBatter();
}

/* ============================================================
   camera
   ============================================================ */
const camSettled = () =>
  CAM.wx === undefined ||
  Math.hypot(CAM.ex - CAM.wx, CAM.ey - CAM.wy, CAM.ez - CAM.wz) < 0.9;

/* the pitcher has to be back on the rubber before he can deliver */
const pitcherSet = () => {
  const f = G.fielders[0];
  return !f || (f.down <= 0 && Math.hypot(f.x - f.st.x, f.z - f.st.z) < 0.7);
};

function updateCamera(dt) {
  // indoors the camera must stay under the roof or it looks through it
  const ceilY = G.st && G.st.ceiling ? G.st.ceiling - 1.4 : 1e9;
  let ex, ey, ez, tx, ty, tz, fov = 46, sp = 3.2;
  if (G.camMode === 'bat') {
    const tall = clamp(1.25 - R.w / R.h, 0, 0.5);   // >0 once the view goes portrait
    ex = 0.55; ey = 4.6 + tall * 3.2; ez = -9.0 - tall * 5.0;
    tx = 0; ty = 0.4 + tall * 0.5; tz = 7.0; fov = 40; sp = 5;
  } else if (G.camMode === 'fly') {
    const b = G.ball;
    ex = b.x * 0.55; ey = clamp(6 + b.y * 0.55, 6, 46); ez = b.z * 0.30 - 21;
    tx = b.x * 0.9; ty = b.y * 0.85 + 0.6; tz = b.z * 0.96; fov = 48; sp = 3.4;
  } else if (G.camMode === 'foul') {
    // the eye stays at the plate so the ball genuinely recedes; only the aim
    // and the field of view open up to keep it in shot
    const b = G.ball;
    ex = 0.55; ey = 5.2; ez = -10.0;
    tx = clamp(b.x * 0.62, -15, 15); ty = clamp(b.y * 0.30 + 1.0, 1.0, 6.5);
    tz = 8; fov = 62; sp = 4.5;
  } else if (ceilY < 40) {
    // indoors: as high as the roof allows, and in front of the checkouts
    ex = 0; ey = Math.min(9.0, ceilY); ez = -11;
    tx = 0; ty = 0.9; tz = 28; fov = 68; sp = 1.8;
  } else {
    ex = 0; ey = 33; ez = -26;
    tx = 0; ty = 0; tz = 30; fov = 50; sp = 1.8;
  }
  ey = Math.min(ey, ceilY);
  ty = Math.min(ty, ceilY - 0.6);
  CAM.wx = ex; CAM.wy = ey; CAM.wz = ez;
  const k = Math.min(1, dt * sp);
  CAM.ex += (ex - CAM.ex) * k; CAM.ey += (ey - CAM.ey) * k; CAM.ez += (ez - CAM.ez) * k;
  CAM.tx += (tx - CAM.tx) * k; CAM.ty += (ty - CAM.ty) * k; CAM.tz += (tz - CAM.tz) * k;
  CAM.fov += (fov - CAM.fov) * k;
}

/* ============================================================
   drawing
   ============================================================ */
let clock = 0;

/* ---------- the swing ----------
   Keyframes in seconds from the press. Contact lands at 0.090s, which is
   SWING_LAG, so the barrel is in the zone exactly when the hit is judged.
     az    bat azimuth, degrees (0 = toward centre field)
     tilt  barrel elevation
     r/gy  where the hands ride: radius from the spine, and height
     ry    body turn, added to the batter's facing
     shift stride toward the pitcher                                        */
const BAT_LEN = 0.98;
/* gx/gy/gz put the bottom hand at an explicit point (gx and gz are offsets from
   the batter's spot); az/tilt aim the barrel from there. px/py/pz hint which
   way the elbows break. */
const SWING = [
  { t: 0.000, gx: 0.13, gy: 1.05, gz: -0.40, az: 145, tilt: 0.95, ry: -0.34, lean: 0.05, spread: 0.05, lgL: 0.10, lgR: -0.10, shift: 0.00, head: 1.64, px: 0.35, py: -0.70, pz: -0.45 },
  { t: 0.032, gx: 0.17, gy: 1.10, gz: -0.48, az: 152, tilt: 1.05, ry: -0.50, lean: 0.02, spread: 0.06, lgL: 0.13, lgR: -0.17, shift: -0.03, head: 1.86, px: 0.40, py: -0.65, pz: -0.50 },
  { t: 0.090, gx: -0.40, gy: 1.00, gz: 0.05, az: -90, tilt: 0.02, ry: 0.26, lean: 0.14, spread: 0.15, lgL: -0.02, lgR: 0.07, shift: 0.11, head: 0.79, px: 0.20, py: -0.90, pz: 0.10 },
  { t: 0.200, gx: -0.20, gy: 1.06, gz: 0.30, az: -40, tilt: -0.15, ry: 0.70, lean: 0.17, spread: 0.16, lgL: -0.05, lgR: 0.09, shift: 0.13, head: 0.15, px: 0.10, py: -0.90, pz: 0.30 },
  { t: 0.520, gx: 0.05, gy: 1.26, gz: 0.34, az: 45, tilt: 0.75, ry: 1.10, lean: 0.09, spread: 0.12, lgL: -0.02, lgR: 0.05, shift: 0.11, head: -0.15, px: 0.10, py: -0.75, pz: 0.45 },
];

function batterRig(t, clk) {
  let k;
  if (t < 0) {
    k = Object.assign({}, SWING[0]);           // waiting: a small bat waggle
    k.az += Math.sin(clk * 2.4) * 6.0;
    k.tilt += Math.sin(clk * 2.4 + 0.6) * 0.08;
    k.gy += Math.sin(clk * 1.9) * 0.015;
    k.gz += Math.sin(clk * 1.9 + 1.1) * 0.012;
  } else {
    const last = SWING[SWING.length - 1];
    const tt = Math.min(t, last.t);
    let i = 0;
    while (i < SWING.length - 2 && tt > SWING[i + 1].t) i++;
    const a = SWING[i], b = SWING[i + 1];
    const u = clamp((tt - a.t) / (b.t - a.t), 0, 1);
    const e = u * u * (3 - 2 * u);
    k = {};
    for (const key in a) k[key] = lerp(a[key], b[key], e);
  }
  const az = k.az * DEG, ct = Math.cos(k.tilt), st = Math.sin(k.tilt);
  const grip = [BAT_X + k.gx, k.gy, BAT_Z + k.gz];
  const dir = [Math.sin(az) * ct, st, Math.cos(az) * ct];
  const on = (d) => [grip[0] + dir[0] * d, grip[1] + dir[1] * d, grip[2] + dir[2] * d];
  k.grip = grip; k.dir = dir; k.bx = BAT_X; k.bz = BAT_Z + k.shift;
  // right-handed hitter: left hand at the knob, right hand above it. The
  // character's local +x side faces the pitcher, so that is the left arm.
  k.topAt = 0.20; k.botAt = 0.06;
  k.handTop = on(k.topAt);
  k.handBot = on(k.botAt);
  k.pole = [k.px, k.py, k.pz];
  return k;
}

/* runners follow the base-path polyline, touching every bag */
/* How far down the line a man who is not running stands. Before the pitch it
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

function runnerAt(m) {
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
}

/* a hand target, pulled back so it stays within `max` of the shoulder */
function reachFrom(sx, sy, sz, tx, ty, tz, max) {
  const dx = tx - sx, dy = ty - sy, dz = tz - sz;
  const d = Math.hypot(dx, dy, dz) || 1;
  const k = Math.min(1, max / d);
  return [sx + dx * k, sy + dy * k, sz + dz * k];
}

function drawScene() {
  const st = G.st;
  const env = { light: st.light, skyTint: st.skyTint, gndTint: st.gndTint, fog: st.fog, fogDist: st.fogDist };
  R.begin(CAM, env);
  G.scene.draw();

  const bt = batTeam(), ft = fldTeam();
  const bob = Math.sin(clock * 2.2) * 0.03;
  // moods only show while the play is being read out; before the pitch the
  // batter and the pitcher are bearing down instead
  const mood = G.phase === 'result' || G.phase === 'halfend'
            || G.phase === 'walkoff' || G.phase === 'change';
  const faceBat = mood ? (G.faceBat || EXPR.idle) : EXPR.focus;
  const faceFld = mood ? (G.faceFld || EXPR.idle) : EXPR.idle;
  if (G.traffic) for (const c of G.traffic) { if (c.walk) drawShopper(c); else drawCar(c); }

  // fielders
  for (let i = 0; i < G.fielders.length; i++) {
    const f = G.fielders[i];
    const pl = ft.roster.find((r) => r.pos === f.st.k) || ft.roster[i];
    const running = f.run > 0.6;
    const swing = running ? Math.sin(clock * 13) * 0.8 : 0;
    const pose = {
      armL: running ? swing * 0.7 : 0.2 + bob, armR: running ? -swing * 0.7 : -0.2 - bob,
      legL: swing, legR: -swing, bob: running ? Math.abs(Math.sin(clock * 13)) * 0.06 : bob * 0.5,
      face: f.st.k === 'P' && (G.phase === 'ready' || G.phase === 'pitch') ? EXPR.focus : faceFld,
    };
    if (f.down > 0) {                       // run over: flat on his back
      const settle = clamp(f.down * 2.2, 0, 1);
      drawAnimal(f.x, f.z, f.ry, pl.look, {
        fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4,
        armL: -1.1, armR: 1.1, bob: -0.30, face: EXPR.down,
      }, 0);
      for (let s2 = 0; s2 < 3; s2++) {
        const a2 = clock * 5 + s2 * 2.1;
        R.b('sphere', f.x + Math.cos(a2) * 0.34, 0.92 + Math.sin(clock * 6 + s2) * 0.05,
            f.z + Math.sin(a2) * 0.34, 0.13, 0.13, 0.13, col('#FFE04A'));
      }
      continue;
    }
    const isP = f.st.k === 'P', isC = f.st.k === 'C';
    let ry = f.ry;
    if (isP) {
      if (G.phase === 'ready') {                 // wind up
        const u = clamp(G.pt / Math.max(0.3, G.phaseLen), 0, 1);
        pose.armL = -0.5 - u * 2.0; pose.armR = -0.4 - u * 0.8; pose.legR = -u * 0.45;
      } else if (G.phase === 'pitch') {
        const t = G.pitch.t;
        if (t < 0.10 && G.ball.vis) {             // the ball is still in his hand
          pose.handL = reachFrom(f.x, 0.94, f.z, G.ball.x, G.ball.y, G.ball.z, 0.60);
          pose.pole = [0.4, -0.6, 0.2];
        }
        pose.armR = -1.6 + clamp(t * 5, 0, 2.0);
      }
    }
    // The glove goes on the LEFT hand, which is the local +x arm: a character
    // faces its local +z, so its right side is local -x. The right hand throws.
    pose.noPawR = 1;
    if (!isP && G.ball.vis) {
      const shy = 0.94 + (f.st.k === 'C' ? -0.22 : 0);
      const shx = f.x + 0.17 * Math.cos(f.ry), shz = f.z - 0.17 * Math.sin(f.ry);
      if (Math.hypot(G.ball.x - shx, G.ball.y - shy, G.ball.z - shz) < 2.3) {
        pose.handR = reachFrom(shx, shy, shz, G.ball.x,
                               clamp(G.ball.y, 0.15, 2.1), G.ball.z, 0.62);
        pose.pole = [0, -0.7, 0.5];
      }
    }
    if (f.fumbling) {                       // arms up — it got away from him
      pose.handR = null; pose.armL = -2.3; pose.armR = -2.2; pose.lean = -0.20;
    }
    if (isC && G.phase === 'pitch') {
      // the mitt sits up in front of him and only moves the last little bit to
      // meet the ball — it never chases it out toward the mound
      const shy = 0.94 - 0.22;
      let tx = f.x * 0.4, ty = 0.78, tz = f.z + 0.62;
      if (G.ball.vis && G.ball.z < f.z + 2.6) {
        tx = G.ball.x; ty = clamp(G.ball.y, 0.28, 1.75); tz = Math.max(G.ball.z, f.z + 0.42);
      }
      pose.handR = reachFrom(f.x, shy, f.z, tx, ty, tz, 0.60);
      pose.pole = [0, -0.7, 0.7];
    }
    const y0 = isC ? -0.22 : 0;
    const a = drawAnimal(f.x, f.z, ry, pl.look, pose, y0);
    if (!f.fumbling && !ANIMALS[pl.look.animal].noGlove) {
      const gp = L2W(a.f, a.hr[0], a.hr[2]);
      inked(pl.look, () => drawGlove(pose.handR
        ? [pose.handR[0], pose.handR[1], pose.handR[2]]
        : [gp[0], a.hr[1], gp[1]], f.ry));
    }
  }

  // umpire
  drawAnimal(-1.55, -4.9, 0, { animal: 'hippo', uni: '#2B3138', trim: '#4A525C', cap: '#1E242A' },
    { armL: 0.5, armR: -0.5, bob: bob * 0.4 }, -0.30);

  // batter (unless already running)
  // on the third out he walks off with everybody else
  const batterRunning = G.movers.some((m) => m.from === -1 && m.t >= 0);
  if (!batterRunning && G.phase !== 'change') {
    const b = curBatter();
    if (G.hbpT > 0) {                       // just wore one — no bat, on the deck
      drawAnimal(BAT_X + 0.25, BAT_Z - 0.2, -Math.PI / 2, b.look,
        { fall: -0.62, spread: 0.20, legL: -0.35, legR: 0.30,
          armL: -1.7, armR: -1.6, bob: -0.12, helmet: 1, face: EXPR.down }, 0);
      for (let s2 = 0; s2 < 3; s2++) {
        const a2 = clock * 5 + s2 * 2.1;
        R.b('sphere', BAT_X + 0.25 + Math.cos(a2) * 0.34, 1.05 + Math.sin(clock * 6 + s2) * 0.05,
            BAT_Z - 0.2 + Math.sin(a2) * 0.34, 0.13, 0.13, 0.13, col('#FFE04A'));
      }
    } else {
    const rig = batterRig(G.batSwingT, clock);
    drawAnimal(rig.bx, rig.bz, -Math.PI / 2 + rig.ry, b.look, {
      handL: rig.handTop, handR: rig.handBot, pole: rig.pole,
      legL: rig.lgL, legR: rig.lgR, spread: rig.spread,
      lean: rig.lean, headRy: rig.head,
      helmet: 1, gloveC: bt.trim, face: faceBat, swingT: G.batSwingT,
      bob: G.batSwingT < 0 ? bob * 0.5 : 0.015,
    }, 0);
    if (!ANIMALS[b.look.animal].noBat) inked(b.look, () => {
      drawBatRig(rig.grip, rig.dir, BAT_LEN, '#C99A5E', '#6B4A2A');
      drawGrip(rig.grip, rig.dir, rig.botAt, bt.trim);
      drawGrip(rig.grip, rig.dir, rig.topAt, bt.trim);
    });
    }
  }

  // runners in motion
  for (const m of G.movers) {
    if (m.t < 0) continue;
    const r = runnerAt(m);
    if (r.done && m.scored) continue;
    if (m.down > 0) {
      drawAnimal(r.x, r.z, r.ry, m.p.look,
        { fall: -1.45, spread: 0.18, legL: -0.5, legR: 0.4, armL: -1.1, armR: 1.1,
          bob: -0.30, helmet: 1, face: EXPR.down }, 0);
      for (let s2 = 0; s2 < 3; s2++) {
        const a2 = clock * 5 + s2 * 2.1;
        R.b('sphere', r.x + Math.cos(a2) * 0.34, 0.92 + Math.sin(clock * 6 + s2) * 0.05,
            r.z + Math.sin(a2) * 0.34, 0.13, 0.13, 0.13, col('#FFE04A'));
      }
      continue;
    }
    if (m.slide && r.u > 0.80) {          // a throw is coming: get down
      const k = clamp((r.u - 0.80) / 0.13, 0, 1);
      drawAnimal(r.x, r.z, r.ry, m.p.look, {
        fall: -1.18 * k, spread: 0.26, legL: -1.05, legR: -0.45,
        armL: -1.55, armR: -1.15, bob: -0.44 * k, helmet: 1, face: EXPR.focus,
      }, 0);
      continue;
    }
    const sw = r.done ? 0 : Math.sin(clock * 15) * 0.9;
    drawAnimal(r.x, r.z, r.ry, m.p.look, {
      armL: sw * 0.8, armR: -sw * 0.8, legL: sw, legR: -sw, helmet: 1, face: faceBat,
      bob: r.done ? 0 : Math.abs(Math.sin(clock * 15)) * 0.07, lean: 0.16,
    }, 0);
  }
  // runners standing on base
  for (let i = 0; i < 3; i++) {
    const p = G.bases[i];
    if (!p || G.movers.some((m) => m.p === p)) continue;
    // he takes his lead down the line, shuffling and watching the pitcher
    const b = BASE_POS[i], n2 = basePt(i + 1);
    const ux = n2[0] - b[0], uz = n2[1] - b[1], ul = Math.hypot(ux, uz) || 1;
    // he only takes his lead before the pitch — once the ball is hit he is
    // back on the bag, watching the fly
    const off = leadOff(i);
    const lx = b[0] + (ux / ul) * off, lz = b[1] + (uz / ul) * off;
    // he watches the ball while it is up, and the pitcher the rest of the time
    const up = G.phase === 'play' && G.ball.vis;
    const wx = up ? G.ball.x : MOUND_POS[0], wz = up ? G.ball.z : MOUND_POS[1];
    drawAnimal(lx, lz, Math.atan2(wx - lx, wz - lz), p.look,
               { armL: 0.42, armR: 0.42, legL: 0.10, legR: -0.10, spread: 0.19,
                 lean: 0.17, bob: bob * 0.6, helmet: 1, face: faceBat }, 0);
  }

  // ball, with a shadow on the ground so its height and distance are readable
  if (G.ball.vis) {
    if (G.phase === 'play' && G.ball.y > 0.28)
      shadow(G.ball.x, G.ball.z, 0.30 * (G.ballBoost || 1), clamp(0.38 - G.ball.y * 0.007, 0.14, 0.38));
    drawTrail(G.trail);
    drawBall(G.ball.x, G.ball.y, G.ball.z, clock * 9);
  }

  // aiming overlay, only while the pitch is live
  if ((G.phase === 'pitch' || G.phase === 'aim') && !G.over) drawZone();

  flushShadows(0);
}

function drawZone() {
  const z = 0.30;
  R.unlit(true, 0.55);
  // two passes: a dark backing then a light face, so the zone reads on grass,
  // asphalt, a white tiled floor and grey regolith alike
  const frame = (c, t, dz, a) => {
    R.gl.uniform1f(R.u.uAlpha, a);
    const seg = (x, y, w, h) => R.b('box', x, y, z + dz, w, h, 0.02, c);
    seg(0, ZY0, ZX * 2 + t, t); seg(0, ZY1, ZX * 2 + t, t);
    seg(-ZX, (ZY0 + ZY1) / 2, t, ZY1 - ZY0); seg(ZX, (ZY0 + ZY1) / 2, t, ZY1 - ZY0);
  };
  frame(col('#141C26'), 0.075, 0.012, 0.5);
  frame(col('#FFFFFF'), 0.035, 0, 0.9);
  // meet cursor
  const a = col('#FFC44D'), ao = col('#5A3B06');
  const rx = G.reticle.x, ry = G.reticle.y;
  for (let i = 0; i < 8; i++) {
    const th = (i / 8) * Math.PI * 2;
    const px = rx + Math.cos(th) * 0.2, py = ry + Math.sin(th) * 0.2;
    R.gl.uniform1f(R.u.uAlpha, 0.55);
    R.b('box', px, py, z - 0.01, 0.105, 0.105, 0.02, ao);
    R.gl.uniform1f(R.u.uAlpha, 0.95);
    R.b('box', px, py, z - 0.03, 0.07, 0.07, 0.02, a);
  }
  R.b('box', rx, ry, z - 0.03, 0.05, 0.05, 0.02, a);
  R.unlit(false);
}

/* ============================================================
   boot
   ============================================================ */
function frame(now) {
  const dt = Math.min(0.05, (now - frame.last || 16) / 1000);
  frame.last = now;
  clock += dt;
  update(dt);
  if (G.st) drawScene();
  else drawIdle();
  requestAnimationFrame(frame);
}
frame.last = 0;

let idleScene = null, idleTeam = null, idleStations = null;
function drawIdle() {
  if (!idleScene) {
    idleScene = STADIUMS[0].build();
    idleTeam = makeTeam(TEAMS[3]);
    idleStations = stationsFor(STADIUMS[0]);
  }
  const st = STADIUMS[0];
  const a = clock * 0.16;
  CAM.ex = Math.sin(a) * 26; CAM.ez = 6 + Math.cos(a) * 26; CAM.ey = 7.5;
  CAM.tx = 0; CAM.ty = 1.2; CAM.tz = 16; CAM.fov = 48;
  R.begin(CAM, { light: st.light, skyTint: st.skyTint, gndTint: st.gndTint, fog: st.fog, fogDist: st.fogDist });
  idleScene.draw();
  const bob = Math.sin(clock * 2.2) * 0.03;
  for (let i = 0; i < 9; i++) {
    const s = idleStations[i];
    drawAnimal(s.x, s.z, Math.atan2(-s.x, -s.z), idleTeam.roster[i].look, { armL: 0.2 + bob, armR: -0.2 - bob, bob }, 0);
  }
  flushShadows(0);
}

function boot() {
  const cv = $('#gl');
  if (!R.init(cv)) {
    document.body.innerHTML = '<div style="padding:40px;font-family:sans-serif;color:#F6EFE1">' +
      'このブラウザではWebGLが使えないため、ゲームを表示できません。</div>';
    return;
  }
  const faceAtlas = buildFaceAtlas();
  R.upload(faceAtlas);
  applyFaceScans(faceAtlas, () => R.upload(faceAtlas));
  buildMenus();
  bindInput();
  $('#btn-start').onclick = () => { Snd.boot(); G.mode = 'cpu'; show('#s-stadium'); };
  $('#btn-vs').onclick = () => { Snd.boot(); G.mode = 'vs'; show('#s-stadium'); };
  $('#btn-quit').onclick = () => togglePause();
  $('#btn-resume').onclick = () => togglePause();
  $('#btn-abandon').onclick = () => {
    G.paused = false; G.active = false; G.over = false; G.st = null;
    show('#s-title');
  };
  $('#btn-rules').onclick = () => show('#s-rules');
  $('#btn-rules-back').onclick = () => show('#s-title');
  $('#btn-st-back').onclick = () => show('#s-title');
  $('#btn-tm-back').onclick = () => show('#s-stadium');
  $('#btn-again').onclick = () => { G.st = null; teamPick = 0; show('#s-stadium'); };
  $('#btn-menu').onclick = () => { G.st = null; show('#s-title'); };
  addEventListener('resize', () => R.resize());
  requestAnimationFrame(frame);
}
boot();
