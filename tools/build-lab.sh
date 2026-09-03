# 顔ラボ — a development tool, not part of the game. It reuses the game's
# renderer and character code so what you see here is what you get there.
out=tools/face-lab.html
cat tools/lab-shell.html > $out
echo '<script>' >> $out
cat src/10-core.js src/30-actors.js tools/lab-main.js >> $out
echo '</script>' >> $out
echo "built $out"
