#!/bin/sh
# src/ を連結して animal-baseball.html を出す。
#
# 連結するときにコメントだけの行と行頭の字下げを落とす。コメントはソースを
# 読む人のためのもので、遊ぶ人には要らない。これだけで約55KB減り、
# プレビューペインで開ける 512KB の天井までの余裕がそのぶん増える。
# 行の途中のコメントは触らない（'https://' のような文字列を壊さないため）し、
# 行をつなげもしないので、自動セミコロン挿入の結果も変わらない。
out=animal-baseball.html
strip() {
  awk '
    c { i = index($0, "*/"); if (!i) next
        c = 0; s = substr($0, i + 2); sub(/^[ \t]+/, "", s); if (s != "") print s; next }
    { s = $0; sub(/^[ \t]+/, "", s)
      if (s ~ /^\/\//) next
      if (s ~ /^\/\*/) {
        i = index(s, "*/"); if (!i) { c = 1; next }
        s = substr(s, i + 2); sub(/^[ \t]+/, "", s)
      }
      if (s != "") print s }' "$@"
}
cat src/00-shell.html > $out
echo '<script>' >> $out
strip src/10-core.js src/15-meshes.js src/20-world.js src/30-actors.js src/40-game.js src/50-main.js >> $out
echo '</script>' >> $out
echo "built $out ($(wc -c < $out) bytes)"
