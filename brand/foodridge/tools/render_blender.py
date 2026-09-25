"""FOODRIDGE photoreal 3D logo renderer (Blender / Cycles).

Imports a flat master SVG, extrudes it into a solid gold object with rounded
bevelled edges, lights it in a virtual studio and renders it through a real
perspective camera. Output is a transparent PNG.

Usage:
    python3 render_blender.py <svg> <out.png> [--angle DEG] [--tilt DEG]
                              [--width PX] [--samples N]
    --angle  camera yaw: 0 = straight on, 18 = side angle (left side nearer)
    --tilt   camera elevation in degrees (default 6)
Requires: pip install bpy   (Blender as a Python module)
"""
import argparse
import math
import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET

import bpy
import addon_utils
from mathutils import Vector

# Bright yellow gold, matched to the original FOODRIDGE artwork
GOLD_LINEAR = (1.0, 0.74, 0.27, 1.0)


def parse():
    p = argparse.ArgumentParser()
    p.add_argument("svg")
    p.add_argument("out")
    p.add_argument("--angle", type=float, default=0.0)
    p.add_argument("--tilt", type=float, default=6.0)
    p.add_argument("--width", type=int, default=3000)
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--depth", type=float, default=0.32, help="extrusion depth, logo width = 10")
    return p.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])


def _matrix(attr):
    """translate(a b) / scale(s) / matrix(...) -> affine tuple (xx, xy, yx, yy, dx, dy)."""
    m = (1, 0, 0, 1, 0, 0)
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", attr or ""):
        v = [float(x) for x in re.split(r"[ ,]+", args.strip())]
        if name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[-1], 0, 0)
        elif name == "matrix":
            t = tuple(v)
        else:
            raise ValueError(name)
        m = _mul(m, t)
    return m


def _mul(a, b):
    xx, xy, yx, yy, dx, dy = a
    return (xx * b[0] + yx * b[1], xy * b[0] + yy * b[1],
            xx * b[2] + yx * b[3], xy * b[2] + yy * b[3],
            xx * b[4] + yx * b[5] + dx, xy * b[4] + yy * b[5] + dy)


def union_svg(svg):
    """Merge every filled shape into one clean outline (no overlaps), so the
    extrusion has no stray faces where shapes cross (tower, hangers, cables)."""
    import pathops
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.svgLib.path.parser import parse_path

    root = ET.parse(svg).getroot()
    ns = "{http://www.w3.org/2000/svg}"
    merged = pathops.Path()

    def walk(el, m):
        m = _mul(m, _matrix(el.get("transform")))
        tag = el.tag.replace(ns, "")
        if tag == "path":
            one = pathops.Path()
            parse_path(el.get("d"), TransformPen(one.getPen(), m))
            one.simplify(fix_winding=True)
            merged.addPath(one)
        elif tag == "rect" and el.get("width") != "100%":
            x, y = float(el.get("x", 0)), float(el.get("y", 0))
            w, h = float(el.get("width")), float(el.get("height"))
            pen = TransformPen(merged.getPen(), m)
            pen.moveTo((x, y)); pen.lineTo((x + w, y)); pen.lineTo((x + w, y + h)); pen.lineTo((x, y + h))
            pen.closePath()
        for child in el:
            if child.tag.replace(ns, "") not in ("defs", "title"):
                walk(child, m)

    walk(root, (1, 0, 0, 1, 0, 0))
    merged.simplify(fix_winding=True)
    out = SVGPathPen(None)
    merged.draw(out)
    fd, path = tempfile.mkstemp(suffix=".svg")
    with os.fdopen(fd, "w") as fh:
        fh.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{root.get("viewBox")}" '
                 f'width="{root.get("width")}" height="{root.get("height")}">'
                 f'<path fill="#000" d="{out.getCommands()}"/></svg>')
    return path


def build_logo(svg, depth):
    addon_utils.enable("io_curve_svg")
    bpy.ops.import_curve.svg(filepath=union_svg(svg))
    curves = [o for o in bpy.data.objects if o.type == "CURVE"]
    # the black master's colour is irrelevant; everything gets one material
    for o in curves:
        o.select_set(True)
    bpy.context.view_layer.objects.active = curves[0]
    bpy.ops.object.join()
    logo = bpy.context.view_layer.objects.active

    # measure: bevel/extrude are set in SVG units so the result is width-10 based
    bb = [logo.matrix_world @ Vector(c) for c in logo.bound_box]
    w = max(v.x for v in bb) - min(v.x for v in bb)
    s = 10 / w

    cu = logo.data
    cu.dimensions = "2D"
    cu.fill_mode = "BOTH"
    cu.extrude = depth / 2 / s
    cu.bevel_mode = "ROUND"
    cu.bevel_depth = depth * 0.14 / s
    cu.offset = -depth * 0.10 / s  # pull the outline in so the bevel doesn't fatten thin strokes
    cu.bevel_resolution = 6
    cu.resolution_u = 24
    for sp in cu.splines:
        sp.use_smooth = True

    bpy.ops.object.convert(target="MESH")
    logo = bpy.context.view_layer.objects.active
    logo.scale = (s, s, s)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="BOUNDS")
    logo.location = (0, 0, 0)
    bpy.ops.object.shade_auto_smooth(angle=math.radians(35))
    logo.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(rotation=True)

    mat = bpy.data.materials.new("Foodridge Gold")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = GOLD_LINEAR
    bsdf.inputs["Metallic"].default_value = 1.0
    bsdf.inputs["Roughness"].default_value = 0.2
    logo.data.materials.clear()
    logo.data.materials.append(mat)
    return logo


def studio():
    """Soft studio: bright gradient environment + three softboxes for glints."""
    world = bpy.data.worlds.new("Studio")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.30, (0.22, 0.19, 0.15, 1)   # floor: soft dark
    els[1].position, els[1].color = 0.62, (1.0, 0.95, 0.85, 1)    # sky: bright warm
    mid = els.new(0.50)
    mid.color = (0.80, 0.72, 0.60, 1)                               # horizon band
    bg.inputs["Strength"].default_value = 1.5

    def area(name, loc, size, energy, rot_target=(0, 0, 0)):
        bpy.ops.object.light_add(type="AREA", location=loc)
        L = bpy.context.object
        L.name = name
        L.data.shape = "RECTANGLE"
        L.data.size, L.data.size_y = size
        L.data.energy = energy
        L.data.color = (1.0, 0.96, 0.9)
        d = Vector(rot_target) - Vector(loc)
        L.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    area("Key", (-7, -9, 7), (6, 3), 2500)
    area("Fill", (8, -8, 2), (4, 6), 900)
    area("Top", (0, -2, 10), (12, 2), 1200)


def camera(logo, yaw, tilt):
    bpy.ops.object.camera_add()
    cam = bpy.context.object
    cam.data.lens = 50
    bpy.context.scene.camera = cam
    d = 22
    y, t = math.radians(yaw), math.radians(tilt)
    # yaw > 0 swings the camera so the left side is nearer and the right recedes
    cam.location = (-d * math.sin(y) * math.cos(t), -d * math.cos(y) * math.cos(t), d * math.sin(t))
    cam.rotation_euler = (Vector((0, 0, 0)) - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    # frame the logo tightly, then back off for a margin
    deps = bpy.context.evaluated_depsgraph_get()
    pts = [c for v in logo.data.vertices for c in (logo.matrix_world @ v.co)]
    loc, _ = cam.camera_fit_coords(deps, pts)
    cam.location = loc + (loc - Vector((0, 0, 0))).normalized() * (loc.length * 0.12)
    return cam


def main():
    a = parse()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    logo = build_logo(a.svg, a.depth)
    studio()

    # aspect ratio from the logo silhouette
    bb = [logo.matrix_world @ Vector(c) for c in logo.bound_box]
    aspect = (max(v.x for v in bb) - min(v.x for v in bb)) / (max(v.z for v in bb) - min(v.z for v in bb))
    sc = bpy.context.scene
    sc.render.resolution_x = a.width
    sc.render.resolution_y = int(a.width / aspect * 1.15)
    camera(logo, a.angle, a.tilt)

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.filepath = a.out
    bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
