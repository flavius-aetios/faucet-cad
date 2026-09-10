"""Measure the curved outer surface and its STL approximation (millimetres)."""
import argparse
import json
import math
import struct
import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Surface

from model import ROOT, section


def measure(p, mesh):
    angle = math.radians(p["correction_angle_deg"])
    depth = p["head_spigot_height"] + p["socket_axial_clearance"]
    radius = p["bend_height"] / math.sin(angle)
    tube_r = p["body_diameter"] / 2

    def deviation(point):
        x, y, z = point
        return abs(math.hypot(math.hypot(x - radius, z - depth) - radius, y) - tube_r)

    frames = []
    for i in range(9):
        t = angle * i / 8
        frames.append(((radius * (1 - math.cos(t)), 0, depth + radius * math.sin(t)),
                       (math.sin(t), 0, math.cos(t))))
    outer = cq.Solid.makeLoft([section(c, n, tube_r) for c, n in frames])
    surface = next(f for f in outer.Faces() if f.geomType() != "PLANE")
    adaptor = BRepAdaptor_Surface(surface.wrapped)
    cad_errors = []
    for i in range(101):
        u = adaptor.FirstUParameter() + (adaptor.LastUParameter()-adaptor.FirstUParameter())*i/100
        for j in range(41):
            v = adaptor.FirstVParameter() + (adaptor.LastVParameter()-adaptor.FirstVParameter())*j/40
            pt = adaptor.Value(u, v)
            cad_errors.append(deviation((pt.X(), pt.Y(), pt.Z())))

    data = mesh.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    errors = []
    outer_triangles = 0
    for k in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50*k)
        pts = [row[i:i+3] for i in (3, 6, 9)]
        if all(deviation(pt) < 0.0001 for pt in pts):
            outer_triangles += 1
            # Edge midpoints and centroid measure the polygon's chord error.
            samples = [tuple(sum(pt[i] for pt in pts)/3 for i in range(3))]
            samples += [tuple((pts[a][i]+pts[b][i])/2 for i in range(3))
                        for a, b in ((0, 1), (1, 2), (2, 0))]
            errors.extend(deviation(pt) for pt in samples)
    assert outer_triangles > 0
    return {"cad_surface_type": surface.geomType(), "cad_samples": len(cad_errors),
            "cad_max_sampled_deviation_from_ideal_bend_mm": max(cad_errors),
            "stl_total_triangles": count, "stl_outer_bend_triangles": outer_triangles,
            "stl_max_sampled_chord_error_mm": max(errors),
            "note": "Sampled comparison to the ideal circular bend; not a certified global error bound."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="current")
    args = parser.parse_args()
    params = json.loads((ROOT / "parameters.json").read_text(encoding="utf-8"))
    path = ROOT / "output" / "surface_quality.json"
    report = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    report[args.label] = measure(params, ROOT / "output" / "adapter_prototype.stl")
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
