# Batting kit: hitters and runners wear a helmet with an ear flap on the side
# facing the pitcher, and batting gloves rather than bare paws.
import io, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def rd(p): return io.open(p, encoding='utf-8').read()
def wr(p, s): io.open(p, 'w', encoding='utf-8').write(s)

p = 'src/30-actors.js'; s = rd(p)

a = """  // cap
  part(fh, 'dome', 0, hy + 0.24, 0.01, 0.70 * big, 0.42, 0.66 * big, cap);
  part(fh, 'box', 0, hy + 0.235, 0.30, 0.44, 0.07, 0.30, cap);
  part(fh, 'sphere', 0, hy + 0.44, 0.01, 0.09, 0.09, 0.09, trim);"""
b = """  // headwear: a batting helmet at the plate and on the bases, otherwise a cap
  if (p.helmet) {
    part(fh, 'dome', 0, hy + 0.16, 0.01, 0.82 * big, 0.54, 0.80 * big, cap);
    part(fh, 'sphere', 0, hy + 0.14, 0.01, 0.82 * big, 0.34, 0.80 * big, cap);
    part(fh, 'box', 0, hy + 0.20, 0.34, 0.50, 0.075, 0.26, cap);
    // the flap covers the ear turned toward the pitcher (local +x)
    part(fh, 'sphere', 0.34 * big, hy + 0.02, 0.03, 0.15, 0.38, 0.42, cap);
    part(fh, 'box', 0, hy + 0.30, 0.10, 0.10, 0.06, 0.62, trim);
  } else {
    part(fh, 'dome', 0, hy + 0.24, 0.01, 0.70 * big, 0.42, 0.66 * big, cap);
    part(fh, 'box', 0, hy + 0.235, 0.30, 0.44, 0.07, 0.30, cap);
    part(fh, 'sphere', 0, hy + 0.44, 0.01, 0.09, 0.09, 0.09, trim);
  }"""
assert a in s, 'MISS helmet'
s = s.replace(a, b)

# batting gloves on the IK hands
a = """    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.088, uni, fur)
      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.088, uni, fur)
      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);"""
b = """    const poleL = p.pole || [0, -1, 0], poleR = p.pole || [0, -1, 0];
    const hand = p.gloveC ? col(p.gloveC) : fur;
    hl = p.handL
      ? armIK(slx, shY, slz, p.handL[0], p.handL[1], p.handL[2], BONE, BONE, poleL, 0.088, uni, hand)
      : limb(f, -0.33 * big, shY, 0, p.armL || 0, -0.30, 0.36, 0.095, uni, fur, 0.24);
    hr = p.handR
      ? armIK(srx, shY, srz, p.handR[0], p.handR[1], p.handR[2], BONE, BONE, poleR, 0.088, uni, hand)
      : limb(f, 0.33 * big, shY, 0, p.armR || 0, 0.30, 0.36, 0.095, uni, fur, 0.24);"""
assert a in s, 'MISS gloves'
s = s.replace(a, b)
wr(p, s)

# ---------- wire it up ----------
p = 'src/50-main.js'; s = rd(p)
a = """      handL: rig.handTop, handR: rig.handBot, pole: rig.pole,
      legL: rig.lgL, legR: rig.lgR, spread: rig.spread,
      lean: rig.lean, headRy: rig.head,
      bob: G.batSwingT < 0 ? bob * 0.5 : 0.015,"""
b = """      handL: rig.handTop, handR: rig.handBot, pole: rig.pole,
      legL: rig.lgL, legR: rig.lgR, spread: rig.spread,
      lean: rig.lean, headRy: rig.head,
      helmet: 1, gloveC: bt.trim,
      bob: G.batSwingT < 0 ? bob * 0.5 : 0.015,"""
assert a in s, 'MISS batter pose'
s = s.replace(a, b)

a = """    drawAnimal(r.x, r.z, r.ry, m.p.look, {
      armL: sw * 0.8, armR: -sw * 0.8, legL: sw, legR: -sw,
      bob: r.done ? 0 : Math.abs(Math.sin(clock * 15)) * 0.07, lean: 0.16,
    }, 0);"""
b = """    drawAnimal(r.x, r.z, r.ry, m.p.look, {
      armL: sw * 0.8, armR: -sw * 0.8, legL: sw, legR: -sw, helmet: 1,
      bob: r.done ? 0 : Math.abs(Math.sin(clock * 15)) * 0.07, lean: 0.16,
    }, 0);"""
assert a in s, 'MISS runner pose'
s = s.replace(a, b)

a = """    const b = BASE_POS[i];
    drawAnimal(b[0] * 1.06, b[1] - 1.15, Math.PI, p.look, { armL: 0.3, armR: -0.3, bob }, 0);"""
b = """    const b = BASE_POS[i];
    drawAnimal(b[0] * 1.06, b[1] - 1.15, Math.PI, p.look,
               { armL: 0.3, armR: -0.3, bob, helmet: 1 }, 0);"""
assert a in s, 'MISS onbase pose'
s = s.replace(a, b)
wr(p, s)
print('patched ok')
