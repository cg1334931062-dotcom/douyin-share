from __future__ import annotations

import os
from pathlib import Path
import queue
import re
import shlex
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from douyin_agent import ShareRuleConfig, load_share_rule_config

RUNNER = ROOT / "examples" / "run_real_site_once.py"
DEFAULT_SHARE_RULES_CONFIG = ROOT / "configs" / "share_rules.toml"

BG = "#17181f"
SURFACE = "#1f2230"
SURFACE_ALT = "#25293a"
CARD = "#2b3044"
CARD_SOFT = "#31364b"
TEXT = "#f5f7fb"
TEXT_MUTED = "#a8b1c7"
ACCENT = "#f4b860"
ACCENT_STRONG = "#ff9852"
SUCCESS = "#4bc58a"
DANGER = "#ef6a6a"
BORDER = "#3a415c"
LOG_BG = "#111319"
LOG_BORDER = "#444c67"

FONT_TITLE = ("Avenir Next", 24, "bold")
FONT_SUBTITLE = ("Avenir Next", 11)
FONT_SECTION = ("Avenir Next", 12, "bold")
FONT_LABEL = ("PingFang SC", 10)
FONT_VALUE = ("PingFang SC", 11)
FONT_MONO = ("SF Mono", 11)


class ScanGui(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("全网找‘屎’专家启动器")
        self.geometry("1380x860")
        self.minsize(1240, 780)
        self.configure(bg=BG)

        self.process: subprocess.Popen[str] | None = None
        self.output_queue: queue.Queue[str | None] = queue.Queue()
        share_rules = self._load_share_rules()

        self.iterations_var = tk.StringVar(value="20")
        self.profile_dir_var = tk.StringVar(value=".playwright_profile_main")
        self.wait_scale_var = tk.StringVar(value="1.6")
        self.live_wait_var = tk.StringVar(value="3")
        self.video_wait_var = tk.StringVar(value="10")
        self.post_next_settle_var = tk.StringVar(value="8")
        self.snapshot_settle_var = tk.StringVar(value="2")
        self.share_target_var = tk.StringVar(value="")
        self.share_min_like_var = tk.StringVar(value=str(share_rules.min_like_count))
        self.share_min_share_var = tk.StringVar(value=str(share_rules.min_share_count))
        self.share_min_ratio_var = tk.StringVar(value=f"{share_rules.min_share_like_ratio:g}")
        self.comment_mention_friend_var = tk.StringVar(value="")
        self.share_threshold_mode_options = {
            "满足任一条件": "any",
            "满足全部条件": "all",
        }
        self.share_threshold_mode_var = tk.StringVar(
            value=self._threshold_mode_label(share_rules.threshold_mode)
        )
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
        self.status_var = tk.StringVar(value="空闲")
        self.status_note_var = tk.StringVar(value="等待启动")
        self.summary_scan_var = tk.StringVar(value="")
        self.summary_share_var = tk.StringVar(value="")
        self.summary_comment_var = tk.StringVar(value="")
        self.summary_output_var = tk.StringVar(value="")
        self._left_scroll_canvas: tk.Canvas | None = None
        self._left_scroll_region: tk.Misc | None = None
        self._left_scroll_accumulator = 0.0

        self._configure_styles()
        self._build_layout()
        self._bind_live_updates()
        self._refresh_overview()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(120, self._poll_output_queue)

    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure("App.TFrame", background=SURFACE)
        style.configure("App.TLabel", background=SURFACE, foreground=TEXT, font=FONT_LABEL)
        style.configure("Muted.TLabel", background=SURFACE, foreground=TEXT_MUTED, font=FONT_LABEL)
        style.configure(
            "App.TEntry",
            foreground=TEXT,
            fieldbackground=CARD_SOFT,
            background=CARD_SOFT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(10, 8),
            insertcolor=ACCENT,
        )
        style.configure(
            "App.TCombobox",
            foreground=TEXT,
            fieldbackground=CARD_SOFT,
            background=CARD_SOFT,
            arrowcolor=ACCENT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=(10, 8),
        )
        style.map(
            "App.TCombobox",
            fieldbackground=[("readonly", CARD_SOFT)],
            foreground=[("readonly", TEXT)],
            selectbackground=[("readonly", CARD_SOFT)],
            selectforeground=[("readonly", TEXT)],
        )
        style.configure("App.TCheckbutton", background=CARD, foreground=TEXT, font=FONT_VALUE)
        style.map("App.TCheckbutton", background=[("active", CARD)], foreground=[("active", TEXT)])
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground=BG,
            borderwidth=0,
            focusthickness=0,
            font=FONT_VALUE,
            padding=(14, 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_STRONG), ("disabled", BORDER)],
            foreground=[("disabled", TEXT_MUTED)],
        )
        style.configure(
            "Danger.TButton",
            background=DANGER,
            foreground=TEXT,
            borderwidth=0,
            focusthickness=0,
            font=FONT_VALUE,
            padding=(14, 10),
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#ff7c7c"), ("disabled", BORDER)],
            foreground=[("disabled", TEXT_MUTED)],
        )
        style.configure(
            "Subtle.TButton",
            background=CARD_SOFT,
            foreground=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            font=FONT_VALUE,
            padding=(14, 10),
        )
        style.map("Subtle.TButton", background=[("active", CARD)], foreground=[("disabled", TEXT_MUTED)])
        style.configure(
            "App.Vertical.TScrollbar",
            background=CARD_SOFT,
            troughcolor=LOG_BG,
            bordercolor=LOG_BORDER,
            arrowcolor=TEXT_MUTED,
            darkcolor=CARD_SOFT,
            lightcolor=CARD_SOFT,
            arrowsize=14,
            relief="flat",
        )
        style.map(
            "App.Vertical.TScrollbar",
            background=[("active", ACCENT_STRONG), ("pressed", ACCENT)],
            arrowcolor=[("active", TEXT), ("pressed", BG)],
        )

    def _build_layout(self) -> None:
        shell = tk.Frame(self, bg=BG)
        shell.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        self._build_header(shell)

        content = tk.Frame(shell, bg=BG)
        content.pack(fill=tk.BOTH, expand=True, pady=(18, 0))
        content.grid_columnconfigure(0, weight=0, minsize=470)
        content.grid_columnconfigure(1, weight=1)
        content.grid_rowconfigure(0, weight=1)

        left_panel = tk.Frame(
            content,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        right_panel = tk.Frame(
            content,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            bd=0,
        )
        right_panel.grid(row=0, column=1, sticky="nsew")

        self._build_controls_column(left_panel)
        self._build_runtime_column(right_panel)
        self._append_log(f"[gui] 项目根目录: {ROOT}")

    def _build_header(self, parent: tk.Frame) -> None:
        header = tk.Frame(parent, bg=BG)
        header.pack(fill=tk.X)

        title_wrap = tk.Frame(header, bg=BG)
        title_wrap.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            title_wrap,
            text="全网找‘屎’专家",
            bg=BG,
            fg=TEXT,
            font=FONT_TITLE,
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_wrap,
            text="扫描、分享、评论参数按工作流分区组织，命令与运行状态实时联动。",
            bg=BG,
            fg=TEXT_MUTED,
            font=FONT_SUBTITLE,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        status_card = tk.Frame(
            header,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=14,
            pady=10,
        )
        status_card.pack(side=tk.RIGHT)
        tk.Label(status_card, text="运行状态", bg=SURFACE, fg=TEXT_MUTED, font=FONT_LABEL).pack(anchor="e")
        self.status_badge = tk.Label(
            status_card,
            textvariable=self.status_var,
            bg=ACCENT,
            fg=BG,
            font=FONT_SECTION,
            padx=12,
            pady=4,
        )
        self.status_badge.pack(anchor="e", pady=(6, 6))
        tk.Label(
            status_card,
            textvariable=self.status_note_var,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            anchor="e",
            justify=tk.RIGHT,
        ).pack(anchor="e")

    def _build_controls_column(self, parent: tk.Frame) -> None:
        canvas = tk.Canvas(parent, bg=SURFACE, highlightthickness=0, bd=0)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=canvas.yview, style="App.Vertical.TScrollbar")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=1, pady=1)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=1)
        self._left_scroll_canvas = canvas
        self._left_scroll_region = parent

        body = tk.Frame(canvas, bg=SURFACE)
        canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")

        def _on_body_configure(_event: tk.Event[tk.Misc]) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event[tk.Misc]) -> None:
            canvas.itemconfigure(canvas_window, width=event.width)

        body.bind("<Configure>", _on_body_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        self._bind_left_scroll_region()

        scan_body = self._create_section_card(
            body,
            "扫描配置",
            "先设轮次和节奏，再决定是否走登录、分享与真实发送。",
        )
        scan_body.grid_columnconfigure(0, weight=1)
        scan_body.grid_columnconfigure(1, weight=1)
        self._add_entry_field(scan_body, "扫描轮数", self.iterations_var, 0, 0)
        self._add_entry_field(scan_body, "浏览器配置目录", self.profile_dir_var, 0, 1)
        self._add_entry_field(scan_body, "等待倍率", self.wait_scale_var, 1, 0)
        self._add_entry_field(scan_body, "直播停留秒数", self.live_wait_var, 1, 1)
        self._add_entry_field(scan_body, "视频停留秒数", self.video_wait_var, 2, 0)
        self._add_entry_field(scan_body, "下滑后稳定秒数", self.post_next_settle_var, 2, 1)
        self._add_entry_field(scan_body, "截图前稳定秒数", self.snapshot_settle_var, 3, 0)
        self._add_entry_field(scan_body, "分享目标", self.share_target_var, 3, 1)

        share_body = self._create_section_card(
            body,
            "分享门槛",
            "这里定义短视频互动门槛，只影响是否进入分享候选。",
        )
        share_body.grid_columnconfigure(0, weight=1)
        share_body.grid_columnconfigure(1, weight=1)
        self._add_entry_field(share_body, "最少点赞数", self.share_min_like_var, 0, 0)
        self._add_entry_field(share_body, "最少转发数", self.share_min_share_var, 0, 1)
        self._add_entry_field(share_body, "最少转赞比", self.share_min_ratio_var, 1, 0)
        self._add_combo_field(
            share_body,
            "分享判定模式",
            self.share_threshold_mode_var,
            tuple(self.share_threshold_mode_options.keys()),
            1,
            1,
        )

        comment_body = self._create_section_card(
            body,
            "评论与 AI",
            "评论生成、@好友、模型接入都集中在这里，便于检查依赖是否齐全。",
        )
        comment_body.grid_columnconfigure(0, weight=1)
        comment_body.grid_columnconfigure(1, weight=1)
        self._add_combo_field(
            comment_body,
            "评论风格",
            self.comment_style_var,
            tuple(self.comment_style_options.keys()),
            0,
            0,
        )
        self._add_entry_field(comment_body, "评论好友（逗号分隔，@+AI）", self.comment_mention_friend_var, 0, 1)
        self._add_entry_field(comment_body, "LLM 接口地址", self.llm_api_base_var, 1, 0, columnspan=2)
        self._add_entry_field(comment_body, "LLM 模型", self.llm_model_var, 2, 0)
        self._add_entry_field(comment_body, "API Key 环境变量", self.llm_api_key_env_var, 2, 1)
        self._add_entry_field(comment_body, "API Key 明文（可选）", self.llm_api_key_var, 3, 0, columnspan=2, show="*")

        switches_body = self._create_section_card(
            body,
            "运行开关",
            "高风险动作和辅助行为拆开看，启动前更容易做最终检查。",
        )
        switches_body.grid_columnconfigure(0, weight=1)
        switches_body.grid_columnconfigure(1, weight=1)
        self._add_toggle_card(switches_body, 0, 0, "要求已登录", "缺失登录态时先停住，等待手动登录。", self.require_login_var)
        self._add_toggle_card(switches_body, 0, 1, "按内容评论", "命中候选时进入评论分析与生成链路。", self.comment_by_content_var)
        self._add_toggle_card(switches_body, 1, 0, "使用 AI 评论", "从模型生成评论，不走纯本地模板。", self.use_ai_var)
        self._add_toggle_card(switches_body, 1, 1, "启用分享", "真的执行分享动作，而不是只做候选判断。", self.enable_share_var)
        self._add_toggle_card(switches_body, 2, 0, "不开分享但按分享条件评论", "不真实分享，但命中条件仍生成评论。", self.comment_without_share_var)
        self._add_toggle_card(switches_body, 2, 1, "启用真实评论发送", "评论不仅生成，还会真的点击发送。", self.enable_post_var)
        self._add_toggle_card(switches_body, 3, 0, "无头模式", "后台运行浏览器，不弹可视窗口。", self.headless_var)
        self._add_toggle_card(switches_body, 3, 1, "关闭日志窗口", "只保留终端与本启动器日志。", self.no_log_window_var)
        self._add_toggle_card(switches_body, 4, 0, "跳过 TLS 证书校验", "保留当前兼容策略，但属于不安全连接方式。", self.insecure_skip_verify_var)

    def _build_runtime_column(self, parent: tk.Frame) -> None:
        parent.grid_rowconfigure(3, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        overview_card = tk.Frame(parent, bg=SURFACE, padx=20, pady=18)
        overview_card.grid(row=0, column=0, sticky="ew", padx=1, pady=(1, 14))
        tk.Label(overview_card, text="运行概览", bg=SURFACE, fg=TEXT, font=FONT_SECTION).pack(anchor="w")
        tk.Label(
            overview_card,
            text="启动前先看四张摘要卡，确认这次到底是扫描、评论验证，还是会触发真实动作。",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(4, 14))

        stat_grid = tk.Frame(overview_card, bg=SURFACE)
        stat_grid.pack(fill=tk.X)
        for idx in range(4):
            stat_grid.grid_columnconfigure(idx, weight=1)

        self._create_summary_card(stat_grid, 0, "本次扫描", self.summary_scan_var)
        self._create_summary_card(stat_grid, 1, "分享策略", self.summary_share_var)
        self._create_summary_card(stat_grid, 2, "评论链路", self.summary_comment_var)
        self._create_summary_card(stat_grid, 3, "输出方式", self.summary_output_var)

        action_card = tk.Frame(parent, bg=SURFACE, padx=20, pady=18)
        action_card.grid(row=1, column=0, sticky="ew", padx=1, pady=(0, 14))
        tk.Label(action_card, text="操作区", bg=SURFACE, fg=TEXT, font=FONT_SECTION).pack(anchor="w")
        tk.Label(
            action_card,
            text="命令始终由当前表单生成，复制和启动看到的是同一套参数。",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(4, 12))

        button_row = tk.Frame(action_card, bg=SURFACE)
        button_row.pack(fill=tk.X)
        self.start_btn = ttk.Button(button_row, text="开始扫描", style="Accent.TButton", command=self._start_scan)
        self.start_btn.pack(side=tk.LEFT)
        self.stop_btn = ttk.Button(button_row, text="停止任务", style="Danger.TButton", command=self._stop_scan, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(10, 0))
        self.copy_btn = ttk.Button(button_row, text="复制命令", style="Subtle.TButton", command=self._copy_command)
        self.copy_btn.pack(side=tk.LEFT, padx=(10, 0))

        tk.Label(
            action_card,
            textvariable=self.status_note_var,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            anchor="w",
        ).pack(anchor="w", pady=(12, 0))

        preview_card = tk.Frame(parent, bg=SURFACE, padx=20, pady=18)
        preview_card.grid(row=2, column=0, sticky="ew", padx=1, pady=(0, 14))
        tk.Label(preview_card, text="命令预览", bg=SURFACE, fg=TEXT, font=FONT_SECTION).pack(anchor="w")
        tk.Label(
            preview_card,
            text="配置变动后即时刷新，便于在 GUI 和 CLI 间来回切换。",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            justify=tk.LEFT,
        ).pack(anchor="w", pady=(4, 10))
        preview_shell, self.command_preview = self._create_text_panel(preview_card, height=7)
        preview_shell.pack(fill=tk.BOTH, expand=True)
        self.command_preview.configure(state=tk.DISABLED)

        log_card = tk.Frame(parent, bg=SURFACE, padx=20, pady=18)
        log_card.grid(row=3, column=0, sticky="nsew", padx=1, pady=(0, 1))
        log_card.grid_rowconfigure(1, weight=1)
        log_card.grid_columnconfigure(0, weight=1)
        log_header = tk.Frame(log_card, bg=SURFACE)
        log_header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        log_header.grid_columnconfigure(0, weight=1)
        tk.Label(log_header, text="运行日志", bg=SURFACE, fg=TEXT, font=FONT_SECTION).grid(row=0, column=0, sticky="w")
        tk.Label(
            log_header,
            text="这里保留 GUI 自身日志和脚本输出，方便检查启动命令、退出码和异常。",
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            justify=tk.RIGHT,
        ).grid(row=0, column=1, sticky="e")
        log_shell, self.log = self._create_text_panel(log_card, height=18)
        log_shell.grid(row=1, column=0, sticky="nsew")

    def _create_section_card(self, parent: tk.Frame, title: str, subtitle: str) -> tk.Frame:
        card = tk.Frame(parent, bg=SURFACE, padx=18, pady=18)
        card.pack(fill=tk.X, padx=1, pady=(1, 14))
        tk.Label(card, text=title, bg=SURFACE, fg=TEXT, font=FONT_SECTION).pack(anchor="w")
        tk.Label(
            card,
            text=subtitle,
            bg=SURFACE,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            justify=tk.LEFT,
            wraplength=400,
        ).pack(anchor="w", pady=(4, 12))
        body = tk.Frame(card, bg=SURFACE)
        body.pack(fill=tk.X)
        return body

    def _create_summary_card(self, parent: tk.Frame, column: int, title: str, variable: tk.StringVar) -> None:
        card = tk.Frame(
            parent,
            bg=CARD,
            padx=14,
            pady=14,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        card.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 10, 0))
        tk.Label(card, text=title, bg=CARD, fg=TEXT_MUTED, font=FONT_LABEL).pack(anchor="w")
        tk.Label(
            card,
            textvariable=variable,
            bg=CARD,
            fg=TEXT,
            font=FONT_VALUE,
            justify=tk.LEFT,
            wraplength=220,
        ).pack(anchor="w", pady=(8, 0))

    def _create_text_panel(self, parent: tk.Frame, *, height: int) -> tuple[tk.Frame, tk.Text]:
        shell = tk.Frame(
            parent,
            bg=LOG_BG,
            highlightbackground=LOG_BORDER,
            highlightthickness=1,
            bd=0,
        )

        text = tk.Text(
            shell,
            wrap=tk.WORD,
            font=FONT_MONO,
            height=height,
            bg=LOG_BG,
            fg=TEXT,
            insertbackground=ACCENT,
            relief=tk.FLAT,
            borderwidth=0,
            highlightthickness=0,
            padx=12,
            pady=12,
            selectbackground=CARD_SOFT,
            selectforeground=TEXT,
        )
        scrollbar = ttk.Scrollbar(
            shell,
            orient=tk.VERTICAL,
            command=text.yview,
            style="App.Vertical.TScrollbar",
        )
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        return shell, text

    def _add_entry_field(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int,
        *,
        columnspan: int = 1,
        show: str | None = None,
    ) -> None:
        field = tk.Frame(parent, bg=CARD, padx=12, pady=12, highlightbackground=BORDER, highlightthickness=1)
        field.grid(row=row, column=column, columnspan=columnspan, sticky="ew", padx=6, pady=6)
        tk.Label(field, text=label, bg=CARD, fg=TEXT_MUTED, font=FONT_LABEL).pack(anchor="w")
        entry = ttk.Entry(field, textvariable=variable, style="App.TEntry", show=show)
        entry.pack(fill=tk.X, pady=(8, 0))

    def _add_combo_field(
        self,
        parent: tk.Frame,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
        row: int,
        column: int,
    ) -> None:
        field = tk.Frame(parent, bg=CARD, padx=12, pady=12, highlightbackground=BORDER, highlightthickness=1)
        field.grid(row=row, column=column, sticky="ew", padx=6, pady=6)
        tk.Label(field, text=label, bg=CARD, fg=TEXT_MUTED, font=FONT_LABEL).pack(anchor="w")
        box = ttk.Combobox(field, textvariable=variable, values=values, state="readonly", style="App.TCombobox")
        box.pack(fill=tk.X, pady=(8, 0))

    def _add_toggle_card(
        self,
        parent: tk.Frame,
        row: int,
        column: int,
        title: str,
        description: str,
        variable: tk.BooleanVar,
    ) -> None:
        card = tk.Frame(parent, bg=CARD, padx=12, pady=12, highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=row, column=column, sticky="ew", padx=6, pady=6)
        title_var = tk.StringVar()

        def _refresh_toggle(*_args: object) -> None:
            title_var.set(f"{'✅' if variable.get() else '□'} {title}")

        def _toggle(_event: tk.Event[tk.Misc] | None = None) -> str:
            variable.set(not variable.get())
            return "break"

        variable.trace_add("write", _refresh_toggle)
        _refresh_toggle()

        title_label = tk.Label(
            card,
            textvariable=title_var,
            bg=CARD,
            fg=TEXT,
            font=FONT_SECTION,
            anchor="w",
            cursor="hand2",
        )
        title_label.pack(anchor="w")
        desc_label = tk.Label(
            card,
            text=description,
            bg=CARD,
            fg=TEXT_MUTED,
            font=FONT_LABEL,
            wraplength=180,
            justify=tk.LEFT,
            cursor="hand2",
        )
        desc_label.pack(anchor="w", pady=(8, 0))

        for widget in (card, title_label, desc_label):
            widget.bind("<Button-1>", _toggle, add="+")

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

    def _read_non_negative_number(
        self,
        name: str,
        raw: str,
        cast: type[int] | type[float],
    ) -> int | float:
        value = raw.strip()
        if not value:
            raise ValueError(f"{name}不能为空")
        try:
            parsed = cast(value)
        except ValueError as exc:
            num_type = "整数" if cast is int else "数字"
            raise ValueError(f"{name}必须是有效的{num_type}") from exc
        if parsed < 0:
            raise ValueError(f"{name}必须大于等于 0")
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

    def _load_share_rules(self) -> ShareRuleConfig:
        try:
            return load_share_rule_config(DEFAULT_SHARE_RULES_CONFIG)
        except ValueError:
            return ShareRuleConfig()

    def _threshold_mode_label(self, value: str) -> str:
        for label, raw in self.share_threshold_mode_options.items():
            if raw == value:
                return label
        return "满足任一条件"

    def _bind_live_updates(self) -> None:
        watched = (
            self.iterations_var,
            self.profile_dir_var,
            self.wait_scale_var,
            self.live_wait_var,
            self.video_wait_var,
            self.post_next_settle_var,
            self.snapshot_settle_var,
            self.share_target_var,
            self.share_min_like_var,
            self.share_min_share_var,
            self.share_min_ratio_var,
            self.comment_mention_friend_var,
            self.share_threshold_mode_var,
            self.comment_style_var,
            self.llm_api_base_var,
            self.llm_model_var,
            self.llm_api_key_env_var,
            self.llm_api_key_var,
            self.require_login_var,
            self.comment_by_content_var,
            self.use_ai_var,
            self.enable_share_var,
            self.comment_without_share_var,
            self.enable_post_var,
            self.headless_var,
            self.no_log_window_var,
            self.insecure_skip_verify_var,
        )
        for variable in watched:
            variable.trace_add("write", self._refresh_overview)

    def _refresh_overview(self, *_args: object) -> None:
        iterations = self.iterations_var.get().strip() or "-"
        profile_dir = self.profile_dir_var.get().strip() or ".playwright_profile_main"
        self.summary_scan_var.set(
            f"{iterations} 轮\n{profile_dir}\nwait x{self.wait_scale_var.get().strip() or '-'}"
        )

        share_target = " ".join(self.share_target_var.get().split()).strip() or "未设置"
        share_mode = self.share_threshold_mode_var.get().strip() or "满足任一条件"
        share_state = "真实分享" if self.enable_share_var.get() else "仅候选判断"
        if self.comment_without_share_var.get() and not self.enable_share_var.get():
            share_state = "仅评论验证"
        self.summary_share_var.set(
            f"{share_state}\n目标: {share_target}\n{share_mode}"
        )

        mention_friend = self._normalize_mention_friends(self.comment_mention_friend_var.get()) or "无"
        ai_state = "AI开启" if self.use_ai_var.get() else "AI关闭"
        comment_state = "真实发送" if self.enable_post_var.get() else "仅生成草稿"
        self.summary_comment_var.set(
            f"{ai_state} / {comment_state}\n风格: {self.comment_style_var.get().strip() or '-'}\n@好友: {mention_friend}"
        )

        output_mode = "无头" if self.headless_var.get() else "可视"
        login_mode = "要求登录" if self.require_login_var.get() else "允许未登录"
        log_mode = "内置日志关闭" if self.no_log_window_var.get() else "内置日志开启"
        self.summary_output_var.set(f"{output_mode}\n{login_mode}\n{log_mode}")

        try:
            command = self._build_command()
            preview = " \\\n  ".join(shlex.quote(part) for part in command)
        except ValueError as exc:
            preview = f"配置未完成：{exc}"
        self._set_text_content(self.command_preview, preview)

    def _set_text_content(self, widget: ScrolledText, text: str) -> None:
        widget.configure(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert("1.0", text)
        widget.configure(state=tk.DISABLED)

    def _bind_left_scroll_region(self) -> None:
        self.bind_all("<MouseWheel>", self._handle_left_scroll_mousewheel, add="+")
        self.bind_all("<Button-4>", self._handle_left_scroll_button4, add="+")
        self.bind_all("<Button-5>", self._handle_left_scroll_button5, add="+")

    def _pointer_in_left_scroll_region(self, event: tk.Event[tk.Misc]) -> bool:
        region = self._left_scroll_region
        if region is None or not region.winfo_exists():
            return False
        x1 = region.winfo_rootx()
        y1 = region.winfo_rooty()
        x2 = x1 + region.winfo_width()
        y2 = y1 + region.winfo_height()
        return x1 <= event.x_root <= x2 and y1 <= event.y_root <= y2

    def _left_region_can_scroll(self) -> bool:
        canvas = self._left_scroll_canvas
        if canvas is None or not canvas.winfo_exists():
            return False
        bbox = canvas.bbox("all")
        if bbox is None:
            return False
        content_height = bbox[3] - bbox[1]
        viewport_height = canvas.winfo_height()
        return content_height > max(0, viewport_height + 4)

    def _scroll_left_region(self, delta: int) -> str | None:
        canvas = self._left_scroll_canvas
        if canvas is None or not canvas.winfo_exists() or delta == 0:
            return None
        if not self._left_region_can_scroll():
            self._left_scroll_accumulator = 0.0
            return None

        if sys.platform == "darwin":
            self._left_scroll_accumulator += (-delta / 6.0)
        else:
            self._left_scroll_accumulator += (-delta / 120.0)

        steps = int(self._left_scroll_accumulator)
        if steps == 0:
            return "break"

        self._left_scroll_accumulator -= steps
        canvas.yview_scroll(steps, "units")
        return "break"

    def _handle_left_scroll_mousewheel(self, event: tk.Event[tk.Misc]) -> str | None:
        if not self._pointer_in_left_scroll_region(event):
            return None
        return self._scroll_left_region(int(event.delta))

    def _handle_left_scroll_button4(self, event: tk.Event[tk.Misc]) -> str | None:
        if not self._pointer_in_left_scroll_region(event):
            return None
        return self._scroll_left_region(120)

    def _handle_left_scroll_button5(self, event: tk.Event[tk.Misc]) -> str | None:
        if not self._pointer_in_left_scroll_region(event):
            return None
        return self._scroll_left_region(-120)

    def _build_command(self) -> list[str]:
        iterations = self._read_number("扫描轮数", self.iterations_var.get(), int)
        wait_scale = self._read_number("等待倍率", self.wait_scale_var.get(), float)
        live_wait = self._read_number("直播停留秒数", self.live_wait_var.get(), float)
        video_wait = self._read_number("视频停留秒数", self.video_wait_var.get(), float)
        post_next_settle = self._read_number("下滑后稳定秒数", self.post_next_settle_var.get(), float)
        snapshot_settle = self._read_number("截图前稳定秒数", self.snapshot_settle_var.get(), float)
        share_min_like = self._read_non_negative_number("最少点赞数", self.share_min_like_var.get(), int)
        share_min_share = self._read_non_negative_number("最少转发数", self.share_min_share_var.get(), int)
        share_min_ratio = self._read_non_negative_number("最少转赞比", self.share_min_ratio_var.get(), float)
        share_threshold_mode_key = self.share_threshold_mode_var.get().strip()
        share_threshold_mode = self.share_threshold_mode_options.get(
            share_threshold_mode_key,
            "any",
        )
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
            "--share-rules-config",
            str(DEFAULT_SHARE_RULES_CONFIG),
            "--share-min-like-count",
            str(int(share_min_like)),
            "--share-min-share-count",
            str(int(share_min_share)),
            "--share-min-share-like-ratio",
            str(share_min_ratio),
            "--share-threshold-mode",
            share_threshold_mode,
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
        self.status_note_var.set("命令已复制，可直接切到终端执行。")

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
        self.status_note_var.set("正在启动扫描进程...")

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
            self.status_note_var.set(f"启动失败: {exc}")
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
        self.status_note_var.set("停止请求已发送，等待进程退出。")
        try:
            self.process.terminate()
        except Exception as exc:
            self._append_log(f"[gui] 停止失败: {exc}")
            self.status_note_var.set(f"停止失败: {exc}")

    def _set_running(self, running: bool) -> None:
        self.start_btn.configure(state=tk.DISABLED if running else tk.NORMAL)
        self.stop_btn.configure(state=tk.NORMAL if running else tk.DISABLED)
        self.status_var.set("运行中" if running else "空闲")
        self.status_badge.configure(bg=SUCCESS if running else ACCENT)
        if running:
            self.status_note_var.set("扫描进行中，日志与命令预览保持联动。")
        elif self.status_note_var.get() == "扫描进行中，日志与命令预览保持联动。":
            self.status_note_var.set("等待启动")

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
            if item.startswith("[gui] 进程退出，退出码: "):
                self.status_note_var.set(item.replace("[gui] ", "", 1))
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
