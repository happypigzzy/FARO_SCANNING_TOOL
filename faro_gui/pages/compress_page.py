# compress_page.py — Step2: 压缩设置（Compress Settings）
import tkinter as tk
from tkinter import ttk
import os

from utils import tr
from workers import CompressWorker


class CompressPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._compressing = False
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(
            self,
            text=tr("Step 2: 视频压缩设置", "Step 2: Video Compression Settings"),
            font=('', 13, 'bold'),
        )
        title.pack(pady=(15, 20))

        # 说明
        ttk.Label(
            self,
            text=tr(
                "压缩视频可显著提升 OCR 处理速度，同时减小文件体积",
                "Compress video to improve OCR speed and reduce file size",
            ),
            foreground='gray',
        ).pack(pady=(0, 15))

        # 设置区
        settings_frame = ttk.LabelFrame(
            self,
            text=tr("压缩参数", "Compression Parameters"),
            padding=20,
        )
        settings_frame.pack(fill=tk.X, padx=30, pady=5)

        # 分辨率
        res_frame = ttk.Frame(settings_frame)
        res_frame.pack(fill=tk.X, pady=5)
        ttk.Label(res_frame, text=tr("目标分辨率:", "Target Resolution:"), font=('', 10)).pack(side=tk.LEFT)

        self._width_var = tk.IntVar(value=768)
        self._height_var = tk.IntVar(value=480)

        ttk.Spinbox(res_frame, from_=160, to=3840, increment=16,
                    textvariable=self._width_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(res_frame, text="×").pack(side=tk.LEFT)
        ttk.Spinbox(res_frame, from_=120, to=2160, increment=16,
                    textvariable=self._height_var, width=6).pack(side=tk.LEFT, padx=5)

        # 帧率
        fps_frame = ttk.Frame(settings_frame)
        fps_frame.pack(fill=tk.X, pady=5)
        ttk.Label(fps_frame, text=tr("目标帧率:", "Target FPS:"), font=('', 10)).pack(side=tk.LEFT)
        self._fps_var = tk.IntVar(value=20)
        ttk.Spinbox(fps_frame, from_=1, to=60, textvariable=self._fps_var, width=6).pack(side=tk.LEFT, padx=5)
        ttk.Label(fps_frame, text="fps", foreground='gray').pack(side=tk.LEFT)

        # CRF
        crf_frame = ttk.Frame(settings_frame)
        crf_frame.pack(fill=tk.X, pady=5)
        ttk.Label(crf_frame, text=tr("CRF 质量:", "CRF Quality:"), font=('', 10)).pack(side=tk.LEFT)
        self._crf_var = tk.IntVar(value=28)
        crf_scale = ttk.Scale(
            crf_frame, from_=0, to=51, variable=self._crf_var,
            orient=tk.HORIZONTAL, length=250,
            command=lambda v: self._crf_label.config(text=f"{int(float(v))}"))
        crf_scale.pack(side=tk.LEFT, padx=10)
        self._crf_label = ttk.Label(crf_frame, text="28", font=('', 10))
        self._crf_label.pack(side=tk.LEFT)
        ttk.Label(crf_frame, text=tr("(越小越清晰)", "(lower = better quality)"),
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        # 预设
        preset_frame = ttk.Frame(settings_frame)
        preset_frame.pack(fill=tk.X, pady=5)
        ttk.Label(preset_frame, text=tr("编码预设:", "Preset:"), font=('', 10)).pack(side=tk.LEFT)
        self._preset_var = tk.StringVar(value='ultrafast')
        presets = ['ultrafast', 'superfast', 'veryfast', 'faster', 'fast', 'medium']
        preset_combo = ttk.Combobox(
            preset_frame, textvariable=self._preset_var,
            values=presets, state='readonly', width=12)
        preset_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(preset_frame, text=tr("(越快处理越快, 文件越大)", "(faster = quicker, larger file)"),
                  foreground='gray').pack(side=tk.LEFT, padx=5)

        # 压缩按钮
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=30, pady=15)

        self._compress_btn = ttk.Button(
            btn_frame,
            text=tr("开始压缩", "Start Compression"),
            command=self._start_compress,
        )
        self._compress_btn.pack(side=tk.LEFT, padx=(0, 10))

        self._cancel_btn = ttk.Button(
            btn_frame,
            text=tr("取消", "Cancel"),
            command=self._cancel_compress,
            state=tk.DISABLED,
        )
        self._cancel_btn.pack(side=tk.LEFT)

        self._skip_btn = ttk.Button(
            btn_frame,
            text=tr("跳过压缩 (使用原视频)", "Skip (Use Original Video)"),
            command=self._skip_compress,
        )
        self._skip_btn.pack(side=tk.RIGHT)

        # 进度条
        self._progress = ttk.Progressbar(self, mode='indeterminate')
        self._progress.pack(fill=tk.X, padx=30, pady=5)

        # 日志区
        log_frame = ttk.LabelFrame(
            self,
            text=tr("压缩日志", "Compression Log"),
            padding=5,
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        self._log_text = tk.Text(log_frame, height=10, font=('Consolas', 9), wrap=tk.WORD)
        self._log_text.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self._log_text, command=self._log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.config(yscrollcommand=scrollbar.set)

    def _start_compress(self):
        input_path = self.app.shared.get('input_video', '')
        if not input_path or not os.path.isfile(input_path):
            self._log_text.insert(tk.END, tr("错误: 请先在 Step1 选择一个有效的视频文件\n",
                                             "Error: Please select a valid video in Step1\n"))
            return

        settings = {
            'width': self._width_var.get(),
            'height': self._height_var.get(),
            'fps': self._fps_var.get(),
            'crf': self._crf_var.get(),
            'preset': self._preset_var.get(),
        }
        self.app.shared['compress_settings'] = settings

        output_path = self.app.shared['output_video']

        self._compressing = True
        self._compress_btn.config(state=tk.DISABLED)
        self._skip_btn.config(state=tk.DISABLED)
        self._cancel_btn.config(state=tk.NORMAL)
        self._progress.start(10)
        self._log_text.delete(1.0, tk.END)
        self._log_text.insert(tk.END, tr("正在压缩视频...\n", "Compressing video...\n"))

        worker = CompressWorker(input_path, output_path, settings, None)
        self.app.submit_worker(worker)
        self.app.set_status(tr("正在压缩视频...", "Compressing video..."))

    def _cancel_compress(self):
        self.app.cancel_worker()
        self._log_text.insert(tk.END, tr("正在取消...\n", "Cancelling...\n"))

    def _skip_compress(self):
        input_path = self.app.shared.get('input_video', '')
        if not input_path:
            return
        # 直接使用原视频
        self.app.shared['output_video'] = input_path
        self.app.shared['compress_done'] = True
        self._log_text.delete(1.0, tk.END)
        self._log_text.insert(tk.END, tr("已跳过压缩，将直接使用原视频进行 OCR\n",
                                         "Compression skipped, will use original video for OCR\n"))
        self.app.mark_step_done(1)
        self.app.set_status(tr("压缩已跳过", "Compression skipped"))

    def handle_worker_msg(self, msg):
        kind = msg[0]

        if kind == 'log':
            self._log_text.insert(tk.END, msg[1] + '\n')
            self._log_text.see(tk.END)

        elif kind == 'progress_pulse':
            pass  # indeterminate 进度条自动动画

        elif kind == 'done':
            self._compressing = False
            self._progress.stop()
            self._compress_btn.config(state=tk.NORMAL)
            self._skip_btn.config(state=tk.NORMAL)
            self._cancel_btn.config(state=tk.DISABLED)

            if msg[1]:
                self.app.shared['compress_done'] = True
                self.app.mark_step_done(1)
                self.app.set_status(tr("压缩完成", "Compression finished"))
            else:
                self.app.set_status(tr("压缩失败", "Compression failed"))

        elif kind == 'error':
            self._log_text.insert(tk.END, f"[ERROR] {msg[1]}\n")
            self._log_text.see(tk.END)

    def on_enter(self):
        # 同步压缩设置参数
        s = self.app.shared.get('compress_settings', {})
        self._width_var.set(s.get('width', 768))
        self._height_var.set(s.get('height', 480))
        self._fps_var.set(s.get('fps', 20))
        self._crf_var.set(s.get('crf', 28))
        self._preset_var.set(s.get('preset', 'ultrafast'))
        self._crf_label.config(text=str(s.get('crf', 28)))

        input_path = self.app.shared.get('input_video', '')
        if not input_path:
            self._compress_btn.config(state=tk.DISABLED)
            self._skip_btn.config(state=tk.DISABLED)
        else:
            self._compress_btn.config(state=tk.NORMAL)
            self._skip_btn.config(state=tk.NORMAL)
            self._cancel_btn.config(state=tk.DISABLED)

        if not self._compressing:
            self._progress.stop()

        self.app.set_status(tr("Step 2: 配置视频压缩参数", "Step 2: Configure compression parameters"))
