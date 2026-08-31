import io, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)

def rep(s, a, b, label):
    if a not in s:
        raise SystemExit('MISS: ' + label)
    return s.replace(a, b)

# ================= 20-world.js =================
p = '20-world.js'; s = rd(p)

s = rep(s, """function fenceAt(st, aDeg) {
  const t = clamp(Math.abs(aDeg) / 45, 0, 1);""",
"""function fenceAt(st, aDeg) {
  if (st.fenceFn) return st.fenceFn(aDeg);
  const t = clamp(Math.abs(aDeg) / 45, 0, 1);""", 'fenceFn')

# ---- ROAD ----
s = rep(s, """    desc: 'センターは高架の壁まで78m、両翼はビルまで40m。ライン際に引っぱれば安いホームランが出る。路上駐車の車にも当たる。',
    gravity: 9.8, fenceCenter: 78, fenceLine: 40, fenceH: 5.0, ceiling: 0,""",
"""    desc: '正面の高架壁まで88m。左右はビルがそのまま壁なので、引っぱるほどフェンスが近づく。ライン際なら57mでビルの窓へ。',
    gravity: 9.8, fenceCenter: 88, fenceLine: 57, fenceH: 9.0, ceiling: 0,
    fenceFn: (a) => Math.min(88, 40 / Math.max(0.10, Math.abs(Math.sin(a * DEG)))),""", 'road desc')
s = rep(s, "    quirk: '両翼40m。引っぱった打球はビルの窓へ',",
           "    quirk: '左右のビルが壁。引っぱるほどフェンスが近い',", 'road quirk')
s = rep(s, """        S.box(s * 15.5, 0.012, 45, 0.34, 0.02, 190, '#E8E8DE');
        S.box(s * 22, 0.16, 45, 5.5, 0.32, 200, '#8E9298');   // sidewalk
        S.box(s * 19.3, 0.2, 45, 0.4, 0.42, 200, '#B9BDC1');  // curb""",
"""        S.box(s * 26, 0.012, 45, 0.34, 0.02, 190, '#E8E8DE');
        S.box(s * 35, 0.16, 45, 7.0, 0.32, 210, '#8E9298');   // sidewalk
        S.box(s * 31.4, 0.2, 45, 0.4, 0.42, 210, '#B9BDC1');  // curb""", 'road sidewalk')
s = rep(s, "          const h = rnd(12, 30), w = rnd(10, 12.4), x = s * (26 + rnd(0, 2));",
           "          const h = rnd(14, 34), w = rnd(10, 12.4), x = s * (40 + rnd(0, 2.5));", 'road buildings')
s = rep(s, """      S.box(0, 5, 78, 62, 10, 2, '#7E8489');
      S.box(0, 10.6, 78, 62, 1.4, 3.2, '#666C71');
      for (let i = -4; i <= 4; i++) S.box(i * 7, 12, 78, 1.2, 2.6, 3.6, '#565C61');
      S.box(0, 3.2, 77, 26, 3.0, 0.3, '#2C5FA8');
      S.box(0, 3.2, 76.8, 22, 2.2, 0.2, '#EDF1F4');""",
"""      S.box(0, 5, 88, 84, 10, 2, '#7E8489');
      S.box(0, 10.6, 88, 84, 1.4, 3.2, '#666C71');
      for (let i = -5; i <= 5; i++) S.box(i * 7.6, 12, 88, 1.2, 2.6, 3.6, '#565C61');
      S.box(0, 3.4, 87, 26, 3.0, 0.3, '#2C5FA8');
      S.box(0, 3.4, 86.8, 22, 2.2, 0.2, '#EDF1F4');""", 'road overpass')
s = rep(s, """        addCar(S, -17.2, z, 0, pick(['#D9483B', '#3E6FBF', '#EFEFEF', '#2E3B45', '#E8B23A']));
        addCar(S, 17.2, z + 11, Math.PI, pick(['#48A96B', '#EFEFEF', '#B44D8C', '#3E6FBF']));""",
"""        addCar(S, -29, z, 0, pick(['#D9483B', '#3E6FBF', '#EFEFEF', '#2E3B45', '#E8B23A']));
        addCar(S, 29, z + 11, Math.PI, pick(['#48A96B', '#EFEFEF', '#B44D8C', '#3E6FBF']));""", 'road cars')
s = rep(s, """        S.cyl(s * 20, 3, 30, 0.16, 6, '#4A555F');
        S.box(s * 20, 6.2, 30, 0.7, 1.9, 0.5, '#2C3841');
        S.sph(s * 20, 6.7, 29.7, 0.2, '#E85A3A'); S.sph(s * 20, 6.2, 29.7, 0.2, '#E8C23A'); S.sph(s * 20, 5.7, 29.7, 0.2, '#5ECB7A');
        S.cyl(s * 20.6, 1.7, 62, 0.13, 3.4, '#4A555F');
        S.box(s * 20.6, 3.6, 62, 1.5, 1.1, 0.2, '#2E7D4F');""",
"""        S.cyl(s * 32, 3, 30, 0.16, 6, '#4A555F');
        S.box(s * 32, 6.2, 30, 0.7, 1.9, 0.5, '#2C3841');
        S.sph(s * 32, 6.7, 29.7, 0.2, '#E85A3A'); S.sph(s * 32, 6.2, 29.7, 0.2, '#E8C23A'); S.sph(s * 32, 5.7, 29.7, 0.2, '#5ECB7A');
        S.cyl(s * 32.6, 1.7, 62, 0.13, 3.4, '#4A555F');
        S.box(s * 32.6, 3.6, 62, 1.5, 1.1, 0.2, '#2E7D4F');""", 'road lights')

# ---- MARKET ----
s = rep(s, """    desc: '天井9m、冷凍ケースの壁まで46m。狭いのでホームランは出やすいが、天井直撃はエンタイトルツーベース。床がすべって守備は少し遅い。',
    gravity: 9.8, fenceCenter: 46, fenceLine: 34, fenceH: 3.4, ceiling: 9.0,""",
"""    desc: '天井が10.5mしかない。高く上げた打球は天井に当たって落ちてくるので、冷凍ケースの壁（中堅62m）を越えたければ低いライナーで運ぶしかない。床はすべる。',
    gravity: 9.8, fenceCenter: 62, fenceLine: 48, fenceH: 3.4, ceiling: 10.5,""", 'market desc')
s = rep(s, "    quirk: '天井直撃はエンタイトルツーベース／床がすべる',",
           "    quirk: '天井10.5m。ホームランは低いライナーだけ',", 'market quirk')
s = rep(s, """      S.plate(0, 9.0, 40, 200, 200, '#C4C7BE');
      for (let x = -4; x <= 4; x++) for (let z = 0; z <= 8; z++)
        S.box(x * 11, 8.8, z * 10 - 8, 8.4, 0.3, 1.2, '#FFF8DC');
      for (let x = -3; x <= 3; x += 3) S.box(x * 11, 8.3, 40, 1.6, 1.0, 120, '#AAB0AC');
      // side walls
      for (const s of [-1, 1]) {
        S.box(s * 40, 4.5, 40, 1.0, 9, 130, '#E6E7DF');
        for (let z = -10; z < 100; z += 16) S.box(s * 39.2, 2.2, z, 0.4, 4.4, 9, pick(['#5FB6C4', '#E8B23A', '#E8734A']));
      }""",
"""      S.plate(0, 10.5, 40, 230, 230, '#C4C7BE');
      for (let x = -4; x <= 4; x++) for (let z = 0; z <= 8; z++)
        S.box(x * 13, 10.3, z * 11 - 8, 9.4, 0.3, 1.2, '#FFF8DC');
      for (let x = -3; x <= 3; x += 3) S.box(x * 13, 9.7, 40, 1.6, 1.0, 140, '#AAB0AC');
      // side walls
      for (const s of [-1, 1]) {
        S.box(s * 54, 5.25, 40, 1.0, 10.5, 160, '#E6E7DF');
        for (let z = -10; z < 110; z += 16) S.box(s * 53.2, 2.4, z, 0.4, 4.8, 9, pick(['#5FB6C4', '#E8B23A', '#E8734A']));
      }""", 'market ceiling')
s = rep(s, "      for (const [sx, sz, len, rot] of [[-26, 30, 16, 0], [26, 30, 16, 0], [-14, 56, 13, 0], [14, 56, 13, 0], [0, 66, 15, Math.PI / 2]]) {",
           "      for (const [sx, sz, len, rot] of [[-32, 34, 16, 0], [32, 34, 16, 0], [-17, 52, 13, 0], [17, 52, 13, 0], [0, 50, 15, Math.PI / 2]]) {", 'market shelves')
s = rep(s, """      S.box(0, 6.6, -22, 26, 2.4, 0.5, '#E8734A');
      S.box(0, 6.6, -22.4, 22, 1.4, 0.3, '#FFF8E8');""",
"""      S.box(0, 7.6, -22, 26, 2.4, 0.5, '#E8734A');
      S.box(0, 7.6, -22.4, 22, 1.4, 0.3, '#FFF8E8');""", 'market sign')

# ---- MOON ----
s = rep(s, """    desc: '重力は地球の1/6。打球はとんでもなく飛ぶが、滞空時間も長いので外野に追いつかれやすい。フェンスは中堅150m。',
    gravity: 1.62, fenceCenter: 150, fenceLine: 126, fenceH: 3.0, ceiling: 0,""",
"""    desc: '重力は地球のおよそ半分。打球はよく伸びるがフェンスも中堅176mと遠く、滞空時間が1.4倍になるぶんフライは外野に追いつかれやすい。',
    gravity: 5.4, fenceCenter: 176, fenceLine: 146, fenceH: 3.0, ceiling: 0,""", 'moon desc')
s = rep(s, "    fog: '#1B2230', skyTint: '#3E4C66', gndTint: '#5A5A5E', fogDist: 420,",
           "    fog: '#1B2230', skyTint: '#3E4C66', gndTint: '#5A5A5E', fogDist: 560,", 'moon fog')
s = rep(s, "    quirk: '重力1/6。飛距離は伸びるが滞空時間も伸びる',",
           "    quirk: '低重力。飛距離も滞空時間も伸びる',", 'moon quirk')
s = rep(s, "        const x = rnd(-220, 220), z = rnd(-60, 260);",
           "        const x = rnd(-280, 280), z = rnd(-60, 320);", 'moon craters')
s = rep(s, "        const a = rnd(-Math.PI, Math.PI), e = rnd(0.08, 0.9), d = 460;",
           "        const a = rnd(-Math.PI, Math.PI), e = rnd(0.08, 0.9), d = 700;", 'moon stars')
s = rep(s, """      S.sph(-40, 110, 400, 34, '#3E6FA8');
      S.sph(-52, 118, 372, 13, '#5E9A5E'); S.sph(-22, 96, 376, 11, '#5E9A5E');
      S.sph(-34, 128, 374, 8, '#E4EAF2'); S.sph(-48, 92, 378, 7, '#E4EAF2');""",
"""      S.sph(-66, 158, 560, 48, '#3E6FA8');
      S.sph(-86, 172, 520, 19, '#5E9A5E'); S.sph(-36, 136, 526, 16, '#5E9A5E');
      S.sph(-56, 186, 522, 12, '#E4EAF2'); S.sph(-78, 130, 528, 11, '#E4EAF2');""", 'moon earth')
s = rep(s, "        const [x, z] = polar(a, 170);", "        const [x, z] = polar(a, 218);", 'moon base')
s = rep(s, """      S.cyl(0, 6, 176, 0.4, 12, '#B4BAC6');
      S.box(1.9, 11, 176, 3.6, 2.2, 0.12, '#D94A3A');""",
"""      S.cyl(0, 6, 206, 0.4, 12, '#B4BAC6');
      S.box(1.9, 11, 206, 3.6, 2.2, 0.12, '#D94A3A');""", 'moon flag')
wr(p, s)

# ================= 10-core.js =================
p = '10-core.js'; s = rd(p)
s = rep(s, "this.w / this.h, 0.35, 620)", "this.w / this.h, 0.35, 1100)", 'far plane')
wr(p, s)

# ================= 40-game.js =================
p = '40-game.js'; s = rd(p)
s = rep(s, """  if (fl.ceilHit && st.ceiling) {
    return { kind: 'ground_rule', bases: 2, text: '天井直撃！\\nエンタイトルツーベース', hit: true };
  }""",
"""  // indoors: a roof-scraper is dead only if it still carries to the wall
  if (fl.ceilHit && st.ceiling && fl.dist >= fenceAt(st, fl.ang) * 0.94) {
    return { kind: 'ground_rule', bases: 2, text: '天井に当たった！\\nエンタイトルツーベース', hit: true };
  }""", 'ceiling rule')
s = rep(s, "    const d = Math.abs(angOf(s.x, s.z) - fl.ang);",
           "    const d = Math.abs(angOf(s.x, s.z) - fl.ang) + (s.k === 'P' ? 8 : 0);", 'pitcher bias')
wr(p, s)

# ================= 50-main.js =================
p = '50-main.js'; s = rd(p)
s = rep(s, "ey = clamp(6 + b.y * 0.55, 6, 34);", "ey = clamp(6 + b.y * 0.55, 6, 46);", 'fly cam')
wr(p, s)

print('patched ok')
