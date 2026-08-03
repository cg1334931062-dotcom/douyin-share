# 全网找‘屎’专家 分享指南

内部 Python 模块兼容名仍为 `douyin_agent`。

这个项目目前最适合用三种方式分享给他人：

1. 代码仓库 + 命令行（最稳，推荐）
2. Codex Skill（适合让 AI 助手按固定流程执行）
3. 简单 GUI 启动器（适合不想记命令的人）

## 1) 代码仓库分享（推荐）

### 给使用者的最小步骤
```bash
git clone <你的仓库地址> quanwang_zhao_shi_zhuanjia
cd quanwang_zhao_shi_zhuanjia
python3 -m pip install -e .
python3 -m pip install playwright
python3 -m playwright install chromium
```

首次建议只做登录引导：
```bash
python3 examples/run_real_site_once.py --login-only --require-login --login-timeout 180 --profile-dir .playwright_profile_main
```

安全扫描（默认不分享）：
```bash
OPENAI_API_KEY='<YOUR_KEY>' python3 examples/run_real_site_once.py \
  --mode scan \
  --iterations 20 \
  --require-login \
  --profile-dir .playwright_profile_main \
  --wait-scale 1.6 \
  --live-wait-seconds 3 \
  --video-wait-seconds 10 \
  --post-next-settle-seconds 8 \
  --snapshot-settle-seconds 2 \
  --comment-by-content \
  --use-ai-comment
```

开启分享（高风险，务必先小轮次验证）：
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

### 对外发布前建议
- 不要打包 `.playwright_profile*`（可能包含登录态）
- 不要提交真实 API Key
- 附上 `PROJECT_HANDOFF.md`，让接手人按现有业务规则运行

## 2) 总结为 Skill（适合 Codex / Agent 协作）

仓库已提供 Skill 模板：
- `skills/quanwang-zhao-shi-zhuanjia/SKILL.md`

使用者安装方式（示例）：
```bash
mkdir -p ~/.codex/skills
cp -R skills/quanwang-zhao-shi-zhuanjia ~/.codex/skills/
```

之后可在对话中直接说：
- “用 quanwang-zhao-shi-zhuanjia skill 跑 10 轮 scan 回归”
- “先 login-only，再跑 scan，开启 AI 评论但不开启分享”

## 3) 简单 GUI 启动器（适合非命令行用户）

仓库已提供 GUI：
```bash
python3 tools/run_scan_gui.py
```

界面支持：
- 配置轮次、等待参数、profile 目录
- 配置 AI 参数（API base、model、key env、可直接输入 key）
- 控制开关（登录校验、AI评论、是否分享、headless）
- 实时查看终端日志，并可手动停止任务

## 4) 如何选择

- 团队内开发协作：选“代码仓库 + README/PROJECT_HANDOFF”
- 让 AI 助手稳定复用流程：选“Skill”
- 给运营或测试同学快速使用：选“GUI”
