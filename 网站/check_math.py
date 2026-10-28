#!/usr/bin/env python3
"""检查（可选自动修复）书稿里的 MathJax 公式写法。

常见事故：
- 把 \\begin{align}/bmatrix 塞进行内 \\(...\\) → 线上露源码
- 行内公式跨多行
- \\frac1d 一类缺花括号

用法：
  python3 网站/check_math.py              # 只检查，有问题 exit 1
  python3 网站/check_math.py --fix       # 能修的先修，再检查
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BOOK_ROOT = HERE.parent / "书稿"

INLINE_MATH = re.compile(r"\\\(([\s\S]*?)\\\)")
FRAC_SHORTHAND = re.compile(r"\\frac([0-9])([a-zA-Z])")


def iter_manuscripts() -> list[Path]:
    if not BOOK_ROOT.is_dir():
        return []
    return sorted(p for p in BOOK_ROOT.rglob("*.md") if p.is_file())


def check_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    rel = path.relative_to(BOOK_ROOT.parent)
    errors: list[str] = []
    for m in INLINE_MATH.finditer(text):
        body = m.group(1)
        line = text[: m.start()].count("\n") + 1
        if r"\begin" in body:
            errors.append(f"{rel}:{line}: 行内公式含 \\begin{{...}}，应改成 \\[...\\]")
        elif "\n" in body.strip("\n"):
            # 单行首尾空白不算
            if body.count("\n") >= 1:
                errors.append(f"{rel}:{line}: 行内公式跨多行，应改成 \\[...\\] 或拆开")
    for i, line in enumerate(text.splitlines(), 1):
        if FRAC_SHORTHAND.search(line):
            errors.append(f"{rel}:{i}: 疑似 \\frac1d 简写，请写成 \\frac{{1}}{{d}}")
    # 定界符数量
    n_inline_open, n_inline_close = text.count(r"\("), text.count(r"\)")
    if n_inline_open != n_inline_close:
        errors.append(f"{rel}: \\( 与 \\) 数量不一致 ({n_inline_open} vs {n_inline_close})")
    n_disp_open, n_disp_close = text.count(r"\["), text.count(r"\]")
    if n_disp_open != n_disp_close:
        errors.append(f"{rel}: \\[ 与 \\] 数量不一致 ({n_disp_open} vs {n_disp_close})")
    return errors


def fix_file(path: Path) -> bool:
    """返回是否改写了文件。"""
    text = path.read_text(encoding="utf-8")
    original = text

    def promote_inline(m: re.Match[str]) -> str:
        body = m.group(1)
        if r"\begin" in body or "\n" in body.strip("\n"):
            inner = body.strip("\n")
            # align → aligned（更常嵌在 \[\] 里）
            inner = re.sub(r"\\begin\{align\*?\}", r"\\begin{aligned}", inner)
            inner = re.sub(r"\\end\{align\*?\}", r"\\end{aligned}", inner)
            return "\\[\n" + inner + "\n\\]"
        return m.group(0)

    text = INLINE_MATH.sub(promote_inline, text)
    text = FRAC_SHORTHAND.sub(r"\\frac{\1}{\2}", text)

    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fix", action="store_true", help="自动修复可安全改写的项")
    ap.add_argument(
        "paths",
        nargs="*",
        type=Path,
        help="可选：只检查这些 md；默认全书稿",
    )
    args = ap.parse_args()

    files = [p.resolve() for p in args.paths] if args.paths else iter_manuscripts()
    if not files:
        print("no manuscripts found", file=sys.stderr)
        return 2

    fixed = []
    if args.fix:
        for path in files:
            if path.suffix == ".md" and fix_file(path):
                fixed.append(path)
        if fixed:
            print(f"fixed {len(fixed)} file(s):")
            for p in fixed:
                try:
                    print(" ", p.relative_to(BOOK_ROOT.parent))
                except ValueError:
                    print(" ", p)

    errors: list[str] = []
    for path in files:
        if path.suffix != ".md":
            continue
        errors.extend(check_file(path))

    if errors:
        print(f"math check FAILED ({len(errors)}):", file=sys.stderr)
        for e in errors:
            print(" ", e, file=sys.stderr)
        return 1

    print(f"math check OK ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
