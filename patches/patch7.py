# Narrow-screen pass: a scorebug that fits 375px, hints that stay on one row and
# clear of the batter card, and a batting camera that backs off on tall screens.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)
def rep(s, a, b, label):
    if a not in s: raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

p = 'src/00-shell.html'; s = rd(p)
s = rep(s, """@media (max-width:900px){
  #log{display:none} .countbox{transform:scale(.86);transform-origin:top left}
  .scorebug{font-size:13px} .sb-team{min-width:100px} .sb-nm{font-size:11px}
  #hint{max-width:94vw} #batter{transform:scale(.9);transform-origin:bottom left}
}""",
"""@media (max-width:900px){
  #log{display:none} .countbox{transform:scale(.86);transform-origin:top left}
  .scorebug{font-size:13px} .sb-team{min-width:100px} .sb-nm{font-size:11px}
  #hint{max-width:94vw} #batter{transform:scale(.9);transform-origin:bottom left}
}
@media (max-width:560px){
  .scorebug{top:10px;font-size:12px}
  .sb-team{min-width:0;padding:6px 8px;gap:5px}
  .sb-nm{font-size:10px;max-width:70px}
  .sb-run{font-size:18px;min-width:20px}
  .sb-inn{padding:5px 9px;min-width:46px}
  .sb-inn .n{font-size:17px} .sb-inn .h{font-size:8px}
  .countbox{top:56px;left:10px;padding:8px 10px;gap:10px;transform:none}
  .diamond{width:44px;height:44px} .diamond span{width:14px;height:14px}
  /* the batter card moves under the count so the hints keep the bottom row */
  #batter{top:56px;left:auto;right:10px;bottom:auto;transform:none;min-width:0;
    max-width:44vw;padding:8px 10px}
  #batter .who{font-size:14px} #batter .meta{display:none}
  #hint{bottom:10px;gap:5px;max-width:96vw}
  .key{padding:5px 8px;font-size:10.5px;gap:5px}
  .key kbd{font-size:9.5px;padding:2px 5px}
  #pitchpick{bottom:52px;gap:4px}
  .pc{padding:5px 8px;font-size:11px} .pc small{font-size:8.5px}
  #banner{top:38%}
}""", 'mobile css')
wr(p, s)

p = 'src/50-main.js'; s = rd(p)
# on a portrait screen, back the camera off so the catcher does not fill the frame
s = rep(s, """    ex = 0.55; ey = 4.6; ez = -9.0;
    tx = 0; ty = 0.4; tz = 7.0; fov = 40; sp = 5;""",
"""    const tall = clamp(1.25 - R.w / R.h, 0, 0.5);   // >0 once the view goes portrait
    ex = 0.55; ey = 4.6 + tall * 3.2; ez = -9.0 - tall * 5.0;
    tx = 0; ty = 0.4 + tall * 0.5; tz = 7.0; fov = 40; sp = 5;""", 'portrait cam')
# touch devices get touch wording
s = rep(s, """  const keys = mine
    ? [['矢印 / マウス', 'ねらう'], ['SPACE', 'スイング'], ['SHIFT+SPACE', 'バント']]
    : [['1〜5', '球種'], ['矢印 / マウス', 'コース'], ['SPACE', '投げる']];""",
"""  const touch = matchMedia('(pointer:coarse)').matches;
  const keys = mine
    ? (touch ? [['ドラッグ', 'ねらう'], ['タップ', 'スイング']]
             : [['矢印 / マウス', 'ねらう'], ['SPACE', 'スイング'], ['SHIFT+SPACE', 'バント']])
    : (touch ? [['球種ボタン', 'えらぶ'], ['ドラッグ', 'コース'], ['タップ', '投げる']]
             : [['1〜5', '球種'], ['矢印 / マウス', 'コース'], ['SPACE', '投げる']]);""", 'touch hints')
wr(p, s)
print('patched ok')
