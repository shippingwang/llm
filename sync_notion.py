#!/usr/bin/env python3
"""把书稿 Markdown 同步到 Notion（可反复跑：有 page_id 则整页覆盖，无则新建）。

依赖：仅标准库。需要环境变量：

  export NOTION_TOKEN='ntn_...'          # 或 NOTION_API_KEY
  export NOTION_PARENT_PAGE_ID='...'     # 可选；默认用已有第一册父页

用法：

  cd /picassox/intelligent-cpfs/human-body/wsp/research/现代大模型
  python3 sync_notion.py toc             # 子页「目录总览」← 00 目录总览.md（绝不覆盖父页正文）
  python3 sync_notion.py prologue        # 序章 案例：行程助手
  python3 sync_notion.py part1           # 第一部分：导读 + 第0–4章
  # 父页只保留子页链接；读者说明写在「目录总览」子页，不要往父页灌正文。

  python3 sync_notion.py part2           # 第二部分：导读 + 第5–8章
  python3 sync_notion.py part3           # 第三部分：导读 + 第9–10章
  python3 sync_notion.py part4           # 第四部分：导读 + 第11–13章
  python3 sync_notion.py part4 --dry-run # 只转换、不写 Notion

本地插图：书稿里 ``![说明](figures/xxx.jpg)`` 先写成正文占位符，整页
写入后再 File Upload + 块 API 插到对应位置（markdown 里直接写
file_upload id 会变成空的「Add an image」）。dry-run 不上传。

Integration 须能访问父页：Notion → 页面右上角 ··· → Connections → 添加你的 integration。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import sys
import time
import uuid
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
SRC = HERE / "书稿" / "第一册 现代大模型架构"
STATE_PATH = HERE / "notion_sync_state.json"
NOTION_VERSION = "2026-03-11"
API = "https://api.notion.com/v1"

# 上次已写入的第一册父页；可用环境变量覆盖
DEFAULT_PARENT = "3e99aa47-9603-81e2-80c9-cdbc3f5c6c7e"

# 目录总览书稿 → Notion 父页下的子页「目录总览」。禁止用 replace_content 覆盖父页
# （父页上的 child_page 块会被清掉，子页进回收站）。
TOC_REL = "目录总览.md"

# scope → 源文件列表。page_id 按「内容角色」对齐旧 Notion 页，不是旧章号字面。
SCOPES = {
    "toc": [
        TOC_REL,
    ],
    "prologue": [
        "序章 案例：行程助手.md",
    ],
    "part1": [
        "第一部分 基础组件与工程/导读.md",
        "第一部分 基础组件与工程/第0章 预备知识.md",
        "第一部分 基础组件与工程/第1章 语言模型.md",
        "第一部分 基础组件与工程/第2章 核心组件.md",
        "第一部分 基础组件与工程/第3章 组装训练.md",
        "第一部分 基础组件与工程/第4章 推理生成.md",
    ],
    "part2": [
        "第二部分 稠密模型/导读.md",
        "第二部分 稠密模型/第5章 稳定训练.md",
        "第二部分 稠密模型/第6章 rope.md",
        "第二部分 稠密模型/第7章 KV Cache 优化.md",
        "第二部分 稠密模型/第8章 组装稠密模型.md",
    ],
    "part3": [
        "第三部分 混合专家/导读.md",
        "第三部分 混合专家/第9章 MoE.md",
        "第三部分 混合专家/第10章 扩容.md",
    ],
    "part4": [
        "第四部分 长上下文/导读.md",
        "第四部分 长上下文/第11章 稀疏注意力.md",
        "第四部分 长上下文/第12章 线性注意力.md",
        "第四部分 长上下文/第13章 状态空间模型.md",
    ],
}

# 旧相对路径 → 现路径（改名后保留 Notion page_id）
PATH_RENAMES = {
    "第一部分 跑起来/导读.md": "第一部分 基础组件与工程/导读.md",
    "第一部分 跑起来/第0章 开始之前.md": "第一部分 基础组件与工程/第0章 预备知识.md",
    "第一部分 跑起来/第1章 语言模型.md": "第一部分 基础组件与工程/第1章 语言模型.md",
    "第一部分 跑起来/第2章 Transformer 组件.md": "第一部分 基础组件与工程/第2章 核心组件.md",
    "第一部分 跑起来/第3章 训练.md": "第一部分 基础组件与工程/第3章 组装训练.md",
    "第一部分 跑起来/第4章 推理.md": "第一部分 基础组件与工程/第4章 推理生成.md",
    "第二部分 稠密模型/第7章 优化kv cache.md": "第二部分 稠密模型/第7章 KV Cache 优化.md",
    "第二部分 稠密模型/第8章 合起来看.md": "第二部分 稠密模型/第8章 组装稠密模型.md",
    "第三部分 把模型做大/导读.md": "第三部分 混合专家/导读.md",
    "第三部分 把模型做大/第9章 MoE.md": "第三部分 混合专家/第9章 MoE.md",
    "第三部分 把模型做大/第10章 更大的架构设计.md": "第三部分 混合专家/第10章 扩容.md",
}

SEED_PAGE_IDS = {
    # part1
    "第一部分 基础组件与工程/导读.md": "3e99aa47-9603-817d-863e-f2feb2b665b3",
    "第一部分 基础组件与工程/第0章 预备知识.md": "3e99aa47-9603-8190-b0dd-f3fdff83a389",
    "第一部分 基础组件与工程/第1章 语言模型.md": "3e99aa47-9603-8164-b5b3-f83b79f7b4f5",
    "第一部分 基础组件与工程/第2章 核心组件.md": "3e99aa47-9603-8141-a4d0-e3e7815e6097",
    "第一部分 基础组件与工程/第3章 组装训练.md": "3f49aa47-9603-81c5-83b2-e433d7ee8b2f",
    "第一部分 基础组件与工程/第4章 推理生成.md": "3e99aa47-9603-8121-845d-fc6d7d0d9e0d",
    # part2
    "第二部分 稠密模型/导读.md": "3e99aa47-9603-8117-9e0d-cad70caebf4d",
    "第二部分 稠密模型/第5章 稳定训练.md": "3e99aa47-9603-815f-a03d-eb21a9f4a828",
    "第二部分 稠密模型/第6章 rope.md": "3e99aa47-9603-8193-91d5-cc387d3e589c",
    "第二部分 稠密模型/第7章 KV Cache 优化.md": "3e99aa47-9603-81bc-8482-de314ae81281",
    "第二部分 稠密模型/第8章 组装稠密模型.md": "3e99aa47-9603-8165-9a93-ff17d84604d0",
    # part3
    "第三部分 混合专家/导读.md": "3e99aa47-9603-81e8-864f-ea2ef806bf6b",
    "第三部分 混合专家/第9章 MoE.md": "3e99aa47-9603-81f9-bced-f8e2aaa15cf3",
    "第三部分 混合专家/第10章 扩容.md": "3e99aa47-9603-814d-8132-ec02bbc165ac",
    # part4
    "第四部分 长上下文/导读.md": "3e99aa47-9603-81e1-a2ef-e9319fa33c1d",
    "第四部分 长上下文/第11章 稀疏注意力.md": "3e99aa47-9603-81f8-aaa9-ea79358cd479",
    "第四部分 长上下文/第12章 线性注意力.md": "3e99aa47-9603-811d-87cf-fd3779c6cbfe",
    "第四部分 长上下文/第13章 状态空间模型.md": "3e99aa47-9603-810e-9dec-cb9f07a6989f",
}

ESCAPE_CHARS = "<>{}^~"


def normalize_page_id(raw: str) -> str:
    s = raw.strip()
    if "notion." in s:
        s = s.rstrip("/").split("?")[0].split("/")[-1]
        s = re.sub(r"^.*-([0-9a-f]{32})$", r"\1", s, flags=re.I)
        s = s.replace("-", "")
    hex32 = re.sub(r"[^0-9a-fA-F]", "", s)
    if len(hex32) != 32:
        raise ValueError(f"无法解析 page_id: {raw!r}")
    hex32 = hex32.lower()
    return f"{hex32[:8]}-{hex32[8:12]}-{hex32[12:16]}-{hex32[16:20]}-{hex32[20:]}"


def escape_text(seg: str) -> str:
    return "".join("\\" + ch if ch in ESCAPE_CHARS else ch for ch in seg)


def convert_inline(line: str) -> str:
    parts = re.split(r"(`[^`]*`)", line)
    result = []
    for part in parts:
        if part.startswith("`") and part.endswith("`") and len(part) >= 2:
            result.append(part)
            continue
        sub = re.split(r"(\\\(.*?\\\))", part)
        for s in sub:
            if s.startswith("\\(") and s.endswith("\\)"):
                result.append("$`" + s[2:-2].strip() + "`$")
            else:
                result.append(escape_text(s))
    return "".join(result)


def convert_table(rows: list[str]) -> list[str]:
    data = []
    for r in rows:
        cells_raw = r.strip().strip("|")
        if re.fullmatch(r"[\s|:\-]+", r.strip()):
            continue
        cells = [c.strip() for c in cells_raw.split("|")]
        data.append(cells)
    lines = ['<table header-row="true">']
    for cells in data:
        lines.append("\t<tr>")
        for c in cells:
            lines.append("\t\t<td>" + convert_inline(c) + "</td>")
        lines.append("\t</tr>")
    lines.append("</table>")
    return lines


# 整页 markdown 写入后，用块 API 替换该占位段落为真图
IMG_PLACEHOLDER_PREFIX = "@@NOTION_IMG@@ "


def _parse_image_line(line: str) -> Optional[tuple[str, str]]:
    """若整行是 ``![alt](path)``，返回 (alt, path)；否则 None。"""
    s = line.strip()
    if not s.startswith("!["):
        return None
    mid = s.find("](", 2)
    if mid < 0 or not s.endswith(")"):
        return None
    alt = s[2:mid]
    raw = s[mid + 2 : -1].strip()
    path_part = raw.split()[0].strip("\"'")
    if not path_part or path_part.startswith(("http://", "https://", "data:")):
        return None
    return alt, path_part


def _image_placeholder(rel: str, alt: str) -> str:
    # 路径与说明用罕见分隔，避免和正文撞车
    return "{}{}@@{}".format(IMG_PLACEHOLDER_PREFIX, rel, alt)


def _parse_image_placeholder(text: str) -> Optional[tuple[str, str]]:
    if not text.startswith(IMG_PLACEHOLDER_PREFIX):
        return None
    rest = text[len(IMG_PLACEHOLDER_PREFIX) :]
    if "@@" not in rest:
        return None
    rel, alt = rest.split("@@", 1)
    return rel, alt


def convert_markdown(
    text: str,
    source_path: Optional[Path] = None,
    embed_local_images: bool = False,
) -> tuple[str, str]:
    """返回 (title, notion_markdown_body)。首个 H1 作为标题并从正文去掉。

    ``embed_local_images=True`` 时，本地 ``![](figures/...)`` 写成占位段落，
    稍后由 ``materialize_page_images`` 上传并插入图片块。
    """
    lines = text.splitlines()
    title = None
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if title is None and line.startswith("# "):
            title = line[2:].strip()
            i += 1
            continue
        img = _parse_image_line(line)
        if img is not None:
            alt, rel = img
            if source_path is None:
                raise FileNotFoundError("插图需要 source_path: {}".format(rel))
            src = (source_path.parent / rel).resolve()
            if not src.is_file():
                raise FileNotFoundError(
                    "缺插图 {}（相对 {}）".format(rel, source_path)
                )
            if embed_local_images:
                out.append(_image_placeholder(rel, alt))
                print("  [图] 占位 {}".format(rel))
            else:
                out.append("![{}]({})".format(alt, rel))
                print("  [图] {} (dry-run，未上传)".format(rel))
            i += 1
            continue
        if line.strip().startswith("```"):
            out.append(line.strip())
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                out.append(lines[i])
                i += 1
            if i < n:
                out.append("```")
            i += 1
            continue
        if line.strip() == "\\[":
            buf = []
            i += 1
            while i < n and lines[i].strip() != "\\]":
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("$$")
            out.extend(buf)
            out.append("$$")
            continue
        if line.strip().startswith("|"):
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i])
                i += 1
            out.extend(convert_table(rows))
            continue
        if line.startswith(">"):
            parts = []
            while i < n and lines[i].startswith(">"):
                body = lines[i][1:].strip()
                if body:
                    parts.append(convert_inline(body))
                i += 1
            out.append("> " + "<br>".join(parts))
            continue
        if line.strip() == "---":
            out.append("---")
            i += 1
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = min(len(m.group(1)), 3)
            out.append("#" * level + " " + convert_inline(m.group(2)))
            i += 1
            continue
        m = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)$", line)
        if m:
            indent = m.group(1).replace("    ", "\t").replace("  ", "\t")
            marker = "-" if m.group(2) == "*" else m.group(2)
            out.append(indent + marker + " " + convert_inline(m.group(3)))
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        out.append(convert_inline(line))
        i += 1
    if not title:
        raise ValueError("书稿缺少一级标题 # ...")
    return title, "\n".join(out) + "\n"


def load_state() -> dict:
    if STATE_PATH.is_file():
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    else:
        data = {"parent_page_id": DEFAULT_PARENT, "pages": {}}
    pages = data.setdefault("pages", {})
    for old, new in PATH_RENAMES.items():
        if old in pages and new not in pages:
            pages[new] = pages.pop(old)
        elif old in pages and new in pages:
            pages.pop(old, None)
    for rel, pid in SEED_PAGE_IDS.items():
        pages.setdefault(rel, {"page_id": pid})
    data.setdefault("parent_page_id", DEFAULT_PARENT)
    return data


def save_state(state: dict) -> None:
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _title_props(title: str) -> dict:
    return {
        "title": {
            "title": [{"type": "text", "text": {"content": title[:2000]}}],
        }
    }


class NotionAPIError(RuntimeError):
    def __init__(self, method, path, status, body):
        self.method = method
        self.path = path
        self.status = status
        self.body = body if isinstance(body, dict) else {}
        self.code = self.body.get("code")
        msg = self.body.get("message") or str(body)
        super().__init__(
            "Notion {} {} -> {}: {}".format(method, path, status, msg)
        )

    @property
    def not_found(self):
        return self.status == 404 or self.code == "object_not_found"


class NotionClient:
    def __init__(self, token: str, allow_async: bool = False, upload_cache: Optional[dict] = None):
        self.token = token
        self.allow_async = allow_async
        # sha256 -> file_upload_id（首次挂到页面后可复用）
        self.upload_cache = upload_cache if upload_cache is not None else {}

    def _request(self, method: str, path: str, body=None, data=None, extra_headers=None) -> dict:
        url = path if path.startswith("http") else API + path
        headers = {
            "Authorization": "Bearer {}".format(self.token),
            "Notion-Version": NOTION_VERSION,
        }
        if data is None:
            data = None if body is None else json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except Exception:
                payload = {"message": raw}
            raise NotionAPIError(method, path, e.code, payload) from e

    def upload_file(self, path: Path) -> str:
        """Direct Upload（≤20MB），返回 file_upload id。"""
        path = path.resolve()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        cached = self.upload_cache.get(digest)
        if cached:
            return cached

        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        meta = self._request(
            "POST",
            "/file_uploads",
            {
                "filename": path.name,
                "content_type": content_type,
                "mode": "single_part",
            },
        )
        upload_id = meta["id"]
        upload_url = meta.get("upload_url") or "{}/file_uploads/{}/send".format(
            API, upload_id
        )
        boundary = "----NotionBoundary{}".format(uuid.uuid4().hex)
        file_bytes = path.read_bytes()
        if len(file_bytes) > 20 * 1024 * 1024:
            raise RuntimeError(
                "插图超过 20MB，需改 multi_part：{}".format(path)
            )
        body = b"".join(
            [
                "--{}\r\n".format(boundary).encode(),
                (
                    'Content-Disposition: form-data; name="file"; filename="{}"\r\n'
                    .format(path.name)
                ).encode(),
                "Content-Type: {}\r\n\r\n".format(content_type).encode(),
                file_bytes,
                "\r\n--{}--\r\n".format(boundary).encode(),
            ]
        )
        sent = self._request(
            "POST",
            upload_url,
            data=body,
            extra_headers={
                "Content-Type": "multipart/form-data; boundary={}".format(boundary),
            },
        )
        if sent.get("object") == "file_upload" and sent.get("status") == "uploaded":
            pass
        elif sent.get("status") not in (None, "uploaded"):
            if sent.get("object") != "file_upload":
                raise RuntimeError("上传失败: {}".format(sent))
        self.upload_cache[digest] = upload_id
        return upload_id

    def iter_block_children(self, block_id: str):
        cursor = None
        while True:
            path = "/blocks/{}/children?page_size=100".format(block_id)
            if cursor:
                path += "&start_cursor={}".format(cursor)
            data = self._request("GET", path)
            for block in data.get("results") or []:
                yield block
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                break

    def delete_block(self, block_id: str) -> dict:
        return self._request("DELETE", "/blocks/{}".format(block_id))

    def append_image_after(
        self, parent_id: str, after_block_id: str, upload_id: str, caption: str
    ) -> dict:
        caption_rt = []
        if caption:
            caption_rt = [
                {"type": "text", "text": {"content": caption[:2000]}},
            ]
        body = {
            "children": [
                {
                    "type": "image",
                    "image": {
                        "type": "file_upload",
                        "file_upload": {"id": upload_id},
                        "caption": caption_rt,
                    },
                }
            ],
            "position": {
                "type": "after_block",
                "after_block": {"id": after_block_id},
            },
        }
        return self._request("PATCH", "/blocks/{}/children".format(parent_id), body)

    def materialize_page_images(self, page_id: str, source_path: Path) -> int:
        """把占位段落换成已上传图片块。返回替换张数。"""
        jobs = []
        prev_id = None
        for block in self.iter_block_children(page_id):
            bid = block.get("id")
            if block.get("type") == "paragraph":
                texts = block.get("paragraph", {}).get("rich_text") or []
                plain = "".join(t.get("plain_text") or "" for t in texts)
                parsed = _parse_image_placeholder(plain.strip())
                if parsed:
                    rel, alt = parsed
                    jobs.append((bid, prev_id, rel, alt))
            if bid:
                prev_id = bid

        n_ok = 0
        # 自下而上替换，避免连续占位时 after 指向已删块
        for placeholder_id, after_id, rel, alt in reversed(jobs):
            src = (source_path.parent / rel).resolve()
            if not src.is_file():
                raise FileNotFoundError(
                    "缺插图 {}（相对 {}）".format(rel, source_path)
                )
            upload_id = self.upload_file(src)
            # 占位段先删，插到「前一块」后面；若无前一块则插到页首
            self.delete_block(placeholder_id)
            if after_id:
                self.append_image_after(page_id, after_id, upload_id, alt)
            else:
                self._request(
                    "PATCH",
                    "/blocks/{}/children".format(page_id),
                    {
                        "children": [
                            {
                                "type": "image",
                                "image": {
                                    "type": "file_upload",
                                    "file_upload": {"id": upload_id},
                                    "caption": [
                                        {
                                            "type": "text",
                                            "text": {"content": alt[:2000]},
                                        }
                                    ]
                                    if alt
                                    else [],
                                },
                            }
                        ],
                        "position": {"type": "start"},
                    },
                )
            print("  [图] {} -> 已插入".format(rel))
            n_ok += 1
            time.sleep(0.25)
        return n_ok

    def get_page(self, page_id: str) -> dict:
        return self._request("GET", "/pages/{}".format(page_id))

    def page_accessible(self, page_id: str) -> bool:
        try:
            self.get_page(page_id)
            return True
        except NotionAPIError as e:
            if e.not_found:
                return False
            raise

    def create_page(self, parent_id: str, title: str, markdown: str) -> dict:
        md = "# {}\n\n{}".format(title, markdown)
        body = {
            "parent": {"page_id": parent_id},
            "properties": _title_props(title),
            "markdown": md,
        }
        if self.allow_async:
            body["allow_async"] = True
        return self._request("POST", "/pages", body)

    def replace_content(self, page_id: str, markdown: str) -> dict:
        body = {
            "type": "replace_content",
            "replace_content": {
                "new_str": markdown,
                "allow_deleting_content": True,
            },
        }
        if self.allow_async:
            body["allow_async"] = True
        return self._request("PATCH", "/pages/{}/markdown".format(page_id), body)

    def set_title(self, page_id: str, title: str) -> dict:
        return self._request(
            "PATCH",
            "/pages/{}".format(page_id),
            {"properties": _title_props(title)},
        )

    def wait_task(self, task: dict, label: str) -> dict:
        """若响应是 async_task，则轮询到结束，返回终态任务对象。"""
        if task.get("object") != "async_task":
            return task
        task_id = task.get("id")
        if not task_id:
            raise RuntimeError("async_task 无 id: {}".format(task))
        for _ in range(90):
            delay = int(task.get("poll_after_seconds") or 2)
            time.sleep(max(delay, 1))
            info = self._request("GET", "/async_tasks/{}".format(task_id))
            status = info.get("status")
            if status == "succeeded":
                return info
            if status == "failed":
                raise RuntimeError("异步任务失败 ({}): {}".format(label, info))
            task = info
        raise RuntimeError("异步任务超时 ({}): {}".format(label, task_id))


def resolve_created_page_id(resp: dict, client: NotionClient) -> str:
    if resp.get("object") == "page" and resp.get("id"):
        return normalize_page_id(resp["id"])
    done = client.wait_task(resp, "create")
    if done.get("object") == "page" and done.get("id"):
        return normalize_page_id(done["id"])
    result = done.get("result") or {}
    if isinstance(result, dict):
        pid = result.get("id") or result.get("page_id")
        if pid:
            return normalize_page_id(pid)
    raise RuntimeError("创建页响应里找不到 page_id: {}".format(done or resp))


def _share_hint(parent_id: str) -> str:
    url = "https://www.notion.so/{}".format(parent_id.replace("-", ""))
    return (
        "请打开父页 → 右上角 ··· → Connections → 添加 integration「llm_book」：\n"
        "  {}\n"
        "只连父页即可；子页会随父页授权。连好后重跑。\n"
        "若要用别的父页：export NOTION_PARENT_PAGE_ID='你的父页id'"
    ).format(url)


def sync_files(rels, dry_run, create_missing, allow_async, fresh):
    state = load_state()
    parent = normalize_page_id(
        os.environ.get("NOTION_PARENT_PAGE_ID") or state.get("parent_page_id") or DEFAULT_PARENT
    )
    state["parent_page_id"] = parent

    token = os.environ.get("NOTION_TOKEN") or os.environ.get("NOTION_API_KEY")
    if not dry_run and not token:
        print(
            "缺少 NOTION_TOKEN（或 NOTION_API_KEY）。\n"
            "到 https://www.notion.so/my-integrations 建 integration，复制 secret，\n"
            "再在父页 Connections 里接入该 integration。",
            file=sys.stderr,
        )
        return 2

    uploads = state.setdefault("uploads", {})
    client = (
        NotionClient(token, allow_async=allow_async, upload_cache=uploads)
        if token
        else None
    )
    pages = state.setdefault("pages", {})
    if fresh:
        for rel in rels:
            pages.pop(rel, None)
        print("[fresh] 忽略已有 page_id，全部在父页下新建")

    # 若误把目录总览绑到父页 id，清掉，避免再次 replace_content 父页
    toc_entry = pages.get(TOC_REL) or {}
    if normalize_page_id(toc_entry.get("page_id") or "") == parent:
        pages.pop(TOC_REL, None)
        print("[安全] 已解除 00 目录总览.md 与父页的错误绑定，将新建子页")

    if client is not None and not dry_run:
        if not client.page_accessible(parent):
            print(
                "父页对当前 integration 不可见（404）。\n" + _share_hint(parent),
                file=sys.stderr,
            )
            return 3
        print("父页 OK: {}".format(parent))

    ok = 0

    for rel in rels:
        path = SRC / rel
        if not path.is_file():
            print("[缺文件] {}".format(rel), file=sys.stderr)
            return 1
        print("— {}".format(rel))
        title, body = convert_markdown(
            path.read_text(encoding="utf-8"),
            source_path=path,
            embed_local_images=not dry_run,
        )
        if rel == TOC_REL:
            # 子页标题用「目录总览」，避免和父页同名；正文仍含书稿全文
            title = "目录总览"
        entry = pages.get(rel) or {}
        page_id = entry.get("page_id")
        print("  title: {}  ({} chars)".format(title, len(body)))

        if dry_run:
            preview = HERE / ".notion_preview" / (rel.replace("/", "__"))
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_text("TITLE: {}\n{}".format(title, body), encoding="utf-8")
            print("  dry-run -> {}".format(preview))
            ok += 1
            continue

        assert client is not None
        updated = False
        if page_id:
            page_id = normalize_page_id(page_id)
            if client.page_accessible(page_id):
                print("  update {}".format(page_id))
                try:
                    client.set_title(page_id, title)
                    resp = client.replace_content(page_id, body)
                    client.wait_task(resp, rel)
                    updated = True
                except NotionAPIError as e:
                    if not e.not_found:
                        raise
                    print("  旧页突然 404，改为新建")
            else:
                print("  旧 page_id 不可见，改为新建")
                page_id = None

        if not updated:
            if not create_missing:
                print(
                    "[跳过] 无可用 page_id 且未开 --create-missing: {}".format(rel),
                    file=sys.stderr,
                )
                continue
            print("  create under {}".format(parent))
            try:
                resp = client.create_page(parent, title, body)
            except NotionAPIError as e:
                if e.not_found:
                    print(
                        "在父页下新建失败（父页未分享给 integration）。\n"
                        + _share_hint(parent),
                        file=sys.stderr,
                    )
                    return 3
                raise
            page_id = resolve_created_page_id(resp, client)
            print("  created {}".format(page_id))

        n_img = client.materialize_page_images(page_id, path)
        if n_img:
            print("  插入插图 {} 张".format(n_img))

        pages[rel] = {
            "page_id": page_id,
            "title": title,
            "url": "https://www.notion.so/{}".format(page_id.replace("-", "")),
        }
        state["uploads"] = client.upload_cache
        save_state(state)
        ok += 1
        time.sleep(0.35)

    print("\n完成 {}/{}。状态: {}".format(ok, len(rels), STATE_PATH))
    print("父页: https://www.notion.so/{}".format(parent.replace("-", "")))
    return 0


def main():
    p = argparse.ArgumentParser(description="同步书稿到 Notion")
    p.add_argument(
        "scope",
        choices=sorted(SCOPES.keys()),
        help="同步范围：{}".format(", ".join(sorted(SCOPES.keys()))),
    )
    p.add_argument("--dry-run", action="store_true", help="只转换到 .notion_preview/")
    p.add_argument(
        "--create-missing",
        dest="create_missing",
        action="store_true",
        default=True,
        help="无 page_id 时新建子页（默认开）",
    )
    p.add_argument(
        "--no-create-missing",
        dest="create_missing",
        action="store_false",
        help="无 page_id 时跳过，不新建",
    )
    p.add_argument(
        "--fresh",
        action="store_true",
        help="忽略已记录的 page_id，全部在父页下新建（适合换父页/旧映射失效）",
    )
    p.add_argument(
        "--async",
        dest="allow_async",
        action="store_true",
        help="大页用 Notion allow_async + 轮询（一般不必开）",
    )
    args = p.parse_args()
    return sync_files(
        SCOPES[args.scope],
        dry_run=args.dry_run,
        create_missing=args.create_missing,
        allow_async=args.allow_async,
        fresh=args.fresh,
    )


if __name__ == "__main__":
    raise SystemExit(main())
