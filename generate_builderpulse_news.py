"""
文件路径: c:/Users/Administrator/Desktop/github新闻/builderpulse-news-site/generate_builderpulse_news.py
创建时间: 2026-04-17 15:27
上次修改时间: 2026-04-17 16:10
开发者: aidaox
"""

from __future__ import annotations

import datetime as dt  # 当前时间处理模块
import hashlib  # 哈希计算模块
import json  # JSON 序列化模块
import os  # 操作系统环境变量模块
import re  # 正则表达式模块
import subprocess  # 执行 git 命令模块
import sys  # 系统退出模块
from html import escape  # HTML 转义模块
from pathlib import Path  # 路径处理模块

import requests  # HTTP 请求模块


README_RAW_URL = "https://raw.githubusercontent.com/BuilderPulse/BuilderPulse/main/README.md"  # BuilderPulse 仓库 README 原始地址
DAILY_FILE_RAW_BASE = "https://raw.githubusercontent.com/BuilderPulse/BuilderPulse/main"  # BuilderPulse 每日文件 RAW 基础地址
DAILY_FILE_WEB_BASE = "https://github.com/BuilderPulse/BuilderPulse/blob/main"  # BuilderPulse 每日文件网页基础地址
DEFAULT_API_BASE = "https://token.n13.club/v1/chat/completions"  # 兼容 OpenAI 的聊天接口地址
DEFAULT_MODEL = "deepseek-reasoner-search"  # 默认调用的模型名称
DEFAULT_TARGET_REPO = "taofuli8/builderpulse-news-site"  # 默认推送的目标仓库
DEFAULT_SITE_URL = "https://taofuli8.github.io/builderpulse-news-site/"  # 默认站点访问地址
DEFAULT_SOURCE_LANG = "zn"  # 默认抓取语言目录（zn 会自动映射为 zh）
DEFAULT_STATE_FILE = "state/source_state.json"  # 源内容哈希状态文件路径


def fetch_builderpulse_readme(readme_url: str) -> str:
    """下载 BuilderPulse 的 README 全文。"""
    readme_response = requests.get(readme_url, timeout=60)  # 请求 README 文本
    readme_response.raise_for_status()  # 状态码非 200 时抛错
    return readme_response.text  # 返回 README 内容字符串


def fetch_daily_markdown_file(source_lang: str, date_text: str) -> str:
    """优先按日期抓取 BuilderPulse 当天明细 Markdown。"""
    lang_alias_map = {"zn": "zh", "cn": "zh"}  # 用户习惯写法到仓库目录的映射表
    normalized_lang = lang_alias_map.get(source_lang.lower(), source_lang.lower())  # 标准化语言目录
    year_text = date_text[:4]  # 从日期提取年份目录
    daily_raw_url = f"{DAILY_FILE_RAW_BASE}/{normalized_lang}/{year_text}/{date_text}.md"  # 拼接当天文件地址
    daily_response = requests.get(daily_raw_url, timeout=60)  # 请求当天明细文件
    daily_response.raise_for_status()  # 非 200 状态码抛错
    return daily_response.text  # 返回当天完整 markdown 正文


def build_source_web_url(source_lang: str, date_text: str) -> str:
    """拼接当天源文件的 GitHub 网页地址。"""
    lang_alias_map = {"zn": "zh", "cn": "zh"}  # 用户习惯写法到仓库目录的映射表
    normalized_lang = lang_alias_map.get(source_lang.lower(), source_lang.lower())  # 标准化语言目录
    year_text = date_text[:4]  # 从日期提取年份目录
    source_web_url = f"{DAILY_FILE_WEB_BASE}/{normalized_lang}/{year_text}/{date_text}.md"  # 构造 GitHub 网页 URL
    return source_web_url  # 返回源文件网页地址


def extract_latest_daily_block(readme_text: str) -> str:
    """从 README 中提取当日新闻区块。"""
    section_pattern = re.compile(
        r"##\s*📰.*?(?=\n##\s|\Z)",
        flags=re.DOTALL,
    )  # 匹配“今日新闻”主区块的正则
    section_match = section_pattern.search(readme_text)  # 搜索第一个新闻区块
    if section_match is None:  # 如果没有匹配到，说明源格式发生变化
        raise ValueError("未在 README 中找到每日新闻区块，请检查源格式是否变更。")
    latest_block = section_match.group(0).strip()  # 提取并去除首尾空白
    return latest_block  # 返回“今日新闻”Markdown片段


def call_deepseek_model(
    api_base_url: str,
    api_key_value: str,
    model_name: str,
    source_markdown: str,
) -> str:
    """调用 deepseek 模型，将 Markdown 片段整理为 HTML 片段。"""
    system_prompt = (
        "你是一个技术新闻主编。"
        "请将输入的 BuilderPulse 当日新闻重写为清晰、可读、层级分明的中文日报 HTML。"
        "你必须只输出 HTML 片段，不允许输出 markdown、代码块、解释说明。"
        "输出结构必须严格包含: "
        "1个<section>根节点；"
        "1个<h2>今日核心结论；"
        "1个<ul>（3到6条，短句要点）；"
        "1个<h3>今日可执行动作；"
        "1个<ol>（2到4条，具体行动）；"
        "1个<h3>风险与观察；"
        "1个<ul>（2到4条）。"
        "禁止整段照抄原文；每条尽量不超过45个中文字符。"
    )  # 系统提示词
    user_prompt = f"请整理以下内容:\n\n{source_markdown}"  # 用户提示词

    request_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key_value}",
    }  # 请求头
    request_payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }  # 请求体

    model_response = requests.post(
        api_base_url,
        headers=request_headers,
        data=json.dumps(request_payload),
        timeout=120,
    )  # 发送模型请求
    model_response.raise_for_status()  # 非 200 抛错
    response_json = model_response.json()  # 解析 JSON
    choices_list = response_json.get("choices", [])  # 读取候选结果列表
    if not choices_list:  # 没有候选时抛错
        raise ValueError(f"模型返回为空: {response_json}")
    html_fragment = choices_list[0]["message"]["content"].strip()  # 提取第一条内容
    html_fragment = re.sub(r"^```(?:html)?\s*", "", html_fragment, flags=re.IGNORECASE)  # 清理可能的代码块起始标记
    html_fragment = re.sub(r"\s*```$", "", html_fragment)  # 清理可能的代码块结束标记
    return html_fragment  # 返回模型整理后的 HTML 片段


def compute_text_sha256(content_text: str) -> str:
    """计算文本内容的 SHA256 哈希。"""
    content_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()  # 计算 UTF-8 文本哈希
    return content_hash  # 返回十六进制哈希字符串


def read_state_map(state_file_path: Path) -> dict[str, str]:
    """读取源内容状态映射（date -> hash）。"""
    if not state_file_path.exists():  # 状态文件不存在时返回空映射
        return {}
    try:
        raw_state_text = state_file_path.read_text(encoding="utf-8")  # 读取状态文件文本
        loaded_state = json.loads(raw_state_text)  # 解析 JSON
        if isinstance(loaded_state, dict):  # 只接受对象结构
            return {str(k): str(v) for k, v in loaded_state.items()}  # 统一键值为字符串
        return {}
    except Exception:
        return {}  # 解析失败时回退为空映射


def write_state_map(state_file_path: Path, state_map: dict[str, str]) -> None:
    """写入源内容状态映射（date -> hash）。"""
    state_file_path.parent.mkdir(parents=True, exist_ok=True)  # 确保状态目录存在
    serialized_state = json.dumps(state_map, ensure_ascii=False, indent=2)  # 序列化 JSON 文本
    state_file_path.write_text(serialized_state + "\n", encoding="utf-8")  # 写入状态文件


def build_archive_index_map(repo_dir: Path) -> dict[str, dict[str, list[str]]]:
    """扫描仓库中的历史 HTML 文件，生成按年月分组的日期列表。"""
    archive_map: dict[str, dict[str, list[str]]] = {}  # 年份 -> 月份 -> 日期列表 的映射
    daily_file_pattern = re.compile(
        r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<date>\d{4}-\d{2}-\d{2})\.html$"
    )  # 识别 yyyy/mm/yyyy-mm-dd.html
    for html_path in repo_dir.rglob("*.html"):  # 遍历仓库所有 html 文件
        relative_path_text = html_path.relative_to(repo_dir).as_posix()  # 转成相对路径字符串
        matched = daily_file_pattern.match(relative_path_text)  # 判断是否日报文件
        if matched is None:  # 非日报文件直接跳过
            continue
        year_text = matched.group("year")  # 提取年份目录
        month_text = matched.group("month")  # 提取月份目录
        date_text = matched.group("date")  # 提取日期文件名
        archive_map.setdefault(year_text, {}).setdefault(month_text, []).append(date_text)  # 累加入年月分组列表

    for year_text in archive_map:  # 对每年每月日期按新到旧排序
        for month_text in archive_map[year_text]:
            archive_map[year_text][month_text] = sorted(archive_map[year_text][month_text], reverse=True)
    return archive_map  # 返回整理后的归档映射


def build_daily_html(
    news_html_fragment: str,
    generated_time_text: str,
    source_web_url: str,
    current_year_text: str,
    current_month_text: str,
    archive_dates: list[str],
) -> str:
    """拼装单日页面 HTML（含历史切换导航）。"""
    history_links_html = "\n".join(
        [
            f'<li><a href="{escape(date_text)}.html">{escape(date_text)}</a></li>'
            for date_text in archive_dates
        ]
    )  # 历史日期链接列表 HTML
    daily_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BuilderPulse 中文日报整理</title>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      background: #f7f7fb;
      color: #111827;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.7;
    }}
    main {{
      max-width: 1080px;
      margin: 0 auto;
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.06);
      display: grid;
      grid-template-columns: 1fr 260px;
      gap: 24px;
    }}
    h1 {{
      margin-top: 0;
      font-size: 28px;
      line-height: 1.3;
    }}
    .meta {{
      color: #6b7280;
      font-size: 14px;
      margin-bottom: 16px;
    }}
    a {{
      color: #2563eb;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    .panel {{
      position: sticky;
      top: 16px;
      align-self: start;
      border-left: 1px solid #e5e7eb;
      padding-left: 16px;
    }}
    .panel ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .panel li {{
      margin: 4px 0;
    }}
  </style>
</head>
<body>
  <main>
    <section>
      <h1>BuilderPulse 中文日报整理</h1>
      <p class="meta">生成时间（Asia/Shanghai）: {generated_time_text}</p>
      {news_html_fragment}
      <hr />
      <p class="meta">
        原始来源:
        <a href="{escape(source_web_url)}" target="_blank" rel="noreferrer">
          当天原文
        </a>
      </p>
    </section>
    <aside class="panel">
      <h3>{escape(current_year_text)}-{escape(current_month_text)} 历史日报</h3>
      <ul>
        {history_links_html}
      </ul>
      <p class="meta"><a href="../../index.html">返回首页归档</a></p>
    </aside>
  </main>
</body>
</html>
"""
    return daily_html  # 返回单日 HTML 文本


def build_root_index_html(archive_index_map: dict[str, dict[str, list[str]]]) -> str:
    """生成根目录首页归档 HTML。"""
    year_sections_html_list: list[str] = []  # 每个年份区块 HTML 列表
    for year_text in sorted(archive_index_map.keys(), reverse=True):  # 从新到旧遍历年份
        month_sections_html_list: list[str] = []  # 年份内月份区块列表
        for month_text in sorted(archive_index_map[year_text].keys(), reverse=True):  # 从新到旧遍历月份
            date_links_html = "\n".join(
                [
                    f'<li><a href="{escape(year_text)}/{escape(month_text)}/{escape(date_text)}.html">{escape(date_text)}</a></li>'
                    for date_text in archive_index_map[year_text][month_text]
                ]
            )  # 月份内日报链接列表
            month_sections_html_list.append(
                f"<details><summary>{escape(year_text)}-{escape(month_text)}</summary><ul>{date_links_html}</ul></details>"
            )  # 追加月份折叠区块
        merged_month_sections_html = "\n".join(month_sections_html_list)  # 合并该年月份区块
        year_sections_html_list.append(
            f"<section><h2>{escape(year_text)}</h2>{merged_month_sections_html}</section>"
        )  # 追加年份区块

    merged_year_sections_html = "\n".join(year_sections_html_list)  # 合并所有年份区块
    index_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BuilderPulse 中文日报归档</title>
  <style>
    body {{
      margin: 0;
      padding: 24px;
      background: #f7f7fb;
      color: #111827;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.7;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.06);
    }}
    h1 {{ margin-top: 0; }}
    ul {{ margin-top: 8px; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <main>
    <h1>BuilderPulse 中文日报归档</h1>
    <p>按年份查看每日整理内容：</p>
    {merged_year_sections_html}
  </main>
</body>
</html>
"""
    return index_html  # 返回首页归档 HTML


def run_command(command_args: list[str], working_dir: Path) -> str:
    """执行 shell 命令并在失败时抛错。"""
    command_env = os.environ.copy()  # 复制当前环境变量用于子进程
    if command_env.get("GIT_AUTHOR_NAME") is None:  # 未设置作者名时使用默认值
        command_env["GIT_AUTHOR_NAME"] = command_env.get("GIT_USER_NAME", "aidaox")
    if command_env.get("GIT_COMMITTER_NAME") is None:  # 未设置提交者名时使用默认值
        command_env["GIT_COMMITTER_NAME"] = command_env.get("GIT_USER_NAME", "aidaox")
    if command_env.get("GIT_AUTHOR_EMAIL") is None:  # 未设置作者邮箱时使用默认值
        command_env["GIT_AUTHOR_EMAIL"] = command_env.get("GIT_USER_EMAIL", "aidaox@example.com")
    if command_env.get("GIT_COMMITTER_EMAIL") is None:  # 未设置提交者邮箱时使用默认值
        command_env["GIT_COMMITTER_EMAIL"] = command_env.get("GIT_USER_EMAIL", "aidaox@example.com")

    completed_process = subprocess.run(
        command_args,
        cwd=str(working_dir),
        env=command_env,
        capture_output=True,
        text=True,
        check=False,
    )  # 执行命令
    if completed_process.returncode != 0:  # 非 0 返回码抛错
        raise RuntimeError(
            f"命令执行失败: {' '.join(command_args)}\n"
            f"stdout:\n{completed_process.stdout}\n"
            f"stderr:\n{completed_process.stderr}"
        )
    return completed_process.stdout.strip()  # 返回标准输出


def git_commit_and_push(
    repo_dir: Path,
    output_file_paths: list[str],
    target_repo_full_name: str,
    github_token_value: str,
    commit_message: str,
) -> None:
    """提交并推送 HTML 文件到目标仓库。"""
    run_command(["git", "add", *output_file_paths], repo_dir)  # 暂存输出文件列表
    status_output = run_command(["git", "status", "--porcelain"], repo_dir)  # 检查是否有变更
    if not status_output:  # 没有变更时直接返回，不创建空提交
        print("内容无变化，跳过 commit/push。")
        return

    run_command(["git", "commit", "-m", commit_message], repo_dir)  # 创建提交
    push_url = f"https://{github_token_value}@github.com/{target_repo_full_name}.git"  # 临时带 token 的推送地址
    run_command(["git", "push", push_url, "HEAD:main"], repo_dir)  # 推送到 main 分支
    print("已成功推送到远端仓库。")


def push_wechat_notification(wechat_push_url: str, site_url: str, generated_time_text: str) -> None:
    """推送更新通知到微信（通过第三方微信推送URL）。"""
    if not wechat_push_url:  # 未配置微信推送地址时直接跳过
        print("未配置 WECHAT_PUSH_URL，跳过微信推送。")
        return

    notify_title = "BuilderPulse 每日新闻已更新"  # 微信通知标题
    notify_body = (
        f"更新时间: {generated_time_text}\n"
        f"访问地址: {site_url}\n"
        "说明: 该消息由定时任务自动发送。"
    )  # 微信通知正文

    if "sctapi.ftqq.com" in wechat_push_url:  # 兼容 Server酱接口格式
        response = requests.post(
            wechat_push_url,
            data={"title": notify_title, "desp": notify_body},
            timeout=30,
        )  # 发送Server酱表单请求
    else:  # 兼容通用 webhook json 格式
        response = requests.post(
            wechat_push_url,
            json={"title": notify_title, "content": notify_body, "url": site_url},
            timeout=30,
        )  # 发送Webhook JSON请求

    response.raise_for_status()  # 请求失败时抛错
    print("微信推送已发送。")


def main() -> None:
    """主流程：抓取 -> 模型整理 -> 生成HTML -> Git推送。"""
    api_key_value = os.getenv("N13_API_KEY", "").strip()  # 模型 API Key 环境变量
    github_token_value = os.getenv("GITHUB_TOKEN", "").strip()  # GitHub Token 环境变量
    api_base_url = os.getenv("N13_API_BASE", DEFAULT_API_BASE).strip()  # 模型 API 地址
    model_name = os.getenv("MODEL_NAME", DEFAULT_MODEL).strip()  # 模型名称
    target_repo_full_name = os.getenv("TARGET_REPO", DEFAULT_TARGET_REPO).strip()  # 目标仓库全名
    site_url = os.getenv("SITE_URL", DEFAULT_SITE_URL).strip()  # 页面访问地址
    wechat_push_url = os.getenv("WECHAT_PUSH_URL", "").strip()  # 微信推送URL
    source_lang = os.getenv("SOURCE_LANG", DEFAULT_SOURCE_LANG).strip() or DEFAULT_SOURCE_LANG  # 新闻源语言目录

    if (not api_key_value) or ("请填写" in api_key_value):  # API Key 缺失或还是模板值时终止
        raise EnvironmentError("缺少 N13_API_KEY 环境变量。")
    if (not github_token_value) or ("请填写" in github_token_value):  # GitHub Token 缺失或还是模板值时终止
        raise EnvironmentError("缺少 GITHUB_TOKEN 环境变量。")

    working_dir = Path(__file__).resolve().parent  # 当前脚本所在目录
    now_time = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))  # 生成东八区时间
    source_date_text = now_time.strftime("%Y-%m-%d")  # 生成当天日期文本
    source_year_text = source_date_text[:4]  # 生成当天年份目录文本
    source_month_text = source_date_text[5:7]  # 生成当天月份目录文本
    state_file_path = working_dir / DEFAULT_STATE_FILE  # 状态文件完整路径
    try:
        latest_news_markdown = fetch_daily_markdown_file(
            source_lang=source_lang,
            date_text=source_date_text,
        )  # 优先抓取当天明细文件
        print(f"已使用当天明细文件: {source_lang}/{source_year_text}/{source_date_text}.md")
    except Exception:  # 当天文件不存在时按用户要求提示“没有更新”
        print("今日暂无更新。")
        return

    state_map = read_state_map(state_file_path=state_file_path)  # 读取历史哈希状态映射
    source_content_hash = compute_text_sha256(latest_news_markdown)  # 计算当天源文档哈希
    previous_hash = state_map.get(source_date_text, "")  # 读取当天上次哈希值
    if previous_hash == source_content_hash:  # 若源内容未变化则短路退出
        print("今日暂无更新。")
        return

    news_html_fragment = call_deepseek_model(
        api_base_url=api_base_url,
        api_key_value=api_key_value,
        model_name=model_name,
        source_markdown=latest_news_markdown,
    )  # 模型整理

    generated_time_text = now_time.strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间字符串
    source_web_url = build_source_web_url(source_lang=source_lang, date_text=source_date_text)  # 构造源文件网页地址
    month_dir_path = working_dir / source_year_text / source_month_text  # 年月目录路径
    month_dir_path.mkdir(parents=True, exist_ok=True)  # 若年月目录不存在则创建
    daily_html_path = month_dir_path / f"{source_date_text}.html"  # 当天页面输出路径

    archive_index_map = build_archive_index_map(working_dir)  # 扫描已有历史归档
    archive_index_map.setdefault(source_year_text, {}).setdefault(source_month_text, [])  # 确保当前年月存在
    if source_date_text not in archive_index_map[source_year_text][source_month_text]:  # 确保当日日期存在
        archive_index_map[source_year_text][source_month_text].append(source_date_text)
    archive_index_map[source_year_text][source_month_text] = sorted(
        archive_index_map[source_year_text][source_month_text], reverse=True
    )  # 当月日期新到旧排序

    daily_html = build_daily_html(
        news_html_fragment=news_html_fragment,
        generated_time_text=generated_time_text,
        source_web_url=source_web_url,
        current_year_text=source_year_text,
        current_month_text=source_month_text,
        archive_dates=archive_index_map[source_year_text][source_month_text],
    )  # 生成单日页面 HTML
    daily_html_path.write_text(daily_html, encoding="utf-8")  # 写入单日页面文件

    root_index_html = build_root_index_html(archive_index_map=archive_index_map)  # 生成首页归档 HTML
    root_index_path = working_dir / "index.html"  # 首页文件路径
    root_index_path.write_text(root_index_html, encoding="utf-8")  # 写入首页归档文件
    print(f"HTML 已生成: {daily_html_path}")

    state_map[source_date_text] = source_content_hash  # 更新当天哈希值
    write_state_map(state_file_path=state_file_path, state_map=state_map)  # 写入状态文件

    commit_message = f"chore: update BuilderPulse daily news ({now_time.strftime('%Y-%m-%d')})"  # 提交信息
    git_commit_and_push(
        repo_dir=working_dir,
        output_file_paths=[daily_html_path.relative_to(working_dir).as_posix(), "index.html", DEFAULT_STATE_FILE],
        target_repo_full_name=target_repo_full_name,
        github_token_value=github_token_value,
        commit_message=commit_message,
    )  # 提交并推送
    push_wechat_notification(
        wechat_push_url=wechat_push_url,
        site_url=site_url,
        generated_time_text=generated_time_text,
    )  # 发送微信通知


if __name__ == "__main__":
    try:
        main()  # 执行主流程
    except Exception as error:  # 捕获异常，打印并返回失败码
        print(f"执行失败: {error}", file=sys.stderr)
        sys.exit(1)
