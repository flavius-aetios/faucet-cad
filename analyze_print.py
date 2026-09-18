"""Geometric overhang audit of the exported adapter, not a slicer simulation."""
import argparse
import json
from pathlib import Path

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "output/flush_v2")
out = parser.parse_args().output_dir
report = json.loads((out / "geometry_report.json").read_text(encoding="utf-8"))
p = report["parameters"]
data = (out / "adapter_prototype.stl").read_bytes()
records = np.frombuffer(data, offset=84, dtype=np.dtype([
    ("normal", "<f4", 3), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")]))
v = records["vertices"].astype(float)
cross = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0])
norm = np.linalg.norm(cross, axis=1)
assert np.all(norm > 0)
nz = cross[:, 2] / norm
z = v[:, :, 2].mean(axis=1)
# Exclude the bed contact and the 0.6 mm lead-in chamfer at the bottom.
above_base = z > p["entry_chamfer"] + 0.01
downward = above_base & (nz < 0)
slopes = np.degrees(np.arcsin(np.clip(-nz[downward], 0, 1)))
steep = above_base & (nz < -np.sin(np.radians(45)))
worst = np.argmin(np.where(above_base, nz, 1))
socket_d = report["derived"]["socket_diameter"]
pin_d = report["derived"]["pin_diameter"]
analysis = {
    "method": "Triangle normals; slopes measured from vertical, 90 degrees is horizontal underside.",
    "limitations": "Geometry only, no slicing, extrusion paths, cooling, load or creep simulation.",
    "excluded_base_height_mm": p["entry_chamfer"] + 0.01,
    "max_downward_slope_above_base_deg": round(float(slopes.max()), 3),
    "downward_surface_over_45_deg_area_mm2": round(float(norm[steep].sum()/2), 3),
    "worst_triangle_center_mm": [round(float(x), 3) for x in v[worst].mean(axis=0)],
    "nominal_radial_wall_away_from_slot_rounds_mm": {
        "lower_socket": round((p["body_diameter"]-socket_d)/2, 3),
        "lower_entry_chamfer": round((p["body_diameter"]-socket_d)/2-p["entry_chamfer"], 3),
        "upper_pin": round((pin_d-p["upper_passage_diameter"])/2, 3),
        "upper_tip_chamfer": round((pin_d-p["upper_passage_diameter"])/2-p["entry_chamfer"], 3),
    },
    "nominal_slot_hose_clearance_mm": p["side_slot_width"]-p["hose_diameter"],
    "cad_volume_cm3": round(report["parts"]["adapter_prototype"]["volume_mm3"]/1000, 3),
}
(out / "print_analysis.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
print(json.dumps(analysis, indent=2))
