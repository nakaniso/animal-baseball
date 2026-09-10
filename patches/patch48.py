import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
def edit(path, pairs):
    s = io.open(path, encoding='utf-8').read()
    for a, b, label in pairs:
        if a not in s: raise SystemExit('MISS %s: %s' % (path, label))
        s = s.replace(a, b, 1)
    io.open(path, 'w', encoding='utf-8').write(s)

exotic = io.open('patches/exotic.js', encoding='utf-8').read().strip()

edit('src/30-actors.js', [
# species
("""  panda:   {""",
 """  // Drawn as the real animal rather than a round cartoon of one, and given no
  // face cell, so they never change expression.
  salmon:  { ink: 0.013, body: 'fish', ear: 'none', tail: 'none', capY: -0.02,
             fur: '#B4C2CB', fur2: '#EFF2F0', back: '#3C5E71', blush: '#B0524C',
             fin: '#7F909B', spot: '#22323C', jaw: '#9DAAB2',
             head: 'sphere', hw: 0.60, hh: 0.78, hd: 1.30 },

  beetle:  { ink: 0.013, body: 'beetle', ear: 'none', tail: 'none', capY: -0.30,
             fur: '#3E2717', fur2: '#5C3C22', horn: '#20130A', leg: '#281A0E',
             head: 'rbox', hw: 0.66, hh: 0.50, hd: 0.66 },

  panda:   {""", 'species'),
# the models
("/* pose: { armL, armR, legL, legR, lean, bob, ry } — all radians */",
 exotic + "\n\n/* pose: { armL, armR, legL, legR, lean, bob, ry } — all radians */", 'models'),
# legs + torso branch
("""  // legs (local -x is the character's right side, +x their left)
  const sp = p.spread || 0;
  const pant = shade(look.uni, 0.93), shoe = shade(look.cap, 0.66);
  limb(f, -(0.155 * big + sp), y + 0.44, 0, p.legL || 0, -0.04, 0.36, 0.12, pant, shoe, 0.30, 1);
  limb(f, 0.155 * big + sp, y + 0.44, 0, p.legR || 0, 0.04, 0.36, 0.12, pant, shoe, 0.30, 1);
""",
 """  // legs (local -x is the character's right side, +x their left)
  const sp = p.spread || 0;
  const pant = A.body ? col(A.body === 'fish' ? A.fin : A.leg) : shade(look.uni, 0.93);
  const shoe = A.body ? pant : shade(look.cap, 0.66);
  const legR2 = A.body === 'beetle' ? 0.05 : 0.12;      // a beetle's leg is a wire
  const footS = A.body === 'beetle' ? 0.09 : 0.30;
  limb(f, -(0.155 * big + sp), y + 0.44, 0, p.legL || 0, -0.04, 0.36, legR2, pant, shoe, footS, 1);
  limb(f, 0.155 * big + sp, y + 0.44, 0, p.legR || 0, 0.04, 0.36, legR2, pant, shoe, footS, 1);
""", 'legs'),
# torso branch
("""  // torso
  part(f, 'sphere', 0, y + 0.74, 0, 0.66 * big, 0.70, 0.56 * big, uni, p.lean || 0);""",
 """  // torso
  if (A.body === 'fish') salmonBody(f, A, look, p, y, big);
  else if (A.body === 'beetle') beetleBody(f, A, look, p, y, big);
  else {
  part(f, 'sphere', 0, y + 0.74, 0, 0.66 * big, 0.70, 0.56 * big, uni, p.lean || 0);""", 'torso open'),
("""  part(f, 'sphere', 0, y + 0.515, 0.02, 0.60 * big, 0.10, 0.50 * big, shade(look.cap, 0.85));
""",
 """  part(f, 'sphere', 0, y + 0.515, 0.02, 0.60 * big, 0.10, 0.50 * big, shade(look.cap, 0.85));
  }
""", 'torso close'),
# head branch
("""  const HW = A.hw || 1, HH = A.hh || 1, HD = A.hd || 1;
  const hzF = 0.32 * HD + 0.02;                 // where the front of the face is
  part(fh, A.head || 'sphere', 0, hy, 0.02, 0.68 * big * HW, 0.66 * HH, 0.64 * big * HD, fur);
""",
 """  const HW = A.hw || 1, HH = A.hh || 1, HD = A.hd || 1;
  const hzF = 0.32 * HD + 0.02;                 // where the front of the face is
  if (A.body === 'fish') salmonHead(fh, A, look, p, hy, big);
  else if (A.body === 'beetle') beetleHead(fh, A, look, p, hy, big);
  else
  part(fh, A.head || 'sphere', 0, hy, 0.02, 0.68 * big * HW, 0.66 * HH, 0.64 * big * HD, fur);
""", 'head'),
# names
("  fox:     ['コン',",
 """  salmon:  ['サケオ', 'シャケ', 'ベニ', 'ソジロウ', 'アキアジ', 'トキシラズ', 'ハラス', 'イクラ', 'メジカ'],
  beetle:  ['カブト', 'ツノオ', 'クヌギ', 'ゲンジ', 'ムシタロウ', 'コクワ', 'ジュエキ', 'ヨナガ', 'カブオ'],
  fox:     ['コン',""", 'names'),
# teams
("""  { id: 'cats',     name: 'ねこじゃらしキャッツ', animal: 'cat', uni: '#F2C14E', trim: '#3A3630', cap: '#2E2A24',
    tag: 'CONTACT', desc: 'バットに当てるのがうまい。四球も選ぶ。', pow: 3, con: 5, spd: 3, def: 3 },""",
 """  { id: 'salmons',  name: 'そじょうサーモンズ', animal: 'salmon', uni: '#D8DEE2', trim: '#B0524C', cap: '#3C5E71',
    tag: 'CONTACT', desc: 'バットに当てるのがうまい。四球も選ぶ。', pow: 3, con: 5, spd: 3, def: 3 },""", 'salmons'),
("""  { id: 'foxes',    name: 'あかやまフォクシーズ', animal: 'fox',  uni: '#C4502E', trim: '#F6EFE2', cap: '#8E3A20',
    tag: 'PITCHING',desc: '投手陣が強力。変化球のキレがちがう。', pow: 3, con: 3, spd: 3, def: 4, arm: 5 },""",
 """  { id: 'beetles',  name: 'くぬぎカブトズ', animal: 'beetle', uni: '#6E5A3C', trim: '#D8C08A', cap: '#3E2717',
    tag: 'PITCHING',desc: '投手陣が強力。変化球のキレがちがう。', pow: 3, con: 3, spd: 3, def: 4, arm: 5 },""", 'beetles'),
])
print('patched ok')
