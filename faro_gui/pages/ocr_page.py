# ocr_page.py — Step4: 运行 OCR（Run OCR）
import tkinter as tk
from tkinter import ttk, messagebox
import os

from utils import tr
from workers import OCRWorker


class OCRPage(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._running = False
        self._build_ui()

    def _build_ui(self):
        title = ttk.Label(
            self,
            text=tr("Step 4: 运行 OCR 识别", "Step 4: Run OCR Recognition"),
            font=('', 13, 'bold'),
        )
        title.pack(pady=(15, 10))

        # 参数设置
        param_frame = ttk.LabelFrame(
            self,
            text=tr("识别参数", "Recognition Parameters"),
            padding=15,
        )
        param_frame.pack(fill=tk.X, padx=30, pady=10)

        # 采样间隔
        row1 = ttk.Frame(param_frame)
        row1.pack(fill=tk.X, pady=3)
        ttk.Label(row1, text=tr("采样间隔 (每N帧):", "Sample Interval (every N frames):"),
                  font=('', 10)).pack(side=tk.LEFT)
        self._step_var = tk.IntVar(value=3)
        ttk.Spinbox(row1, from_=1, to=100, textvariable=self._step_var, width=6).pack(side=tk.LEFT, padx=8)

        # 位移有效范围
        row2 = ttk.Frame(param_frame)
        row2.pack(fill=tk.X, pady=3)
        ttk.Label(row2, text=tr("有效位移下限 (mm):", "Disp. Min (mm):"),
                  font=('', 10)).pack(side=tk.LEFT)
        self._min_var = tk.DoubleVar(value=0.0)
        ttk.Entry(row2, textvariable=self._min_var, width=8).pack(side=tk.LEFT, padx=5)

        ttk.Label(row2, text=tr("上限:", "Max:")).pack(side=tk.LEFT, padx=(15, 5))
        self._max_var = tk.DoubleVar(value=3.0)
        ttk.Entry(row2, textvariable=self._max_var, width=8).pack(side=tk.LEFT, padx=5)
        ttk.Label(row2, text="mm").pack(side=tk.LEFT)

        # 控制按钮
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill=tk.X, padx=30, pady=10)

        self._start_btn = ttk.Button(
            ctrl_frame,
            text=tr("开始识别", "Start OCR"),
            command=self._start_ocr,
        )
        self._start_btn.pack(side=tk.LEFT, padx=(0, 10))

        self._cancel_btn = ttk.Button(
            ctrl_frame,
            text=tr("取消", "Cancel"),
            command=self._cancel_ocr,
            state=tk.DISABLED,
        )
        self._cancel_btn.pack(side=tk.LEFT)

        # 实时统计
        stats_frame = ttk.Frame(ctrl_frame)
        stats_frame.pack(side=tk.RIGHT)

        self._hit_var = tk.StringVar(value=tr("命中: 0", "Hits: 0"))
        ttk.Label(stats_frame, textvariable=self._hit_var, font=('', 10)).pack(side=tk.LEFT, padx=10)

        self._max_err_var = tk.StringVar(value=tr("最大误差: 0", "Max Error: 0"))
        ttk.Label(stats_frame, textvariable=self._max_err_var, font=('', 10)).pack(side=tk.LEFT, padx=10)

        self._frame_var = tk.StringVar(value=tr("帧: 0/0", "Frame: 0/0"))
        ttk.Label(stats_frame, textvariable=self._frame_var, font=('', 10)).pack(side=tk.LEFT, padx=10)

        # 进度条
        self._progress = ttk.Progressbar(self, mode='determinate', maximum=100)
        self._progress.pack(fill=tk.X, padx=30, pady=5)

        # 日志区
        log_frame = ttk.LabelFrame(
            self,
            text=tr("识别日志", "OCR Log"),
            padding=5,
        )
        log_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)

        self._log_text = tk.Text(log_frame, height=12, font=('Consolas', 9), wrap=tk.WORD)
        self._log_text.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(self._log_text, command=self._log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._log_text.config(yscrollcommand=scrollbar.set)

    def _start_ocr(self):
        # 验证前置条件
        video_path = self.app.shared.get('output_video', '')
        if not video_path or not os.path.isfile(video_path):
            messagebox.showwarning(
                tr("提示", "Notice"),
                tr("请先在 Step1 选择视频并在 Step2 完成压缩", "Please select video in Step1 and compress in Step2"),
            )
            return

        roi = self.app.shared.get('roi')
        if not roi:
            messagebox.showwarning(
                tr("提示", "Notice"),
                tr("请先在 Step3 框选 ROI 区域", "Please select ROI region in Step3"),
            )
            return

        step = self._step_var.get()
        dmin = self._min_var.get()
        dmax = self._max_var.get()
        tesseract = self.app.shared.get('tesseract_cmd',
                                        r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        output_txt = self.app.shared['output_txt']

        self.app.shared['ocr_step'] = step
        self.app.shared['displacement_min'] = dmin
        self.app.shared['displacement_max'] = dmax

        self._running = True
        self._start_btn.config(state=tk.DISABLED)
        self._cancel_btn.config(state=tk.NORMAL)
        self._progress['value'] = 0
        self._log_text.delete(1.0, tk.END)
        self._log_text.insert(tk.END, tr("开始 OCR 识别...\n", "Starting OCR...\n"))

        worker = OCRWorker(video_path, roi, step, dmax, output_txt, tesseract, None)
        self.app.submit_worker(worker)
        self.app.set_status(tr("OCR 识别中...", "OCR processing..."))

    def _cancel_ocr(self):
        self.app.cancel_worker()
        self._log_text.insert(tk.END, tr("正在取消...\n", "Cancelling...\n"))

    def handle_worker_msg(self, msg):
        kind = msg[0]

        if kind == 'log':
            self._log_text.insert(tk.END, msg[1] + '\n')
            self._log_text.see(tk.END)

        elif kind == 'hit':
            _, frame_id, x_val, y_val, z_val, err = msg
            self._log_text.insert(
                tk.END,
                f"Frame{frame_id}: X={x_val:.4f} Y={y_val:.4f} Z={z_val:.4f} -> {err:.6f} mm\n"
            )
            self._log_text.see(tk.END)

        elif kind == 'stats':
            _, hits, max_err, frame_id, total = msg
            self._hit_var.set(tr(f"命中: {hits}", f"Hits: {hits}"))
            self._max_err_var.set(tr(f"最大误差: {max_err:.4f} mm", f"Max Error: {max_err:.4f} mm"))
            self._frame_var.set(tr(f"帧: {frame_id}/{total}", f"Frame: {frame_id}/{total}"))

            if total > 0:
                pct = min(100, int(frame_id / total * 100))
                self._progress['value'] = pct

        elif kind == 'done':
            self._running = False
            self._start_btn.config(state=tk.NORMAL)
            self._cancel_btn.config(state=tk.DISABLED)
            self._progress['value'] = 100

            results = msg[1]
            self.app.shared['ocr_results'] = results
            self.app.shared['ocr_done'] = True

            if results:
                self.app.mark_step_done(3)
                self.app.set_status(
                    tr(f"OCR 完成，有效结果: {len(results)} 条", f"OCR done, valid results: {len(results)}"))
            else:
                self.app.set_status(tr("OCR 完成，但无有效结果", "OCR done, but no valid results"))

        elif kind == 'error':
            self._log_text.insert(tk.END, f"[ERROR] {msg[1]}\n")
            self._log_text.see(tk.END)

    def on_enter(self):
        # 同步参数
        self._step_var.set(self.app.shared.get('ocr_step', 3))
        self._min_var.set(self.app.shared.get('displacement_min', 0.0))
        self._max_var.set(self.app.shared.get('displacement_max', 3.0))

        self._cancel_btn.config(state=tk.DISABLED)
        if not self._running:
            self._start_btn.config(state=tk.NORMAL)
            self._progress['value'] = 0

        self.app.set_status(tr("Step 4: 配置参数后点击开始识别", "Step 4: Configure and start OCR"))
