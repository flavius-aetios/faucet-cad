"""Exercise both native solvers and CadQuery in child processes; check real exit codes."""
import json
import subprocess
import sys
from pathlib import Path

cases = {
    "native_solvers": """
import casadi as ca
import nlopt
import numpy as np
opt = nlopt.opt(nlopt.LN_NELDERMEAD, 1)
opt.set_min_objective(lambda x, grad: (x[0] - 2.0)**2)
opt.set_xtol_rel(1e-7)
assert abs(opt.optimize([0.0])[0] - 2.0) < 1e-5
x = ca.SX.sym('x')
f = ca.Function('f', [x], [x*x])
assert float(f(3)) == 9.0
print('CasADi', ca.__version__, 'NLopt', nlopt.__version__)
""",
    "cadquery_and_viewer_import": """
import cadquery as cq
import ocp_vscode
part = cq.Workplane('XY').box(10, 10, 10).hole(4)
assert part.val().isValid()
assert len(part.solids().vals()) == 1
print('CadQuery', cq.__version__, 'solid valid')
""",
}
results = []
for name, body in cases.items():
    # Applies only to a diagnostic child: prevents modal OS dialogs but does not
    # hide a crash or change its exit code. Normal model.py does not use this.
    prefix = "import sys\nif sys.platform == 'win32':\n import ctypes\n ctypes.windll.kernel32.SetErrorMode(3)\n"
    result = subprocess.run([sys.executable, "-c", prefix + body], capture_output=True,
                            text=True, timeout=45, cwd=Path(__file__).resolve().parent)
    results.append({"check": name, "exit_code": result.returncode,
                    "stdout": result.stdout.strip(), "stderr": result.stderr.strip()})
out = Path(__file__).resolve().parent / "output"
out.mkdir(exist_ok=True)
(out / "environment_report.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results, indent=2))
sys.exit(0 if all(r["exit_code"] == 0 for r in results) else 1)
