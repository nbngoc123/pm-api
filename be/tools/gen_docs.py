"""Sinh docs/openapi.json + docs/API_FRONTEND.md (mục catalog, mã lỗi, ma trận quyền tự sinh). Chạy: python -m tools.gen_docs"""
import glob, json, re
from app.main import create_app
from app.seed import PERMISSIONS, ROLES

o = create_app().openapi()
json.dump(o, open("docs/openapi.json", "w"), ensure_ascii=False, indent=1)
tags = {}
for path, ops in o["paths"].items():
    for m, op in ops.items():
        tags.setdefault(op["tags"][0] if op.get("tags") else "Khác", []).append((m.upper(), path.replace("/api/v1", ""), op.get("summary", "")))
cat = []
for t in sorted(tags):
    cat.append(f"#### {t}\n\n| Method | Path | Mô tả |\n|---|---|---|")
    for m, p, s in tags[t]:
        if re.fullmatch(r"[A-Z][a-z]+( [A-Z][a-z]+)*", s):
            s = ""
        cat.append(f"| `{m}` | `{p}` | {s} |")
    cat.append("")
catalog = "\n".join(cat)

ST = {"bad": 400, "unauthorized": 401, "forbidden": 403, "not_found": 404, "conflict": 409, "invalid": 422}
codes = {"FILE_TOO_LARGE": 413, "VALIDATION_ERROR": 422}
for f in glob.glob("app/**/*.py", recursive=True):
    for fn, c in re.findall(r'\b(bad|unauthorized|forbidden|not_found|conflict|invalid)\("([A-Z_]+)"', open(f).read()):
        codes[c] = ST[fn]
err = "| HTTP | `error.code` |\n|---|---|\n" + "\n".join(
    f"| {s} | {', '.join(f'`{c}`' for c, x in sorted(codes.items()) if x == s)} |" for s in sorted(set(codes.values())))


def matrix(rs):
    h = "| Quyền | " + " | ".join(r.value for r in rs) + " |\n|---|" + "---|" * len(rs)
    return h + "\n" + "\n".join(f"| `{p}` — {d} | " + " | ".join("✔" if p in ROLES[r][2] else "" for r in rs) + " |" for p, d in PERMISSIONS.items())


sysr = [r for r in ROLES if ROLES[r][1].value == "SYSTEM"]
prj = [r for r in ROLES if ROLES[r][1].value == "PROJECT"]
tpl = open("docs/API_FRONTEND.tpl.md", encoding="utf-8").read()
n_ops = sum(len(v) for v in o["paths"].values())
doc = (tpl.replace("{{ERRORS}}", err).replace("{{MATRIX}}", matrix(sysr + prj)).replace("{{CATALOG}}", catalog)
          .replace("{{N_OPS}}", str(n_ops)))
open("docs/API_FRONTEND.md", "w", encoding="utf-8").write(doc)
print(n_ops, "operations;", len(codes), "error codes")
