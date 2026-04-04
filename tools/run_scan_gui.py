from __future__ import annotations

import os
from pathlib import Path
import queue
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
        self.title("Douyin Scan Launcher")
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
        self.comment_style_var = tk.StringVar(value="humorous")

        self.llm_api_base_var = tk.StringVar(value="https://api.openai.com/v1")
        self.llm_model_var = tk.StringVar(value="gpt-4.1-mini")
        self.llm_api_key_env_var = tk.StringVar(value="OPENAI_API_KEY")
        self.llm_api_key_var = tk.StringVar(value="")

        self.require_login_var = tk.BooleanVar(value=True)
        self.comment_by_content_var = tk.BooleanVar(value=True)
        self.use_ai_var = tk.BooleanVar(value=True)
        self.enable_share_var = tk.BooleanVar(value=False)
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

        self._add_entry(form, "Iterations", self.iterations_var, 0, 0)
        self._add_entry(form, "Profile Dir", self.profile_dir_var, 0, 2, width=38)
        self._add_entry(form, "Wait Scale", self.wait_scale_var, 1, 0)
        self._add_entry(form, "Live Wait Sec", self.live_wait_var, 1, 2)
        self._add_entry(form, "Video Wait Sec", self.video_wait_var, 2, 0)
        self._add_entry(form, "Post Next Settle", self.post_next_settle_var, 2, 2)
        self._add_entry(form, "Snapshot Settle", self.snapshot_settle_var, 3, 0)
        self._add_entry(form, "Share Target", self.share_target_var, 3, 2, width=38)

        ttk.Label(form, text="Comment Style").grid(row=4, column=0, sticky=tk.W, pady=(8, 4))
        style_box = ttk.Combobox(
            form,
            textvariable=self.comment_style_var,
            values=("humorous", "neutral"),
            state="readonly",
            width=22,
        )
        style_box.grid(row=4, column=1, sticky=tk.W, pady=(8, 4))

        self._add_entry(form, "LLM API Base", self.llm_api_base_var, 5, 0, width=42)
        self._add_entry(form, "LLM Model", self.llm_model_var, 5, 2, width=26)
        self._add_entry(form, "API Key Env", self.llm_api_key_env_var, 6, 0)
        self._add_entry(form, "API Key Value (optional)", self.llm_api_key_var, 6, 2, width=38, show="*")

        flags = ttk.Frame(container)
        flags.pack(fill=tk.X, pady=(8, 10))

        ttk.Checkbutton(flags, text="Require Login", variable=self.require_login_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="Comment By Content", variable=self.comment_by_content_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="Use AI Comment", variable=self.use_ai_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="Enable Share", variable=self.enable_share_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="Headless", variable=self.headless_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="No Log Window", variable=self.no_log_window_var).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Checkbutton(flags, text="Insecure Skip TLS Verify", variable=self.insecure_skip_verify_var).pack(side=tk.LEFT)

        buttons = ttk.Frame(container)
        buttons.pack(fill=tk.X)

        self.start_btn = ttk.Button(buttons, text="Start Scan", command=self._start_scan)
        self.start_btn.pack(side=tk.LEFT)

        self.stop_btn = ttk.Button(buttons, text="Stop", command=self._stop_scan, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.copy_btn = ttk.Button(buttons, text="Copy Command", command=self._copy_command)
        self.copy_btn.pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="Idle")
        ttk.Label(buttons, textvariable=self.status_var).pack(side=tk.RIGHT)

        self.log = ScrolledText(container, wrap=tk.WORD, font=("Menlo", 11), height=26)
        self.log.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self._append_log(f"[gui] project root: {ROOT}")

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
            raise ValueError(f"{name} cannot be empty")
        try:
            parsed = cast(value)
        except ValueError as exc:
            raise ValueError(f"{name} must be a valid {cast.__name__}") from exc
        if parsed <= 0:
            raise ValueError(f"{name} must be > 0")
        return parsed

    def _build_command(self) -> list[str]:
        iterations = self._read_number("Iterations", self.iterations_var.get(), int)
        wait_scale = self._read_number("Wait Scale", self.wait_scale_var.get(), float)
        live_wait = self._read_number("Live Wait Sec", self.live_wait_var.get(), float)
        video_wait = self._read_number("Video Wait Sec", self.video_wait_var.get(), float)
        post_next_settle = self._read_number("Post Next Settle", self.post_next_settle_var.get(), float)
        snapshot_settle = self._read_number("Snapshot Settle", self.snapshot_settle_var.get(), float)

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
            self.comment_style_var.get().strip() or "humorous",
        ]

        if self.require_login_var.get():
            cmd.append("--require-login")
        if self.headless_var.get():
            cmd.append("--headless")
        if self.no_log_window_var.get():
            cmd.append("--no-log-window")

        if self.comment_by_content_var.get():
            cmd.append("--comment-by-content")
            if self.use_ai_var.get():
                cmd.append("--use-ai-comment")
                cmd.extend(["--llm-api-base", self.llm_api_base_var.get().strip() or "https://api.openai.com/v1"])
                cmd.extend(["--llm-model", self.llm_model_var.get().strip() or "gpt-4.1-mini"])
                cmd.extend(["--llm-api-key-env", self.llm_api_key_env_var.get().strip() or "OPENAI_API_KEY"])
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

        return cmd

    def _copy_command(self) -> None:
        try:
            cmd = self._build_command()
        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc), parent=self)
            return
        text = " ".join(cmd)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("Command copied")

    def _start_scan(self) -> None:
        if self.process is not None and self.process.poll() is None:
            messagebox.showinfo("Running", "A scan is already running.", parent=self)
            return
        if not RUNNER.exists():
            messagebox.showerror("Missing Runner", f"Cannot find {RUNNER}", parent=self)
            return

        try:
            cmd = self._build_command()
        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc), parent=self)
            return

        env = os.environ.copy()
        key_env = self.llm_api_key_env_var.get().strip() or "OPENAI_API_KEY"
        key_value = self.llm_api_key_var.get().strip()
        if key_value:
            env[key_env] = key_value

        self._append_log("")
        self._append_log(f"[gui] start command: {' '.join(cmd)}")
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
            messagebox.showerror("Start Failed", str(exc), parent=self)
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
        self.output_queue.put(f"[gui] process exited with code {exit_code}")
        self.output_queue.put(None)

    def _stop_scan(self) -> None:
        if self.process is None or self.process.poll() is not None:
            return
        self._append_log("[gui] stopping process...")
        try:
            self.process.terminate()
        except Exception as exc:
            self._append_log(f"[gui] terminate failed: {exc}")

    def _set_running(self, running: bool) -> None:
        self.start_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        self.status_var.set("Running" if running else "Idle")

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
                "Quit",
                "A scan is running. Stop and quit?",
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
