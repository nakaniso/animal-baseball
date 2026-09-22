/* 造形ラボと本体をヘッドレスで撮る — 開発ツール。ゲームのビルドには不要。
 *
 * 造形ラボは「ブラウザで開いて見る」前提で作ってあるが、手元にブラウザの
 * ない環境（リモートのセッションなど）では何も確認できない。Chromium を
 * 直接叩けば同じ絵が PNG で出るので、造形を触った側がその場で見られる。
 *
 *   node tools/shots.js bear acd out/      1体を指定セットで撮る
 *   node tools/shots.js --check            全種 × 全セットの glError だけ見る
 *   node tools/shots.js --game out/        本体を自動対戦で進めて撮る
 *
 * WebGL は SwiftShader で回るので GPU は要らない。1枚あたり1秒ほど。
 */
const path = require('path');
const CHROME = process.env.CHROME_PATH ||
  '/opt/pw-browsers/chromium-1194/chrome-linux/chrome';
const ARGS = ['--use-gl=angle', '--use-angle=swiftshader',
              '--enable-unsafe-swiftshader', '--no-sandbox'];
const ROOT = path.join(__dirname, '..');
const LAB = 'file://' + path.join(ROOT, 'tools/shape-lab.html');
const GAME = 'file://' + path.join(ROOT, 'animal-baseball.html');

function playwright() {
  try { return require('playwright'); }
  catch (e) { return require('/opt/node22/lib/node_modules/playwright'); }
}

async function open(browser, url, w, h) {
  const page = await browser.newPage({ viewport: { width: w, height: h } });
  const errs = [];
  page.on('pageerror', (e) => errs.push('PAGEERROR ' + e.message));
  page.on('console', (m) => { if (m.type() === 'error') errs.push(m.text()); });
  await page.goto(url);
  await page.waitForTimeout(2500);
  return { page, errs };
}

async function sheets(browser, animal, sets, outDir) {
  const { page, errs } = await open(browser, LAB + '?a=' + animal + '&v=' + sets[0], 1100, 1200);
  for (const v of sets) {
    await page.evaluate(([a, s]) => window.LAB(a, s), [animal, v]);
    await page.waitForTimeout(700);
    const file = path.join(outDir, animal + '-' + v + '.png');
    await (await page.$('#sheet')).screenshot({ path: file });
    console.log(file);
  }
  console.log(await page.textContent('#info'));
  if (errs.length) console.log('errors: ' + JSON.stringify(errs.slice(0, 8)));
}

/* every species through every pose set, reporting only what went wrong —
   the sweep CLAUDE.md asks for after touching a character */
async function check(browser) {
  const { page, errs } = await open(browser, LAB + '?a=bear&v=a', 1100, 1200);
  const bad = await page.evaluate(() => {
    const out = [];
    for (const name in ANIMALS) {
      if (!LOOKS[name]) continue;
      for (const v of ['a', 'b', 'c', 'd', 'e', 'f']) {
        window.LAB(name, v);
        const e = R.gl.getError();
        if (e) out.push(name + '/' + v + ' glError ' + e);
      }
    }
    return out;
  });
  console.log(JSON.stringify({ ok: !bad.length && !errs.length, bad, errs }));
}

async function game(browser, outDir) {
  const { page, errs } = await open(browser, GAME, 1000, 640);
  if (await page.evaluate(() => R.gl === false)) {
    console.log('R.gl === false — 起動に失敗している');
    return;
  }
  for (const [n, frames] of [['1', 300], ['2', 1200]]) {
    await page.evaluate((f) => {
      G.mode = 'auto'; G.innings = 3;
      if (f === 300) startGame('dome', 'bears', 'rabbits');
      for (let i = 0; i < f; i++) update(1 / 60);
      show(null);                       // the menu overlay sits on top otherwise
    }, frames);
    await page.waitForTimeout(800);
    const file = path.join(outDir, 'game' + n + '.png');
    await page.screenshot({ path: file });
    console.log(file);
  }
  if (errs.length) console.log('errors: ' + JSON.stringify(errs.slice(0, 8)));
}

(async () => {
  const { chromium } = playwright();
  const browser = await chromium.launch({ executablePath: CHROME, args: ARGS });
  const a = process.argv.slice(2);
  if (a[0] === '--check') await check(browser);
  else if (a[0] === '--game') await game(browser, a[1] || '.');
  else await sheets(browser, a[0] || 'bear', (a[1] || 'a').split(''), a[2] || '.');
  await browser.close();
})();
