#!/bin/sh
out=animal-baseball.html
cat src/00-shell.html > $out
echo '<script>' >> $out
cat src/10-core.js src/20-world.js src/30-actors.js src/40-game.js src/50-main.js >> $out
echo '</script>' >> $out
echo "built $out"
