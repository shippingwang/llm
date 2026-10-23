#!/usr/bin/env python3
"""Build MkDocs pages from the canonical manuscripts.

The manuscripts in ../书稿 are the only editable source. This script splits
multi-chapter Markdown files at level-one headings and writes generated pages
to ./docs in a stable reading order.
"""

from pathlib import Path
from typing import List, Optional
import re
import shutil


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "书稿"
DOCS = HERE / "docs"


BOOKS = [
    {
        "directory": "01-architecture",
        "title": "第一册 · 现代大模型架构",
        "description": "从自回归语言模型与 Transformer 出发，理解现代稠密模型、MoE、长上下文与混合架构。",
        "source": "第一册 现代大模型架构",
        "files": [
            "00 目录总览.md",
            "序章 案例：行程助手.md",
            "第一部分 基础组件与工程/导读.md",
            "第一部分 基础组件与工程/第0章 预备知识.md",
            "第一部分 基础组件与工程/第1章 语言模型.md",
            "第一部分 基础组件与工程/第2章 核心组件.md",
            "第一部分 基础组件与工程/第3章 组装训练.md",
            "第一部分 基础组件与工程/第4章 推理生成.md",
            "第二部分 稠密模型/导读.md",
            "第二部分 稠密模型/第5章 稳定训练.md",
            "第二部分 稠密模型/第6章 rope.md",
            "第二部分 稠密模型/第7章 KV Cache 优化.md",
            "第二部分 稠密模型/第8章 组装稠密模型.md",
            "第三部分 混合专家/导读.md",
            "第三部分 混合专家/第9章 MoE.md",
            "第三部分 混合专家/第10章 扩容.md",
            "第四部分 长上下文/导读.md",
            "第四部分 长上下文/第11章 稀疏注意力.md",
            "第四部分 长上下文/第12章 线性注意力.md",
            "第四部分 长上下文/第13章 状态空间模型.md",
            "第五部分 混合架构/导读.md",
            "第五部分 混合架构/第14章 混合架构.md",
            "第五部分 混合架构/第15章 投机解码.md",
            "第五部分 混合架构/第16章 Qwen架构解析.md",
            "第五部分 混合架构/结语.md",
            # 暂时不上线附录；恢复时取消注释并同步 mkdocs.yml 导航
            # "附录/附录A 从ResNet到CLIP.md",
            # "附录/附录B 关键节点2017-2022.md",
            # "附录/附录C 关键节点2023-2024.md",
            # "附录/附录D 关键节点2025-2026.md",
            # "附录/附录E 显存与速度速算表.md",
            # "附录/附录F muP与超参迁移.md",
            # "附录/附录G 多模态入口.md",
        ],
    },
    {
        "directory": "02-systems",
        "title": "第二册 · 大模型训练与推理系统",
        "description": "从硬件资源模型出发，掌握分布式训练、推理引擎、量化优化和生产部署。",
        "source": "第二册 工业级大模型技术",
        "files": [
            "00 目录总览.md",
            "第一部分 先看懂机器.md",
            "第二部分 多卡训练.md",
            "第三部分 推理引擎.md",
            "第四部分 压缩与加速.md",
            "第五部分 生产交付.md",
            "附录 多模态服务.md",
        ],
    },
    {
        "directory": "03-post-training",
        "title": "第三册 · 大模型后训练与智能体系统",
        "description": "围绕任务数据、监督微调、偏好对齐、推理训练、评测体系和 Agent 构建完整迭代闭环。",
        "source": "第三册 改模型",
        "files": [
            "00 目录总览.md",
            "第一部分 定义目标.md",
            "第二部分 用示范教模型.md",
            "第三部分 偏好与强化学习.md",
            "第四部分 评测与迭代.md",
            "第五部分 上下文与Agent.md",
            "附录 多模态后训练.md",
        ],
    },
]


HOME = """\
---
hide:
  - navigation
  - toc
---

# 现代大模型

<div class="book-list">
  <a href="01-architecture/">第一册 · 现代大模型架构</a>
  <a href="02-systems/">第二册 · 训练与推理系统</a>
  <a href="03-post-training/">第三册 · 后训练与智能体系统</a>
</div>
"""


def split_h1(markdown):
    """Split Markdown into complete sections starting with a level-one heading.

    Headings inside fenced code blocks (``` ... ```) are ignored, so Python
    comments like ``# continue training`` do not become separate pages.
    """
    matches = []
    in_fence = False
    for match in re.finditer(r"(?m)^(```.*|# (?!#)(.+?))\s*$", markdown):
        line = match.group(0)
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        title = match.group(2)
        if title is None:
            continue
        matches.append((match.start(), title.strip()))
    if not matches:
        return []
    sections = []
    for index, (start, title) in enumerate(matches):
        end = matches[index + 1][0] if index + 1 < len(matches) else len(markdown)
        sections.append((title, markdown[start:end].strip() + "\n"))
    return sections


def front_matter(title):
    safe = title.replace('"', '\\"')
    return f'---\ntitle: "{safe}"\n---\n\n'


def write_text(path, text, written, changed):
    """Update a generated page only when content changes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    written.add(path.resolve())
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")
    changed.add(path)


def copy_asset(src, dst, written, changed):
    dst.parent.mkdir(parents=True, exist_ok=True)
    written.add(dst.resolve())
    if dst.exists() and dst.read_bytes() == src.read_bytes():
        return
    shutil.copy2(src, dst)
    changed.add(dst)


def _manuscript_stem_key(filename: str) -> Optional[str]:
    """Stable id for a chapter file when only the title after the stem changes.

    ``序章 一个行程助手在算什么.md`` and ``序章 案例：行程助手.md`` share key
    ``序章``; ``第6章 rope.md`` / ``第6章 位置表示.md`` share ``第6章``.
    """
    if filename.startswith("序章"):
        return "序章"
    if filename.startswith("尾声") or filename.startswith("结语"):
        return "尾声"
    if filename == "导读.md" or filename.startswith("导读"):
        return "导读"
    m = re.match(r"(附录[A-Za-z])", filename)
    if m:
        return m.group(1)
    m = re.match(r"(第\d+章)", filename)
    if m:
        return m.group(1)
    if "目录总览" in filename:
        return "目录总览"
    return None


def resolve_manuscript(source_dir: Path, relative_path: str) -> Path:
    """Resolve a listed manuscript path; tolerate folder and title renames.

    Order: exact path → same filename under「第N部分*」→ same stem key
    (序章 / 第N章 / 附录X / 导读 / 尾声) in the listed directory, then anywhere
    under the book root.
    """
    direct = source_dir / relative_path
    if direct.is_file():
        return direct

    rel = Path(relative_path)
    name = rel.name
    part_key = None
    if rel.parts:
        m = re.match(r"(第.+?部分)", rel.parts[0])
        if m:
            part_key = m.group(1)

    def _prefer_part(paths: List[Path]) -> List[Path]:
        if not part_key or not paths:
            return paths
        prefer = [
            p
            for p in paths
            if any(
                part.startswith(part_key)
                for part in p.relative_to(source_dir).parts
            )
        ]
        return prefer or paths

    def _finish(candidates: List[Path]) -> Optional[Path]:
        candidates = _prefer_part(candidates)
        if len(candidates) == 1:
            found = candidates[0].relative_to(source_dir).as_posix()
            print(f"[sync] path moved: {relative_path} -> {found}")
            return candidates[0]
        if len(candidates) > 1:
            opts = ", ".join(
                p.relative_to(source_dir).as_posix() for p in candidates
            )
            raise FileNotFoundError(
                f"Ambiguous manuscript for {relative_path!r}; candidates: {opts}"
            )
        return None

    by_name = [p for p in source_dir.rglob(name) if p.is_file()]
    hit = _finish(by_name)
    if hit is not None:
        return hit

    stem_key = _manuscript_stem_key(name)
    if stem_key:
        parent_listed = (source_dir / rel).parent
        same_dir = []
        if parent_listed.is_dir():
            same_dir = [
                p
                for p in parent_listed.iterdir()
                if p.is_file()
                and p.suffix == ".md"
                and _manuscript_stem_key(p.name) == stem_key
            ]
        hit = _finish(same_dir)
        if hit is not None:
            return hit

        by_stem = [
            p
            for p in source_dir.rglob("*.md")
            if p.is_file() and _manuscript_stem_key(p.name) == stem_key
        ]
        # 导读/尾声在多个部分下会撞名：已用 part_key 收窄
        hit = _finish(by_stem)
        if hit is not None:
            return hit

    raise FileNotFoundError(f"Missing manuscript: {direct}")


def materialize_local_images(text, source_path, output_dir, written, changed):
    """Copy relative figure files next to the chapter into docs/<book>/figures/.

    Manuscript may use ``figures/foo.jpg`` (relative to the .md file). Generated
    pages live flat under the book docs dir, so links are rewritten to
    ``figures/<basename>``. Alt text may contain ``]`` (e.g. ``[]``), so parse
    with ``![`` … ``](`` … ``)`` rather than a naive character class.
    """
    parts = []
    i = 0
    while True:
        start = text.find("![", i)
        if start < 0:
            parts.append(text[i:])
            break
        mid = text.find("](", start + 2)
        if mid < 0:
            parts.append(text[i:])
            break
        end = text.find(")", mid + 2)
        if end < 0:
            parts.append(text[i:])
            break
        parts.append(text[i:start])
        alt = text[start + 2 : mid]
        raw = text[mid + 2 : end].strip()
        if raw.startswith(("http://", "https://", "/", "data:")):
            parts.append(text[start : end + 1])
        else:
            path_part = raw.split()[0].strip("\"'")
            src = (source_path.parent / path_part).resolve()
            if not src.is_file():
                raise FileNotFoundError(
                    f"Missing figure for {source_path.name}: {path_part}"
                )
            dst = output_dir / "figures" / src.name
            copy_asset(src, dst, written, changed)
            parts.append(f"![{alt}](figures/{src.name})")
        i = end + 1
    return "".join(parts)


def write_book(book, written, changed):
    source_dir = SOURCE / book["source"]
    output_dir = DOCS / book["directory"]
    page_number = 0
    kept_names = {"index.md"}

    for file_index, relative_path in enumerate(book["files"]):
        source_path = resolve_manuscript(source_dir, relative_path)
        text = materialize_local_images(
            source_path.read_text(encoding="utf-8"),
            source_path,
            output_dir,
            written,
            changed,
        )

        if file_index == 0:
            title = split_h1(text)[0][0]
            write_text(
                output_dir / "index.md",
                front_matter(title) + text,
                written,
                changed,
            )
            continue

        for title, section in split_h1(text):
            page_number += 1
            filename = f"{page_number:02d}.md"
            kept_names.add(filename)
            write_text(
                output_dir / filename,
                front_matter(title) + section,
                written,
                changed,
            )

    if output_dir.exists():
        for path in output_dir.glob("*.md"):
            if path.name not in kept_names:
                path.unlink()
                changed.add(path)


def prune_orphans(written, changed):
    if not DOCS.exists():
        return
    for path in DOCS.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix == ".tmp" or path.name.endswith(".tmp"):
            path.unlink()
            changed.add(path)
            continue
        if path.resolve() not in written:
            path.unlink()
            changed.add(path)
    for path in sorted(DOCS.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def _page_nav_title(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    m = re.search(r'(?m)^title:\s*"(.*)"\s*$', text)
    if m:
        return m.group(1).strip()
    m = re.search(r"(?m)^#\s+(.+?)\s*$", text)
    if m:
        return m.group(1).strip()
    return path.stem


def build_nav_yaml() -> str:
    """显式 nav：中文册名，避免侧栏出现 01 architecture。"""
    lines = ["nav:", '  - "现代大模型": index.md']
    for book in BOOKS:
        directory = book["directory"]
        title = book["title"].replace('"', '\\"')
        lines.append(f'  - "{title}":')
        lines.append(f"    - {directory}/index.md")
        pages = sorted((DOCS / directory).glob("[0-9][0-9].md"))
        for page in pages:
            page_title = _page_nav_title(page).replace('"', '\\"')
            lines.append(f'    - "{page_title}": {directory}/{page.name}')
    return "\n".join(lines) + "\n"


def write_mkdocs_nav() -> None:
    mkdocs = HERE / "mkdocs.yml"
    text = mkdocs.read_text(encoding="utf-8")
    begin, end = "# BEGIN_NAV", "# END_NAV"
    block = f"{begin}\n{build_nav_yaml()}{end}"
    if begin in text and end in text:
        text = re.sub(
            re.escape(begin) + r".*?" + re.escape(end),
            block,
            text,
            count=1,
            flags=re.S,
        )
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    mkdocs.write_text(text, encoding="utf-8")


def main():
    written = set()
    changed = set()
    (DOCS / "stylesheets").mkdir(parents=True, exist_ok=True)
    (DOCS / "javascripts").mkdir(parents=True, exist_ok=True)
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)

    write_text(DOCS / "index.md", HOME, written, changed)
    copy_asset(
        HERE / "assets" / "favicon.png",
        DOCS / "assets" / "favicon.png",
        written,
        changed,
    )
    copy_asset(
        HERE / "stylesheets" / "extra.css",
        DOCS / "stylesheets" / "extra.css",
        written,
        changed,
    )
    copy_asset(
        HERE / "javascripts" / "mathjax-config.js",
        DOCS / "javascripts" / "mathjax-config.js",
        written,
        changed,
    )
    copy_asset(
        HERE / "javascripts" / "formula-flow.js",
        DOCS / "javascripts" / "formula-flow.js",
        written,
        changed,
    )
    copy_asset(
        HERE / "javascripts" / "vendor" / "tex-mml-chtml.js",
        DOCS / "javascripts" / "vendor" / "tex-mml-chtml.js",
        written,
        changed,
    )

    for book in BOOKS:
        write_book(book, written, changed)

    prune_orphans(written, changed)
    write_mkdocs_nav()
    page_count = len(list(DOCS.rglob("*.md")))
    print(
        f"Generated {page_count} Markdown pages in {DOCS}"
        + (f" ({len(changed)} changed)" if changed else " (unchanged)")
    )
    return bool(changed)


if __name__ == "__main__":
    main()
