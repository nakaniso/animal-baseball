/* CPU同士の自動対戦をヘッドレスで回す — 開発ツール。ゲームのビルドには不要。
 *
 * CLAUDE.md の「検証のしかた」をブラウザなしで回すためのもの。
 * 本体（animal-baseball.html）をヘッドレスの Chromium で開き、
 * update(1/60) を回して試合を最後まで進める。
 *
 *   node tools/sim.js                 3・6・9回 × 5球場 × 3カードの完走チェック
 *   node tools/sim.js --stats 60      9回の試合を60本回して成績を出す（較正用）
 *   node tools/sim.js --stats 60 dome 球場を指定
 *
 * 出力は失敗項目と集計だけ。成績は9イニング換算・1チームあたり。
 * 1回の計測で判断しないこと（CLAUDE.md）。60本でも得点は±0.4ほど揺れる。
 */
const path = require('path');
const CHROME = process.env.CHROME_PATH ||
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const ARGS = ['--use-gl=angle', '--use-angle=swiftshader',
              '--enable-unsafe-swiftshader', '--no-sandbox'];
const GAME = 'file://' + path.join(__dirname, '..', 'animal-baseball.html');

function playwright() {
  try { return require('playwright'); }
  catch (e) { return require('/opt/node22/lib/node_modules/playwright'); }
}

/* runs inside the page */
function sweep() {
  const bad = [];
  const cards = [['bears', 'rabbits'], ['salmons', 'beetles'], ['frogs', 'penguins']];
  G.mode = 'auto';
  for (const N of [3, 6, 9]) {
    G.innings = N;
    for (const s of STADIUMS.map((x) => x.id)) {
      for (const [a, h] of cards) {
        startGame(s, a, h); let g = 0;
        while (!G.over && g < 900000) {
          g++; update(1 / 60);
          if (!isFinite(G.ball.x) || G.outs > 3 || G.score[0] < 0 || G.score[1] < 0) {
            bad.push({ N, s, a, why: 'state', outs: G.outs }); break;
          }
          const occ = G.bases.filter(Boolean);
          if (new Set(occ).size !== occ.length) { bad.push({ N, s, a, why: 'dup runner' }); break; }
        }
        const sum = G.lines.map((L) => L.reduce((x, y) => x + (y || 0), 0));
        if (g >= 900000) bad.push({ N, s, a, why: 'hang', phase: G.phase });
        if (sum[0] !== G.score[0] || sum[1] !== G.score[1]) bad.push({ N, s, a, why: 'linescore', sum, score: G.score.slice() });
        if (G.score[0] === G.score[1] && G.lines[0].length < N + 3) bad.push({ N, s, a, why: 'early tie' });
      }
    }
  }
  G.innings = 6; G.mode = 'cpu'; G.active = false; G.st = null;
  return bad;
}

function stats(n, park) {
  const cards = [['bears', 'rabbits'], ['salmons', 'beetles'], ['frogs', 'penguins'],
                 ['rabbits', 'salmons'], ['beetles', 'bears'], ['penguins', 'frogs']];
  const tot = { pa: 0, ab: 0, h: 0, hr: 0, k: 0, bb: 0, hbp: 0, r: 0, inn: 0,
                pitches: 0, strikes: 0, err: 0, dp: 0, sf: 0 };
  // count every pitch and whether it went for a strike (called, swung at, fouled
  // or put in play), by wrapping the functions the game already calls
  const _throw = throwPitch, _after = afterPitch, _contact = doContact;
  throwPitch = function () { tot.pitches++; return _throw.apply(this, arguments); };
  afterPitch = function (k) { if (k === 'strike' || k === 'whiff' || k === 'foul') tot.strikes++; return _after.apply(this, arguments); };
  doContact = function () {
    const r = _contact.apply(this, arguments);
    if (G.pendingCount !== 'foul') tot.strikes++;   // put in play
    return r;
  };
  G.mode = 'auto'; G.innings = 9;
  const parks = park ? [park] : STADIUMS.map((x) => x.id);
  for (let i = 0; i < n; i++) {
    const [a, h] = cards[i % cards.length];
    startGame(parks[i % parks.length], a, h);
    let g = 0;
    while (!G.over && g < 900000) { g++; update(1 / 60); }
    for (const t of [G.away, G.home]) for (const p of t.roster) {
      tot.ab += p.ab; tot.h += p.h; tot.hr += p.hr; tot.k += p.k; tot.bb += p.bb; tot.hbp += p.hbp;
    }
    tot.r += G.score[0] + G.score[1];
    tot.err += G.errs[0] + G.errs[1];
    tot.inn += G.lines[0].length + G.lines[1].filter((v) => v !== null).length;
  }
  throwPitch = _throw; afterPitch = _after; doContact = _contact;
  G.innings = 6; G.mode = 'cpu'; G.active = false; G.st = null;
  tot.pa = tot.ab + tot.bb + tot.hbp;
  const per9 = (v) => +(v / tot.inn * 9).toFixed(2);   // per team per 9 innings
  return {
    games: n, AVG: +(tot.h / tot.ab).toFixed(3),
    H: per9(tot.h), HR: per9(tot.hr), K: per9(tot.k), BB: per9(tot.bb), R: per9(tot.r),
    E: per9(tot.err),
    'P/PA': +(tot.pitches / tot.pa).toFixed(2),
    'STR%': +(tot.strikes / tot.pitches * 100).toFixed(1),
  };
}

(async () => {
  const argv = process.argv.slice(2);
  const browser = await playwright().chromium.launch({ executablePath: CHROME, args: ARGS });
  const page = await browser.newPage({ viewport: { width: 960, height: 600 } });
  const errs = [];
  page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error' && !/ERR_CERT|net::/.test(m.text())) errs.push(m.text()); });
  await page.goto(GAME);
  await page.waitForTimeout(1500);
  // the frame loop would advance the game underneath us; keep it out of the way
  await page.evaluate(() => { window.requestAnimationFrame = () => 0; });
  await page.waitForTimeout(200);
  if (argv[0] === '--stats') {
    const n = +(argv[1] || 60);
    await page.addScriptTag({ content: 'window.__stats = ' + stats.toString() });
    console.log(JSON.stringify(await page.evaluate(([n, p]) => __stats(n, p), [n, argv[2] || null])));
  } else {
    await page.addScriptTag({ content: 'window.__sweep = ' + sweep.toString() });
    const bad = await page.evaluate(() => __sweep());
    console.log(bad.length ? 'NG ' + JSON.stringify(bad) : 'OK 45 games');
  }
  if (errs.length) console.log('errors: ' + JSON.stringify(errs.slice(0, 8)));
  await browser.close();
})();
