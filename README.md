# 全网找‘屎’专家

一个“安全优先、可回归”的抖音自动化 PoC，主要用于从推荐流里筛出适合转给好友的搞笑 / 怪诞 / 幽默视频，并半自动完成评论与分享。内部 Python 模块兼容名仍为 `douyin_agent`。  
主入口是 `examples/run_real_site_once.py --mode scan`，核心目标是稳定跑通：

1. 直播/非直播识别
2. 非直播互动量提取（点赞/转发）
3. 规则化筛出“值得发给好友”的搞笑候选
4. 命中后才触发 AI 分析、评论草稿与分享动作
5. 运行日志输出（终端 + 可选窗口）

## 1. 项目定位

这个项目是“搞笑视频筛选与好友分享助手”，不是“无人值守刷量器”。

- 默认高风险动作是关闭的
- 不包含验证码绕过、风控规避、批量垃圾行为
- 目标是把值得转发的离谱、怪诞、幽默视频送到好友/群，而不是泛化抓取所有内容
- 建议先小轮次回归，再开启真实分享/发送
- 请确保使用方式符合平台规则与本地法律法规

## 2. 当前能力（`scan` 模式）

围绕“找出适合分享给好友的搞笑 / 怪诞 / 幽默视频”，每轮处理逻辑（按当前实现）：

1. 打开推荐流卡片并判断是否直播
2. 如果是直播：等待 `--live-wait-seconds` 后滑到下一条
3. 如果是非直播：读取右侧互动指标（点赞/转发）
4. 按规则判断是否“值得转给好友”
5. 仅在命中分享条件时，进入评论区并执行 AI 分析 + AI 评论草稿
6. 视参数决定是否真实发送评论、是否真实执行分享给指定好友/群
7. 输出每轮日志（含 `share_result`、`task_status`、互动指标等）

## 3. 核心规则（2026-04 当前）

### 3.1 广告过滤规则

- 仅 `author-area ad badge`（`广告`）作为广告判定依据
- 命中广告直接硬拦截，不评论、不提及、不分享（`share_result=skip_ad`）
- 额外兜底：若文本或 AI 内容画像命中明显推广/带货信号，也会跳过（`share_result=skip_promo`）

### 3.1.1 直播硬规则

- 沿用原有直播判定逻辑；命中后直接硬拦截，不评论、不提及、不分享
- 不额外引入分类器或普通 DOM 文本的新增直播判定条件

### 3.2 分享判定规则

作为“是否值得转给好友”的第一层筛选，先计算：

- `like_count`（点赞数）
- `share_count`（转发数）
- `ratio = share_count / like_count`

默认规则来自 `configs/share_rules.toml`，GUI 会读取这份配置，CLI 也可用参数覆盖。

当前默认值：

- `like_count < 1000` 时不分享
- 否则满足任一条件可分享：
  - `share_count > 200000`
  - `ratio > 0.5`

### 3.3 AI 触发规则

- 非直播但未命中分享条件：不进评论链路
- 仅“分享候选”进入 AI 分析与评论生成
- 评论风格默认围绕幽默表达，适合好友间转发场景

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
└── skills/quanwang-zhao-shi-zhuanjia/ # Skill 模板
```

## 5. 环境准备

要求：

- Python `>= 3.11`
- macOS / Linux（Windows 可尝试，未重点验证）
- Playwright Chromium

安装：

```bash
cd /Users/elewave/Desktop/CLI_Folder/quanwang_zhao_shi_zhuanjia
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
cd <your-repo>\quanwang_zhao_shi_zhuanjia
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

## 7. 快速开始（GUI 推荐）

### 7.1 启动 GUI

```bash
python3 tools/run_scan_gui.py
```

GUI 是这个项目最适合日常使用的入口，适合“找搞笑视频 -> 判断值不值得发给好友 -> 决定是否评论/分享”的完整流程。

界面提供：

- 中文参数面板（轮次、等待、profile、LLM、分享目标、分享阈值等）
- `开始扫描` / `停止`
- `复制命令`（把当前 GUI 配置转成 CLI 命令）
- 实时日志窗口，方便看登录、每轮判断、评论结果和分享结果

### 7.2 首次使用流程

推荐按下面顺序上手：

1. 打开 GUI 后，保留 `要求已登录` 勾选，先不要勾 `无头模式`
2. `浏览器配置目录` 先用默认 `.playwright_profile_main`
3. 首次建议保持 `启用分享` 关闭、`启用真实评论发送` 关闭
4. 点 `开始扫描` 后，如果当前未登录，程序会自动打开浏览器并等待手动登录
5. 登录成功后，扫描会继续执行；日志里会看到 `[login] 已检测到登录成功`

注意：

- 勾选 `无头模式` 时，若当前还没登录，无法手动完成登录
- `浏览器配置目录` 决定登录态复用；不要频繁切换目录，否则每次都可能重新登录

### 7.3 三套最常用的 GUI 配置

#### A. 安全扫描搞笑候选

适合先观察系统会把哪些视频当作“值得转给好友”的候选。

- 保持 `启用分享` 关闭
- 保持 `不开分享但按分享条件评论` 关闭
- 保持 `启用真实评论发送` 关闭
- `要求已登录` 保持开启
- 其余参数先用默认值即可

这套配置下，程序会做直播识别、互动量提取和分享候选判断，但不会真的发评论或分享。

#### B. 只验证幽默评论链路

适合验证“命中分享条件的视频，能否生成适合好友场景的幽默评论草稿”。

- 开启 `按内容评论`
- 开启 `使用 AI 评论`
- 开启 `不开分享但按分享条件评论`
- 保持 `启用分享` 关闭
- 保持 `启用真实评论发送` 关闭

这套配置会在命中分享条件时生成评论草稿，但不会真实分享，也不会真实发评论。

#### C. 真实分享给好友或群

适合小轮次实战。

- 开启 `启用分享`
- 在 `分享目标` 填好友名或群名
- 如果只想分享，不想真的发评论：保持 `启用真实评论发送` 关闭
- 如果想把评论也真实发出去：再额外开启 `启用真实评论发送`

这里有一个关键区别：

- `启用分享` 控制“是否真实执行分享动作”
- `启用真实评论发送` 只控制“评论是否真的点发送”

也就是说，你可以“真实分享，但评论只生成不发送”。

### 7.4 GUI 字段和开关说明

常用输入框：

- `扫描轮数`：本次扫描多少轮，首次建议 `5` 到 `20`
- `浏览器配置目录`：浏览器用户数据目录，用来复用登录态，建议长期固定
- `等待倍率`：页面慢时增大，默认 `1.6` 是当前推荐值
- `直播停留秒数` / `视频停留秒数`：控制每轮节奏
- `分享目标`：仅在勾选 `启用分享` 时生效
- `评论好友（逗号分隔，@+AI）`：支持 `@张三 @李四` 或 `张三,李四`
- `LLM 接口地址` / `LLM 模型` / `API Key`：AI 评论生成配置，GUI 默认是 DeepSeek 组合

常用开关：

- `要求已登录`：推荐一直开启
- `按内容评论`：允许进入评论分析链路
- `使用 AI 评论`：允许调用模型生成评论
- `启用分享`：真实执行分享
- `不开分享但按分享条件评论`：分享关闭时，仍对命中条件的视频生成评论
- `启用真实评论发送`：把生成好的评论真正发出去；默认关闭
- `无头模式`：只有在登录态已经稳定复用时再开
- `关闭日志窗口`：关闭运行时弹出的独立日志窗
- `跳过 TLS 证书校验（不安全）`：当前默认开启，用于兼容部分环境证书问题

### 7.5 GUI 日志怎么看

你主要看这几类输出：

- `[login] ...`：登录等待、登录成功或登录超时
- `[round N] ...`：每一轮的视频判断结果
- `share_result=shared|skip_live|skip_low_engagement|skip_ad|skip_promo|disabled`：分享是否发生，以及为什么没发生
- `comment_result=generated_only|posted|post_failed|panel_not_open`：评论是只生成了、真实发出了，还是失败了
- `[gui] 启动命令: ...`：当前 GUI 配置对应的 CLI 命令，可直接复现问题

如果你要复盘某次运行，先点 `复制命令`，再把那条命令拿去终端复现最稳。

## 8. 命令行快速开始（对照）

### 8.1 首次先做登录引导

```bash
python3 examples/run_real_site_once.py \
  --login-only \
  --require-login \
  --login-timeout 180 \
  --profile-dir .playwright_profile_main
```

### 8.2 安全扫描搞笑候选（推荐起步）

特点：

- 只做识别、互动量提取与“是否值得转给好友”判定
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

### 8.3 命中分享条件但不开启真实分享（只验证幽默评论链路）

用于验证“搞笑/怪诞视频 -> AI 评论草稿”链路，不触发真实分享动作：

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

### 8.4 开启真实分享给好友/群（高风险，先小轮次）

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

### 8.5 `@好友` 评论（命中分享条件时）

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

## 9. 运行模式说明

### 9.1 `--mode scan`（推荐）

真实站点扫描流程，包含：

- 内容判断
- 互动量提取
- 搞笑候选分享门控
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
- `--share-rules-config`: 分享判定规则配置文件，默认 `configs/share_rules.toml`
- `--share-min-like-count`: 覆盖最少点赞数门槛
- `--share-min-share-count`: 覆盖最少转发数门槛
- `--share-min-share-like-ratio`: 覆盖最少转赞比门槛
- `--share-threshold-mode`: 判定模式，`any` 表示命中任一条件，`all` 表示必须全部满足
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
- `skip_live`: 直播内容被硬拦截
- `skip_promo`: 疑似推广/带货内容被过滤
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
- Skill 模板：`skills/quanwang-zhao-shi-zhuanjia/SKILL.md`

如果在新会话让 AI 按既有规则执行，建议先让它读取 `PROJECT_HANDOFF.md`。
