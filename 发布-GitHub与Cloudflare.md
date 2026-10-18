# 发布：GitHub → Cloudflare Pages → shippingwang.com

本机不直接上传。换网络后按下面做。

## 1. 建 GitHub 仓库并上传

1. 打开 https://github.com/new  
2. 仓库名随意（如 `modern-llm-book`），**Public**（免费 CF/Pages 都好用）  
3. **不要**勾选 Add README（空仓）  
4. 把 `现代大模型-github.zip` 解压，得到文件夹 `现代大模型/`  
5. 任选一种上传：

**图形界面：** 打开仓库 → uploading an existing file → 把解压后的**内容**拖进去  
（最终仓库根目录应能看到 `书稿/`、`网站/`、`.github/`，不要多套一层多余目录名搞乱路径；若解压后多了一层 `现代大模型`，上传的是里面那一层。）

**命令行（本机已装 git）：**

```bash
cd 现代大模型   # 解压后的那一层，能看到 书稿/ 网站/
git init
git add .
git commit -m "Initial import: manuscripts and MkDocs site"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git push -u origin main
```

## 2. Cloudflare Pages 关联 GitHub

1. https://dash.cloudflare.com/?to=/:account/workers-and-pages  
2. **创建** → **Pages** → **连接 Git** → 授权 GitHub → 选刚建的仓库  
3. 构建设置：

| 项 | 值 |
|----|-----|
| 生产分支 | `main` |
| 构建命令 | `pip install -r 网站/requirements.txt && python 网站/sync_content.py && mkdocs build --strict --config-file 网站/mkdocs.yml` |
| 构建输出目录 | `网站/site` |
| 根目录 | `/`（仓库根） |

环境变量如有 Python 版本选项，选 **3.11** 或 **3.12**。

4. 保存并部署，记下 `*.pages.dev` 地址，能打开首页即可。

## 3. 绑域名 shippingwang.com

同一 Pages 项目 → **自定义域** → 添加：

- `shippingwang.com`
- `www.shippingwang.com`（可选）

Cloudflare 会自动写 DNS。回到域名 **DNS → 记录** 应出现 CNAME，不用手填。  
**SSL/TLS** 用「完全（严格）」。

## 说明

- 只改 `书稿/`，push 到 `main` 后 Pages 会自动重建。  
- 仓库里的 `.github/workflows/deploy-pages.yml` 是 **GitHub Pages** 用的；你走 Cloudflare 可以先不管它（或之后删掉以免混用）。  
- `网站/docs/`、`网站/site/` 由构建生成，不必手改。
