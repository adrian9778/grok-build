#!/usr/bin/env python3
"""生成 .progress/drift-map.md：每篇文档 → 本轮(0e2bfffb..HEAD)变更且被它引用的源码文件清单。"""
import os, re, pathlib, collections, subprocess

REPO = pathlib.Path(os.environ.get("SR_REPO", pathlib.Path(__file__).resolve().parents[4]))
DOCS = sorted(p for d in ["docs/adrian/sourceReader", "docs/adrian/topic"]
              for p in (REPO / d).rglob("*.md") if ".progress" not in p.parts)

out = subprocess.run(["git", "diff", "--name-status", "0e2bfffb..HEAD", "--", "crates/", "Cargo.toml"],
                     capture_output=True, text=True, cwd=REPO).stdout
changed = {}
for line in out.splitlines():
    parts = line.split("\t")
    st = parts[0]
    if st.startswith("R"):
        changed[parts[2]] = ("R", parts[1])
    elif st in ("A", "M", "D"):
        changed[parts[1]] = (st, None)
    if st == "R":
        changed[parts[1]] = ("R-src", parts[2])
CHANGED_RS = {p for p in changed if p.endswith(".rs")}

PATH_TOKEN_RE = re.compile(r"([A-Za-z0-9_.+-]*(?:xai-[a-z0-9-]+|crates|third_party|prod)[A-Za-z0-9_./+-]*\.rs)")
CRATE_DIRS = {}
for g in ["crates/codegen", "crates/common", "crates/build", "third_party", "prod"]:
    b = REPO / g
    if b.is_dir():
        for c in b.iterdir():
            if c.is_dir():
                CRATE_DIRS[c.name] = str(c.relative_to(REPO))

def match(tok):
    """把文档里的路径 token 匹配到变更文件（容忍缺 crates/ 前缀 / 只写文件名）。"""
    tok = tok.lstrip("./")
    base = os.path.basename(tok)
    if tok in CHANGED_RS:
        return tok
    # xai-<crate>/src/... 形式 → 补上真实 crate 目录前缀
    head = tok.split("/")[0]
    if head in CRATE_DIRS:
        cand = os.path.join(CRATE_DIRS[head], *tok.split("/")[1:])
        if cand in CHANGED_RS:
            return cand
    # 尾部两段（src/xxx.rs）唯一命中
    tail2 = "/".join(tok.split("/")[-2:])
    cands = {p for p in CHANGED_RS if p.endswith("/" + tail2)}
    if len(cands) == 1:
        return cands.pop()
    return None

lines = ["# 本轮重核清单（自动生成）",
         "",
         "> 生成方式：`.progress/make_drift_map.py`；数据源 = `git diff --name-status 0e2bfffb..HEAD` ∩「本篇正文引用过的 `.rs` 路径」。",
         "> 状态码：A=新增 M=修改 R=改名（→ 指向新路径）D=已删除。",
         "> 用法：编辑某篇时，先按本表逐文件回源码核对该篇中依赖它的结论；本表没列到不代表内容没错，只代表本轮该文件没动。",
         ""]
tot = collections.Counter()
for d in DOCS:
    text = d.read_text(encoding="utf-8", errors="replace")
    toks = set(PATH_TOKEN_RE.findall(text))
    hit = {}
    for t in toks:
        m = match(t)
        if m:
            st, alt = changed[m]
            hit[m] = (st, alt, t)
    lines.append(f"## {d.name}｜命中 {len(hit)} 个本轮变更文件")
    if hit:
        by_dir = collections.defaultdict(list)
        for p, (st, alt, t) in sorted(hit.items()):
            seg = "/".join(p.split("/")[:3])
            by_dir[seg].append((st, p, alt))
        for seg, items in sorted(by_dir.items(), key=lambda x: -len(x[1])):
            lines.append(f"- **{seg}**（{len(items)}）")
            for st, p, alt in sorted(items):
                arrow = f"  ← 原 {alt}" if st == "R-src" else (f"  → {alt}" if st == "R" else "")
                if st == "R-src":
                    continue
                lines.append(f"  - `{st}` `{p}`{arrow}")
    else:
        lines.append("- （无命中：本轮这些文件没动）")
    lines.append("")
    tot["docs"] += 1
    tot["hits"] += len(hit)

lines.insert(5, f"\n共 {tot['docs']} 篇，命中 {tot['hits']} 个本轮变更文件（去重前，按篇计）。\n")
(REPO / "docs/adrian/sourceReader/.progress/drift-map.md").write_text("\n".join(lines), encoding="utf-8")
print("wrote drift-map.md; docs=%d hits=%d" % (tot["docs"], tot["hits"]))
