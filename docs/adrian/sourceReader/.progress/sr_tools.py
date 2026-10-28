#!/usr/bin/env python3
"""sr_tools.py — 源码文档库定位/校验工具（docs/adrian/sourceReader + topic）

用法:
  sr_tools.py locate  SYM [SYM...]     全库定位符号定义（生产树优先，tests/examples 兜底）
  sr_tools.py outline FILE [--top]     输出文件符号骨架 + 行号
  sr_tools.py offset  FILE SYM         打印符号定义行号（供读者把 `+N` 换算成绝对行）
  sr_tools.py verify  DOC|DIR ...      文档引用校验（路径 / 符号归属 / 绝对行号）
  sr_tools.py nav     DIR              文档间链接断链与孤儿检查

定位记法（见 UPDATE-SPEC.md）：`crate/path.rs` · 符号：Name 偏移：+N
  +0 = 该符号定义行；impl/trait 成员的 +0 = 其 impl / trait 头行。
"""
import os, re, sys, pathlib, collections

HERE = pathlib.Path(__file__).resolve()
REPO = pathlib.Path(os.environ.get("SR_REPO", HERE.parents[3].parent))
PROD_ROOTS = ["crates/codegen", "crates/common", "crates/build", "third_party", "prod"]
SKIP_DIRS = {".git", "target", "node_modules", ".cargo", ".crush", ".idea",
             ".workbuddy-ai", "dist", "out"}

DEF_RE = re.compile(
    r"^\s*(?:#\[[^\]]*\]\s*)*(?:pub(?:\([^)]*\))?\s+)?(?:default\s+)?"
    r"(?:(?:async|unsafe|extern\s+\S*)\s+)*"
    r"(?:macro_rules!\s+|fn\s+|struct\s+|enum\s+|trait\s+|type\s+|union\s+|mod\s+|"
    r"const\s+|static\s+|impl\s+)(?:<[^>]{0,160}>\s*)?([A-Za-z_][A-Za-z0-9_]*)", re.M)
VARIANT_RE = re.compile(
    r"^\s*(?:#\[[^\]]*\]\s*)?(?:pub(?:\([^)]*\))?\s+)?([A-Z][A-Za-z0-9_]*)\s*(?:\(|,|;|\{|$)", re.M)
FIELD_RE = re.compile(r"^\s*(?:pub(?:\([^)]*\))?\s+)?([a-z_][a-z0-9_]*)\s*:", re.M)


def _iter_rs(roots):
    for root in roots:
        base = REPO / root
        if not base.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for f in filenames:
                if f.endswith(".rs"):
                    yield str(pathlib.Path(dirpath, f).relative_to(REPO))


PROD_FILES = list(_iter_rs(PROD_ROOTS))
PROD_SET = set(PROD_FILES)
ALL_FILES = PROD_FILES + [p for p in _iter_rs(["crates", "third_party", "prod"]) if p not in PROD_SET]
FILE_TEXT, FILE_DEFS = {}, {}
for _rp in ALL_FILES:
    try:
        _t = (REPO / _rp).read_text(encoding="utf-8", errors="replace")
    except OSError:
        continue
    FILE_TEXT[_rp] = _t
    FILE_DEFS[_rp] = set(DEF_RE.findall(_t)) | set(VARIANT_RE.findall(_t)) | set(FIELD_RE.findall(_t))
SYMS = collections.defaultdict(list)
for _rp, _ds in FILE_DEFS.items():
    for _d in _ds:
        SYMS[_d].append(_rp)
BY_NAME = collections.defaultdict(list)
for _rp in ALL_FILES:
    BY_NAME[pathlib.Path(_rp).name].append(_rp)
BY_SUFFIX = collections.defaultdict(list)
for _rp in ALL_FILES:
    parts = _rp.split("/")
    for i in range(len(parts)):
        BY_SUFFIX["/".join(parts[i:])].append(_rp)

# 仓库里所有文件 + 目录（路径校验要认目录引用）
FS_ENTRIES = set()
for dirpath, dirnames, filenames in os.walk(REPO):
    dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
    for x in filenames + dirnames:
        FS_ENTRIES.add(os.path.relpath(os.path.join(dirpath, x), REPO))
CRATES = {}
for _g in PROD_ROOTS:
    _b = REPO / _g
    if _b.is_dir():
        for _c in _b.iterdir():
            if _c.is_dir():
                CRATES[_c.name] = str(_c.relative_to(REPO))


# ------------------------------------------------------------------ locate
def cmd_locate(syms):
    for sym in syms:
        hits = []
        for rp in PROD_FILES + [p for p in ALL_FILES if p not in PROD_SET]:
            t = FILE_TEXT.get(rp)
            if not sym or sym not in FILE_DEFS.get(rp, ()):
                continue
            kind = "?"
            for m in DEF_RE.finditer(t):
                if m.group(1) == sym:
                    ln = t.count("\n", 0, m.start()) + 1
                    kind = m.group(0).strip()[:44].replace("\n", " ")
                    break
            else:
                ln = next((i + 1 for i, l in enumerate(t.splitlines())
                           if re.search(r"(?:^|[^A-Za-z0-9_])" + re.escape(sym) + r"\b", l)), 0)
            hits.append((rp, ln, kind))
        if hits:
            for rp, ln, kind in hits[:6]:
                print(f"{sym}\t{rp}:{ln}\t{kind}")
            if len(hits) > 6:
                print(f"{sym}\t… 另有 {len(hits)-6} 处同名定义")
        else:
            print(f"{sym}\tNOT FOUND (仓库内无此定义/变体/字段)")
    return 0


# ------------------------------------------------------------------ outline
def _resolve(tok, docdir=None, strict=False):
    """把文档路径 token 解析为仓库相对路径；strict=True 时只允许原样命中。"""
    tok = tok.strip().lstrip("./").rstrip(".,;)`")
    cands = []
    if docdir:
        cands.append((REPO / docdir / tok))
    cands.append(REPO / tok)
    for pre in PROD_ROOTS:
        cands.append(REPO / pre / tok)
    for c in cands:
        try:
            c = c.resolve()
            if str(c.relative_to(REPO)) in FS_ENTRIES:
                return str(c.relative_to(REPO))
        except (OSError, ValueError):
            pass
    if strict:
        return None
    if tok in ALL_FILES or tok in FS_ENTRIES:
        return tok
    for key in (tok, "/".join(tok.split("/")[-2:]), pathlib.Path(tok).name):
        if key in BY_SUFFIX and str(tok).count("/") >= 1:
            return BY_SUFFIX[key][0]
        if key in BY_NAME and str(tok).count("/") == 0:
            return BY_NAME[key][0]
    return None


def cmd_outline(path, top=False):
    rp = _resolve(path)
    if not rp or rp not in FILE_TEXT:
        print(f"!! 无法解析文件: {path}")
        return 1
    for i, line in enumerate(FILE_TEXT[rp].splitlines(), 1):
        m = DEF_RE.match(line)
        if m and (not top or not line.startswith("    ")):
            print(f"{i:6d}  {line.strip()[:118]}")
    return 0


def cmd_offset(path, sym):
    rp = _resolve(path)
    t = FILE_TEXT.get(rp, "")
    for m in DEF_RE.finditer(t):
        if m.group(1) == sym:
            print(f"{rp}:{m.group(0).count(chr(10)) + t.count(chr(10), 0, m.start()) + 1}  {sym}")
            body = t[m.start():]
            depth, lines = 0, 0
            for ch in body:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
                if ch == "\n":
                    lines += 1
            print(f"   函数体约 {lines} 行 ⇒ 合法偏移上界 +{lines}（+N 必须落在此区间）")
            return 0
    print(f"!! {rp} 中没有定义 {sym}")
    return 1


# ------------------------------------------------------------------ verify
PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_./-])"
    r"((?:crates|third_party|prod)/[A-Za-z0-9_./+-]+|"
    r"xai-[a-z0-9][a-z0-9-]*(?:-[a-z0-9]+)*/(?:src|tests|benches|examples)/[A-Za-z0-9_./+-]+|"
    r"[A-Za-z0-9_.+-]+/(?:src|tests|benches|examples)/[A-Za-z0-9_./+-]+|"
    r"[A-Za-z0-9_.+-]+\.(?:rs|toml|md|json|ya?ml|sh|py|lock))")
BARE_FILE_RE = re.compile(r"^[A-Za-z0-9_.+-]+\.(rs|toml|md|json|ya?ml|sh|py|lock)$")
SYM_KV_RE = re.compile(r"(?:符号|函数|方法|Struct|Enum|Trait|Type|Impl|Const|Module|字段)：\s*"
                       r"(?:`|\*\*)?(?:impl\s+|async\s+|fn\s+|struct\s+|enum\s+|trait\s+|const\s+)?"
                       r"([A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_~][A-Za-z0-9_]*)?)")
SYM_DOT_RE = re.compile(r"`([A-Za-z0-9_./+-]+\.(?:rs|toml))`\s*·\s*"
                        r"`(?:impl\s+|struct\s+|enum\s+|trait\s+|const\s+|fn\s+)?([A-Za-z_][A-Za-z0-9_:<>~']*)`")
ABS_LINE_RE = re.compile(r"(?:定义在|头在|位于|见|在)\s*(?:第\s*)?(\d{3,6})\s*(?:行|:)|@(\d{3,6})\b")
# 裸行号引用（`file.rs:123` / `Cargo.toml:8`）：规范只允许「符号(+偏移)」，
# 绝对行号必须显式标成快照。校验器按「同一行内有无『快照』二字」分档。
BARE_LINE_RE = re.compile(r"[A-Za-z0-9_./+-]+\.(?:rs|toml|lock|md|sh|py|json|ya?ml|sbpl):\d+")
NEG_WORDS = ("不存在", "已删除", "被删", "已移除", "消失", "不再有", "已废弃", "不再", "没有", "缺少",
             "旧文档", "旧版", "旧写法", "历史上",
             "gone", "removed", "deleted")
PLACEHOLDER = ("your_", "xxx", "XXX", "<", "{", "*", "some_", "example")
# 从 `符号：X` 里抽出来的噪声（crate 路径片段 / 泛型占位 / 模块关键字），不是真符号
SYM_NOISE = {"xai", "lib", "mod", "crate", "self", "super", "Y", "Z", "T", "Name", "E", "K", "V", "N"}


def _claimed_crate_path(tok):
    """若 token 自带 crate 名，返回 (crate, 该 crate 内应存在的相对路径)；否则 (None, None)。"""
    parts = tok.split("/")
    for i, seg in enumerate(parts):
        if seg in CRATES:
            tail = "/".join(parts[i + 1:]).rstrip("/")
            if not tail:
                return None, None
            return seg, os.path.join(CRATES[seg], tail)
    return None, None


GENERIC_NAMES = {"lib.rs", "mod.rs", "main.rs", "tests.rs", "test.rs"}


def _move_candidates(crate, real):
    """给一个「声称在某 crate 内但已不存在」的路径找搬家目的地（确定性排序）。

    lib.rs / mod.rs 这类通用名按 basename 全库匹配毫无意义（会随机指到别的 crate 的
    lib.rs）⇒ 只在声称的 crate 内找同目录兄弟文件，即「文件改名」而非「文件搬家」。
    """
    name = os.path.basename(real)
    cdir = CRATES.get(crate, "")
    if name == "lib.rs" and (os.path.dirname(real) + "/mod.rs") in FS_ENTRIES:
        return [os.path.dirname(real) + "/mod.rs"]      # Rust 模块文件 lib.rs→mod.rs 改名
    if name not in GENERIC_NAMES:
        cand = [p for p in FS_ENTRIES if p.endswith("/" + name)]
    else:
        parent = os.path.basename(os.path.dirname(real))
        cand = [p for p in FS_ENTRIES
                if cdir and p.startswith(cdir + "/")
                and os.path.basename(os.path.dirname(p)) == parent]
    return sorted({p for p in cand if p.endswith(".rs") and "target/" not in p})


def cmd_verify(docs):
    tot = collections.Counter()
    for d in docs:
        text = d.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        dead, moved, illus, nonrepo, bare, okp = [], collections.OrderedDict(), [], [], [], 0
        wrapped = []
        for idx, line in enumerate(lines):
            neg = any(w in line for w in NEG_WORDS) or any(
                w in (lines[idx - 1] if idx else "") for w in NEG_WORDS)
            for m in PATH_TOKEN_RE.finditer(line):
                tok = m.group(1).rstrip(".,;)`")
                if any(p in tok for p in PLACEHOLDER):
                    continue
                tot["mentions"] += 1
                if tok.endswith("-"):        # ASCII 框线图里的跨行折断路径，非失效
                    wrapped.append(tok)
                    continue
                crate, real = _claimed_crate_path(tok)
                if crate:                                  # 严格：必须在声称的 crate 内
                    if real in FS_ENTRIES:
                        okp += 1
                        continue
                    alt = _move_candidates(crate, real)
                    # 只有真的在别的 crate 里找到同名 .rs 才算「搬家」，否则算失效
                    if neg:
                        illus.append(tok)
                    elif alt:
                        moved[tok] = alt[0] if len(alt) == 1 else \
                            f"多候选({len(alt)}): " + ", ".join(alt[:4])
                    else:
                        dead.append(tok)
                    continue
                rp = _resolve(tok, d.parent)
                if rp:
                    okp += 1
                elif neg:
                    illus.append(tok)
                elif BARE_FILE_RE.match(tok) and BY_NAME.get(tok):
                    bare.append(tok)
                elif "/" not in tok:
                    nonrepo.append(tok)
                else:
                    dead.append(tok)
        # 裸行号（非快照标注）
        lineref = [(i + 1, BARE_LINE_RE.findall(l))
                   for i, l in enumerate(lines)
                   if "快照" not in l and BARE_LINE_RE.search(l)]
        tot["bare_line"] += sum(len(h) for _, h in lineref)
        # 符号归属：可配对的部分
        pairs = set()
        for a, b in SYM_DOT_RE.findall(text):
            pairs.add((a, b))
        for line in lines:
            mm = PATH_TOKEN_RE.search(line)
            if mm:
                for sym in SYM_KV_RE.findall(line):
                    pairs.add((mm.group(1), sym))
        pbad = []
        for tok, sym in pairs:
            base = sym.split("::")[-1].strip("<>")
            crate, real = _claimed_crate_path(tok)
            target = real if (crate and real in FILE_DEFS) else _resolve(tok, d.parent, strict=True)
            if target not in FILE_DEFS or not base or len(base) < 3 or base in SYM_NOISE:
                continue
            tot["pairs"] += 1
            if base not in FILE_DEFS[target]:
                if base in SYMS:
                    pbad.append((tok, sym, "在他处", SYMS[base][0]))
                else:
                    pbad.append((tok, sym, "全库无", ""))
                tot["pair_bad"] += 1
        absn = len(ABS_LINE_RE.findall(text))
        tot["abs_line"] += absn
        tot["dead"] += len(set(dead))
        tot["moved"] += len(moved)
        tot["illus"] += len(set(illus))
        tot["bare"] += len(set(bare))
        tot["nonrepo"] += len(set(nonrepo))
        tot["wrapped"] += len(set(wrapped))
        print(f"\n=== {d.name}｜路径 ok={okp} 失效={len(set(dead))} 搬家={len(moved)} "
              f"符号配对={len(pairs)} 待判读={len(pbad)} 绝对行号={absn} 裸行号={sum(len(h) for _, h in lineref)} 折行={len(set(wrapped))}")
        for t in sorted(set(dead)):
            print(f"  ✗ 失效路径 {t}")
        for tok, dst in moved.items():
            print(f"  ↦ 搬家 {tok}  ->  {dst}")
        for tok, sym, why, where in pbad:
            print(f"  ? 符号待判读 {tok} · {sym}  [{why}{': ' + where if where else ''}]")
        for ln, toks in lineref[:12]:
            print(f"  # 裸行号（无『快照』标注）:{ln} " + ", ".join(toks[:4]))
        if len(lineref) > 12:
            print(f"  # … 另有 {len(lineref) - 12} 行含裸行号")
        if illus:
            print(f"  · 说明性引用(非错误) {len(set(illus))}: " + ", ".join(sorted(set(illus))[:8]))
        if bare:
            print(f"  · 裸文件名缩写(风格,非错误) {len(set(bare))}: " + ", ".join(sorted(set(bare))[:8]))
        if nonrepo:
            print(f"  · 非仓库文件名 {len(set(nonrepo))}: " + ", ".join(sorted(set(nonrepo))[:8]))
    print(f"\n=== 汇总 提及={tot['mentions']} 符号配对={tot['pairs']} 待判读={tot['pair_bad']} "
          f"绝对行号残留={tot['abs_line']} 裸行号={tot['bare_line']} "
          f"失效路径={tot['dead']} 搬家={tot['moved']} "
          f"折行={tot['wrapped']} 说明性={tot['illus']} 裸文件名={tot['bare']} 非仓库名={tot['nonrepo']}")
    return 0


# ------------------------------------------------------------------ nav
LINK_RE = re.compile(r"\]\(((?:\.\.?/)*[A-Za-z0-9_\u4e00-\u9fff./-]+\.md)(?:#[^)]*)?\)")


def cmd_nav(dirs):
    bad, n = [], 0
    for d in dirs:
        base = REPO / d if not pathlib.Path(d).is_absolute() else pathlib.Path(d)
        docs = sorted(p for p in base.rglob("*.md") if ".progress" not in p.parts)
        names = {p.name for p in docs}
        linked = set()
        for p in docs:
            for m in LINK_RE.finditer(p.read_text(encoding="utf-8", errors="replace")):
                tgt = m.group(1)
                linked.add(tgt)
                # 先按「相对本文档」原样解析（含 ../），再退回全库同名文件（目录树里允许只写文件名）
                if not (p.parent / tgt).resolve().exists() and pathlib.Path(tgt).name not in names:
                    bad.append(f"{p.relative_to(base)} -> {tgt}")
                n += 1
        orphan = {p.name for p in docs} - {pathlib.Path(t).name for t in linked} \
                 - {p.name for p in docs if p.name.lower() == "readme.md"}
        print(f"[{base.name}] 链接 {n} 条；断链 {len(bad)}；孤儿页 {sorted(orphan) if orphan else '无'}")
    for b in bad:
        print(f"  ✗ 断链 {b}")
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd, args = sys.argv[1], sys.argv[2:]
    if cmd == "locate":
        return cmd_locate(args)
    if cmd == "outline":
        return cmd_outline(args[0], "--top" in args)
    if cmd == "offset":
        return cmd_offset(args[0], args[1])
    if cmd == "verify":
        docs = []
        for a in args:
            p = pathlib.Path(a)
            if p.is_dir():
                docs += sorted(x for x in p.rglob("*.md") if ".progress" not in x.parts)
            elif p.exists():
                docs.append(p)
            else:
                docs += sorted(x for x in (REPO / a).rglob("*.md") if ".progress" not in x.parts)
        return cmd_verify(docs)
    if cmd == "nav":
        return cmd_nav(args or ["docs/adrian/sourceReader"])
    print("未知子命令:", cmd)
    return 1


if __name__ == "__main__":
    sys.exit(main())
