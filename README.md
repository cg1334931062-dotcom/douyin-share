# Douyin Computer Use PoC

一个“安全优先、可回归”的抖音自动化 PoC。  
主入口是 `examples/run_real_site_once.py --mode scan`，核心目标是稳定跑通：

1. 直播/非直播识别
2. 非直播互动量提取（点赞/转发）
3. 规则化分享判定
4. 命中后才触发 AI 分析与评论流程
5. 运行日志输出（终端 + 可选窗口）

## 1. 项目定位

这个项目是“半自动助手”而不是“无人值守刷量器”。

- 默认高风险动作是关闭的
- 不包含验证码绕过、风控规避、批量垃圾行为
- 建议先小轮次回归，再开启真实分享/发送
- 请确保使用方式符合平台规则与本地法律法规

## 2. 当前能力（`scan` 模式）

每轮处理逻辑（按当前实现）：

1. 打开推荐流卡片并判断是否直播
2. 如果是直播：等待 `--live-wait-seconds` 后滑到下一条
3. 如果是非直播：读取右侧互动指标（点赞/转发）
4. 按规则判断是否“值得分享”
5. 仅在命中分享条件时，进入评论区并执行 AI 分析 + AI 评论草稿
6. 视参数决定是否真实发送评论、是否真实执行分享
7. 输出每轮日志（含 `share_result`、`task_status`、互动指标等）

## 3. 核心规则（2026-04 当前）

### 3.1 广告过滤规则

- 仅 `author-area ad badge`（`广告`）作为广告判定依据
- 命中广告直接不分享（`share_result=skip_ad`）

### 3.2 分享判定规则

先计算：

- `like_count`（点赞数）
- `share_count`（转发数）
- `ratio = share_count / like_count`

规则：

- `like_count < 1000` 时不分享
- 否则满足任一条件可分享：
  - `share_count > 200000`
  - `ratio > 0.5`

### 3.3 AI 触发规则

- 非直播但未命中分享条件：不进评论链路
- 仅“分享候选”进入 AI 分析与评论生成

## 4. 仓库结构

```text
.
├── src/douyin_agent/
│   ├── browser_playwright.py         # 真实站点浏览器适配（评论/分享/提取）
│   ├── classifier.py                 # 内容分类（直播/非直播）
│   ├── commenting.py                 # 评论生成/策略模块（workflow 用）
│   ├── models.py                     # 数据结构
│   └── state_machine.py              # workflow runner
├── examples/
│   ├── run_real_site_once.py         # 主入口（推荐）
│   └── run_fake_demo.py              # 本地假浏览器演示
├── configs/                          # 提示词与策略文件
├── tools/run_scan_gui.py             # GUI 启动器（中文界面）
├── tests/                            # 单元测试
├── PROJECT_HANDOFF.md                # 当前业务规则与交接说明（重要）
├── SHARE_GUIDE.md                    # 对外分享建议
└── skills/douyin-scan-share/         # Skill 模板
```

## 5. 环境准备

要求：

- Python `>= 3.11`
- macOS / Linux（Windows 可尝试，未重点验证）
- Playwright Chromium

安装：

```bash
cd /Users/elewave/Desktop/CLI_Folder/douyin_computer_use_poc
python3 -m pip install -e .
python3 -m pip install playwright
python3 -m playwright install chromium
```

可选：如果 Linux 没有 Tk，GUI 可能无法打开，需要安装 `python3-tk`。

### 5.1 Windows 一键安装脚本

仓库内置 Windows 一键安装脚本：

- `tools/install_windows_oneclick.ps1`

功能：

- 自动检测 Python（`py -3.11` / `py -3` / `python` / `python3`）
- 校验 Python 版本是否 `>= 3.11`
- 自动执行：
  - `pip install --upgrade pip`
  - `pip install -e .`
  - `pip install playwright`
  - `python -m playwright install chromium`

使用方式（Windows PowerShell）：

```powershell
cd <your-repo>\douyin_computer_use_poc
.\tools\install_windows_oneclick.ps1
```

如果你只想安装 Python 依赖、不下载浏览器，可执行：

```powershell
.\tools\install_windows_oneclick.ps1 -SkipPlaywright
```

## 6. API Key 配置

CLI 默认读取：

- `--llm-api-key-env`（默认 `OPENAI_API_KEY`）

你可以用 `.env` 或 shell 环境变量管理 Key，例如：

```bash
export OPENAI_API_KEY="your_openai_key"
export DEEPSEEK_API_KEY="your_deepseek_key"
```

说明：

- CLI 默认 `--llm-api-base=https://api.openai.com/v1`、`--llm-model=gpt-4.1-mini`
- GUI 默认是 DeepSeek 组合（`https://api.deepseek.com/v1` + `deepseek-chat`）
- GUI 在“评论@好友”模式下会检查可用 API Key（环境变量 / `.env` / 明文输入）

## 7. 快速开始

### 7.1 首次先做登录引导

```bash
python3 examples/run_real_site_once.py \
  --login-only \
  --require-login \
  --login-timeout 180 \
  --profile-dir .playwright_profile_main
```

### 7.2 安全扫描（推荐起步）

特点：

- 只做识别、互动量提取与分享判定
- 不进入评论链路
- 不做真实分享

```bash
OPENAI_API_KEY="<YOUR_KEY>" python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 20 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --wait-scale 1.6 \
  --live-wait-seconds 3 \
  --video-wait-seconds 10 \
  --post-next-settle-seconds 8 \
  --snapshot-settle-seconds 2
```

### 7.3 命中分享条件但不开启真实分享（只跑评论链路）

用于验证评论链路，不触发分享动作：

```bash
OPENAI_API_KEY="<YOUR_KEY>" python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 20 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --comment-by-content \
  --use-ai-comment \
  --comment-without-share
```

### 7.4 开启真实分享（高风险，先小轮次）

```bash
OPENAI_API_KEY="<YOUR_KEY>" python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 5 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --comment-by-content \
  --use-ai-comment \
  --enable-share \
  --share-target "你的群名"
```

### 7.5 `@好友` 评论（命中分享条件时）

支持输入 `@张三 @李四` 或 `张三,李四`，会自动规范化和去重：

```bash
OPENAI_API_KEY="<YOUR_KEY>" python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 10 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --comment-by-content \
  --use-ai-comment \
  --comment-without-share \
  --comment-mention-friend "@张三 @李四"
```

注意：

- `@好友` 依赖 AI 评论内容；AI 不可用时会 `skip_need_ai_comment`
- 真正发送评论仍需 `--enable-post`

## 8. GUI 启动器

```bash
python3 tools/run_scan_gui.py
```

GUI 功能：

- 中文参数面板（轮次、等待、profile、LLM、分享目标等）
- 一键启动/停止 + 实时日志
- 一键复制当前命令（便于 CLI 复现）
- 支持“不开分享但按分享条件评论”
- 支持“启用真实评论发送”
- 支持“评论好友（逗号分隔，@+AI）”

## 9. 运行模式说明

### 9.1 `--mode scan`（推荐）

真实站点扫描流程，包含：

- 内容判断
- 互动量提取
- 分享门控
- AI 评论/分享动作

### 9.2 `--mode workflow`

本地 workflow runner（策略机）路径，主要用于策略与状态机验证，不是当前主线回归模式。

## 10. 常用参数速查（`examples/run_real_site_once.py`）

### 10.1 基础参数

- `--iterations`: 轮次（默认 `1`）
- `--profile-dir`: 浏览器用户目录（默认 `.playwright_profile`）
- `--require-login`: 强制要求登录态
- `--headless`: 无头模式
- `--no-log-window`: 关闭运行日志窗口（scan 模式默认会开）
- `--wait-scale`: 全局等待倍率（默认 `3.0`）
- `--live-wait-seconds`: 直播等待时长（默认 `3`）
- `--video-wait-seconds`: 非直播等待时长（默认 `10`）
- `--post-next-settle-seconds`: 下滑后稳定等待（默认 `8`）
- `--snapshot-settle-seconds`: 抓取前稳定等待（默认 `2`）

### 10.2 评论/AI 参数

- `--comment-by-content`: 开启按内容评论链路
- `--comment-style humorous|neutral`: 评论风格
- `--use-ai-comment` / `--no-ai-comment`: 开关 AI 评论
- `--enable-post`: 真实发送评论（默认关闭，默认是 dry-run）
- `--comment-mention-friend`: `@好友` 列表

### 10.3 LLM 参数

- `--llm-api-base`: OpenAI 兼容基地址
- `--llm-model`: 模型名
- `--llm-api-key-env`: API Key 环境变量名
- `--llm-insecure-skip-verify`: 跳过 TLS 校验（当前默认开启）
- `--llm-verify`: 开启 TLS 校验（与上项互斥）
- `--llm-debug`: 打印 LLM 请求错误

### 10.4 分享参数

- `--enable-share`: 真实分享开关
- `--share-target`: 目标好友/群名（填写后走“分享给指定对象”路径）
- `--share-all`: 非直播全部分享（绕过分享评估，慎用）
- `--comment-without-share`: 分享关掉时仍在“命中分享条件的视频”执行评论链路

### 10.5 兼容/历史参数

- `--scan-report-csv`: 已废弃，传入会被忽略
- `--share-strong-only`: 已废弃，当前不生效

## 11. 日志与状态解读

常见 `share_result`：

- `shared`: 已分享成功
- `share_failed`: 分享动作执行失败
- `skip_low_engagement`: 未通过互动量门槛
- `skip_ad`: 广告卡片被过滤
- `disabled`: 当前未启用分享或仅评论模式

常见 `task_status`：

- `live_skipped`: 直播跳过
- `ok_generated`: 评论已生成（dry-run）
- `ok_posted`: 评论已真实发送
- `post_failed`: 评论发送失败
- `context_not_found`: 视频上下文不足
- `ai_unavailable`: AI 不可用（Key/网络/API）
- `skip_need_ai_comment`: 开了 `@好友` 但未拿到可用 AI 评论

## 12. 常见问题

### 12.1 `login check failed`

- 先单独跑 `--login-only`
- 保证 `--profile-dir` 固定并可复用
- 检查是否因二维码过期导致登录态失效

### 12.2 AI 一直不可用

- 检查 `--llm-api-key-env` 对应环境变量是否存在
- 检查 `--llm-api-base` / `--llm-model` 是否匹配服务商
- 需要定位错误时加 `--llm-debug`
- 网络证书环境异常时可暂用 `--llm-insecure-skip-verify`

### 12.3 评论没发出去

- 默认是 dry-run，需显式加 `--enable-post`
- 查看日志中的 `comment_result` / `task_status`
- 若出现 `panel_not_open`，通常是页面结构变化或加载不稳定

### 12.4 为什么没有 CSV 文件

- `--scan-report-csv` 已被策略禁用，当前版本不会写 CSV

## 13. 测试

运行单元测试：

```bash
pytest -q
```

当前测试主要覆盖：

- 分类逻辑（`test_classifier.py`）
- 评论策略（`test_comment_policy.py`）
- 状态机（`test_state_machine.py`）

不包含真实站点端到端自动化回归。

## 14. 相关文档

- 交接与业务规则：`PROJECT_HANDOFF.md`
- 分享方式建议：`SHARE_GUIDE.md`
- Skill 模板：`skills/douyin-scan-share/SKILL.md`

如果在新会话让 AI 按既有规则执行，建议先让它读取 `PROJECT_HANDOFF.md`。
