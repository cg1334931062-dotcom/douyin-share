# Douyin Computer Use PoC

一个“安全优先”的抖音自动化 PoC：  
以 `scan` 流程为核心，先识别是否直播，再按规则决定是否执行评论生成/分享动作，默认不做高风险自动行为。

## 1. 项目目标

本项目用于验证以下流程是否可稳定运行：

1. 打开抖音首页并进入推荐流
2. 判断当前卡片是否为直播
3. 非直播时提取上下文信息与互动指标
4. 按规则决定是否执行 AI 分析、评论、分享
5. 输出运行日志，便于回归和规则校验

## 2. 安全边界与声明

- 项目定位是“半自动助手”，不是无人值守刷量工具
- 不包含验证码绕过、风控规避、批量垃圾行为
- 默认应先跑小轮次验证，再决定是否开启真实分享/发送
- 请确保你的使用方式符合平台规则与本地法律法规

## 3. 仓库结构

```text
.
├── src/douyin_agent/                 # 核心模块
│   ├── browser_playwright.py         # 真实站点浏览器适配
│   ├── classifier.py                 # 直播/短视频分类
│   ├── commenting.py                 # 评论生成与策略
│   └── state_machine.py              # workflow runner
├── examples/
│   ├── run_real_site_once.py         # 主入口（推荐）
│   └── run_fake_demo.py              # 假浏览器演示
├── configs/                          # 提示词与策略规则
├── tests/                            # 单元测试
├── PROJECT_HANDOFF.md                # 业务规则与交接说明（重要）
├── SHARE_GUIDE.md                    # 对外分享说明
├── skills/douyin-scan-share/         # Skill 模板
└── tools/run_scan_gui.py             # 简易 GUI 启动器
```

## 4. 环境要求

- Python `>= 3.11`
- macOS / Linux（Windows 也可尝试，但未重点验证）
- Playwright Chromium 运行时

安装依赖：

```bash
python3 -m pip install -e .
python3 -m pip install playwright
python3 -m playwright install chromium
```

## 5. 快速开始

### 5.1 先做登录引导（推荐首次执行）

```bash
python3 examples/run_real_site_once.py \
  --login-only \
  --require-login \
  --login-timeout 180 \
  --profile-dir .playwright_profile_main
```

### 5.2 跑安全扫描（默认不启用真实分享）

```bash
OPENAI_API_KEY='<YOUR_KEY>' python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 10 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --wait-scale 1.6 \
  --live-wait-seconds 3 \
  --video-wait-seconds 10 \
  --post-next-settle-seconds 8 \
  --snapshot-settle-seconds 2 \
  --comment-by-content \
  --use-ai-comment \
  --comment-style humorous
```

### 5.3 开启真实分享（高风险，先小轮次）

```bash
OPENAI_API_KEY='<YOUR_KEY>' python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 5 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --comment-by-content \
  --use-ai-comment \
  --enable-share \
  --share-target '你的群名'
```

## 6. 常用参数说明（`run_real_site_once.py`）

- `--mode scan|workflow`：推荐使用 `scan`
- `--iterations N`：执行轮次
- `--require-login`：要求登录态存在
- `--profile-dir`：Playwright 用户数据目录
- `--wait-scale`：全局等待倍率，网慢时可增大
- `--live-wait-seconds`：直播等待时间
- `--video-wait-seconds`：非直播等待时间
- `--comment-by-content`：按内容生成评论
- `--use-ai-comment` / `--no-ai-comment`：开启/关闭 AI 评论
- `--enable-share`：开启真实分享动作
- `--share-target`：分享目标（群/好友）

## 7. GUI 启动方式

如果使用者不想手敲长命令，可以使用 GUI：

```bash
python3 tools/run_scan_gui.py
```

GUI 支持：

- 配置轮次、等待参数、profile
- 配置 LLM base/model/API key
- 一键启停任务并查看实时日志
- 复制当前命令用于命令行复现

## 8. Skill 打包方式

仓库内置 Skill 模板：

- `skills/douyin-scan-share/SKILL.md`

安装到本机（Codex）：

```bash
mkdir -p ~/.codex/skills
cp -R skills/douyin-scan-share ~/.codex/skills/
```

## 9. 测试

```bash
pytest -q
```

## 10. 交接与规则文件

- 业务规则与运行注意事项：`PROJECT_HANDOFF.md`
- 分享与分发建议：`SHARE_GUIDE.md`

如果你要在新会话中让 AI 按既有规则执行，请优先让它先读 `PROJECT_HANDOFF.md`。
