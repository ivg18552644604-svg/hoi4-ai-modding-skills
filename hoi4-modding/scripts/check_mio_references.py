#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_mio_references.py —— 交叉核验 HOI4 模组中 MIO（军工组织）的引用是否真实存在。

解决的问题：MIO 组织的 `equipment_type`（装备原型 / 装备组）与 `research_categories`
（科技类别）引用的都是别处定义的 token。写错一个字母（或引用了主机模组里其实不存在的
自定义原型）并不会让游戏崩溃，只会让组织在界面里永远置灰 / 加成失效——极难排查。
本脚本把这些 token 与"真实存在集合"逐一对齐。

用法：
    python check_mio_references.py <模组目录> [--ref <被引用模组目录> ...] [--game <游戏目录>]

- <模组目录>：待检查的模组（会读取其 common/military_industrial_organization/
  organizations/*.txt，以及它自己的 common/equipment_groups、common/technology_tags）。
- --ref：可多次传入"被本模组引用/依赖"的其它模组目录（例如主机模组），用于扩充
  "真实存在集合"（大改模组的自定义装备/科技类别在这里定义）。
- --game：游戏本体安装目录（含 common/、documentation/ 的那一层）。不传则尝试常见位置。

退出码：0 = 全部引用存在；1 = 发现悬空引用或参数错误。

注意：存在性判断用的是"所有被搜索目录的并集"（宽松口径）——只要任一模组/本体定义过该
token 就算通过。这能抓出拼写错误与凭记忆瞎写，但抓不出"A 模组覆盖了 B 模组的同名文件、
从而删掉了某 token"这类边界情形（需人工对照同名文件）。
"""

import argparse
import os
import re
import sys

# 常见游戏安装位置（Windows Steam / 其它盘）
GAME_CANDIDATES = [
    r"D:/SteamLibrary/steamapps/common/Hearts of Iron IV",
    r"C:/Program Files (x86)/Steam/steamapps/common/Hearts of Iron IV",
    r"C:/Program Files/Steam/steamapps/common/Hearts of Iron IV",
    r"E:/SteamLibrary/steamapps/common/Hearts of Iron IV",
    r"F:/SteamLibrary/steamapps/common/Hearts of Iron IV",
    os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Hearts of Iron IV"),
]

BLOCK_KEY_RE = re.compile(r"([A-Za-z0-9_]+)\s*=\s*\{")
ARCHETYPE_RE = re.compile(r"archetype\s*=\s*([A-Za-z0-9_]+)")
BARE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_]+$")


def strip_comments(text: str) -> str:
    """去掉 # 注释（不误伤引号内的 #）。"""
    out = []
    for line in text.splitlines():
        res, in_quote = [], False
        for ch in line:
            if ch == '"':
                in_quote = not in_quote
            if ch == "#" and not in_quote:
                break
            res.append(ch)
        out.append("".join(res))
    return "\n".join(out)


def read_text(path: str) -> str:
    """HOI4 脚本文件多为 UTF-8（部分含 BOM），容错读取。"""
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, LookupError):
            continue
    return ""


def iter_txt(root: str):
    """递归产出 dir 下所有 .txt 文件路径（忽略大小写，跳过 documentation）。"""
    if not os.path.isdir(root):
        return
    for dirpath, _dirs, files in os.walk(root):
        for fn in files:
            if fn.lower().endswith((".txt",)):
                yield os.path.join(dirpath, fn)


def collect_block_keys(root: str) -> set:
    """收集 root 下所有 .txt 中出现的 `XXX = {` 块键（任意嵌套层级）。"""
    keys = set()
    for fp in iter_txt(root):
        keys.update(BLOCK_KEY_RE.findall(strip_comments(read_text(fp))))
    return keys


def collect_archetypes(root: str) -> set:
    """收集 `archetype = XXX` 的值（duplicate_archetypes 中变体所继承的原型名）。"""
    found = set()
    for fp in iter_txt(root):
        found.update(ARCHETYPE_RE.findall(strip_comments(read_text(fp))))
    return found


def collect_bare_tokens(root: str) -> set:
    """收集 common/technology_tags 这类"裸列表"文件里的 token。"""
    tokens = set()
    for fp in iter_txt(root):
        txt = strip_comments(read_text(fp)).replace("{", " ").replace("}", " ")
        for tok in txt.split():
            if BARE_TOKEN_RE.match(tok):
                tokens.add(tok)
    return tokens


def extract_block_tokens(text: str, block_name: str):
    """提取 `block_name = { ... }` 大括号内的所有裸 token（支持嵌套大括号）。"""
    results = []
    for m in re.finditer(r"\b" + re.escape(block_name) + r"\s*=\s*\{", text):
        i = m.end() - 1
        depth, buf = 0, []
        while i < len(text):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            if depth >= 1:
                buf.append(ch)
            i += 1
        body = "".join(buf).replace("{", " ").replace("}", " ")
        results.append([t for t in body.split() if BARE_TOKEN_RE.match(t)])
    return results


def mio_files(mod_dir: str):
    d = os.path.join(mod_dir, "common", "military_industrial_organization", "organizations")
    return list(iter_txt(d))


def main() -> int:
    ap = argparse.ArgumentParser(description="核验 HOI4 MIO 组织的 equipment_type / research_categories 引用")
    ap.add_argument("mod_dir", help="待检查的模组目录")
    ap.add_argument("--ref", action="append", default=[], help="被引用的其它模组目录（可重复）")
    ap.add_argument("--game", default=None, help="游戏本体目录（含 common/）")
    args = ap.parse_args()

    mod_dir = os.path.abspath(args.mod_dir)
    if not os.path.isdir(mod_dir):
        print(f"[!!] 模组目录不存在：{mod_dir}")
        return 1

    ref_dirs = [mod_dir] + [os.path.abspath(p) for p in args.ref]
    for p in args.ref:
        if not os.path.isdir(p):
            print(f"[!!] --ref 目录不存在：{p}")

    game_dir = args.game
    if not game_dir:
        for cand in GAME_CANDIDATES:
            if os.path.isdir(os.path.join(cand, "common")):
                game_dir = cand
                break
    search_dirs = list(ref_dirs)
    if game_dir and os.path.isdir(os.path.join(game_dir, "common")):
        search_dirs.append(game_dir)
        print(f"[i] 游戏本体：{game_dir}")
    else:
        print("[i] 未找到游戏本体目录（仅用模组目录做核验；建议用 --game 指定以覆盖原版 token）")

    # ---- 构建"真实存在集合" ----
    known_equipment, known_groups, known_research = set(), set(), set()
    for d in search_dirs:
        known_equipment |= collect_block_keys(os.path.join(d, "common", "units"))
        known_equipment |= collect_archetypes(os.path.join(d, "common", "units"))
        known_groups |= collect_block_keys(os.path.join(d, "common", "equipment_groups"))
        known_research |= collect_bare_tokens(os.path.join(d, "common", "technology_tags"))

    print(f"[i] 已知装备原型/块键 {len(known_equipment)} 个 / 装备组 {len(known_groups)} 个 / 科技类别 {len(known_research)} 个")

    # ---- 解析模组的 MIO 文件 ----
    files = mio_files(mod_dir)
    if not files:
        print("[i] 未发现 common/military_industrial_organization/organizations/*.txt —— 本模组不含 MIO，跳过。")
        return 0

    bad = 0
    for fp in files:
        text = strip_comments(read_text(fp))
        org_re = re.compile(r"(?m)^\s*([A-Za-z0-9_]+)\s*=\s*\{")
        for m in org_re.finditer(text):
            org = m.group(1)
            if org in ("equipment_type", "research_categories", "trait", "initial_trait", "override_trait", "add_trait"):
                continue
            # 组织块体（大括号配对）
            i, depth, buf = m.end() - 1, 0, []
            while i < len(text):
                ch = text[i]
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        break
                if depth >= 1:
                    buf.append(ch)
                i += 1
            body = "".join(buf)

            for group in extract_block_tokens(body, "equipment_type"):
                for tok in group:
                    if tok in known_equipment or tok in known_groups:
                        continue
                    print(f"[!!] {os.path.relpath(fp, mod_dir)}  MIO「{org}」equipment_type 悬空 token: {tok}")
                    bad += 1

            for group in extract_block_tokens(body, "research_categories"):
                for tok in group:
                    if tok in known_research:
                        continue
                    print(f"[!!] {os.path.relpath(fp, mod_dir)}  MIO「{org}」research_categories 悬空 token: {tok}")
                    bad += 1

    print()
    if bad:
        print(f"结果：发现 {bad} 个悬空引用 —— 请修正后再交付。")
        return 1
    print("结果：MIO 引用全部存在 ✔")
    return 0


if __name__ == "__main__":
    sys.exit(main())
