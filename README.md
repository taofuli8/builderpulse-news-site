# BuilderPulse 中文日报镜像站

在线访问地址：`https://taofuli8.github.io/builderpulse-news-site/`

## 项目背景

原项目 [BuilderPulse/BuilderPulse](https://github.com/BuilderPulse/BuilderPulse/) 很优秀，核心价值非常明确：

- 每天固定时间从 Hacker News / GitHub / Product Hunt / HuggingFace / Google Trends / Reddit 等多源聚合信息；
- 给独立开发者输出“今天该做什么”的行动建议；
- 提供中英文日报，且按日期持续更新。

## 原始痛点（本项目为什么存在）

虽然原始日报内容质量很高，但直接阅读有几个不方便点：

1. 原文信息密度大，用户快速浏览成本高；
2. 原仓库阅读体验偏文档流，不够适合“日报归档站点化浏览”；
3. 想看历史内容时，缺少更直观的“站点内切换”体验。

## 本项目做了什么

这个项目做的是 **“结构不改源、阅读体验增强”**：

1. 每天优先抓取当天中文明细文件（`zn` 自动映射到 `zh`，例如 `zh/2026/2026-04-17.md`）；
2. 调用 `deepseek-reasoner-search` 对当天内容进行二次整理，生成更适合阅读的 HTML；
3. 站点按“年/月/日”归档保存，例如：
   - `2026/04/2026-04-17.html`
   - `2026/04/2026-04-18.html`
4. 每天页面内可直接切换本年度历史日报；
5. 增加 `state/source_state.json` 记录 `date -> hash`；
6. 如果当天源文件不存在或内容哈希未变化，则只提示：`今日暂无更新。`

## 页面结构说明

- 根首页：`/index.html`
  - 展示按“年份 -> 月份”分组的历史日报入口
- 每日页：`/YYYY/MM/YYYY-MM-DD.html`
  - 展示当天整理后的正文
  - 右侧展示该月份历史日期，支持快速切换

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

先复制模板：

```bash
cp .env.example .env
```

关键变量说明：

- `N13_API_KEY`：你在 `token.n13.club` 的模型访问 key
- `GITHUB_TOKEN`：有仓库写权限的 fine-grained token
- `N13_API_BASE`：默认 `https://token.n13.club/v1/chat/completions`
- `MODEL_NAME`：默认 `deepseek-reasoner-search`
- `TARGET_REPO`：默认 `taofuli8/builderpulse-news-site`
- `SITE_URL`：默认 `https://taofuli8.github.io/builderpulse-news-site/`
- `SOURCE_LANG`：默认 `zn`（脚本内部自动映射到 `zh` 目录）

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

## 4) 定时执行建议

你当前已切到 OpenClaw 定时任务，不再推荐系统 crontab。

建议保持每天 `11:05` 执行（晚于源站 11:00 更新），避免抓到旧内容。

## 5) 运行行为

- 每次执行会优先抓取当天中文明细文件；
- 每次执行会先做源文件哈希校验（`state/source_state.json`）；
- 成功后会更新：
  - 当天页 `YYYY/MM/YYYY-MM-DD.html`
  - 根首页 `index.html`
- 然后自动 `git commit` + `git push` 到目标仓库；
- 若当天源文件不存在，或当天内容哈希未变化，输出 `今日暂无更新。` 并结束；
- 在“暂无更新”路径下，不会调用大模型，不会提交 git，不会推送微信消息。

## 6) 致谢

再次说明：本项目不是替代 [BuilderPulse/BuilderPulse](https://github.com/BuilderPulse/BuilderPulse/)，而是面向中文阅读场景做“再整理 + 归档站点化展示”。
