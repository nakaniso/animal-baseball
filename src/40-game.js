/* ============================================================
   40-game.js — the rules: counts, outs, innings, batted balls,
   fielding, base running, and the end of the game.
   ============================================================ */
'use strict';

const ZX = 0.30, ZY0 = 0.50, ZY1 = 1.26;      // strike zone
const SWING_LAG = 0.09;                        // press -> barrel in the zone
const TIME_WIN = 0.115;                        // usable timing window (s)
const MEET_WIN = 0.46;                         // usable aim window (m)
const BAT_X = 0.95, BAT_Z = 0.25;              // right-handed batter's box (+x = 3B side)

const PITCHES = [
  { k: 'straight', nm: 'ストレート', en: 'FASTBALL', spd: 33.0, bx: 0,     by: 0,     pw: 2.0 },
  { k: 'curve',    nm: 'カーブ',     en: 'CURVE',    spd: 24.5, bx: -0.20, by: -0.55, pw: 2.0 },
  { k: 'slider',   nm: 'スライダー', en: 'SLIDER',   spd: 29.0, bx: -0.44, by: -0.18, pw: 2.6 },
  { k: 'fork',     nm: 'フォーク',   en: 'SPLITTER', spd: 27.5, bx: 0,     by: -0.80, pw: 3.4 },
  { k: 'shoot',    nm: 'シュート',   en: 'SHOOT',    spd: 30.0, bx: 0.38,  by: -0.12, pw: 2.2 },
];

function gauss(sd) {
  let u = 0, v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v) * sd;
}

const G = {
  active: false, over: false,
  st: null, stations: [], away: null, home: null, userSide: 0,
  inning: 1, half: 0, outs: 0, balls: 0, strikes: 0,
  bases: [null, null, null], score: [0, 0], lines: [[], []], order: [0, 0],
  hits: [0, 0], errs: [0, 0], lob: [0, 0], inningRuns: 0,
  phase: 'idle', pt: 0, phaseLen: 0,
  pitch: null, ball: { x: 0, y: 0, z: 0, vis: false }, trail: [],
  reticle: { x: 0, y: 0.88 }, swingT: -1, contactAt: -1, decided: null,
  batSwingT: -1, bunting: false, pitchType: 0,
  fielders: [], movers: [], flight: null, chase: null,
  camMode: 'bat', lastText: '', mode: 'cpu', paused: false, playScript: null, traffic: null, carStall: 0,
  firstPitch: false, ballBoost: 1,
  innings: 6, hbpT: 0,
};

const batTeam = () => (G.half === 0 ? G.away : G.home);
const fldTeam = () => (G.half === 0 ? G.home : G.away);
const userBatting = () => (G.half === 0 ? 0 : 1) === G.userSide;
/* who is at the controls right now */
const humanBats = () => (G.mode === 'vs' ? true : G.mode === 'auto' ? false : userBatting());
const humanPitches = () => (G.mode === 'vs' ? true : G.mode === 'auto' ? false : !userBatting());
/* 1P is always the away side */
const battingPlayer = () => (G.half === 0 ? '1P' : '2P');
const pitchingPlayer = () => (G.half === 0 ? '2P' : '1P');
const curBatter = () => batTeam().roster[G.order[G.half]];
const curPitcher = () => fldTeam().roster[8];
const basePt = (i) => (i < 0 || i >= 3 ? HOME_POS : BASE_POS[i]);

/* ============================================================
   setup
   ============================================================ */
function startGame(stadiumId, awayTeamId, homeTeamId) {
  const st = stadiumById(stadiumId);
  G.st = st;
  G.stations = stationsFor(st);
  G.scene = st.build();
  const others = TEAMS.filter((t) => t.id !== awayTeamId);
  G.away = makeTeam(teamById(awayTeamId));
  G.home = makeTeam(homeTeamId ? teamById(homeTeamId) : pick(others));
  G.userSide = 0;
  G.inning = 1; G.half = 0; G.outs = 0; G.balls = 0; G.strikes = 0;
  G.bases = [null, null, null];
  G.score = [0, 0]; G.lines = [[], []]; G.order = [0, 0];
  G.hits = [0, 0]; G.errs = [0, 0]; G.lob = [0, 0]; G.inningRuns = 0;
  G.over = false; G.active = true; G.paused = false; G.movers = []; G.flight = null; G.playScript = null;
  G.firstPitch = true;
  // start already looking down the barrel instead of swinging in from the menu
  CAM.ex = 0.55; CAM.ey = 4.6; CAM.ez = -9.0; CAM.tx = 0; CAM.ty = 0.4; CAM.tz = 7.0; CAM.fov = 40;
  CAM.wx = CAM.ex; CAM.wy = CAM.ey; CAM.wz = CAM.ez;
  G.fielders = G.stations.map((s) => ({ st: s, x: s.x, z: s.z, tx: s.x, tz: s.z, ry: Math.PI, run: 0, hold: false, down: 0, dvz: 0, dodge: 0 }));
  G.traffic = makeTraffic(st);
  uiTeams();
  clearLog();
  logLine(`${G.st.name}での試合です。${G.away.name} 対 ${G.home.name}。`, true);
  logLine(`ルール：${G.st.quirk}`);
  nextBatter();
}

function setPhase(p, len) { G.phase = p; G.pt = 0; G.phaseLen = len || 0; }

function nextBatter() {
  G.balls = 0; G.strikes = 0;
  G.swingT = -1; G.contactAt = -1; G.decided = null; G.batSwingT = -1; G.bunting = false;
  G.reticle.x = 0; G.reticle.y = 0.88;
  G.ball.vis = false; G.trail.length = 0;
  G.camMode = 'bat';
  placeFielders();
  uiScore();                       // the pips belong to this batter, not the last
  uiBatter();
  setPhase('ready', G.firstPitch ? 3.0 : 1.5);
}

function placeFielders() {
  for (const f of G.fielders) { f.tx = f.st.x; f.tz = f.st.z; f.hold = false; }
}

/* traffic keeps rolling whatever the game is doing */
function updateTraffic(dt) {
  if (!G.traffic) return;
  stepTraffic(G.traffic, dt);
  for (const f of G.fielders) {
    if (f.down > 0) { f.down -= dt; f.z += f.dvz * dt; f.dvz *= 0.90; continue; }
    if (f.dodge > 0) { f.dodge -= dt; continue; }   // just got out of the way
    if (f.scripted) continue;            // he is on the play; leave him to it
    for (const c of G.traffic) {
      if (carHits(c, f.x, 0.6, f.z, 0.30)) {
        if (!chance(c.walk ? 0.20 : 0.13)) { f.dodge = 1.3; break; }  // he skips clear
        f.down = c.walk ? 1.4 : 2.0;
        f.dvz = Math.sign(c.vz) * (c.walk ? 2.0 : 6.0);
        Snd.crash();
        logLine(c.walk ? `${f.st.sn}が買い物客とぶつかって転倒！`
                       : `${f.st.sn}が車にはねられた！`, true);
        break;
      }
    }
  }
}

/* A runner flattened between the bags never gets there: he is out, and any run
   he was in the middle of scoring comes back off the board. */
function runOverRunner(m, walk) {
  if (m.retired) return;
  m.retired = true;
  for (let i = 0; i < 3; i++) if (G.bases[i] === m.p) G.bases[i] = null;
  if (m.scored) {
    G.score[G.half] = Math.max(0, G.score[G.half] - 1);
    G.inningRuns = Math.max(0, G.inningRuns - 1);
    if (m.rbiOwner) m.rbiOwner.rbi = Math.max(0, m.rbiOwner.rbi - 1);
    m.scored = false;
  }
  if (G.outs < 3) G.outs++;
  banner(walk ? `${m.p.name} 買い物客と衝突\nアウト！` : `${m.p.name} 車にはねられ\nアウト！`, true);
  logLine(walk ? `${m.p.name}が買い物客とぶつかってアウト！` : `${m.p.name}が車にはねられてアウト！`, true);
  uiScore();
}

/* ============================================================
   pitching
   ============================================================ */
function cpuPitchChoice() {
  const p = curPitcher();
  const behind = G.balls >= 2 && G.strikes < 2;
  const ahead = G.strikes === 2 || (G.strikes > G.balls);
  let ti = 0;
  if (behind) ti = chance(0.7) ? 0 : rint(1, 4);
  else if (ahead) ti = chance(0.72) ? rint(1, 4) : 0;
  else ti = rint(0, 4);
  // aim: ahead in the count -> chase pitch just off the plate
  const wide = ahead && chance(0.55);
  const ax = clamp(gauss(wide ? 0.44 : 0.36) + (wide ? (chance(0.5) ? 0.34 : -0.34) : 0), -0.85, 0.85);
  const ay = clamp(0.88 + gauss(wide ? 0.40 : 0.34) + (wide ? -0.18 : 0), 0.20, 1.66);
  const acc = 0.62 + p.arm * 0.38;
  let fx = ax + gauss((1 - acc) * 0.30), fy = ay + gauss((1 - acc) * 0.28);
  if (chance(0.10)) { fx += gauss(0.40); fy += gauss(0.38); }   // he misses his spot
  return { ti, ax: fx, ay: fy };
}

function throwPitch(ti, ax, ay) {
  const p = curPitcher();
  const P = PITCHES[ti];
  // no two pitches come out quite the same
  const spd = P.spd * (0.90 + p.arm * 0.16) * (1 + gauss(0.040));
  const T = 18.15 / spd;
  const slip = (1 - p.arm) * 0.11;             // even his own aim drifts a little
  const bx = P.bx * (1 + gauss(0.20)), by = P.by * (1 + gauss(0.20));
  const arrive = { x: clamp(ax + gauss(slip), -0.95, 0.95),
                   y: clamp(ay + gauss(slip), 0.22, 1.68) };
  const pf = G.fielders[0];
  G.pitch = {
    P, T, t: 0, ti, bx, by,
    x0: (pf ? pf.x : 0) + 0.46, y0: 1.92, z0: (pf ? pf.z : MOUND_POS[1]) - 0.16,
    tx: arrive.x - bx, ty: arrive.y - by,
    ax: arrive.x, ay: arrive.y,
    inZone: Math.abs(arrive.x) <= ZX + 0.05 && arrive.y >= ZY0 - 0.05 && arrive.y <= ZY1 + 0.05,
    // way inside and at body height: it is going to hit him unless he spins away
    hbp: arrive.x > 0.80 && arrive.y > 0.18 && arrive.y < 1.58 && chance(0.12),
  };
  G.swingT = -1; G.contactAt = -1; G.decided = null; G.batSwingT = -1;
  G.ball.vis = true; G.trail.length = 0; G.firstPitch = false;
  // in two-player games the hitter re-aims from scratch each pitch
  if (G.mode === 'vs') { G.reticle.x = 0; G.reticle.y = 0.88; }
  if (!humanBats()) cpuBatterDecide();
  Snd.blip();
  setPhase('pitch');
  if (G.mode === 'vs') uiHint();   // controls hand over to the hitter
}

function pitchPos(pc, t) {
  const u = clamp(t / pc.T, 0, 1.6);
  const k = Math.pow(Math.min(u, 1), pc.P.pw);
  return {
    x: lerp(pc.x0, pc.tx, u) + pc.bx * k,
    y: lerp(pc.y0, pc.ty, u) + pc.by * k - (u > 1 ? (u - 1) * 0.5 : 0),
    z: lerp(pc.z0, 0.15, u),
  };
}

function cpuBatterDecide() {
  const b = curBatter(), pc = G.pitch;
  const eye = 0.34 + b.contact * 0.5;
  let sw;
  if (pc.inZone) sw = chance(0.42 + eye * 0.32 + G.strikes * 0.09);
  else {
    const close = Math.abs(pc.ax) < ZX + 0.28 && pc.ay > ZY0 - 0.28 && pc.ay < ZY1 + 0.28;
    sw = chance((close ? 0.34 : 0.09) + (G.strikes === 2 ? (close ? 0.40 : 0.14) : 0) - eye * 0.12);
  }
  if (!sw) return;
  const jitter = 1.75 - b.contact * 0.65;
  G.swingT = pc.T - SWING_LAG + gauss(0.062 * jitter);
  G.cpuAim = {
    x: pc.ax + gauss(0.22 * jitter),
    y: pc.ay + gauss(0.20 * jitter),
  };
}

/* ============================================================
   the swing
   ============================================================ */
function playerSwing(bunt) {
  if (G.phase !== 'pitch' || G.swingT >= 0 || !humanBats()) return;
  G.swingT = G.pitch.t;
  G.bunting = !!bunt;
  G.batSwingT = 0;
  judgeSwing();
}

function judgeSwing() {
  const pc = G.pitch, b = curBatter();
  const contactT = G.swingT + SWING_LAG;
  const dt = contactT - pc.T;
  const aim = humanBats() ? G.reticle : G.cpuAim;
  const err = Math.hypot(pc.ax - aim.x, (pc.ay - aim.y) * 1.05);
  const tw = TIME_WIN * (0.80 + b.contact * 0.42) * (G.bunting ? 1.7 : 1);
  const mw = MEET_WIN * (0.80 + b.contact * 0.42) * (G.bunting ? 1.5 : 1);
  if (Math.abs(dt) > tw || err > mw) { G.decided = { miss: true }; return; }
  const qT = 1 - Math.abs(dt) / tw, qM = 1 - err / mw;
  const q = clamp(qT * 0.56 + qM * 0.44, 0, 1);
  G.decided = { miss: false, q, dt, err, dy: pc.ay - aim.y };
  G.contactAt = Math.max(contactT, pc.T * 0.97);
}

/* ============================================================
   ball flight simulation
   ============================================================ */
/* a snapshot of the traffic, advanced with the ball so the carom is part of
   the same simulation the ruling is read from */
function carsSnapshot() {
  return (G.traffic || []).map((c) => ({ x: c.x, z0: c.z, vz: c.vz, hw: c.hw, hh: c.hh, hl: c.hl }));
}

function simFlight(v0, laDeg, dirDeg, st) {
  const la = laDeg * DEG, dir = dirDeg * DEG;
  let x = BAT_X - 0.80, y = 1.05, z = BAT_Z + 0.17;
  const vh = v0 * Math.cos(la);
  let vx = vh * Math.sin(dir), vz = vh * Math.cos(dir), vy = v0 * Math.sin(la);
  const path = [];
  const cars = carsSnapshot();
  let carHit = 0;
  let t = 0, hr = false, ceilHit = false, apex = y, hang = 0, bounced = 0, groundIdx = -1;
  const dt = 1 / 90, drag = 0.0019;
  const wallTest = () => {
    const d = Math.hypot(x, z), a = angOf(x, z);
    if (Math.abs(a) > 50) return 0;
    const fd = fenceAt(st, a);
    if (d >= fd) return y > st.fenceH ? 2 : 1;
    return 0;
  };
  while (t < 11) {
    const sp = Math.hypot(vx, vy, vz);
    const k = drag * sp;
    vx -= vx * k * dt; vz -= vz * k * dt;
    vy -= (st.gravity + vy * k) * dt;
    x += vx * dt; y += vy * dt; z += vz * dt; t += dt;
    if (y > apex) apex = y;
    if (st.ceiling && y > st.ceiling - BALL_R && !ceilHit) {
      ceilHit = true; y = st.ceiling - BALL_R; vy = -Math.abs(vy) * 0.32; vx *= 0.6; vz *= 0.6;
    }
    if (y <= BALL_R) {
      if (!hang) hang = t;
      if (groundIdx < 0) groundIdx = path.length;
      y = BALL_R;
      if (bounced < 6 && Math.abs(vy) > 0.9) { vy = -vy * 0.36; vx *= 0.82; vz *= 0.82; bounced++; }
      else { vy = 0; vx -= vx * 1.15 * dt; vz -= vz * 1.15 * dt; }  // rolling friction
      if (Math.hypot(vx, vz) < 0.6) { path.push({ x, y, z, t }); break; }
    }
    if (carHit < 3) {
      for (const c of cars) {
        const cz = c.z0 + c.vz * t;
        if (Math.abs(x - c.x) >= c.hw + BALL_R || Math.abs(z - cz) >= c.hl + BALL_R || y >= c.hh + BALL_R) continue;
        const px = (c.hw + BALL_R) - Math.abs(x - c.x);
        const pz = (c.hl + BALL_R) - Math.abs(z - cz);
        const py = (c.hh + BALL_R) - y;
        if (py <= px && py <= pz) {                       // off the roof
          y = c.hh + BALL_R; vy = Math.abs(vy) * 0.45 + 2.2; vz += c.vz * 0.25;
        } else if (px < pz) {                             // off the flank
          const s2 = Math.sign(x - c.x) || 1;
          x = c.x + s2 * (c.hw + BALL_R);
          vx = s2 * (Math.abs(vx) * 0.55 + 3.5); vz += c.vz * 0.35; vy = Math.abs(vy) * 0.4 + 1.2;
        } else {                                          // off the nose or tail
          const s2 = Math.sign(z - cz) || 1;
          z = cz + s2 * (c.hl + BALL_R);
          vz = s2 * (Math.abs(vz) * 0.5 + 2.0) + c.vz * 0.55; vy = Math.abs(vy) * 0.4 + 1.5;
        }
        carHit++; groundIdx = groundIdx < 0 ? -1 : groundIdx;
        break;
      }
    }
    const w = st.fenceH > 0 ? wallTest() : 0;
    if (w === 2) { hr = true; path.push({ x, y, z, t }); break; }
    if (w === 1) { vx *= -0.32; vz *= -0.32; x += vx * dt * 2; z += vz * dt * 2; }
    path.push({ x, y, z, t });
  }
  if (!hang) hang = t;
  // where it first comes down — that is what fielders play
  let land = { x, z }, landT = t;
  for (const p of path) if (p.y <= BALL_R + 0.05) { land = { x: p.x, z: p.z }; landT = p.t; break; }
  const a = angOf(land.x, land.z);
  return {
    path, hang: landT, apex, hr, ceilHit, la: laDeg, dir: dirDeg, v0,
    groundIdx: groundIdx < 0 ? path.length : groundIdx, carHit,
    land, dist: Math.hypot(land.x, land.z), ang: a,
    finalDist: Math.hypot(x, z), finalX: x, finalZ: z, total: t,
    foul: Math.abs(a) > 45,
  };
}

/* ============================================================
   turning a batted ball into a baseball outcome
   ============================================================ */
const fielderOf = (team, k) => team.roster.find((r) => r.pos === k) || team.roster[0];

/* The first moment a fielder starting at (sx,sz) can put a glove on the ball.
   Only points below jumping height count, and he needs time to get there. */
function interceptOn(fl, sx, sz, spd) {
  const path = fl.path;
  for (let i = 0; i < path.length; i++) {
    const q = path[i];
    if (q.y > 2.6) continue;                       // still over his head
    const reach = 0.9 + spd * Math.max(0, q.t - 0.35) * 0.88;
    if (Math.hypot(q.x - sx, q.z - sz) <= reach)
      return { i, t: q.t, p: q, air: i < fl.groundIdx };
  }
  const i = path.length - 1;
  return { i, t: path[i].t, p: path[i], air: false, late: true };
}

/* transfer + throw, with a cut-off man on anything long */
function throwTime(from, tx, tz, arm) {
  const d = Math.hypot(from.x - tx, from.z - tz);
  return 0.55 + d / (27 + (arm || 0.6) * 13) + (d > 42 ? 1.05 : 0);
}

const LEAD_OFF = 2.6;              // how far a runner edges off the bag

/* seconds from contact for a runner to reach base n (1 = first) */
function baseTime(p, n) {
  const first = 27.43 / (5.6 + p.speed * 1.7);   // 4.9s slow .. 3.8s quick
  const rest = 27.43 / (7.6 + p.speed * 2.2);
  return first + (n - 1) * rest + (n > 1 ? 0.25 : 0);
}

/* which fielder covers a bag for the throw; if he is the one who fielded the
   ball, the usual back-up takes it instead */
const BACKUP = { '1B': 'P', '2B': 'SS', '3B': 'P', C: 'P', SS: '2B' };
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
}
const stationIdx = (k) => G.stations.findIndex((s) => s.k === k);

/* the ball squirts out of the glove and he has to go and get it */
const FUMBLE_T = 0.66;
function fumble(play, P) {
  const a = rnd(0, Math.PI * 2), d = rnd(2.2, 3.6);
  play.fumble = 1;
  play.fumbleTo = [P.x + Math.cos(a) * d, P.z + Math.sin(a) * d];
}

function fieldBall(fl) {
  const st = G.st, bat = curBatter(), def = fldTeam();

  if (fl.foul) return { kind: 'foul', text: 'ファウル' };
  if (fl.hr) {
    const far = fl.finalDist > fenceAt(st, fl.ang) * 1.22;
    return { kind: 'hr', bases: 4, big: true,
      text: far ? 'ホームラン！\n特大の一発だ' : 'ホームラン！' };
  }
  if (fl.ceilHit && st.ceiling && fl.dist >= fenceAt(st, fl.ang) * 0.94)
    return { kind: 'ground_rule', bases: 2, hit: true, text: '天井に当たった！\nエンタイトルツーベース' };
  if (st.fenceH === 0 && fl.dist >= fenceAt(st, fl.ang) && fl.la >= 14)
    return { kind: 'hr', bases: 4, big: true, text: 'ホームラン！\n川まで届いた' };

  /* who actually gets to it first */
  let best = null;
  const rest = fl.path[fl.path.length - 1];
  for (let i = 0; i < G.stations.length; i++) {
    if (G.fielders[i] && G.fielders[i].down > 0) continue;   // flattened by a car
    const s = G.stations[i], pl = fielderOf(def, s.k);
    // a pitcher fields comebackers and bunts, not gaps
    const spd = 6.0 * st.fielderSpeed * (0.86 + pl.defense * 0.28) * (s.k === 'P' ? 0.72 : 1);
    const fx = G.fielders[i] ? G.fielders[i].x : s.x;
    const fz = G.fielders[i] ? G.fielders[i].z : s.z;
    const it = interceptOn(fl, fx, fz, spd);
    // if nobody could cut it off, whoever is nearest where it stops goes and
    // gets it — otherwise the tie always fell to the pitcher
    const key = it.late ? 1e5 + dist2(fx, fz, rest.x, rest.z) : it.t;
    if (!best || key < best.key) best = { i, s, pl, spd, it, key };
  }
  let downNote = '';
  {
    let nd = null;
    for (let i = 0; i < G.stations.length; i++) {
      const st2 = G.stations[i], d = dist2(st2.x, st2.z, fl.land.x, fl.land.z);
      if (!nd || d < nd.d) nd = { i, d, sn: st2.sn };
    }
    if (nd && G.fielders[nd.i] && G.fielders[nd.i].down > 0 && nd.d < 22)
      downNote = `${nd.sn}が倒れている！\n`;
  }
  if (!best) {   // everybody is down — the ball just sits there
    const q = fl.path[fl.path.length - 1];
    return { kind: 'hit', bases: 3, hit: true, text: '誰も追いつけない！\nスリーベース',
             play: { fidx: 0, cutIdx: fl.path.length - 1, cutT: q.t,
                     pt: { x: q.x, y: q.y, z: q.z }, air: false, coverIdx: -1 } };
  }
  const P = best.it.p;
  const errP = clamp((1 - best.pl.defense) * 0.05
    + (st.id === 'market' ? 0.03 : 0) + (st.id === 'road' ? 0.025 : 0), 0, 0.13);
  const play = { fidx: best.i, cutIdx: best.it.i, cutT: best.it.t,
                 pt: { x: P.x, y: P.y, z: P.z }, air: best.it.air, moves: [] };
  /* someone has to be standing on the bag when the throw gets there */
  const sendTo = (bx, bz, fromPt, arm, after) => {
    const dur = throwTime(fromPt, bx, bz, arm);
    const ci = coverFor(bx, bz, play.fidx);
    if (ci >= 0 && ci !== play.fidx) {
      const st2 = G.stations[ci];
      const isC = st2.k === 'C';               // he sets up just behind the plate
      const tx2 = isC ? 0 : bx, tz2 = isC ? -1.1 : bz;
      // never drag someone clear across the diamond to take a routine lob
      if (dist2(st2.x, st2.z, tx2, tz2) < 34)
        play.moves.push({ idx: ci, x: tx2, z: tz2, byT: (after || play.cutT) + dur });
    }
    return dur;
  };
  const aimAt = (bx, bz) => {
    play.throwTo = [bx, bz];
    play.throwDur = sendTo(bx, bz, P, best.pl.arm);
  };

  /* ---- caught on the fly ---- */
  if (best.it.air) {
    if (chance(errP * 0.55)) {
      G.errs[1 - G.half]++;
      fumble(play, P);
      aimAt(BASE_POS[1][0], BASE_POS[1][1]);
      return { kind: 'error', bases: fl.dist > 62 ? 2 : 1, err: true, play,
               text: `${best.s.sn}が落球！\nエラー` };
    }
    const liner = fl.la < 24 && fl.hang < 1.7;
    const tight = best.it.t > fl.hang - 0.45;
    // an infielder just holds it; only an outfielder lobs the ball back in
    if (best.s.infield) { play.throwTo = null; play.throwDur = 0; }
    else aimAt(MOUND_POS[0], MOUND_POS[1]);
    return { kind: 'flyout', outs: 1, fielder: best.s, play,
      canSac: !liner && Math.hypot(P.x, P.z) > 48,
      text: liner ? `${best.s.sn}ライナー\nアウト`
        : (tight ? `${best.s.sn}が好捕！\nアウト` : `${best.s.sn}フライ\nアウト`) };
  }

  /* ---- played off the ground: race the throw to the bag ---- */
  let safeTo = 0;
  for (let n = 1; n <= 3; n++) {
    const arrives = best.it.t + throwTime(P, basePt(n - 1)[0], basePt(n - 1)[1], best.pl.arm);
    if (arrives > baseTime(bat, n) + 0.12) safeTo = n; else break;
  }
  const infield = best.s.infield;
  const outDist = Math.hypot(P.x, P.z);
  // nobody throws the batter out at first from deep in the outfield
  if (safeTo === 0 && !infield && outDist > 40) safeTo = 1;
  // once it is past the outfielders he is standing on second before the relay
  if (!infield && outDist > fenceAt(st, fl.ang) * 0.76 + 6) safeTo = Math.max(safeTo, 2);

  if (chance(errP)) {
    G.errs[1 - G.half]++;
    fumble(play, P);
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
    return { kind: 'error', bases: Math.max(1, safeTo), err: true, play,
             text: `${best.s.sn}がはじいた！\nエラー` };
  }

  if (safeTo === 0) {
    if (G.bases[0] && G.outs < 2 && infield && fl.v0 > 17
        && chance(0.34 + best.pl.defense * 0.28)) {
      // ball to the third-base side: the second baseman takes the bag and the
      // shortstop backs him up; to the first-base side it is the other way round
      const leftSide = fl.ang > 0;
      let pivotK = leftSide ? '2B' : 'SS', backK = leftSide ? 'SS' : '2B';
      if (stationIdx(pivotK) === best.i) { const t2 = pivotK; pivotK = backK; backK = t2; }
      const pivotI = stationIdx(pivotK), backI = stationIdx(backK);
      const pivotP = fielderOf(def, pivotK);
      const bag2 = BASE_POS[1], bag1 = BASE_POS[0];

      play.via = bag2;
      play.viaDur = throwTime(P, bag2[0], bag2[1], best.pl.arm);
      play.moves.push({ idx: pivotI, x: bag2[0], z: bag2[1], byT: play.cutT + play.viaDur });
      if (backI >= 0 && backI !== best.i)     // the other one converges as back-up
        play.moves.push({ idx: backI, x: bag2[0] + (leftSide ? 2.6 : -2.6), z: bag2[1] + 3.4,
                          byT: play.cutT + play.viaDur });
      play.throwTo = bag1;
      play.throwDur = throwTime({ x: bag2[0], z: bag2[1] }, bag1[0], bag1[1], pivotP.arm);
      const fbI = coverFor(bag1[0], bag1[1], best.i);
      if (fbI >= 0 && fbI !== best.i && fbI !== pivotI)
        play.moves.push({ idx: fbI, x: bag1[0], z: bag1[1],
                          byT: play.cutT + play.viaDur + play.throwDur });
      return { kind: 'dp', outs: 2, fielder: best.s, play,
               text: `${best.s.sn}→${pivotK === '2B' ? 'セカンド' : 'ショート'}→ファースト\nゲッツー！` };
    }
    if (G.bases[0] && G.outs < 2 && chance(0.22)) {
      aimAt(BASE_POS[1][0], BASE_POS[1][1]);
      return { kind: 'fc', outs: 1, fielder: best.s, play,
               text: `${best.s.sn}\nフィルダースチョイス` };
    }
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
    return { kind: 'groundout', outs: 1, fielder: best.s, play,
             text: `${best.s.sn}ゴロ\nアウト` };
  }

  /* ---- a base hit ---- */
  if (infield) {
    aimAt(BASE_POS[0][0], BASE_POS[0][1]);
  } else if (G.bases[1] || G.bases[2]) {
    aimAt(HOME_POS[0], HOME_POS[1]);        // a runner is coming round: back home
  } else if (safeTo === 2) {
    aimAt(BASE_POS[1][0], BASE_POS[1][1]);  // he is pulling into second: throw there
  } else {
    // never throw to the bag ahead of the runner from the outfield — a throw to
    // third on a triple only opens up the plate. It goes to the cut-off man.
    const d0 = Math.hypot(P.x, P.z) || 1;
    const rx = (P.x / d0) * 36, rz = (P.z / d0) * 36;
    let cutK = fl.ang > 0 ? 'SS' : '2B';
    if (stationIdx(cutK) === best.i) cutK = cutK === 'SS' ? '2B' : 'SS';
    const ci = stationIdx(cutK);
    play.throwTo = [rx, rz];
    play.throwDur = throwTime(P, rx, rz, best.pl.arm);
    if (ci >= 0 && ci !== best.i)
      play.moves.push({ idx: ci, x: rx, z: rz, byT: play.cutT + play.throwDur });
  }
  if (st.fenceH === 0 && safeTo === 3 && bat.speed > 0.72 && chance(0.22))
    return { kind: 'ihr', bases: 4, hit: true, big: true, play, text: 'ランニングホームラン！' };
  const carNote = fl.carHit ? '車に当たった！\n' : downNote;
  const text = carNote + (safeTo === 3 ? `${best.s.sn}へ\nスリーベースヒット！`
    : safeTo === 2 ? `${best.s.sn}へ\nツーベースヒット！`
    : infield ? '内野安打！'
    : outDist < 46 ? 'ポテンヒット！' : `${best.s.sn}前ヒット！`);
  return { kind: 'hit', bases: safeTo, hit: true, play, text };
}

/* ============================================================
   base running
   ============================================================ */
/* A runner follows the base paths and touches every bag on the way, so a man
   on first going to third rounds second instead of cutting the corner. */
function moveRunner(p, from, to, delay, retired) {
  const pts = [];
  for (let b = from; b <= to; b++) {
    let q = basePt(b);
    if (b === from && b >= 0 && b <= 2) {      // he was already off the bag
      const n2 = basePt(b + 1);
      const ux = n2[0] - q[0], uz = n2[1] - q[1], ul = Math.hypot(ux, uz) || 1;
      q = [q[0] + (ux / ul) * LEAD_OFF, q[1] + (uz / ul) * LEAD_OFF];
    }
    // bags he only rounds are taken a little wide, as a runner actually does
    if (b > from && b < to && b >= 0 && b <= 2) {
      const ox = q[0] - 0, oz = q[1] - 19.4, l = Math.hypot(ox, oz) || 1;
      pts.push([q[0] + (ox / l) * 1.7, q[1] + (oz / l) * 1.7]);
    } else pts.push([q[0], q[1]]);
  }
  if (pts.length < 2) pts.push(basePt(to));
  const segs = [];
  let total = 0;
  for (let i = 0; i < pts.length - 1; i++) {
    const d = Math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]);
    segs.push(d); total += d;
  }
  const legs = Math.max(1, to - from);
  // the first 90 feet take exactly as long as the ruling gives him, so a throw
  // that beats him is seen to beat him; later bases are compressed a little
  const first = 27.43 / (5.6 + p.speed * 1.7);
  const rest = 27.43 / (7.6 + p.speed * 2.2);
  let dur = first * (legs === 1 ? 1 : 0.72) + (legs - 1) * rest * 0.48;
  if (legs >= 4) dur = Math.min(dur, 6.0);
  G.movers.push({
    p, from, to, pts, segs, total, t: -(delay || 0), dur,
    scored: to >= 3, retired: !!retired,
    rbiOwner: to >= 3 ? curBatter() : null,
  });
}

function scoreRun(p, batter) {
  G.score[G.half]++;
  if (batter) batter.rbi++;
}

function advanceOnHit(nb, batter) {
  let runs = 0, block = null;
  for (let i = 2; i >= 0; i--) {
    const r = G.bases[i];
    if (!r) continue;
    let adv = nb;
    if (nb < 3 && r.speed > 0.5 && chance(0.22 + r.speed * 0.34)) adv++;
    let t = i + adv;
    if (block !== null) t = Math.min(t, block - 1);
    G.bases[i] = null;
    if (t >= 3) { runs++; scoreRun(r, batter); moveRunner(r, i, 3); }
    else { G.bases[t] = r; block = t; moveRunner(r, i, t); }
  }
  let bt = nb - 1;
  if (block !== null) bt = Math.min(bt, block - 1);
  if (bt >= 3) { runs++; scoreRun(batter, batter); moveRunner(batter, -1, 3); }
  else { G.bases[bt] = batter; moveRunner(batter, -1, bt); }
  return runs;
}

function advanceOnWalk(batter) {
  let runs = 0;
  if (G.bases[0]) {
    if (G.bases[1]) {
      if (G.bases[2]) { runs++; scoreRun(G.bases[2], batter); moveRunner(G.bases[2], 2, 3); G.bases[2] = null; }
      G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null;
    }
    G.bases[1] = G.bases[0]; moveRunner(G.bases[0], 0, 1); G.bases[0] = null;
  }
  G.bases[0] = batter; moveRunner(batter, -1, 0);
  return runs;
}

/* everyone still on base moves up one, lead runner first */
function advanceOneAll(batter, allowScore) {
  let runs = 0;
  for (let i = 2; i >= 0; i--) {
    const r = G.bases[i];
    if (!r) continue;
    G.bases[i] = null;
    if (i === 2) {
      if (allowScore) { runs++; scoreRun(r, batter); moveRunner(r, 2, 3); }
      else G.bases[2] = r;
    } else { G.bases[i + 1] = r; moveRunner(r, i, i + 1); }
  }
  return runs;
}

/* ============================================================
   applying an outcome
   ============================================================ */
function applyOutcome(o) {
  const bat = curBatter();
  let runs = 0, outsAdded = 0;
  G.movers = [];

  switch (o.kind) {
    case 'hr': case 'ihr':
      bat.ab++; bat.h++; bat.hr++; G.hits[G.half]++;
      runs = advanceOnHit(4, bat);
      Snd.cheer();
      break;
    case 'hit': case 'ground_rule':
      bat.ab++; bat.h++; G.hits[G.half]++;
      runs = advanceOnHit(o.bases, bat);
      Snd.good();
      break;
    case 'error':
      bat.ab++;
      runs = advanceOnHit(o.bases, bat);
      Snd.bad();
      break;
    case 'flyout': {
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);
      // a runner tagging up cannot leave until the ball is caught
      const held = o.play ? o.play.cutT + 0.12 : 1.2;
      if (o.canSac && G.outs < 2 && G.bases[2]) {
        runs++; scoreRun(G.bases[2], bat); moveRunner(G.bases[2], 2, 3, held); G.bases[2] = null;
        o.text = '犠牲フライ！\n1点';
      } else if (G.outs < 2 && G.bases[1] && o.canSac && chance(0.62)) {
        G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2, held); G.bases[1] = null;
      }
      Snd.mitt();
      break;
    }
    case 'groundout':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);
      // with the play going to first, everyone else moves up
      if (chance(0.86)) runs += advanceOneAll(bat, G.outs < 2 && chance(0.85));
      Snd.mitt();
      break;
    case 'fc':
      bat.ab++; outsAdded = 1;
      if (G.bases[2]) { runs++; scoreRun(G.bases[2], bat); moveRunner(G.bases[2], 2, 3); G.bases[2] = null; }
      if (G.bases[1]) { G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null; }
      G.bases[0] = bat; moveRunner(bat, -1, 0);
      Snd.mitt();
      break;
    case 'dp': {
      bat.ab++; outsAdded = Math.min(2, 3 - G.outs);
      const forced = G.bases[0];
      G.bases[0] = null;
      moveRunner(bat, -1, 0, 0, true);
      if (forced) moveRunner(forced, 0, 1, 0, true);
      runs += advanceOneAll(bat, G.outs < 2);
      if (G.bases[1]) { G.bases[2] = G.bases[1]; moveRunner(G.bases[1], 1, 2); G.bases[1] = null; }
      Snd.mitt();
      break;
    }
    case 'strikeout':
      bat.ab++; bat.k++; outsAdded = 1;
      Snd.miss();
      break;
    case 'walk':
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
      break;
    case 'bunt_out':
      bat.ab++; outsAdded = 1; moveRunner(bat, -1, 0, 0, true);
      runs += advanceOneAll(bat, G.outs < 2);
      break;
  }

  G.outs += outsAdded;
  if (runs > 0) {
    logLine(`${bat.name}の${o.kind === 'walk' ? '押し出し' : (o.text.split('\n')[0])} — ${runs}点`, true);
  }
  G.inningRuns += runs;
  G.lastText = o.text;
  banner(o.text, o.big);
  uiScore();

  // hand the ball back to the fielders
  placeFielders();
  return runs;
}

/* ============================================================
   count handling
   ============================================================ */
function afterPitch(kind) {
  const bat = curBatter();
  if (kind === 'hbp') {
    finishAtBat({ kind: 'hbp', text: 'デッドボール！' });
    return;
  }
  if (kind === 'ball') {
    G.balls++;
    if (G.balls >= 4) { finishAtBat({ kind: 'walk', text: 'フォアボール' }); return; }
    banner('ボール');
    uiScore(); setPhase('result', 0.70);
    return;
  }
  if (kind === 'strike' || kind === 'whiff' || kind === 'foul') {
    if (kind === 'foul' && G.strikes >= 2) { banner('ファウル'); uiScore(); setPhase('result', 0.70); return; }
    G.strikes++;
    if (G.strikes >= 3) {
      finishAtBat({ kind: 'strikeout', text: kind === 'whiff' ? '空振り三振！' : '見逃し三振！' });
      return;
    }
    banner(kind === 'whiff' ? '空振り' : kind === 'foul' ? 'ファウル' : 'ストライク');
    if (kind === 'whiff') Snd.miss();
    uiScore(); setPhase('result', 0.70);
  }
}

function finishAtBat(o) {
  applyOutcome(o);
  logLine(`${G.inning}回${G.half === 0 ? '表' : '裏'} ${curBatter().name}：${o.text.replace('\n', ' ')}`);
  G.order[G.half] = (G.order[G.half] + 1) % 9;
  if (!G.flight) G.ball.vis = false;   // a batted ball stays on screen
  setPhase('play', Math.max(1.5, playLength()));
}

function playLength() {
  let m = 1.4;
  for (const mv of G.movers) if (!mv.retired) m = Math.max(m, Math.min(mv.dur - mv.t + 0.5, 6.6));
  const pl = G.playScript;
  if (pl) m = Math.max(m, pl.cutT + (pl.fumble ? FUMBLE_T + 0.45 : 0)
                          + (pl.viaDur || 0) + (pl.via ? 0.28 : 0)
                          + (pl.throwDur || 0) + 0.7);
  else if (G.flight) m = Math.max(m, Math.min(G.flight.total, 5.0) + 0.8);
  return m;
}

/* ============================================================
   innings
   ============================================================ */
function endHalfInning() {
  let onBase = 0;
  for (const b of G.bases) if (b) onBase++;
  G.lob[G.half] += onBase;
  recordInningRuns(G.half, G.inning, G.inningRuns);
  G.inningRuns = 0;
  G.bases = [null, null, null];
  G.outs = 0;
  G.movers = [];
  logLine(`${G.inning}回${G.half === 0 ? '表' : '裏'}おわり — ${G.away.name} ${G.score[0]} : ${G.score[1]} ${G.home.name}`, true);

  if (G.half === 0) {
    G.half = 1;
    // home team leads after the top of the 9th or later: no need to bat
    if (G.inning >= G.innings && G.score[1] > G.score[0]) { endGame(); return; }
  } else {
    G.half = 0; G.inning++;
    if (G.inning > G.innings && G.score[0] !== G.score[1]) { endGame(); return; }
    if (G.inning > G.innings + 3) { endGame(); return; }   // three extra, then a tie
  }
  uiScore();
  banner(`${G.inning}回${G.half === 0 ? '表' : 'ウラ'}`);
  setPhase('halfend', 1.6);
}

function inningLine(half, inn) {
  while (G.lines[half].length < inn) G.lines[half].push(null);
}

function recordInningRuns(half, inn, runs) {
  inningLine(half, inn);
  G.lines[half][inn - 1] = (G.lines[half][inn - 1] || 0) + runs;
}

function endGame() {
  if (G.inningRuns > 0) { recordInningRuns(G.half, G.inning, G.inningRuns); G.inningRuns = 0; }
  G.over = true; G.active = false;
  setPhase('gameover', 0);
  showResult();
}

/* walk-off check after runs score in the bottom half */
function checkWalkoff() {
  if (G.half === 1 && G.inning >= G.innings && G.score[1] > G.score[0]) {
    logLine('サヨナラ！', true);
    banner('サヨナラ！', true);
    Snd.cheer();
    setPhase('walkoff', 2.1);
    return true;
  }
  return false;
}
