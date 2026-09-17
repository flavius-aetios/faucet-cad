"""Parametric dry docking adapter. Millimetres. See DESIGN.md before printing.

Run with the workspace Python. --view sends the model to OCP CAD Viewer.
All unmeasured dimensions are assumptions, not dimensions recovered from photos.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".runtime-cache" / "matplotlib"))
import cadquery as cq
from OCP.BRepTools import BRepTools

V = cq.Vector


def cylinder(radius, height, origin=(0, 0, 0), axis=(0, 0, 1)):
    return cq.Solid.makeCylinder(radius, height, V(*origin), V(*axis))


def section(center, normal, radius):
    return cq.Wire.makeCircle(radius, V(*center), V(*normal))


def make_model(p):
    angle = math.radians(p["correction_angle_deg"])
    if not 0 < angle <= math.radians(25):
        raise ValueError("Correction angle must be >0 and <=25 degrees.")
    socket_d = p["head_spigot_diameter"] + p["socket_diametral_clearance"]
    depth = p["head_spigot_height"] + p["socket_axial_clearance"]
    pin_d = p["outlet_bore_diameter"] - p["outlet_diametral_clearance"]
    outer_r = p["body_diameter"] / 2
    pin_h = p["upper_insertion_depth"]
    passage = p["upper_passage_diameter"]
    slot = p["side_slot_width"]
    chamfer = p["entry_chamfer"]
    assert socket_d > p["head_spigot_diameter"]
    assert outer_r - socket_d / 2 >= 2.0
    assert pin_d - passage >= 3.0
    assert p["connector_max_diameter"] < slot < passage < pin_d
    assert 0 < chamfer < pin_h
    radius = p["bend_height"] / math.sin(angle)
    frames = []
    for i in range(9):
        t = angle * i / 8
        frames.append(((radius * (1 - math.cos(t)), 0,
                        depth + radius * math.sin(t)),
                       (math.sin(t), 0, math.cos(t))))
    top, axis = frames[-1]

    body = cylinder(outer_r, depth).fuse(cq.Solid.makeLoft(
        [section(c, n, outer_r) for c, n in frames]))
    pin = cylinder(pin_d / 2, pin_h - chamfer, top, axis)
    tip_base = tuple(top[i] + axis[i] * (pin_h - chamfer) for i in range(3))
    tip = cq.Solid.makeCone(pin_d / 2, pin_d / 2 - chamfer,
                           chamfer, V(*tip_base), V(*axis))
    body = body.fuse(pin, tip)

    # A spacious cavity leaves the rigid connector free; only the lower socket
    # locates the head. The last sections narrow gradually to the upper bore.
    inner_wires = []
    for i, (c, n) in enumerate(frames):
        blend = max(0, (i - 5) / 3)
        r = (socket_d * (1 - blend) + passage * blend) / 2
        inner_wires.append(section(c, n, r))
    cavity = cylinder(socket_d / 2, depth + 1, (0, 0, -1))
    cavity = cavity.fuse(cq.Solid.makeLoft(inner_wires),
                         cylinder(passage / 2, pin_h + 1, top, axis))
    # Lead-in protects the edge of the metal head during insertion.
    cavity = cavity.fuse(cq.Solid.makeCone(socket_d / 2 + chamfer,
                        socket_d / 2, chamfer, V(0, 0, 0), V(0, 0, 1)))
    body = body.cut(cavity)

    # The lateral opening follows the same centreline as the body and pin.
    slot_frames = [((0, 0, -1), (0, 0, 1)), *frames,
                   (tuple(top[i] + axis[i] * (pin_h + 1) for i in range(3)), axis)]
    slot_wires = []
    for c, n in slot_frames:
        plane = cq.Plane(origin=c, xDir=(n[2], 0, -n[0]), normal=n)
        slot_wires.append(cq.Workplane(plane).center(0, 20).rect(slot, 40).val())
    body = body.cut(cq.Solid.makeLoft(slot_wires, ruled=True)).clean()
    return body, {"top": top, "axis": axis, "socket_diameter": socket_d,
                  "socket_depth": depth, "pin_diameter": pin_d}


def coupon(inner_d, outer_d, height, slot=13):
    ring = cylinder(outer_d / 2, height).cut(cylinder(inner_d / 2, height + 2, (0, 0, -1)))
    opening = cq.Workplane("XY").box(slot, outer_d, height + 2,
                                     centered=(True, False, False)).translate((0, 0, -1)).val()
    return ring.cut(opening).clean()


def stroke_label(text, center_y, digits=False):
    """Font-independent, constant-width lettering for the small print coupons."""
    width, xspan = 1.0, 2.4
    height = 4.4 if digits else 2.8
    a, b, c, d = (0, height), (xspan, height), (xspan, 0), (0, 0)
    left, right = (0, height/2), (xspan, height/2)
    segments = {"a": (a, b), "b": (b, right), "c": (right, c),
                "d": (d, c), "e": (d, left), "f": (left, a), "g": (left, right)}
    numbers = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd",
               "4": "fgbc", "5": "afgcd", "6": "afgecd", "7": "abc",
               "8": "abcdefg", "9": "abfgcd"}
    letters = {"I": [((xspan/2, 0), (xspan/2, height))],
               "N": [(d, a), (a, c), (c, b)],
               "O": [(a, b), (b, c), (c, d), (d, a)],
               "U": [(a, d), (d, c), (c, b)],
               "T": [(a, b), ((xspan/2, height), (xspan/2, 0))]}
    advances = [1.2 if ch == "." else xspan + width for ch in text]
    x = -(sum(advances) + 0.6 * (len(text)-1))/2
    y = center_y - (height + width)/2
    parts = []
    for ch, advance in zip(text, advances):
        if ch == ".":
            parts.append(cq.Workplane("XY", origin=(x+0.6, y+0.6, 1.9))
                         .rect(1.2, 1.2).extrude(0.9).val())
        else:
            strokes = [segments[s] for s in numbers[ch]] if ch in numbers else letters[ch]
            for start, end in strokes:
                dx, dy = end[0]-start[0], end[1]-start[1]
                origin = (x+width/2+(start[0]+end[0])/2,
                          y+width/2+(start[1]+end[1])/2, 1.9)
                parts.append(cq.Workplane("XY", origin=origin)
                             .slot2D(math.hypot(dx, dy)+width, width,
                                     math.degrees(math.atan2(dy, dx))).extrude(0.9).val())
        x += advance + 0.6
    return parts[0].fuse(*parts[1:]).clean()


def label_coupon(sample, diameter, kind, body_diameter):
    """Integral identification tab, behind the ring and clear of both fits."""
    center_y = -body_diameter / 2 - 5
    tab = (cq.Workplane("XY").center(0, center_y).rect(16, 14).extrude(2)
           .edges("|Z").fillet(1).val())
    result = sample.fuse(tab)
    # 1 mm strokes, 1.2 mm square dot, and 0.8 mm relief above the tab.
    for text, offset, digits in ((kind, 2.7, False), (f"{diameter:.1f}", -2.8, True)):
        lettering = stroke_label(text, center_y+offset, digits)
        bounds = lettering.BoundingBox()
        assert bounds.xmin > -7 and bounds.xmax < 7
        assert bounds.ymin > center_y-6 and bounds.ymax < center_y+6
        result = result.fuse(lettering)
    result = result.clean()
    # The additions must not change material anywhere inside the original ring
    # footprint, including either bore, the entry chamfer and the lateral slot.
    envelope = cylinder(body_diameter/2, sample.BoundingBox().zmax + 1)
    assert result.cut(sample).intersect(envelope).Volume() < 1e-6
    return result


def preview_labels(samples, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(10, 7), facecolor="#f3f5f7")
    for index, (label, sample) in enumerate(samples, 1):
        ax = fig.add_subplot(1, 2, index, projection="3d")
        ax.set_facecolor("#f3f5f7")
        vertices, triangles = sample.tessellate(0.03, 0.08)
        points = [v.toTuple() for v in vertices]
        faces = [[points[j] for j in t] for t in triangles]
        # Darken raised lettering only for readability in this illustration.
        colors = ["#634025" if all(v[1] < -15.5 and v[2] > 2.05 for v in f)
                  else "#f09b48" for f in faces]
        ax.add_collection3d(Poly3DCollection(faces, facecolors=colors, linewidth=0,
                                            shade=True))
        ax.set(xlim=(-18, 18), ylim=(-30, 18), zlim=(0, 25))
        ax.set_box_aspect((36, 48, 25))
        # A top view avoids painter-order artifacts over the small raised text.
        ax.view_init(elev=90, azim=-90)
        ax.set_proj_type("ortho")
        ax.set_axis_off()
        ax.set_title(label, fontsize=13)
    fig.suptitle("Маркировка образцов · вид сверху", fontsize=17)
    fig.text(0.5, 0.07, "IN — внутренний диаметр · OUT — наружный диаметр · Размеры в мм\n"
             "Штрих 1 мм · Рельеф 0,8 мм · Надписи затемнены только на иллюстрации.",
             ha="center", fontsize=11)
    fig.subplots_adjust(left=0, right=1, bottom=0.12, top=0.87)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def inspect_and_export(shape, path):
    if not shape.isValid() or len(shape.Solids()) != 1 or shape.Volume() <= 0:
        raise ValueError(f"Invalid solid: {path.name}")
    cq.exporters.export(shape, str(path) + ".step")
    # Remove any display triangulation before generating the print mesh.
    BRepTools.Clean_s(shape.wrapped)
    shape.exportStl(str(path) + ".stl", tolerance=0.005,
                    angularTolerance=0.03, relative=False)
    bounds = shape.BoundingBox()
    return {"valid_brep": True, "solid_count": 1,
            "volume_mm3": round(shape.Volume(), 2),
            "bounds_mm": [round(v, 3) for v in (bounds.xlen, bounds.ylen, bounds.zlen)]}


def make_references(p, meta):
    # Visual context only: lengths of the head and outlet are not measured.
    head = cylinder(p["head_body_diameter"] / 2, 65, (0, 0, -65)).fuse(
        cylinder(p["head_spigot_diameter"] / 2, p["head_spigot_height"]))
    outer = cylinder(p["body_diameter"] / 2, 30, meta["top"], meta["axis"])
    inner = cylinder(p["outlet_bore_diameter"] / 2, 32,
                     tuple(meta["top"][i] - meta["axis"][i] for i in range(3)), meta["axis"])
    return head, outer.cut(inner)


def preview(shape, refs, out, angle):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    fig = plt.figure(figsize=(13, 8), facecolor="#f3f5f7")
    for index, (title, azim, elev) in enumerate([
        ("Проставка • примерочная модель", 65, 23),
        ("Установка • условный вид сбоку", -90, 0)
    ], 1):
        ax = fig.add_subplot(1, 2, index, projection="3d", computed_zorder=False)
        ax.set_facecolor("#f3f5f7")
        pieces = [(shape, "#f08b36", 1.0)]
        if index == 2:
            pieces = [(refs[0], "#8293a3", 0.6), (refs[1], "#8293a3", 0.35), *pieces]
        for item, color, alpha in pieces:
            vertices, triangles = item.tessellate(0.12, 0.15)
            points = [v.toTuple() for v in vertices]
            poly = Poly3DCollection([[points[j] for j in t] for t in triangles],
                facecolors=color, linewidth=0, alpha=alpha,
                shade=True, zsort="average")
            ax.add_collection3d(poly)
        ax.view_init(elev=elev, azim=azim)
        ax.set_proj_type("ortho")
        ax.set_title(title, fontsize=13, pad=18)
        if index == 1:
            zmax = shape.BoundingBox().zmax + 3
            ax.set(xlim=(-21, 28), ylim=(-22, 22), zlim=(-1, zmax))
            ax.set_box_aspect((49, 44, zmax + 1))
        else:
            ax.set(xlim=(-35, 40), ylim=(-20, 20), zlim=(-73, 85))
            ax.set_box_aspect((75, 40, 158))
            ax.plot([0, 0], [0, 0], [-72, 72], "--", color="#487eab", linewidth=1)
        ax.set_xlabel("X, мм")
        ax.set_ylabel("Y, мм")
        ax.set_zlabel("Z, мм")
        if index == 2:
            ax.set_yticks([])
            ax.set_ylabel("")
        ax.grid(False)
    fig.suptitle(f"Поворот {angle:g}° — предварительный угол по фото", fontsize=17)
    fig.text(0.5, 0.03,
        "Оранжевый — печатная деталь. Серый — условная геометрия смесителя.\n"
        "Излив Ø22,5 мм. Посадка, удержание и угол требуют примерки.",
        ha="center", fontsize=11, color="#455262")
    fig.subplots_adjust(bottom=0.14, top=0.86, left=0.02, right=0.98)
    fig.savefig(out, dpi=160)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--parameters", type=Path, default=ROOT / "parameters.json")
    parser.add_argument("--view", action="store_true")
    args = parser.parse_args()
    p = json.loads(args.parameters.read_text(encoding="utf-8"))
    out = ROOT / "output"
    out.mkdir(exist_ok=True)
    shape, meta = make_model(p)
    report = {"status": "SOCKET_SAMPLE_CONFIRMED_PIN_FIT_PENDING", "parameters": p,
              "coupon_labels": {"stroke_width_mm": 1.0, "decimal_square_mm": 1.2,
                                "relief_mm": 0.8},
              "stl_export": {"linear_tolerance_mm": 0.005, "angular_tolerance_rad": 0.03},
              "derived": meta, "parts": {}}
    report["parts"]["adapter_prototype"] = inspect_and_export(shape, out / "adapter_prototype")
    labeled_samples = []
    for d in (meta["socket_diameter"],):
        name = f"socket_gauge_ID_{d:.1f}"
        sample = label_coupon(coupon(d, p["body_diameter"], 5, p["side_slot_width"]),
                              d, "IN", p["body_diameter"])
        report["parts"][name] = inspect_and_export(sample, out / name)
        report["parts"][name].update(label=f"IN {d:.1f}", fit_region_unchanged=True)
        labeled_samples.append((f"На лейку · IN {d:.1f}", sample))
    for index, d in enumerate(p["pin_test_diameters"]):
        if d <= p["upper_passage_diameter"] + 3 or d >= p["body_diameter"]:
            raise ValueError("Pin test diameter does not fit the coupon wall/flange.")
        name = f"pin_gauge_OD_{d:.1f}"
        h, chamfer = p["upper_insertion_depth"], p["entry_chamfer"]
        # Full insertion length: a short ring cannot validate pin retention.
        envelope = cylinder(d/2, h-chamfer).fuse(cq.Solid.makeCone(
            d/2, d/2-chamfer, chamfer, V(0, 0, h-chamfer), V(0, 0, 1)))
        sample = coupon(p["upper_passage_diameter"], d, h, p["side_slot_width"]).intersect(envelope)
        sample = sample.fuse(coupon(p["upper_passage_diameter"], p["body_diameter"],
                                    2, p["side_slot_width"]).translate((0, 0, -2))).clean()
        sample = sample.translate((0, 0, 2))
        sample = label_coupon(sample, d, "OUT", p["body_diameter"])
        report["parts"][name] = inspect_and_export(sample, out / name)
        report["parts"][name].update(label=f"OUT {d:.1f}", fit_region_unchanged=True)
        if index == 0:
            labeled_samples.append((f"В излив · OUT {d:.1f}", sample))
    refs = make_references(p, meta)
    assembly = cq.Assembly(name="REFERENCE_ASSEMBLY_DO_NOT_PRINT")
    assembly.add(shape, name="Adapter", color=cq.Color(0.95, 0.48, 0.12))
    assembly.add(refs[0], name="Head_approximate", color=cq.Color(0.5, 0.55, 0.6, 0.5))
    assembly.add(refs[1], name="Outlet_approximate", color=cq.Color(0.5, 0.55, 0.6, 0.4))
    assembly.export(str(out / "assembly_reference.step"))
    report["reference_intersection_mm3"] = [round(shape.intersect(r).Volume(), 6) for r in refs]
    (out / "geometry_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    preview(shape, refs, out / "preview.png", p["correction_angle_deg"])
    preview_labels(labeled_samples, out / "labeled_samples.png")
    print(json.dumps(report, indent=2))
    if args.view:
        from ocp_vscode import show
        show(shape, *refs, names=["Adapter prototype", "Head reference", "Outlet reference"],
             colors=["orange", "silver", "gray"], alphas=[1.0, 0.35, 0.3])


if __name__ == "__main__":
    main()
