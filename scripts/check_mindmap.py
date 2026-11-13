#!/usr/bin/env python3
"""校验思维导图 Markdown：标题层级、缩进、引号、图片引用、末尾汇总块。

用法:
    python check_mindmap.py <文件路径>
"""

import re
import sys
from pathlib import Path

IMAGE_RE = re.compile(r"!\[\[([^\]|]+)")
HEADING_RE = re.compile(r"^(#{1,6})\s")
BOLD_LABEL_RE = re.compile(r"^\s*-\s+\*\*[^*]+\*\*\s*[:：]")
FORBIDDEN = ["定理链", "条件对照", "易错清单", "本章小结", "复习提纲"]

errors = []
warnings = []


def find_vault_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / ".obsidian").is_dir():
            return p
    return start


def check(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    vault = find_vault_root(path.parent)

    in_fence = False
    in_frontmatter = False
    levels = {}
    image_refs = []

    for idx, line in enumerate(lines, 1):
        if idx == 1 and line.strip() == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            continue

        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m = HEADING_RE.match(line)
        if m:
            lv = len(m.group(1))
            levels[lv] = levels.get(lv, 0) + 1
            if lv >= 3:
                warnings.append(f"L{idx}: {'#' * lv} 级标题 —— 导图建议只用两级，细节改成加粗标签")

        if line.startswith("\t") or line.lstrip(" ").startswith("\t"):
            errors.append(f"L{idx}: 行首有 Tab，Obsidian 会渲染成代码块，改成 4 个空格")

        if '"' in line:
            warnings.append(f"L{idx}: 出现半角双引号，中文正文改用「」")

        if BOLD_LABEL_RE.match(line) and re.search(r"\*\*: ", line):
            warnings.append(f"L{idx}: 加粗标签后用了半角冒号，统一改成「：」")

        for name in IMAGE_RE.findall(line):
            image_refs.append((idx, name.strip()))

    if in_fence:
        errors.append("代码块 ``` 未闭合")

    if levels.get(1, 0) != 1:
        errors.append(f"一级标题应为 1 个，实际 {levels.get(1, 0)} 个")
    if levels.get(2, 0) == 0:
        errors.append("没有二级标题，知识点未分层")

    for idx, name in image_refs:
        candidates = [path.parent / name, vault / name]
        if not any(c.exists() for c in candidates):
            hits = list(vault.rglob(Path(name).name))
            if not hits:
                errors.append(f"L{idx}: 图片不存在 —— {name}")

    for idx, line in enumerate(lines, 1):
        for word in FORBIDDEN:
            if line.startswith("## ") and word in line:
                warnings.append(f"L{idx}: 「{line.strip()}」疑似末尾汇总块，用户不看这类内容")

    # 报告
    print(f"文件：{path}")
    print(f"行数：{len(lines)}")
    print(f"标题分布：" + "，".join(f"H{k}×{v}" for k, v in sorted(levels.items())))
    print(f"图片引用：{len(image_refs)} 处")
    print("-" * 40)

    for e in errors:
        print(f"[ERROR] {e}")
    for w in warnings:
        print(f"[WARN ] {w}")
    if not errors and not warnings:
        print("通过：结构、缩进、引号、图片引用均正常。")
    elif not errors:
        print(f"通过（{len(warnings)} 条提示，可忽略）。")

    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python check_mindmap.py <文件路径>")
        sys.exit(2)
    check(Path(sys.argv[1]))
