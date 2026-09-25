#!/bin/sh
# Render every 3D logo with Blender (see render_blender.py). ~30-40 min on 4 CPU cores.
# Depth is in units of logo width = 10; wide layouts (horizontal, wordmark) have
# smaller letters, so they get a thinner body to keep the same visual thickness.
set -e
cd "$(dirname "$0")/.."
R="python3 tools/render_blender.py"
for spec in primary:0.32 primary-kr:0.32 horizontal:0.13 wordmark:0.18 symbol:0.32; do
  n=${spec%%:*}; d=${spec##*:}
  $R svg/foodridge-$n-black.svg 3d/foodridge-$n-3d.png --angle 0 --depth $d --width 3000 --samples 64
done
for spec in primary:0.24 primary-kr:0.24 horizontal:0.11; do
  n=${spec%%:*}; d=${spec##*:}
  $R svg/foodridge-$n-black.svg 3d/foodridge-$n-3d-angle.png --angle 18 --depth $d --width 3000 --samples 64
done
python3 tools/compose_icon_3d.py
