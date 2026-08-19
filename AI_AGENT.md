# AI Agent 操作契约

这是一个安全优先的抖音搞笑/怪诞视频筛选与好友分享助手。自动化代理应先运行离线 demo，再决定是否执行真实站点扫描。

## 入口

```bash
python3 -m douyin_agent --mode demo --iterations 1
```

命令输出单个 JSON 对象，包含 `task_status`、`completed_rounds`、`skip_reasons`、`share_results` 和 `errors`。demo 不访问网络、不需要登录、不会评论或分享。

真实站点必须显式选择 `scan`，并建议先保持所有副作用开关关闭：

```bash
python3 -m douyin_agent --mode scan --iterations 5 --require-login
```

`--enable-post` 才会真实发送评论，`--enable-share --share-target NAME` 才会真实分享；两者默认关闭。`--use-ai-comment` 仅打开 AI 评论生成，不等于发送评论。

## 执行前检查

1. 先确认 `python3 -m douyin_agent --mode demo` 成功且 `task_status=completed`。
2. 真实扫描使用固定的 `--profile-dir` 并保留 `--require-login`。
3. 不要修改直播、广告、推广硬拦截或分享门槛规则来绕过安全门。
4. 真实分享前确认目标名称和用户授权。

## 验收命令

```bash
python3 -m pytest -q
git diff --check
```
