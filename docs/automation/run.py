"""Run local quality gates and save source-bound evidence."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
root=Path(__file__).resolve().parents[2]
python=root/(".venv/Scripts/python.exe" if os.name=="nt" else ".venv/bin/python")
node=shutil.which("node")
run_id=str(int(time.time()))
(root/"var").mkdir(exist_ok=True)
commands=[
 ("backend_tests",[str(python),"-m","pytest","tests","-q","-p","no:cacheprovider","--basetemp="+str(root/"var"/("pytest-"+run_id))],root/"backend"),
 ("backend_lint",[str(python),"-m","ruff","check","src","tests"],root/"backend"),
 ("backend_format",[str(python),"-m","ruff","format","--check","src","tests"],root/"backend"),
 ("frontend_types",[node,"node_modules/typescript/bin/tsc","-b"],root/"frontend"),
 ("frontend_tests",[node,"node_modules/vitest/vitest.mjs","run"],root/"frontend"),
 ("frontend_lint",[node,"node_modules/eslint/bin/eslint.js","src"],root/"frontend"),
 ("frontend_build",[node,"node_modules/vite/bin/vite.js","build"],root/"frontend"),
 ("openapi",[str(python),str(root/"docs/automation/export_openapi.py")],root)]
if "--ui" in sys.argv:
    commands.append(("ui",[node,"node_modules/@playwright/test/cli.js","test"],root/"frontend"))
results=[]
for name,cmd,cwd in commands:
    result=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,encoding="utf-8",errors="replace")
    (root/"docs/automation"/(name+".log")).write_text(result.stdout+result.stderr,encoding="utf-8")
    results.append({"name":name,"command":cmd,"exit_code":result.returncode})
    print(name,"PASS" if result.returncode==0 else "FAIL",flush=True)
source=hashlib.sha256()
paths=[]
for folder in ("backend/src","backend/tests","backend/migrations","frontend/src","frontend/e2e","config"):
    paths.extend(p for p in (root/folder).rglob("*") if p.is_file() and "__pycache__" not in str(p))
for path in sorted(paths):
    source.update(str(path.relative_to(root)).encode());source.update(path.read_bytes())
report={"source_sha256":source.hexdigest(),"run_id":run_id,"results":results,
 "external_live":"NOT_RUN; no real credentials or sends",
 "postgres":"RUN" if os.environ.get("PG_TEST_URL") else "NOT_RUN; PG_TEST_URL unavailable"}
(root/"docs/automation/report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
sys.exit(any(r["exit_code"] for r in results))

