# BuilderPulse 每日新闻自动站点

这个项目用于：

1. 抓取 [BuilderPulse/BuilderPulse](https://github.com/BuilderPulse/BuilderPulse/) 的每日最新新闻；
2. 调用 `deepseek-reasoner-search` 整理内容；
3. 生成 `index.html`；
4. 自动 `git commit` + `git push` 到你的公开仓库，供 GitHub Pages 展示。

## 1) 准备环境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 2) 配置环境变量

复制模板：

```bash
cp .env.example .env
```

把 `.env` 中的 `N13_API_KEY` 和 `GITHUB_TOKEN` 改成你自己的值。

## 3) 首次运行

Windows PowerShell:

```powershell
$env:N13_API_KEY="你的N13Key"
$env:GITHUB_TOKEN="你的GitHubToken"
python .\generate_builderpulse_news.py
```

Linux / PVE:

```bash
export N13_API_KEY="你的N13Key"
export GITHUB_TOKEN="你的GitHubToken"
python3 ./generate_builderpulse_news.py
```

## 4) PVE 定时任务（每天 11:05）

建议比源站更新时间（11:00）晚 5 分钟执行，避免抓到旧内容。

```cron
5 11 * * * cd /opt/builderpulse-news-site && /usr/bin/python3 generate_builderpulse_news.py >> /var/log/builderpulse-news.log 2>&1
```

## 5) 说明

- `generate_builderpulse_news.py` 默认会推送到 `taofuli8/builderpulse-news-site`。
- 你可以通过环境变量 `TARGET_REPO` 覆盖目标仓库。
- 脚本只会提交 `index.html`，当内容无变化时不会产生新提交。
