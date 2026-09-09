"""Check STEP roundtrip and closed, consistently wound STL triangle meshes."""
import collections
import json
import math
import struct
from pathlib import Path

import cadquery as cq

out = Path(__file__).resolve().parent / "output"
report = json.loads((out / "geometry_report.json").read_text(encoding="utf-8"))
checks = {}
for name, metrics in report["parts"].items():
    shape = cq.importers.importStep(str(out / (name + ".step"))).val()
    assert shape.isValid() and len(shape.Solids()) == 1, name
    assert abs(shape.Volume() - metrics["volume_mm3"]) < 0.02, name
    data = (out / (name + ".stl")).read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + count * 50, name
    edges = collections.Counter()
    directed = collections.Counter()
    vertices = {}
    adjacency = collections.defaultdict(set)
    signed_volume = 0.0
    for k in range(count):
        row = struct.unpack_from("<12fH", data, 84 + 50 * k)
        points = [tuple(row[i:i + 3]) for i in (3, 6, 9)]
        assert all(math.isfinite(v) for p in points for v in p), name
        ids = [vertices.setdefault(p, len(vertices)) for p in points]
        assert len(set(ids)) == 3, (name, "degenerate triangle")
        a, b, c = points
        signed_volume += (a[0]*(b[1]*c[2]-b[2]*c[1]) +
                          a[1]*(b[2]*c[0]-b[0]*c[2]) +
                          a[2]*(b[0]*c[1]-b[1]*c[0])) / 6
        for i, j in zip(ids, ids[1:] + ids[:1]):
            edges[tuple(sorted((i, j)))] += 1
            directed[(i, j)] += 1
            adjacency[i].add(j)
            adjacency[j].add(i)
    assert all(n == 2 for n in edges.values()), (name, "open or non-manifold mesh")
    assert all(directed[(i, j)] == directed[(j, i)] == 1 for i, j in edges), name
    visited = set()
    todo = [0]
    while todo:
        i = todo.pop()
        if i not in visited:
            visited.add(i)
            todo.extend(adjacency[i] - visited)
    assert len(visited) == len(vertices), (name, "disconnected mesh")
    assert signed_volume > 0, (name, "inverted surface")
    assert abs(signed_volume - shape.Volume()) / shape.Volume() < 0.005, name
    checks[name] = {"step_valid": True, "triangles": count,
                    "closed_manifold": True, "consistent_winding": True,
                    "connected_components": 1, "mesh_volume_mm3": round(signed_volume, 2)}
(out / "export_validation.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
print(json.dumps(checks, indent=2))
