#!/bin/sh
# Render every 3D logo with Blender (see render_blender.py). ~30-40 min on 4 CPU cores.
set -e
cd "$(dirname "$0")/.."
R="python3 tools/render_blender.py"
for n in primary primary-kr horizontal wordmark symbol; do
  $R svg/foodridge-$n-black.svg 3d/foodridge-$n-3d.png --angle 0 --width 3000 --samples 64
done
for n in primary primary-kr horizontal; do
  $R svg/foodridge-$n-black.svg 3d/foodridge-$n-3d-angle.png --angle 18 --width 3000 --samples 64
done
python3 tools/compose_icon_3d.py
