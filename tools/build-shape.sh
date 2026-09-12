# 造形ラボ — a development tool, not part of the game. Renders one animal from
# several angles into a single contact sheet, using the game's own renderer.
#   tools/shape-lab.html?a=bear&v=a     a=動物, v=セット(a/b/c/d)
# or drive it from the console without reloading:  LAB('bear', 'c')
out=tools/shape-lab.html
cat > $out <<'HTML'
<meta charset="utf-8"><title>造形ラボ</title>
<style>body{margin:0;background:#F2F4F6;font:13px system-ui}
#gl{width:600px;height:600px;position:fixed;left:-9999px;top:0}
#sheet{display:block;width:800px;max-width:100%}
#info{padding:6px 10px;color:#33414E;font-variant-numeric:tabular-nums}</style>
<canvas id="gl"></canvas><canvas id="sheet"></canvas><div id="info">…</div>
<script>
HTML
cat src/10-core.js src/15-meshes.js src/30-actors.js tools/shape-main.js >> $out
echo '</script>' >> $out
echo "built $out"
