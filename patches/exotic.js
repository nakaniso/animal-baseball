/* ============================================================
   The odd ones out.

   Every mammal here is a round cartoon of an animal. These two are the animal:
   their shells come from tools/mesh2js.py, which lofts a salmon through real
   elliptical sections and sweeps a Trypoxylus horn along a curve that forks
   twice. Stacked spheres cannot make either shape.

   Neither has arms, and neither stands still.
     * The salmon has no limbs at all. It flops — in the box, in the field, on
       the base paths — and it hits with its body.
     * The beetle has six legs and hits with its horn. No bat, no glove.

   They keep the shared rig's anchors (torso y+0.74, head y+1.34) so the
   camera, the shadow, knockdowns and slides all still work on them.
   ============================================================ */

/* the flop. A fish out of water never holds still, so this drives everything:
   how high he is off the ground and how far he has rocked over. */
function fishHop(seed) {
  const t = clock * 4.3 + seed;
  return { up: Math.abs(Math.sin(t)) * 0.20, roll: Math.cos(t * 0.97) * 0.30 };
}

/* ---------- 鮭 ---------- */
function drawSalmon(f, A, look, p, y, big) {
  const flank = col(A.fur), back = col(A.back), belly = col(A.fur2);
  const finC = col(A.fin), jaw = col(A.jaw);
  const uni = col(look.uni), trim = col(look.trim);
  const h = p.fall ? { up: 0, roll: 0 } : fishHop(f.ry * 3.1);
  const by = y + h.up;
  const rx = (p.lean || 0) + h.roll;

  part(f, 'sal_body', 0, by, 0, 1, 1, 1, flank, rx);
  part(f, 'sal_back', 0, by, 0, 1, 1, 1, back, rx);
  part(f, 'sal_belly', 0, by, 0, 1, 1, 1, belly, rx);
  part(f, 'sal_fins', 0, by, 0, 1, 1, 1, finC, rx);
  part(f, 'sal_jaw', 0, by, 0, 1, 1, 1, jaw, rx);

  // the flush he gets on the run upriver, and the eyes — both solved against
  // the body profile in the baker, so they stay on the surface at any angle
  part(f, 'sal_blush', 0, by, 0, 1, 1, 1, col(A.blush), rx);
  part(f, 'sal_eye', 0, by, 0, 1, 1, 1, col('#D6C489'), rx);
  part(f, 'sal_pupil', 0, by, 0, 1, 1, 1, col('#0E0B09'), rx);

  // a band of team colour, worn like a sash. Any more and the fish is gone.
  part(f, 'sphere', 0, by + 0.74, 0.02, 0.235, 0.20, 0.50, uni, rx);
  part(f, 'sphere', 0, by + 0.85, 0.02, 0.205, 0.055, 0.44, trim, rx);
}

/* ---------- カブトムシ ---------- */
function drawBeetle(f, A, look, p, y, big) {
  const shell = col(A.fur), legC = col(A.leg), horn = col(A.horn);
  const uni = col(look.uni), trim = col(look.trim);
  const ln = p.lean || 0;
  const gloss = shade(A.fur, 1.5);

  // six legs. The front pair does the work, the middle pair does nothing, and
  // the back pair carries him — all three swing off the running cycle.
  const sw = p.legL || 0, sw2 = p.legR || 0, sp2 = p.spread || 0;
  const rows = [[0.20, 0.22, 1.00, 0.30], [0.23, 0.00, 0.55, 0.10], [0.22, -0.20, 0.20, -0.24]];
  for (const [lx, lz, k, fan] of rows) for (const s of [-1, 1]) {
    const sg = s < 0 ? sw : sw2;
    // femur out and down, then the tibia turns back under him — a beetle's
    // leg is a bent wire, not a peg
    const e = limb(f, s * (lx + sp2), y + 0.60, lz, sg * k * 0.5 - 0.55, s * (0.95 + fan),
                   0.26, 0.036, legC, null, 0);
    limb(f, e[0], e[1], e[2], sg * k + 0.70, s * 0.30, 0.30, 0.028, legC, legC, 0.06);
  }

  part(f, 'bee_elytra', 0, y, 0, 1, 1, 1, shell, ln);
  part(f, 'bee_prono', 0, y, 0, 1, 1, 1, shell, ln);
  part(f, 'bee_head', 0, y, 0, 1, 1, 1, shade(A.fur, 0.76), ln);
  part(f, 'bee_horn', 0, y, 0, 1, 1, 1, horn, ln);

  // the seam down the wing cases, and the sheen along the top of each
  part(f, 'box', 0, y + 0.66, -0.20, 0.020, 0.62, 0.30, shade(A.fur, 0.52), ln);
  for (const s of [-1, 1])
    part(f, 'sphere', s * 0.145, y + 0.90, -0.16, 0.11, 0.07, 0.16, gloss, ln);

  // compound eyes, flat and black and entirely unreadable
  part(f, 'bee_eye', 0, y, 0, 1, 1, 1, col('#120A05'), ln);
  part(f, 'bee_glint', 0, y, 0, 1, 1, 1, col('#75604A'), ln);

  // a band of team colour across the shield
  part(f, 'sphere', 0, y + 1.07, -0.02, 0.30, 0.10, 0.28, uni, ln);
  part(f, 'sphere', 0, y + 1.13, -0.02, 0.26, 0.045, 0.24, trim, ln);
}
