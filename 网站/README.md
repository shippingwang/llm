# 书稿网站

这是三册书稿的 MkDocs Material 站点模板。`../书稿/` 是唯一内容源，`docs/` 为自动生成目录。

## 本地预览

```bash
cd 网站
python3 -m pip install -r requirements.txt
python3 dev_serve.py
```

打开 `http://127.0.0.1:8000`。

`dev_serve.py` 会监听 `../书稿/`（以及本目录的样式/脚本），改完书稿约 0.6 秒内自动同步到 `docs/`，MkDocs 再热刷新页面。不必再手动跑 `sync_content.py`。

## 本地构建

```bash
cd 网站
python3 sync_content.py
mkdocs build --strict
```

静态网站输出到 `网站/site/`。CI / 正式发布仍用一次性同步 + `mkdocs build`。

## 发布到 Cloudflare Pages（当前域名 shippingwang.com）

域名 DNS 已在 Cloudflare 时，用 Pages 最省事。

### 方式 A：直接上传（最快上线）

```bash
cd 网站
python3 sync_content.py
python3 -m mkdocs build --strict
# 将 site/ 目录内容打成 zip 上传，或 Wrangler 推送
```

1. Cloudflare 仪表盘 → **Workers 和 Pages** → **Create** → **Pages** → **Upload assets**
2. 项目名随意（如 `llm-book`），上传 `网站/site/` 里的文件（或 zip）
3. 部署成功后进项目 → **自定义域** → 添加 `shippingwang.com` 和 `www.shippingwang.com`
4. Cloudflare 会自动写 DNS；回到 **DNS → 记录** 应能看到指向本 Pages 项目的 CNAME
5. **SSL/TLS** 用「完全（严格）」

### 方式 B：连接 Git（以后改书稿自动发布）

仓库根目录为 `现代大模型/`（含 `书稿/`、`网站/`）。Pages 构建设置：

| 项 | 值 |
|----|-----|
| 构建命令 | `pip install -r 网站/requirements.txt && python 网站/sync_content.py && mkdocs build --strict --config-file 网站/mkdocs.yml` |
| 输出目录 | `网站/site` |

### GitHub Pages（备选）

仓库根目录应为 `现代大模型/`，其中包含：

```text
现代大模型/
├── .github/workflows/deploy-pages.yml
├── 书稿/
└── 网站/
```

推送到 `main` 后：Settings → Pages → Source = GitHub Actions。

## 内容更新

只编辑 `书稿/`。发布流程会运行 `sync_content.py`，把多章节文件拆成独立网页并按阅读顺序排列。
