from __future__ import annotations

import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.scrolledtext import ScrolledText


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "examples" / "run_real_site_once.py"


class ScanGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("抖音扫描启动器")
        self.geometry("1020x760")

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str | None] = queue.Queue()

        self.iterations_var = tk.StringVar(value="20")
        self.profile_dir_var = tk.StringVar(value=".playwright_profile_main")
        self.wait_scale_var = tk.StringVar(value="1.6")
        self.live_wait_var = tk.StringVar(value="3")
        self.video_wait_var = tk.StringVar(value="10")
        self.post_next_settle_var = tk.StringVar(value="8")
        self.snapshot_settle_var = tk.StringVar(value="2")
        self.share_target_var = tk.StringVar(value="")
        self.comment_mention_friend_var = tk.StringVar(value="")
        self.comment_style_options = {
            "幽默": "humorous",
            "中性": "neutral",
        }
        self.comment_style_var = tk.StringVar(value="幽默")

        self.llm_api_base_var = tk.StringVar(value="https://api.deepseek.com/v1")
        self.llm_model_var = tk.StringVar(value="deepseek-chat")
        self.llm_api_key_env_var = tk.StringVar(value="DEEPSEEK_API_KEY")
        self.llm_api_key_var = tk.StringVar(value="")

        self.require_login_var = tk.BooleanVar(value=True)
        self.comment_by_content_var = tk.BooleanVar(value=True)
        self.use_ai_var = tk.BooleanVar(value=True)
        self.enable_share_var = tk.BooleanVar(value=False)
        self.comment_without_share_var = tk.BooleanVar(value=False)
        self.enable_post_var = tk.BooleanVar(value=False)
        self.headless_var = tk.BooleanVar(value=False)
        self.no_log_window_var = tk.BooleanVar(value=False)
        self.insecure_skip_verify_var = tk.BooleanVar(value=True)

        self._build_layout()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._poll_output_queue)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        form = ttk.Frame(container)
        form.pack(fill=tk.X)

        self._add_entry(form, "扫描轮数", self.iterations_var, 0, 0)
        self._add_entry(form, "浏览器配置目录", self.profile_dir_var, 0, 2, width=38)
        self._add_entry(form, "等待倍率", self.wait_scale_var, 1, 0)
        self._add_entry(form, "直播停留秒数", self.live_wait_var, 1, 2)
        self._add_entry(form, "视频停留秒数", self.video_wait_var, 2, 0)
        self._add_entry(form, "下滑后稳定秒数", self.post_next_settle_var, 2, 2)
        self._add_entry(form, "截图前稳定秒数", self.snapshot_settle_var, 3, 0)
        self._add_entry(form, "分享目标", self.share_target_var, 3, 2, width=38)
        self._add_entry(form, "评论好友（逗号分隔，@+AI）", self.comment_mention_friend_var, 4, 2, width=30)

        ttk.Label(form, text="评论风格").grid(row=4, column=0, sticky=tk.W, pady=(8, 4))
        style_box = ttk.Combobox(
            form,
            textvariable=self.comment_style_var,
            values=tuple(self.comment_style_options.keys()),
            state="readonly",
            width=22,
        )
        style_box.grid(row=4, column=1, sticky=tk.W, pady=(8, 4))

        self._add_entry(form, "LLM 接口地址", self.llm_api_base_var, 5, 0, width=42)
        self._add_entry(form, "LLM 模型", self.llm_model_var, 5, 2, width=26)
        self._add_entry(form, "API Key 环境变量", self.llm_api_key_env_var, 6, 0)
        self._add_entry(form, "API Key 明文（可选）", self.llm_api_key_var, 6, 2, width=38, show="*")

        flags = ttk.Frame(container)
        flags.pack(fill=tk.X, pady=(8, 10))

        ttk.Checkbutton(flags, text="要求已登录", variable=self.require_login_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="按内容评论", variable=self.comment_by_content_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="使用 AI 评论", variable=self.use_ai_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="启用分享", variable=self.enable_share_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="不开分享但按分享条件评论", variable=self.comment_without_share_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="启用真实评论发送", variable=self.enable_post_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="无头模式", variable=self.headless_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="关闭日志窗口", variable=self.no_log_window_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="跳过 TLS 证书校验（不安全）", variable=self.insecure_skip_verify_var).pack(side=tk.LEFT)

        buttons = ttk.Frame(container)
        buttons.pack(fill=tk.X)

        self.start_btn = ttk.Button(buttons, text="开始扫描", command=self._start_scan)
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = ttk.Button(buttons, text="停止", command=self._stop_scan, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.copy_btn = ttk.Button(buttons, text="复制命令", command=self._copy_command)
        self.copy_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="空闲")
        ttk.Label(buttons, textvariable=self.status_var).pack(side=tk.RIGHT)

        self.log = ScrolledText(container, wrap=tk.WORD, font=("Menlo", 11), height=26)
        self.log.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self._append_log(f"[gui] 项目根目录: {ROOT}")

    def _add_entry(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        col: int,
        width: int = 24,
        show: str | None = None,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=col, sticky=tk.W, pady=4)
        entry = ttk.Entry(parent, textvariable=variable, width=width, show=show)
        entry.grid(row=row, column=col + 1, sticky=tk.W, padx=(8, 20), pady=4)

    def _read_number(self, name: str, raw: str, cast: type[int] | type[float]) -> int | float:
        value = raw.strip()
        if not value:
            raise ValueError(f"{name}不能为空")
        try:
            parsed = cast(value)
        except ValueError as exc:
            num_type = "整数" if cast is int else "数字"
            raise ValueError(f"{name}必须是有效的{num_type}") from exc
        if parsed <= 0:
            raise ValueError(f"{name}必须大于 0")
        return parsed

    def _normalize_mention_friends(self, raw: str) -> str:
        text = " ".join(raw.split()).strip()
        if not text:
            return ""
        text = text.replace("，", ",")
        if "@" in text:
            chunks = [item.strip() for item in re.findall(r"@([^@,，]+)", text) if item.strip()]
        else:
            chunks = [item.strip() for item in text.split(",") if item.strip()]

        names: list[str] = []
        seen: set[str] = set()
        for item in chunks:
            name = " ".join(item.split()).strip().lstrip("@")
            if not name:
                continue
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
        return ",".join(names)

    def _load_dotenv_values(self) -> dict[str, str]:
        env_path = ROOT / ".env"
        values: dict[str, str] = {}
        if not env_path.exists():
            return values
        try:
            lines = env_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return values
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if value and value[0] in {"'", '"'} and value[-1:] == value[0]:
                value = value[1:-1]
            values[key] = value
        return values

    def _resolve_api_key(self, api_key_env: str, api_key_value: str) -> str:
        explicit = api_key_value.strip()
        if explicit:
            return explicit
        from_env = os.getenv(api_key_env, "").strip()
        if from_env:
            return from_env
        dotenv = self._load_dotenv_values()
        by_env_name = dotenv.get(api_key_env, "").strip()
        if by_env_name:
            return by_env_name
        deepseek_key = dotenv.get("DEEPSEEK_API_KEY", "").strip()
        return deepseek_key

    def _build_command(self) -> list[str]:
        iterations = self._read_number("扫描轮数", self.iterations_var.get(), int)
        wait_scale = self._read_number("等待倍率", self.wait_scale_var.get(), float)
        live_wait = self._read_number("直播停留秒数", self.live_wait_var.get(), float)
        video_wait = self._read_number("视频停留秒数", self.video_wait_var.get(), float)
        post_next_settle = self._read_number("下滑后稳定秒数", self.post_next_settle_var.get(), float)
        snapshot_settle = self._read_number("截图前稳定秒数", self.snapshot_settle_var.get(), float)
        comment_style_key = self.comment_style_var.get().strip()
        comment_style = self.comment_style_options.get(comment_style_key, comment_style_key or "humorous")
        if comment_style not in {"humorous", "neutral"}:
            comment_style = "humorous"
        mention_friend = self._normalize_mention_friends(self.comment_mention_friend_var.get())
        mention_mode = bool(mention_friend)
        comment_by_content_enabled = self.comment_by_content_var.get() or mention_mode
        use_ai_enabled = self.use_ai_var.get() or mention_mode

        cmd = [
            sys.executable,
            str(RUNNER),
            "--mode",
            "scan",
            "--iterations",
            str(int(iterations)),
            "--profile-dir",
            self.profile_dir_var.get().strip() or ".playwright_profile_main",
            "--wait-scale",
            str(wait_scale),
            "--live-wait-seconds",
            str(live_wait),
            "--video-wait-seconds",
            str(video_wait),
            "--post-next-settle-seconds",
            str(post_next_settle),
            "--snapshot-settle-seconds",
            str(snapshot_settle),
            "--comment-style",
            comment_style,
        ]

        if self.require_login_var.get():
            cmd.append("--require-login")
        if self.headless_var.get():
            cmd.append("--headless")
        if self.no_log_window_var.get():
            cmd.append("--no-log-window")

        if comment_by_content_enabled:
            cmd.append("--comment-by-content")
            if use_ai_enabled:
                cmd.append("--use-ai-comment")
                cmd.extend(["--llm-api-base", self.llm_api_base_var.get().strip() or "https://api.deepseek.com/v1"])
                cmd.extend(["--llm-model", self.llm_model_var.get().strip() or "deepseek-chat"])
                cmd.extend(["--llm-api-key-env", self.llm_api_key_env_var.get().strip() or "DEEPSEEK_API_KEY"])
                if self.insecure_skip_verify_var.get():
                    cmd.append("--llm-insecure-skip-verify")
                else:
                    cmd.append("--llm-verify")
            else:
                cmd.append("--no-ai-comment")

        if self.enable_share_var.get():
            cmd.append("--enable-share")
            target = " ".join(self.share_target_var.get().split()).strip()
            if target:
                cmd.extend(["--share-target", target])
        if self.comment_without_share_var.get():
            cmd.append("--comment-without-share")
        if self.enable_post_var.get():
            cmd.append("--enable-post")
        if mention_friend:
            cmd.extend(["--comment-mention-friend", mention_friend])
            key_env = self.llm_api_key_env_var.get().strip() or "DEEPSEEK_API_KEY"
            resolved_key = self._resolve_api_key(
                api_key_env=key_env,
                api_key_value=self.llm_api_key_var.get(),
            )
            if not resolved_key:
                raise ValueError(
                    f"设置评论@好友时，需提供可用的 AI Key（环境变量 {key_env}、项目 .env 的 DEEPSEEK_API_KEY，或明文）。"
                )

        return cmd

    def _copy_command(self) -> None:
        try:
            cmd = self._build_command()
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc), parent=self)
            return
        text = " ".join(cmd)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("命令已复制")

    def _start_scan(self) -> None:
        if self.process is not None and self.process.poll() is None:
            messagebox.showinfo("任务运行中", "扫描任务已在运行。", parent=self)
            return
        if not RUNNER.exists():
            messagebox.showerror("缺少运行脚本", f"未找到 {RUNNER}", parent=self)
            return

        try:
            cmd = self._build_command()
        except ValueError as exc:
            messagebox.showerror("输入错误", str(exc), parent=self)
            return

        env = os.environ.copy()
        key_env = self.llm_api_key_env_var.get().strip() or "DEEPSEEK_API_KEY"
        key_value = self._resolve_api_key(
            api_key_env=key_env,
            api_key_value=self.llm_api_key_var.get(),
        )
        if key_value:
            env[key_env] = key_value

        self._append_log("")
        self._append_log(f"[gui] 启动命令: {' '.join(cmd)}")
        self._append_log(f"[gui] cwd={ROOT}")

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
            )
        except Exception as exc:
            self.process = None
            messagebox.showerror("启动失败", str(exc), parent=self)
            return

        self._set_running(True)
        threading.Thread(target=self._stream_output_worker, daemon=True).start()

    def _stream_output_worker(self) -> None:
        proc = self.process
        if proc is None:
            return
        if proc.stdout is not None:
            for line in proc.stdout:
                self.output_queue.put(line.rstrip("\n"))
        exit_code = proc.wait()
        self.output_queue.put(f"[gui] 进程退出，退出码: {exit_code}")
        self.output_queue.put(None)

    def _stop_scan(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self._append_log("[gui] 正在停止进程...")
        try:
            self.process.terminate()
        except Exception as exc:
            self._append_log(f"[gui] 停止失败: {exc}")

    def _set_running(self, running: bool) -> None:
        self.start_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        self.status_var.set("运行中" if running else "空闲")

    def _append_log(self, line: str) -> None:
        self.log.insert(tk.END, line + "\n")
        self.log.see(tk.END)

    def _poll_output_queue(self) -> None:
        while True:
            try:
                item = self.output_queue.get_nowait()
            except queue.Empty:
                break
            if item is None:
                self.process = None
                self._set_running(False)
                continue
            self._append_log(item)
        self.after(120, self._poll_output_queue)

    def _on_close(self) -> None:
        if self.process is not None and self.process.poll() is None:
            should_close = messagebox.askyesno(
                "退出",
                "扫描任务正在运行，是否停止并退出？",
                parent=self,
            )
            if not should_close:
                return
            self._stop_scan()
        self.destroy()


def main() -> int:
    app = ScanGui()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
