"""
文件路径: c:/Users/Administrator/Desktop/github新闻/builderpulse-news-site/generate_builderpulse_news.py
创建时间: 2026-04-17 15:27
上次修改时间: 2026-04-17 15:27
开发者: aidaox
"""

from __future__ import annotations

import datetime as dt  # 当前时间处理模块
import json  # JSON 序列化模块
import os  # 操作系统环境变量模块
import re  # 正则表达式模块
import subprocess  # 执行 git 命令模块
import sys  # 系统退出模块
from pathlib import Path  # 路径处理模块

import requests  # HTTP 请求模块


README_RAW_URL = "https://raw.githubusercontent.com/BuilderPulse/BuilderPulse/main/README.md"  # BuilderPulse 仓库 README 原始地址
DEFAULT_API_BASE = "https://token.n13.club/v1/chat/completions"  # 兼容 OpenAI 的聊天接口地址
DEFAULT_MODEL = "deepseek-reasoner-search"  # 默认调用的模型名称
DEFAULT_TARGET_REPO = "taofuli8/builderpulse-news-site"  # 默认推送的目标仓库
DEFAULT_OUTPUT_FILE = "index.html"  # 默认生成的 HTML 文件名


def fetch_builderpulse_readme(readme_url: str) -> str:
    """下载 BuilderPulse 的 README 全文。"""
    readme_response = requests.get(readme_url, timeout=60)  # 请求 README 文本
    readme_response.raise_for_status()  # 状态码非 200 时抛错
    return readme_response.text  # 返回 README 内容字符串


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
        "你是一个技术新闻编辑器。"
        "请把输入的 BuilderPulse 当日新闻整理成简洁、可读、可直接嵌入网页的 HTML 片段。"
        "要求: 仅输出 HTML 片段，不要输出 markdown 代码块，不要输出多余解释。"
        "结构要求: 一个 <section>，包含标题、日期、3-8条要点列表、1段结论。"
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
    return html_fragment  # 返回模型整理后的 HTML 片段


def build_full_html(news_html_fragment: str, generated_time_text: str) -> str:
    """拼装完整静态 HTML 页面内容。"""
    full_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BuilderPulse 每日新闻整理</title>
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
      max-width: 860px;
      margin: 0 auto;
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.06);
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
  </style>
</head>
<body>
  <main>
    <h1>BuilderPulse 每日新闻整理</h1>
    <p class="meta">生成时间（Asia/Shanghai）: {generated_time_text}</p>
    {news_html_fragment}
    <hr />
    <p class="meta">
      数据源:
      <a href="https://github.com/BuilderPulse/BuilderPulse/" target="_blank" rel="noreferrer">
        BuilderPulse/BuilderPulse
      </a>
    </p>
  </main>
</body>
</html>
"""
    return full_html  # 返回完整 HTML 文本


def run_command(command_args: list[str], working_dir: Path) -> str:
    """执行 shell 命令并在失败时抛错。"""
    completed_process = subprocess.run(
        command_args,
        cwd=str(working_dir),
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
    output_file_name: str,
    target_repo_full_name: str,
    github_token_value: str,
    commit_message: str,
) -> None:
    """提交并推送 HTML 文件到目标仓库。"""
    run_command(["git", "add", output_file_name], repo_dir)  # 暂存输出文件
    status_output = run_command(["git", "status", "--porcelain"], repo_dir)  # 检查是否有变更
    if not status_output:  # 没有变更时直接返回，不创建空提交
        print("内容无变化，跳过 commit/push。")
        return

    run_command(["git", "commit", "-m", commit_message], repo_dir)  # 创建提交
    push_url = f"https://{github_token_value}@github.com/{target_repo_full_name}.git"  # 临时带 token 的推送地址
    run_command(["git", "push", push_url, "HEAD:main"], repo_dir)  # 推送到 main 分支
    print("已成功推送到远端仓库。")


def main() -> None:
    """主流程：抓取 -> 模型整理 -> 生成HTML -> Git推送。"""
    api_key_value = os.getenv("N13_API_KEY", "").strip()  # 模型 API Key 环境变量
    github_token_value = os.getenv("GITHUB_TOKEN", "").strip()  # GitHub Token 环境变量
    api_base_url = os.getenv("N13_API_BASE", DEFAULT_API_BASE).strip()  # 模型 API 地址
    model_name = os.getenv("MODEL_NAME", DEFAULT_MODEL).strip()  # 模型名称
    target_repo_full_name = os.getenv("TARGET_REPO", DEFAULT_TARGET_REPO).strip()  # 目标仓库全名
    output_file_name = os.getenv("OUTPUT_FILE", DEFAULT_OUTPUT_FILE).strip()  # 输出 HTML 文件名

    if not api_key_value:  # API Key 缺失时终止
        raise EnvironmentError("缺少 N13_API_KEY 环境变量。")
    if not github_token_value:  # GitHub Token 缺失时终止
        raise EnvironmentError("缺少 GITHUB_TOKEN 环境变量。")

    working_dir = Path(__file__).resolve().parent  # 当前脚本所在目录
    output_file_path = working_dir / output_file_name  # 输出文件完整路径

    readme_text = fetch_builderpulse_readme(README_RAW_URL)  # 下载源 README
    latest_news_markdown = extract_latest_daily_block(readme_text)  # 提取当日新闻块
    news_html_fragment = call_deepseek_model(
        api_base_url=api_base_url,
        api_key_value=api_key_value,
        model_name=model_name,
        source_markdown=latest_news_markdown,
    )  # 模型整理

    now_time = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))  # 生成东八区时间
    generated_time_text = now_time.strftime("%Y-%m-%d %H:%M:%S")  # 格式化时间字符串
    full_html = build_full_html(news_html_fragment, generated_time_text)  # 拼装完整HTML
    output_file_path.write_text(full_html, encoding="utf-8")  # 写入 HTML 文件
    print(f"HTML 已生成: {output_file_path}")

    commit_message = f"chore: update BuilderPulse daily news ({now_time.strftime('%Y-%m-%d')})"  # 提交信息
    git_commit_and_push(
        repo_dir=working_dir,
        output_file_name=output_file_name,
        target_repo_full_name=target_repo_full_name,
        github_token_value=github_token_value,
        commit_message=commit_message,
    )  # 提交并推送


if __name__ == "__main__":
    try:
        main()  # 执行主流程
    except Exception as error:  # 捕获异常，打印并返回失败码
        print(f"执行失败: {error}", file=sys.stderr)
        sys.exit(1)
